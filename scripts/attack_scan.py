import os
import json
import time
import random
import asyncio
import argparse
import logging
import multiprocessing as mp
from dataclasses import dataclass, asdict

import aiohttp

PRODUCT_QUERIES = ["", "a", "e", "lo", "ip", "alpha", "beta", "gamma"]

TIMEOUT_NORMAL = float(os.getenv("TIMEOUT_NORMAL", "2.5"))
TIMEOUT_BAD = float(os.getenv("TIMEOUT_BAD", "30"))


def setup_logging():
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(processName)s %(message)s",
    )


def default_config() -> dict:
    return {
        "targets": ["localhost:8080"],
        "scheme": "http",
        # If <= 0: run at max throughput per process (bounded by async_concurrency).
        "qps_per_process": 1.5,
        "bad_every_seconds": 20,
        # 0 => use cpu cores
        "processes_per_target": 0,
        # Number of in-flight requests per process (primary performance knob)
        "async_concurrency": 200,
        "extra_random_hits": 1,
        "random_url_paths": [
            "/",
            "/health",
            "/api/products",
            "/api/orders",
            "/api/bad",
            "/api/bad?mode=random_sort",
            "/api/bad?mode=join_bomb"
        ],
        # logging / reporting
        "report_every_seconds": 10,
        # If true, read full response body (slower, more realistic). If false, release ASAP.
        "read_response_body": False,
    }


def write_default_config(path: str) -> dict:
    cfg = default_config()
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)
        f.write("\n")
    return cfg


def load_or_create_config(path: str) -> dict:
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return write_default_config(path)


def jittered_interval(qps: float) -> float:
    if qps <= 0:
        return 0.0
    return max(0.0, (1.0 / qps) * random.uniform(0.7, 1.3))


def normalize_base_url(target: str, scheme: str) -> str:
    target = (target or "").strip()
    if not target:
        raise ValueError("Empty target")
    if "://" not in target:
        target = f"{scheme}://{target}"
    return target.rstrip("/")


def full_url(base_url: str, path_with_optional_query: str) -> str:
    p = (path_with_optional_query or "").strip()
    if not p.startswith("/"):
        p = "/" + p
    return base_url.rstrip("/") + p


@dataclass
class Stats:
    started_at: float

    total_requests: int = 0
    ok_responses: int = 0
    bad_status_responses: int = 0
    exceptions: int = 0
    timeouts: int = 0

    # rolling window
    window_started_at: float = 0.0
    window_requests: int = 0
    window_ok: int = 0
    window_bad_status: int = 0
    window_exceptions: int = 0
    window_timeouts: int = 0

    def __post_init__(self):
        if self.window_started_at == 0.0:
            self.window_started_at = self.started_at

    def reset_window(self, now: float):
        self.window_started_at = now
        self.window_requests = 0
        self.window_ok = 0
        self.window_bad_status = 0
        self.window_exceptions = 0
        self.window_timeouts = 0


def bump(stats: Stats, *, ok=False, bad_status=False, exc=False, timeout=False):
    stats.total_requests += 1
    stats.window_requests += 1
    if ok:
        stats.ok_responses += 1
        stats.window_ok += 1
    elif bad_status:
        stats.bad_status_responses += 1
        stats.window_bad_status += 1
    if exc:
        stats.exceptions += 1
        stats.window_exceptions += 1
    if timeout:
        stats.timeouts += 1
        stats.window_timeouts += 1


async def http_get(
    session: aiohttp.ClientSession,
    url: str,
    *,
    timeout: float,
    stats: Stats,
    read_body: bool,
):
    try:
        async with session.get(url, timeout=timeout) as r:
            if read_body:
                await r.read()
            else:
                await r.release()
            if 200 <= r.status < 400:
                bump(stats, ok=True)
            else:
                bump(stats, bad_status=True)
    except asyncio.TimeoutError:
        bump(stats, exc=True, timeout=True)
    except Exception:
        bump(stats, exc=True)


async def http_post(
    session: aiohttp.ClientSession,
    url: str,
    *,
    data=None,
    timeout: float,
    stats: Stats,
    read_body: bool,
):
    try:
        async with session.post(url, data=data, timeout=timeout) as r:
            if read_body:
                await r.read()
            else:
                await r.release()
            if 200 <= r.status < 400:
                bump(stats, ok=True)
            else:
                bump(stats, bad_status=True)
    except asyncio.TimeoutError:
        bump(stats, exc=True, timeout=True)
    except Exception:
        bump(stats, exc=True)


def fmt_rate(count: int, seconds: float) -> float:
    if seconds <= 0:
        return 0.0
    return count / seconds


async def reporter_loop(base_url: str, stats: Stats, every_s: int):
    log = logging.getLogger("reporter")
    while True:
        await asyncio.sleep(max(1, int(every_s)))
        now = time.time()

        window_s = max(0.001, now - stats.window_started_at)
        total_s = max(0.001, now - stats.started_at)

        log.info(
            "progress target=%s window=%.1fs rps=%.2f ok=%d bad_status=%d exc=%d timeouts=%d | total=%.1fs rps=%.2f total_req=%d ok=%d bad_status=%d exc=%d timeouts=%d",
            base_url,
            window_s,
            fmt_rate(stats.window_requests, window_s),
            stats.window_ok,
            stats.window_bad_status,
            stats.window_exceptions,
            stats.window_timeouts,
            total_s,
            fmt_rate(stats.total_requests, total_s),
            stats.total_requests,
            stats.ok_responses,
            stats.bad_status_responses,
            stats.exceptions,
            stats.timeouts,
        )

        stats.reset_window(now)


def build_next_request(base_url: str, *, now: float, last_bad: float, cfg: dict):
    bad_every = int(cfg.get("bad_every_seconds", 20))
    extra_random_hits = int(cfg.get("extra_random_hits", 1))
    random_url_paths = list(cfg.get("random_url_paths") or default_config()["random_url_paths"])

    reqs = []

    # Main selected traffic
    r = random.random()
    if r < 0.6:
        q = random.choice(PRODUCT_QUERIES)
        limit = random.choice([10, 20, 50])
        url = full_url(base_url, "/api/products")
        reqs.append(("GET", f"{url}?q={q}&limit={limit}", None, TIMEOUT_NORMAL))
    elif r < 0.85:
        reqs.append(("GET", full_url(base_url, "/api/orders"), None, TIMEOUT_NORMAL))
    else:
        payload = {
            "customer_email": f"user{random.randint(1, 999)}@example.com",
            "product_id": random.randint(1, 5000),
            "qty": random.randint(1, 5),
        }
        reqs.append(("POST", full_url(base_url, "/api/order"), payload, TIMEOUT_NORMAL))

    # Periodic bad endpoint
    new_last_bad = last_bad
    if now - last_bad >= bad_every:
        new_last_bad = now
        reqs.append(("GET", full_url(base_url, "/api/bad"), None, TIMEOUT_BAD))

    # Additional random URL hits (may include query string already)
    for _ in range(max(0, extra_random_hits)):
        path = random.choice(random_url_paths)
        t = TIMEOUT_BAD if str(path).startswith("/api/bad") else TIMEOUT_NORMAL
        reqs.append(("GET", full_url(base_url, path), None, t))

    return reqs, new_last_bad

async def worker_loop(proc_idx: int, base_url: str, cfg: dict):
    import contextlib

    log = logging.getLogger("worker")

    qps = float(cfg.get("qps_per_process", 1.5))
    async_conc = int(cfg.get("async_concurrency", 50))
    report_every = int(cfg.get("report_every_seconds", 10))
    read_body = bool(cfg.get("read_response_body", False))

    last_bad = 0.0
    stats = Stats(started_at=time.time())

    # Connector tuned for high concurrency per process.
    connector = aiohttp.TCPConnector(
        limit=async_conc,
        limit_per_host=async_conc,
        ttl_dns_cache=300,
        enable_cleanup_closed=True,
    )
    timeout = aiohttp.ClientTimeout(total=None)

    log.info(
        "starting proc=%d target=%s qps=%.3f (<=0 means max) async_conc=%d read_body=%s report_every=%ds",
        proc_idx,
        base_url,
        qps,
        async_conc,
        read_body,
        report_every,
    )

    # Optional pacing. If qps<=0, run flat-out.
    next_due = time.perf_counter()

    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        reporter = asyncio.create_task(reporter_loop(base_url, stats, report_every))
        sem = asyncio.Semaphore(async_conc)
        in_flight = set()

        async def run_one(method: str, url: str, data, tmo: float):
            try:
                if method == "GET":
                    await http_get(session, url, timeout=tmo, stats=stats, read_body=read_body)
                else:
                    await http_post(session, url, data=data, timeout=tmo, stats=stats, read_body=read_body)
            finally:
                sem.release()

        try:
            while True:
                if qps > 0:
                    nowp = time.perf_counter()
                    if nowp < next_due:
                        await asyncio.sleep(min(0.01, next_due - nowp))
                        continue
                    next_due = nowp + jittered_interval(qps)

                now = time.time()
                reqs, last_bad = build_next_request(base_url, now=now, last_bad=last_bad, cfg=cfg)

                # Always schedule at least 1 request (blocking until we have capacity).
                await sem.acquire()
                method, url, data, tmo = reqs[0]
                t = asyncio.create_task(run_one(method, url, data, tmo))
                in_flight.add(t)
                t.add_done_callback(in_flight.discard)

                # Best-effort schedule extra hits without exceeding concurrency.
                # (Uses sem._value as a fast check; it's internal but works across py3.10+.)
                for method, url, data, tmo in reqs[1:]:
                    if getattr(sem, "_value", 0) <= 0:
                        break
                    await sem.acquire()
                    t2 = asyncio.create_task(run_one(method, url, data, tmo))
                    in_flight.add(t2)
                    t2.add_done_callback(in_flight.discard)

        finally:
            reporter.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await reporter
            if in_flight:
                await asyncio.gather(*in_flight, return_exceptions=True)


def run_process(proc_idx: int, base_url: str, cfg: dict):
    setup_logging()
    asyncio.run(worker_loop(proc_idx, base_url, cfg))


def main():
    setup_logging()
    log = logging.getLogger("main")

    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--config",
        default=os.getenv("CONFIG", "config.json"),
        help="Path to JSON config. If missing, it will be created with defaults.",
    )
    args = ap.parse_args()

    cfg_path = args.config
    existed = os.path.exists(cfg_path)
    cfg = load_or_create_config(cfg_path)

    scheme = cfg.get("scheme", "http")
    targets = cfg.get("targets") or default_config()["targets"]

    cpu = os.cpu_count() or 1
    processes_per_target = int(cfg.get("processes_per_target", 0)) or cpu

    base_urls = [normalize_base_url(t, scheme) for t in targets]

    log.info("config=%s %s", cfg_path, "(loaded)" if existed else "(created default)")
    log.info("targets=%s", base_urls)
    log.info("processes_per_target=%d cpu=%d", processes_per_target, cpu)
    log.info("report_every_seconds=%s", cfg.get("report_every_seconds", 10))

    ctx = mp.get_context("spawn")  # macOS-friendly
    workers = []
    proc_idx = 0

    for base_url in base_urls:
        for _ in range(processes_per_target):
            p = ctx.Process(target=run_process, args=(proc_idx, base_url, cfg), daemon=True)
            p.start()
            workers.append(p)
            proc_idx += 1

    try:
        for p in workers:
            p.join()
    except KeyboardInterrupt:
        log.info("stopping (KeyboardInterrupt)")


if __name__ == "__main__":
    main()


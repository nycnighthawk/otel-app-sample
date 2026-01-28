import os
import sys
import time
import random
import logging
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
LOG_PATH = BASE_DIR / "cpu_hog.log"
SCHEDULER_PATH = BASE_DIR / "cpu_hog_scheduler.py"
WORKER_PATH = BASE_DIR / "cpu_hog_worker_once.py"


SCHEDULER_CODE = r"""
import os
import sys
import time
import random
import logging
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
LOG_PATH = BASE_DIR / "cpu_hog.log"
WORKER_PATH = BASE_DIR / "cpu_hog_worker_once.py"

def setup_logger() -> logging.Logger:
    logger = logging.getLogger("cpu_hog_scheduler")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        fh = logging.FileHandler(LOG_PATH, encoding="utf-8")
        fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
        fh.setFormatter(fmt)
        logger.addHandler(fh)
    return logger

def main() -> None:
    logger = setup_logger()
    cpu_count = os.cpu_count() or 1
    python = sys.executable

    duration_range = (10, 40)  # seconds hogging per run
    sleep_range = (60, 90)     # seconds between runs

    logger.info("Scheduler started pid=%s cpu_count=%s worker=%s", os.getpid(), cpu_count, WORKER_PATH)

    cycle = 0
    while True:
        cycle += 1
        interval_s = random.uniform(*sleep_range)
        time.sleep(interval_s)

        duration_s = random.uniform(*duration_range)
        logger.info("[cycle %s] launching %s workers for %.1fs after sleeping %.1fs",
                    cycle, cpu_count, duration_s, interval_s)

        for i in range(cpu_count):
            try:
                p = subprocess.Popen(
                    [python, str(WORKER_PATH), f"{duration_s:.6f}"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
                logger.info("[cycle %s] worker %s/%s launched pid=%s", cycle, i + 1, cpu_count, p.pid)
            except Exception:
                logger.exception("[cycle %s] failed launching worker %s/%s", cycle, i + 1, cpu_count)

if __name__ == "__main__":
    main()
"""


WORKER_CODE = r"""
import os
import sys
import time
import logging
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
LOG_PATH = BASE_DIR / "cpu_hog.log"

def setup_logger() -> logging.Logger:
    logger = logging.getLogger(f"cpu_hog_worker_{os.getpid()}")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        fh = logging.FileHandler(LOG_PATH, encoding="utf-8")
        fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
        fh.setFormatter(fmt)
        logger.addHandler(fh)
    return logger

def burn_cpu(duration_s: float) -> None:
    end = time.perf_counter() + duration_s
    x = 0
    while time.perf_counter() < end:
        x = (x + 1) ^ 0xABCDEF

def main() -> None:
    logger = setup_logger()
    duration_s = float(sys.argv[1]) if len(sys.argv) > 1 else 10.0
    logger.info("Worker started pid=%s duration=%.3fs", os.getpid(), duration_s)
    burn_cpu(duration_s)
    logger.info("Worker finished pid=%s", os.getpid())

if __name__ == "__main__":
    main()
"""


def setup_logger() -> logging.Logger:
    logger = logging.getLogger("cpu_hog_launcher")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        fh = logging.FileHandler(LOG_PATH, encoding="utf-8")
        fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
        fh.setFormatter(fmt)
        logger.addHandler(fh)
    return logger


def ensure_file(path: Path, content: str) -> None:
    if not path.exists():
        path.write_text(content, encoding="utf-8")


def spawn_detached_scheduler(python: str, scheduler_path: Path) -> int:
    # Fully detach so run-command can return immediately.
    # DETACHED_PROCESS prevents a console; CREATE_NEW_PROCESS_GROUP helps detachment.
    creationflags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
    p = subprocess.Popen(
        [python, str(scheduler_path)],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
        creationflags=creationflags,
    )
    return p.pid


def main() -> None:
    logger = setup_logger()
    python = sys.executable

    ensure_file(WORKER_PATH, WORKER_CODE)
    ensure_file(SCHEDULER_PATH, SCHEDULER_CODE)

    pid = spawn_detached_scheduler(python, SCHEDULER_PATH)
    logger.info("Launcher exiting; spawned scheduler pid=%s log=%s", pid, LOG_PATH)


if __name__ == "__main__":
    main()

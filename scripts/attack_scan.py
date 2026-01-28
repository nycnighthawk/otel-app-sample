import os
import random
import time
import requests

TARGET_BASE_URL = os.getenv("TARGET_BASE_URL", "http://localhost:8080").rstrip("/")
BAD_EVERY_SECONDS = int(os.getenv("BAD_EVERY_SECONDS", "20"))
QPS = float(os.getenv("QPS", "1.5"))
BAD_QUERY_MODE = os.getenv("BAD_QUERY_MODE", "like")

PRODUCT_QUERIES = ["", "a", "e", "lo", "ip", "alpha", "beta", "gamma"]


def sleep_for_qps():
    if QPS <= 0:
        return
    time.sleep(max(0.0, (1.0 / QPS) * random.uniform(0.7, 1.3)))


def main():
    print("Legit traffic generator")
    print(f"  TARGET_BASE_URL={TARGET_BASE_URL}")
    print(f"  QPS={QPS}")
    print(f"  BAD_EVERY_SECONDS={BAD_EVERY_SECONDS}")
    print(f"  (Note) App selects bad query via server env BAD_QUERY_MODE; this script just calls /api/bad periodically.")
    print(f"  (Info) Script env BAD_QUERY_MODE={BAD_QUERY_MODE} (not used by server unless you also set it there)")

    last_bad = 0.0

    while True:
        now = time.time()
        try:
            # Normal traffic
            if random.random() < 0.6:
                q = random.choice(PRODUCT_QUERIES)
                limit = random.choice([10, 20, 50])
                requests.get(f"{TARGET_BASE_URL}/api/products", params={"q": q, "limit": limit}, timeout=2.5)
            elif random.random() < 0.85:
                requests.get(f"{TARGET_BASE_URL}/api/orders", timeout=2.5)
            else:
                # Create some orders
                payload = {
                    "customer_email": f"user{random.randint(1,999)}@example.com",
                    "product_id": random.randint(1, 5000),
                    "qty": random.randint(1, 5),
                }
                requests.post(f"{TARGET_BASE_URL}/api/order", data=payload, timeout=2.5)

            # Periodic bad endpoint
            if now - last_bad >= BAD_EVERY_SECONDS:
                last_bad = now
                requests.get(f"{TARGET_BASE_URL}/api/bad", timeout=30)

        except Exception:
            pass

        sleep_for_qps()


if __name__ == "__main__":
    main()

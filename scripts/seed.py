import os
import random
import string
import time
import psycopg2

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://shop:shop@localhost:5432/shop")

# Products
SEED_ROWS = int(os.getenv("SEED_ROWS", "20000"))

# Orders
SEED_ORDERS = int(os.getenv("SEED_ORDERS", "2000"))
ORDER_ITEMS_MIN = int(os.getenv("ORDER_ITEMS_MIN", "1"))
ORDER_ITEMS_MAX = int(os.getenv("ORDER_ITEMS_MAX", "4"))
ORDER_QTY_MIN = int(os.getenv("ORDER_QTY_MIN", "1"))
ORDER_QTY_MAX = int(os.getenv("ORDER_QTY_MAX", "5"))

CATEGORIES = ["alpha", "beta", "gamma", "delta", "epsilon", "zeta", "eta", "theta"]


def rand_word(n: int) -> str:
    return "".join(random.choice(string.ascii_lowercase) for _ in range(n))


def main():
    print(f"Seeding into {DATABASE_URL}")
    print(f"  products: SEED_ROWS={SEED_ROWS}")
    print(f"  orders:   SEED_ORDERS={SEED_ORDERS} items_per_order=[{ORDER_ITEMS_MIN},{ORDER_ITEMS_MAX}]")

    t0 = time.time()

    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = False
    cur = conn.cursor()

    # ---- Products
    cur.execute("SELECT COUNT(*) FROM products")
    existing_products = cur.fetchone()[0]
    if existing_products > 0:
        print(f"products already has {existing_products} rows; will append more")

    batch = 1000
    lorem = (
        "lorem ipsum dolor sit amet consectetur adipiscing elit sed do eiusmod tempor "
        "incididunt ut labore et dolore magna aliqua"
    )

    for i in range(SEED_ROWS):
        sku = f"SKU-{existing_products + i + 1:08d}"
        name = f"{rand_word(6)} {rand_word(7)}"
        category = random.choice(CATEGORIES)
        description = f"{lorem} | {category} | " + (" " + lorem) * random.randint(2, 6)
        price_cents = random.randint(199, 19999)

        cur.execute(
            "INSERT INTO products (sku, name, category, description, price_cents) VALUES (%s, %s, %s, %s, %s)",
            (sku, name, category, description, price_cents),
        )

        if (i + 1) % batch == 0:
            conn.commit()
            print(f"  inserted products {i+1}/{SEED_ROWS}")

    conn.commit()

    # Refresh product id range for order generation
    cur.execute("SELECT COALESCE(MIN(id), 0), COALESCE(MAX(id), 0), COUNT(*) FROM products")
    min_id, max_id, total_products = cur.fetchone()
    if total_products == 0:
        raise RuntimeError("No products in DB after seeding; cannot create orders.")

    # ---- Orders + Order Items
    cur.execute("SELECT COUNT(*) FROM orders")
    existing_orders = cur.fetchone()[0]
    if existing_orders > 0:
        print(f"orders already has {existing_orders} rows; will append more")

    order_batch = 200

    for i in range(SEED_ORDERS):
        email = f"user{random.randint(1, 200000)}@example.com"
        cur.execute("INSERT INTO orders (customer_email) VALUES (%s) RETURNING id", (email,))
        order_id = cur.fetchone()[0]

        items_n = random.randint(max(1, ORDER_ITEMS_MIN), max(1, ORDER_ITEMS_MAX))
        used = set()

        for _ in range(items_n):
            # avoid duplicates in a single order
            for _try in range(10):
                pid = random.randint(int(min_id), int(max_id))
                if pid not in used:
                    used.add(pid)
                    break

            qty = random.randint(max(1, ORDER_QTY_MIN), max(1, ORDER_QTY_MAX))
            cur.execute(
                "INSERT INTO order_items (order_id, product_id, qty) VALUES (%s, %s, %s)",
                (order_id, pid, qty),
            )

        if (i + 1) % order_batch == 0:
            conn.commit()
            print(f"  inserted orders {i+1}/{SEED_ORDERS}")

    conn.commit()

    cur.close()
    conn.close()

    dt = time.time() - t0
    print(f"Done in {dt:.1f}s")


if __name__ == "__main__":
    main()

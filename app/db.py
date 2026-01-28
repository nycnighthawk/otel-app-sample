import os
import psycopg2
import psycopg2.extras

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://shop:shop@127.0.0.1:5432/shop",
)


def get_conn():
    return psycopg2.connect(DATABASE_URL)


def _fetchall_dict(cur):
    return [dict(r) for r in cur.fetchall()]


def get_products(q: str | None, limit: int):
    q = (q or "").strip()
    limit = max(1, min(int(limit), 100))

    sql = """
        SELECT id, sku, name, price_cents
        FROM products
        WHERE (%s = '' OR name ILIKE ('%%' || %s || '%%'))
        ORDER BY id DESC
        LIMIT %s
    """
    with get_conn() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql, (q, q, limit))
        return _fetchall_dict(cur)


def create_order(customer_email: str, product_id: int, qty: int):
    qty = max(1, min(int(qty), 50))
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO orders (customer_email) VALUES (%s) RETURNING id",
            (customer_email,),
        )
        order_id = cur.fetchone()[0]
        cur.execute(
            """
            INSERT INTO order_items (order_id, product_id, qty)
            VALUES (%s, %s, %s)
            """,
            (order_id, int(product_id), qty),
        )
        return order_id


def list_orders(limit: int = 50):
    limit = max(1, min(int(limit), 200))
    sql = """
      SELECT
        o.id,
        o.created_at,
        o.customer_email,
        COALESCE(SUM(oi.qty * p.price_cents), 0) AS total_cents,
        COALESCE(SUM(oi.qty), 0) AS total_items
      FROM orders o
      LEFT JOIN order_items oi ON oi.order_id = o.id
      LEFT JOIN products p ON p.id = oi.product_id
      GROUP BY o.id
      ORDER BY o.id DESC
      LIMIT %s
    """
    with get_conn() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql, (limit,))
        return _fetchall_dict(cur)


def run_bad_query(mode: str):
    mode = (mode or "like").strip().lower()

    LIKE_MIN_COUNT = int(os.getenv("BAD_LIKE_MIN_COUNT", "1"))
    LIKE_PATTERN = os.getenv("BAD_LIKE_PATTERN", "%lorem%")

    # random_sort: force heavy per-row sort key + big sort
    RANDOM_SORT_POOL = int(os.getenv("BAD_RANDOM_POOL", "500000"))
    RANDOM_SORT_KEY_BYTES = int(os.getenv("BAD_RANDOM_KEY_BYTES", "256"))

    # join_bomb: bounded pair explosion (guaranteed to finish)
    JOIN_TOP_CATS = int(os.getenv("BAD_JOIN_TOP_CATS", "4"))
    JOIN_MAX_ROWS_PER_CAT = int(os.getenv("BAD_JOIN_MAX_PER_CAT", "12000"))
    JOIN_FANOUT = int(os.getenv("BAD_JOIN_FANOUT", "80"))

    with get_conn() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        if mode == "like":
            cur.execute(
                """
                SELECT category, COUNT(*) AS matches
                FROM products
                WHERE description ILIKE %s
                GROUP BY category
                HAVING COUNT(*) >= %s
                ORDER BY matches DESC
                """,
                (LIKE_PATTERN, LIKE_MIN_COUNT),
            )
            return _fetchall_dict(cur)

        if mode == "random_sort":
            # This is intentionally nasty:
            # - materialize N rows
            # - compute a large text sort key per row (md5 repeated)
            # - sort by that key (likely spills to disk)
            cur.execute(
                """
                WITH pool AS (
                  SELECT id, sku, category, description
                  FROM products
                  LIMIT %s
                ),
                keyed AS (
                  SELECT
                    id,
                    sku,
                    category,
                    repeat(md5(description), %s) AS sort_key
                  FROM pool
                )
                SELECT id, sku, category
                FROM keyed
                ORDER BY sort_key
                LIMIT 50
                """,
                (RANDOM_SORT_POOL, max(1, RANDOM_SORT_KEY_BYTES // 32)),
            )
            return _fetchall_dict(cur)

        if mode == "join_bomb":
            # Bounded join: for each row, join to the next JOIN_FANOUT rows in same category.
            # Work per category is ~JOIN_MAX_ROWS_PER_CAT * JOIN_FANOUT (linear, not quadratic).
            cur.execute(
                """
                WITH topcats AS (
                  SELECT category
                  FROM products
                  GROUP BY category
                  ORDER BY COUNT(*) DESC
                  LIMIT %s
                ),
                ranked AS (
                  SELECT
                    id,
                    category,
                    row_number() OVER (PARTITION BY category ORDER BY id) AS rn
                  FROM products
                  WHERE category IN (SELECT category FROM topcats)
                ),
                capped AS (
                  SELECT * FROM ranked WHERE rn <= %s
                ),
                pairs AS (
                  SELECT
                    p1.category AS category,
                    p1.id AS left_id,
                    p2.id AS right_id
                  FROM capped p1
                  JOIN capped p2
                    ON p1.category = p2.category
                   AND p2.rn BETWEEN p1.rn AND (p1.rn + %s)
                )
                SELECT
                  category,
                  COUNT(*) AS pair_count,
                  MIN(left_id) AS min_left_id,
                  MAX(right_id) AS max_right_id
                FROM pairs
                GROUP BY category
                ORDER BY pair_count DESC
                """,
                (JOIN_TOP_CATS, JOIN_MAX_ROWS_PER_CAT, JOIN_FANOUT),
            )
            return _fetchall_dict(cur)

        cur.execute(
            """
            SELECT category, COUNT(*) AS matches
            FROM products
            WHERE description ILIKE %s
            GROUP BY category
            ORDER BY matches DESC
            """,
            (LIKE_PATTERN,),
        )
        return _fetchall_dict(cur)


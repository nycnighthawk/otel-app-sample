export DATABASE_URL="postgresql://shop:shop@127.0.0.1:5432/shop"

psql "$DATABASE_URL" -v ON_ERROR_STOP=1 <<'SQL'
TRUNCATE TABLE order_items, orders, products RESTART IDENTITY;
SQL

SEED_ROWS=500000 SEED_ORDERS=20000 .venv/bin/python3 scripts/seed.py

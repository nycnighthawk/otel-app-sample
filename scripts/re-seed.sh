export DATABASE_URL="postgresql://shop:shop@127.0.0.1:5432/shop"

psql "$DATABASE_URL" -v ON_ERROR_STOP=1 <<'SQL'
TRUNCATE TABLE order_items, orders, products RESTART IDENTITY;
SQL

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
if [ -x "$SCRIPT_DIR/../.venv/bin/python" ]; then
  echo "Virtual environment exists."
else
  echo "Virtual environment not found."
  python3.12 -m venv "${SCRIPT_DIR}/../.venv"
fi

python_exe="${SCRIPT_DIR}/../.venv/bin/python"

"${python_exe}" -m pip install --upgrade pip
"${python_exe}" -m pip install --upgrade psycopg2-binary

SEED_ROWS=500000 SEED_ORDERS=20000 "${python_exe}" "${SCRIPT_DIR}/seed.py"

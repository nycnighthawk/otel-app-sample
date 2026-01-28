import os
from pathlib import Path

from fastapi import FastAPI, Request, Form, Query
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from db import get_products, create_order, list_orders, run_bad_query

BASE_DIR = Path(__file__).resolve().parent

# Default mode from env, but can be overridden at runtime via API.
DEFAULT_BAD_QUERY_MODE = os.getenv("BAD_QUERY_MODE", "like").strip().lower()

app = FastAPI(title="Hackathon Shop (Uninstrumented)")

app.state.bad_query_mode = DEFAULT_BAD_QUERY_MODE

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def get_bad_mode(requested: str | None) -> str:
    """
    Mode precedence:
      1) explicit query param `mode=...` (per-request)
      2) runtime setting (set via POST /api/bad/mode)
      3) env default
    """
    if requested:
        return requested.strip().lower()
    mode = getattr(app.state, "bad_query_mode", None)
    return (mode or DEFAULT_BAD_QUERY_MODE).strip().lower()


@app.get("/api/health")
def health():
    return {"ok": True}


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "bad_query_mode": getattr(app.state, "bad_query_mode", DEFAULT_BAD_QUERY_MODE),
        },
    )


@app.get("/api/products")
def api_products(q: str = "", limit: int = 20):
    return {"items": get_products(q=q, limit=limit), "q": q, "limit": limit}


@app.post("/api/order")
def api_order(
    request: Request,
    customer_email: str = Form(default=""),
    product_id: int = Form(default=0),
    qty: int = Form(default=1),
):
    if not customer_email or product_id <= 0:
        return JSONResponse({"error": "customer_email and product_id required"}, status_code=400)

    order_id = create_order(customer_email=customer_email, product_id=product_id, qty=qty)

    if "text/html" in (request.headers.get("accept", "")):
        return RedirectResponse(url="/", status_code=303)

    return {"ok": True, "order_id": order_id}


@app.get("/api/orders")
def api_orders(limit: int = 50):
    return {"items": list_orders(limit=limit)}


@app.get("/api/bad")
def api_bad(
    mode: str | None = Query(default=None, description="Override bad query mode for this request"),
):
    """
    Intentionally slow DB query. Returns a small sample so callers can see what it did.
    Modes:
      - like
      - random_sort
      - join_bomb
    """
    effective_mode = get_bad_mode(mode)
    rows = run_bad_query(effective_mode)

    # Return a small sample of the actual rows to prove behavior differs per mode
    sample = rows[:10]
    return {
        "mode": effective_mode,
        "rows": len(rows),
        "sample": sample,
    }


@app.get("/api/bad/mode")
def api_bad_mode_get():
    return {
        "bad_query_mode": getattr(app.state, "bad_query_mode", DEFAULT_BAD_QUERY_MODE),
        "default": DEFAULT_BAD_QUERY_MODE,
        "allowed": ["like", "random_sort", "join_bomb"],
    }


@app.post("/api/bad/mode")
def api_bad_mode_set(mode: str = Form(default="")):
    mode = (mode or "").strip().lower()
    allowed = {"like", "random_sort", "join_bomb"}
    if mode not in allowed:
        return JSONResponse({"error": "invalid mode", "allowed": sorted(allowed)}, status_code=400)

    app.state.bad_query_mode = mode
    return {"ok": True, "bad_query_mode": mode}

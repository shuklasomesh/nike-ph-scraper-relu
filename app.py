"""
FastAPI web app — displays Nike PH scraped product data from Supabase.
Falls back to local CSV if Supabase is not configured.
"""

import csv
import os
from pathlib import Path

from fastapi import FastAPI, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI(title="Nike PH Products Dashboard")

BASE_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
CSV_PATH = os.environ.get("CSV_PATH", str(BASE_DIR.parent / "nike_products.csv"))
TABLE = "nike_products"

_sb_client = None


def get_supabase():
    global _sb_client
    if SUPABASE_URL and SUPABASE_KEY and _sb_client is None:
        from supabase import create_client
        _sb_client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _sb_client


def load_from_csv():
    rows = []
    if not os.path.exists(CSV_PATH):
        return rows
    with open(CSV_PATH, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append(r)
    return rows


@app.get("/", response_class=HTMLResponse)
async def index(
    request: Request,
    page: int = Query(1, ge=1),
    q: str = Query("", alias="q"),
):
    per_page = 20
    search = q.strip()

    sb = get_supabase()
    if sb:
        query = sb.table(TABLE).select("*", count="exact")
        if search:
            query = query.ilike("Product_Name", f"%{search}%")
        query = query.range((page - 1) * per_page, page * per_page - 1)
        resp = query.execute()
        products = resp.data or []
        total = resp.count or 0
    else:
        all_rows = load_from_csv()
        if search:
            all_rows = [r for r in all_rows if search.lower() in r.get("Product_Name", "").lower()]
        total = len(all_rows)
        products = all_rows[(page - 1) * per_page : page * per_page]

    total_pages = max(1, (total + per_page - 1) // per_page)
    return templates.TemplateResponse(
        request,
        "index.html",
        context={
            "products": products,
            "page": page,
            "total_pages": total_pages,
            "total": total,
            "search": search,
        },
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)

import sqlite3
import secrets
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from database import get_db, init_db

BASE_DIR = Path(__file__).parent


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Good Basket", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")
CART_COOKIE = "good_basket_id"
CART_COOKIE_MAX_AGE = 60 * 60 * 24 * 60


def get_cart_id(request: Request, db: sqlite3.Connection) -> str:
    cart_id = request.cookies.get(CART_COOKIE)
    if cart_id:
        return cart_id
    cart_id = secrets.token_urlsafe(32)
    with db:
        db.execute("UPDATE cart_items SET cart_id = ? WHERE cart_id = 'legacy'", (cart_id,))
    return cart_id


def set_cart_cookie(response, request: Request, cart_id: str):
    if not request.cookies.get(CART_COOKIE):
        response.set_cookie(
            CART_COOKIE,
            cart_id,
            max_age=CART_COOKIE_MAX_AGE,
            httponly=True,
            secure=request.url.scheme == "https",
            samesite="lax",
        )
    return response


def cart_count(db: sqlite3.Connection, cart_id: str) -> int:
    return db.execute(
        "SELECT COALESCE(SUM(quantity), 0) FROM cart_items WHERE cart_id = ?", (cart_id,)
    ).fetchone()[0]


@app.get("/", response_class=HTMLResponse)
def index(
    request: Request,
    q: str = "",
    category: str = "",
    db: sqlite3.Connection = Depends(get_db),
):
    sql = "SELECT * FROM products WHERE 1=1"
    params: list[str] = []
    if q.strip():
        sql += " AND (name LIKE ? OR description LIKE ?)"
        params.extend((f"%{q.strip()}%", f"%{q.strip()}%"))
    if category:
        sql += " AND category = ?"
        params.append(category)
    cart_id = get_cart_id(request, db)
    products = db.execute(sql + " ORDER BY category, name", params).fetchall()
    categories = [row[0] for row in db.execute(
        "SELECT DISTINCT category FROM products ORDER BY category"
    )]
    total = db.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    response = templates.TemplateResponse(request, "index.html", {
        "products": products,
        "categories": categories,
        "q": q,
        "active_category": category,
        "total": total,
        "cart_count": cart_count(db, cart_id),
    })
    return set_cart_cookie(response, request, cart_id)


@app.post("/cart/add/{product_id}")
def add_to_cart(request: Request, product_id: int, db: sqlite3.Connection = Depends(get_db)):
    cart_id = get_cart_id(request, db)
    product = db.execute("SELECT id FROM products WHERE id = ?", (product_id,)).fetchone()
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    with db:
        db.execute(
            "INSERT INTO cart_items (cart_id, product_id, quantity) VALUES (?, ?, 1) "
            "ON CONFLICT(cart_id, product_id) DO UPDATE SET quantity = quantity + 1",
            (cart_id, product_id),
        )
    response = RedirectResponse("/cart?added=1", status_code=303)
    return set_cart_cookie(response, request, cart_id)


@app.get("/cart", response_class=HTMLResponse)
def view_cart(request: Request, added: bool = False, db: sqlite3.Connection = Depends(get_db)):
    cart_id = get_cart_id(request, db)
    items = db.execute(
        "SELECT p.id AS product_id, p.name, p.category, p.unit, p.price_cents, p.image_url, "
        "ci.quantity, p.price_cents * ci.quantity AS line_total_cents "
        "FROM cart_items ci JOIN products p ON p.id = ci.product_id "
        "WHERE ci.cart_id = ? ORDER BY p.name",
        (cart_id,),
    ).fetchall()
    subtotal = sum(item["line_total_cents"] for item in items)
    response = templates.TemplateResponse(request, "cart.html", {
        "items": items,
        "subtotal": subtotal,
        "added": added,
        "cart_count": cart_count(db, cart_id),
    })
    return set_cart_cookie(response, request, cart_id)


@app.post("/cart/items/{product_id}")
def update_cart_item(
    request: Request,
    product_id: int,
    quantity: int = Form(...),
    db: sqlite3.Connection = Depends(get_db),
):
    cart_id = get_cart_id(request, db)
    if not 0 <= quantity <= 99:
        raise HTTPException(status_code=400, detail="Quantity must be between 0 and 99")
    with db:
        if quantity == 0:
            db.execute(
                "DELETE FROM cart_items WHERE cart_id = ? AND product_id = ?",
                (cart_id, product_id),
            )
        else:
            product = db.execute("SELECT id FROM products WHERE id = ?", (product_id,)).fetchone()
            if product is None:
                raise HTTPException(status_code=404, detail="Product not found")
            db.execute(
                "INSERT INTO cart_items (cart_id, product_id, quantity) VALUES (?, ?, ?) "
                "ON CONFLICT(cart_id, product_id) DO UPDATE SET quantity = excluded.quantity",
                (cart_id, product_id, quantity),
            )
    response = RedirectResponse("/cart", status_code=303)
    return set_cart_cookie(response, request, cart_id)


@app.post("/cart/clear")
def clear_cart(request: Request, db: sqlite3.Connection = Depends(get_db)):
    cart_id = get_cart_id(request, db)
    with db:
        db.execute("DELETE FROM cart_items WHERE cart_id = ?", (cart_id,))
    response = RedirectResponse("/cart", status_code=303)
    return set_cart_cookie(response, request, cart_id)


@app.exception_handler(404)
async def not_found(request: Request, exc: HTTPException):
    return templates.TemplateResponse(request, "404.html", {}, status_code=404)
import os
import sqlite3
from pathlib import Path

DB_PATH = Path(os.environ.get("DATABASE_PATH", Path(__file__).parent / "groceries.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS products (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    category    TEXT NOT NULL,
    unit        TEXT NOT NULL,
    price_cents INTEGER NOT NULL CHECK (price_cents >= 0),
    description TEXT NOT NULL,
    image_url   TEXT NOT NULL
);
"""

NEW_CART_SCHEMA = """
CREATE TABLE IF NOT EXISTS cart_items (
    cart_id    TEXT NOT NULL,
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    quantity   INTEGER NOT NULL CHECK (quantity BETWEEN 1 AND 99),
    PRIMARY KEY (cart_id, product_id)
);
"""

SEED_PRODUCTS = [
    ("Sweet strawberries", "Produce", "250 g punnet", 399,
     "Ripe, fragrant berries picked at their sweetest. Lovely by the handful or over breakfast.",
     "https://images.unsplash.com/photo-1464965911861-746a04b4bca6?auto=format&fit=crop&w=900&q=85"),
    ("Ripe avocados", "Produce", "each", 149,
     "Creamy, ready-to-eat avocados with a buttery texture and just the right amount of give.",
     "https://images.unsplash.com/photo-1523049673857-eb18f1d7b578?auto=format&fit=crop&w=900&q=85"),
    ("Heirloom tomatoes", "Produce", "500 g box", 450,
     "A colorful mix of sweet, juicy tomatoes. Best with olive oil, flaky salt and good bread.",
     "https://images.unsplash.com/photo-1546094096-0df4bcaaa337?auto=format&fit=crop&w=900&q=85"),
    ("Baby spinach", "Produce", "120 g bag", 325,
     "Tender young leaves, washed and ready for salads, quick pastas or a green smoothie.",
     "https://images.unsplash.com/photo-1576045057995-568f588f82fb?auto=format&fit=crop&w=900&q=85"),
    ("Country sourdough", "Bakery", "loaf", 575,
     "Slow-fermented with a crisp golden crust and a soft, tangy center. Baked fresh this morning.",
    "https://images.unsplash.com/photo-1509440159596-0249088772ff?auto=format&fit=crop&w=900&q=85"),
    ("Free-range eggs", "Dairy & Eggs", "12 eggs", 650,
     "Rich golden yolks from happy, free-roaming hens. A versatile kitchen staple.",
     "https://images.unsplash.com/photo-1506976785307-8732e854ad03?auto=format&fit=crop&w=900&q=85"),
    ("Whole milk", "Dairy & Eggs", "1 litre", 425,
     "Creamy whole milk from local family farms, gently pasteurized and full of goodness.",
     "https://images.unsplash.com/photo-1563636619-e9143da7973b?auto=format&fit=crop&w=900&q=85"),
    ("Greek-style yogurt", "Dairy & Eggs", "500 g tub", 550,
     "Thick, silky yogurt with a gentle tang. Delicious with berries, honey or a spoon on its own.",
     "https://images.unsplash.com/photo-1488477181946-6428a0291777?auto=format&fit=crop&w=900&q=85"),
    ("Cold-pressed olive oil", "Pantry", "500 ml bottle", 1290,
     "Peppery extra-virgin olive oil from early-harvest olives. A bright finish for everyday meals.",
     "https://images.unsplash.com/photo-1474979266404-7eaacbcd87c5?auto=format&fit=crop&w=900&q=85"),
    ("Roasted almond butter", "Pantry", "250 g jar", 825,
     "Just roasted almonds, stone-ground into a smooth, naturally sweet spread. Nothing else added.",
     "https://images.unsplash.com/photo-1505576633757-0ac1084af824?auto=format&fit=crop&w=900&q=85"),
    ("Dark chocolate", "Snacks", "80 g bar", 350,
     "Deep, balanced 70% cacao with notes of red fruit. A little square goes a long way.",
     "https://images.unsplash.com/photo-1511381939415-e44015466834?auto=format&fit=crop&w=900&q=85"),
    ("Lemon sparkling water", "Drinks", "4 cans", 440,
     "Crisp bubbles with a squeeze of real lemon. Refreshing, bright and never too sweet.",
    "https://images.unsplash.com/photo-1544145945-f90425340c7e?auto=format&fit=crop&w=900&q=85"),
]

IMAGE_REFRESHES = (
    ("Country sourdough", "https://images.unsplash.com/photo-1585478259715-876acc5be8eb?auto=format&fit=crop&w=900&q=85",
    "https://images.unsplash.com/photo-1509440159596-0249088772ff?auto=format&fit=crop&w=900&q=85"),
    ("Lemon sparkling water", "https://images.unsplash.com/photo-1532634896-26909d0d4b65?auto=format&fit=crop&w=900&q=85",
     "https://images.unsplash.com/photo-1544145945-f90425340c7e?auto=format&fit=crop&w=900&q=85"),
    ("Lemon sparkling water", "https://images.unsplash.com/photo-1513558161293-cdaf765edfd7?auto=format&fit=crop&w=900&q=85",
        "https://images.unsplash.com/photo-1544145945-f90425340c7e?auto=format&fit=crop&w=900&q=85"),
)


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db() -> None:
    with get_connection() as connection:
        connection.executescript(SCHEMA)
        cart_table = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'cart_items'"
        ).fetchone()
        if cart_table:
            columns = {row[1] for row in connection.execute("PRAGMA table_info(cart_items)")}
            if "cart_id" not in columns:
                connection.execute("ALTER TABLE cart_items RENAME TO legacy_cart_items")
        connection.executescript(NEW_CART_SCHEMA)
        legacy_table = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'legacy_cart_items'"
        ).fetchone()
        if legacy_table:
            connection.execute(
                "INSERT INTO cart_items (cart_id, product_id, quantity) "
                "SELECT 'legacy', product_id, quantity FROM legacy_cart_items"
            )
            connection.execute("DROP TABLE legacy_cart_items")
        product_count = connection.execute("SELECT COUNT(*) FROM products").fetchone()[0]
        if product_count == 0:
            connection.executemany(
                "INSERT INTO products (name, category, unit, price_cents, description, image_url) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                SEED_PRODUCTS,
            )
        connection.executemany(
            "UPDATE products SET image_url = ? WHERE name = ? AND image_url = ?",
            [(new_url, name, old_url) for name, old_url, new_url in IMAGE_REFRESHES],
        )


def get_db():
    connection = get_connection()
    try:
        yield connection
    finally:
        connection.close()
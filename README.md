# Good Basket

A small grocery storefront built with FastAPI, Jinja2 and SQLite. Browse and search the seeded grocery catalog, add products to your basket, and update quantities. Basket contents are stored in `groceries.db` and remain available after restarting the app.

## Run

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn main:app --reload
```

Open http://127.0.0.1:8000. The catalog and database are initialized automatically on first start. Delete `groceries.db` to reset the sample catalog and basket.

## Deploy on Render

The included `render.yaml` configures a Render web service and a 1 GB persistent disk for SQLite. Persistent disks require a paid Render web-service plan; the Blueprint uses the `0.5c-512mb` plan.

1. Push this project to a GitHub repository.
2. In Render, choose **New → Blueprint** and connect that repository.
3. Review the service and disk plan, then apply the Blueprint.

Render assigns the public `https://good-basket.onrender.com` URL after the service is created (the final hostname may differ if that name is already taken). The SQLite file is stored at `/var/data/groceries.db` on the persistent disk. Each visitor's basket is kept separate in their browser.

## Pages

| Route | Purpose |
| --- | --- |
| `/` | Browse, search and filter groceries |
| `POST /cart/add/{product_id}` | Add one product and open the basket |
| `/cart` | View basket contents and subtotal |
| `POST /cart/items/{product_id}` | Set an item's quantity or remove it |
| `POST /cart/clear` | Empty the basket |

## Files

- `main.py`: FastAPI routes and cart behavior
- `database.py`: SQLite schema, sample catalog and request connections
- `templates/`: Jinja2 storefront and basket pages
- `static/css/shop.css`: Responsive storefront styling
"""SQLite access shared by the API routes and the agent tools."""

import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "campus_customs.db"
SIZE_ORDER = ["XS", "S", "M", "L", "XL", "XXL"]

PRODUCT_SELECT = """
    SELECT c.*, COALESCE(SUM(i.quantity), 0) AS total_stock,
           GROUP_CONCAT(CASE WHEN i.quantity > 0 THEN i.size END) AS sizes_in_stock
    FROM catalogue c LEFT JOIN inventory i ON i.product_id = c.product_id
"""


def get_db(readonly: bool = False) -> sqlite3.Connection:
    """Open the database. Catalogue/inventory reads (everything the agent can reach)
    use readonly=True, so no tool or injected instruction can modify data."""
    uri = f"{DB_PATH.as_uri()}?mode=ro" if readonly else DB_PATH.as_uri()
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def category_of(garment_type: str) -> str:
    """Collapse the 22 free-text garment types into six shopper-facing categories."""
    gt = garment_type.lower()
    if "t-shirt" in gt:
        return "t-shirt"
    if "quarter-zip" in gt:
        return "quarter-zip"
    if "hood" in gt:
        return "hoodie"
    if "jacket" in gt:
        return "jacket"
    if "long-sleeve" in gt:
        return "long-sleeve shirt"
    return "sweatshirt"  # crewneck, raglan crewneck, mockneck


def product_from_row(row: sqlite3.Row) -> dict:
    """Convert a catalogue row into the JSON shape the front end uses."""
    return {
        "product_id": row["product_id"],
        "name": row["name"],
        "garment_type": row["garment_type"],
        "description": row["description"],
        "colors": json.loads(row["colors"]),
        "search_tags": json.loads(row["search_tags"]),
        "price": row["price"],
        # image_file_path is relative to data/, e.g. "products/xyz.jpg"
        "image_url": "/images/" + Path(row["image_file_path"]).name,
        "total_stock": row["total_stock"],
        "category": category_of(row["garment_type"]),
        "sizes_in_stock": [s for s in SIZE_ORDER if s in (row["sizes_in_stock"] or "").split(",")],
    }


def all_products() -> list[dict]:
    conn = get_db(readonly=True)
    try:
        rows = conn.execute(PRODUCT_SELECT + " GROUP BY c.product_id ORDER BY c.name").fetchall()
    finally:
        conn.close()
    return [product_from_row(r) for r in rows]


def products_by_ids(product_ids: list[str]) -> list[dict]:
    """Products for the given ids, in the order given; unknown ids are skipped."""
    if not product_ids:
        return []
    conn = get_db(readonly=True)
    try:
        marks = ",".join("?" * len(product_ids))
        rows = conn.execute(
            PRODUCT_SELECT + f" WHERE c.product_id IN ({marks}) GROUP BY c.product_id",
            product_ids,
        ).fetchall()
    finally:
        conn.close()
    found = {r["product_id"]: product_from_row(r) for r in rows}
    return [found[pid] for pid in dict.fromkeys(product_ids) if pid in found]


def product_with_inventory(product_id: str) -> dict | None:
    products = products_by_ids([product_id])
    if not products:
        return None
    conn = get_db(readonly=True)
    try:
        stock = conn.execute(
            "SELECT size, quantity FROM inventory WHERE product_id = ?", (product_id,)
        ).fetchall()
    finally:
        conn.close()
    product = products[0]
    product["inventory"] = sorted(
        ({"size": s["size"], "quantity": s["quantity"]} for s in stock),
        key=lambda s: SIZE_ORDER.index(s["size"]) if s["size"] in SIZE_ORDER else 99,
    )
    return product


def all_inventory() -> dict[str, dict[str, int]]:
    """{product_id: {size: quantity}} for every product, in one query."""
    conn = get_db(readonly=True)
    try:
        rows = conn.execute("SELECT product_id, size, quantity FROM inventory").fetchall()
    finally:
        conn.close()
    stock: dict[str, dict[str, int]] = {}
    for r in rows:
        stock.setdefault(r["product_id"], {})[r["size"]] = r["quantity"]
    return stock

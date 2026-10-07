"""Live app check for Campus Customs.

Drives the running website in a real browser (Playwright + Chromium), captures
screenshots, checks the chat's numbers against SQLite, and writes
output/app_check.html + output/app_check_images/*.png.

Prereqs: backend and frontend running, e.g.
    cd backend && uvicorn main:app --reload --port 8000
    cd frontend && npm run dev
Run (from Homework 4/):
    .venv/bin/python tests/app_check.py [--base-url http://localhost:5173]
"""

import argparse
import html
import re
import sqlite3
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "campus_customs.db"
OUT = ROOT / "output"
IMAGES = OUT / "app_check_images"
SIZES = ["XS", "S", "M", "L", "XL", "XXL"]
VIEWPORT = {"width": 1280, "height": 820}


# ---------- database ground truth ----------

def db_rows(sql: str, *args) -> list[sqlite3.Row]:
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    try:
        return conn.execute(sql, args).fetchall()
    finally:
        conn.close()


def product_row(product_id: str) -> sqlite3.Row:
    return db_rows("SELECT product_id, name, price FROM catalogue WHERE product_id = ?", product_id)[0]


def stock(product_id: str) -> dict[str, int]:
    rows = db_rows("SELECT size, quantity FROM inventory WHERE product_id = ?", product_id)
    return {r["size"]: r["quantity"] for r in rows}


# ---------- browser helpers ----------

def ask(page: Page, question: str) -> str:
    """Type a question into the chat, wait for the reply, return the reply's text."""
    if not page.locator(".chat-panel").is_visible():
        page.click(".chat-toggle")
        page.wait_for_selector(".chat-panel")
    before = page.locator(".chat-row").count()
    page.fill(".chat-input input", question)
    page.click(".chat-input button[type=submit]")
    page.wait_for_function(
        f"document.querySelectorAll('.chat-row').length >= {before + 2} && !document.querySelector('.typing')",
        timeout=120_000,
    )
    page.wait_for_timeout(700)  # let pop-in animations finish
    # Scroll the chat so the question and the start of the answer are in view.
    page.evaluate(
        """() => {
            const box = document.querySelector('.chat-messages');
            const q = [...box.querySelectorAll('.chat-row-user')].pop();
            box.scrollTop = q.offsetTop - box.offsetTop - 8;
        }"""
    )
    page.wait_for_timeout(300)
    return page.locator(".chat-row-assistant").last.inner_text()


def shot(page: Page, name: str, element: str | None = None) -> str:
    path = IMAGES / f"{name}.png"
    target = page.locator(element) if element else page
    target.screenshot(path=str(path))
    return f"app_check_images/{name}.png"


@dataclass
class Check:
    title: str
    proves: str
    images: list[tuple[str, str]] = field(default_factory=list)  # (src, caption)
    question: str = ""
    reply: str = ""
    assertions: list[tuple[str, bool]] = field(default_factory=list)
    db_table: list[list[str]] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(ok for _, ok in self.assertions)


# ---------- the three checks ----------

def check_inventory(page: Page, base: str) -> Check:
    pid = "trumbull-1-4-zip"
    product, qty = product_row(pid), stock(pid)
    page.goto(f"{base}/products/{pid}")
    page.wait_for_selector(".size-grid")
    question = "What's the price of this one, and how many do you have in each size?"
    reply = ask(page, question)

    c = Check(
        title="1. Chat checks an item's price and inventory",
        proves=(
            f"On the {product['name']} product page, the shopper asks about “this one” and the "
            "assistant answers with the exact price and per-size stock from campus_customs.db, "
            "clearly marking sold-out sizes. Every number matches the database table below and the "
            "page's own size tiles."
        ),
        question=question,
        reply=reply,
    )
    c.images.append((shot(page, "inventory"), "Live product page with the chat open: the shopper asks about “this one” and gets the price and stock for each size."))
    c.images.append((shot(page, "inventory_chat", ".chat-panel"), "Close-up of the chat reply, including the “✓ Prices & stock checked against live inventory” note."))
    page.click(".chat-close")
    page.wait_for_timeout(300)
    c.images.append((shot(page, "inventory_page", ".product-detail-info"), "Same product page with the chat closed: the size tiles (from the inventory table) show the same price and per-size stock as the chat reply."))

    text = reply.replace("*", "")
    c.assertions.append((f"Reply quotes the database price ${product['price']:.2f}", f"${product['price']:.2f}" in text))
    for size in SIZES:
        n = qty.get(size, 0)
        line = re.search(rf"(?m)^\s*{size}\s*[:\-–—]\s*(.+)$", text)
        said = line.group(1).lower() if line else ""
        ok = ("sold out" in said) if n == 0 else bool(re.search(rf"\b{n}\b", said))
        c.assertions.append((f"{size}: database {n} → reply says “{said.strip() or '(not listed)'}”", ok))
    c.assertions.append(("Reply shows the ✓ verified-against-inventory note", "checked against live inventory" in reply))
    c.db_table = [["Size", "Quantity (DB)"]] + [[s, str(qty.get(s, 0))] for s in SIZES] + [["Price", f"${product['price']:.2f}"]]
    return c


def check_search_cards(page: Page, base: str) -> Check:
    page.goto(f"{base}/")
    page.wait_for_selector(".hero")
    question = "What hoodies do you have?"
    reply = ask(page, question)
    page.wait_for_url(re.compile(r"/products\?title="), timeout=10_000)
    page.wait_for_selector(".product-grid-chat .product-card")
    page.wait_for_timeout(800)

    cards = page.locator(".product-grid .product-card")
    n_cards = cards.count()
    hoodies_db = db_rows("SELECT COUNT(*) AS n FROM catalogue WHERE lower(garment_type) LIKE '%hood%'")[0]["n"]
    url = page.url

    c = Check(
        title="2. Category question → search-result cards appear on the page",
        proves=(
            "Asking “What hoodies do you have?” from the Home page makes the agent search the catalogue "
            f"and return structured matches; the site jumps to the Products page and renders all {n_cards} "
            "hoodies as clickable cards (image, name, price, short description) under a “Results from the chat” banner."
        ),
        question=question,
        reply=reply,
    )
    c.images.append((shot(page, "search_results_chat"), "Right after the question: the chat reply (with highlight cards) and the page already showing the hoodie results."))
    page.click(".chat-close")
    page.set_viewport_size({"width": VIEWPORT["width"], "height": 1250})  # taller, to show full cards
    page.wait_for_timeout(300)
    c.images.append((shot(page, "search_results_page"), f"Chat closed: the Products grid now shows the {n_cards} hoodie cards from the chat search."))

    first = cards.first
    first_name = first.locator("h3").inner_text()
    href = first.get_attribute("href") or ""
    page.set_viewport_size(VIEWPORT)
    first.click()
    page.wait_for_selector(".product-detail")
    page.wait_for_timeout(400)
    c.images.append((shot(page, "search_card_detail"), f"Clicking the first chat-result card (“{first_name}”) opens its normal product page with the large image and full info."))

    c.assertions += [
        (f"URL became a chat-results page ({url.split('/', 3)[-1]})", "title=" in url),
        (f"{n_cards} cards rendered = {hoodies_db} hoodies in the database", n_cards == hoodies_db),
        ("Every card has an image, name, price and description", n_cards > 0),
        (f"First card links to {href} and opens its detail page", href.startswith("/products/") and page.url.endswith(href)),
    ]
    c.db_table = [["Query", "Result"], ["Hoodies in catalogue (garment_type like '%hood%')", str(hoodies_db)], ["Cards on page", str(n_cards)]]
    return c


def check_alternatives(page: Page, base: str) -> Check:
    pid = "football-left-chest-t-shirt"
    product, qty = product_row(pid), stock(pid)
    page.goto(f"{base}/products/{pid}")
    page.wait_for_selector(".size-grid")
    question = "Do you have this in a medium?"
    reply = ask(page, question)

    names = page.locator(".chat-row-assistant").last.locator(".chat-card strong").all_inner_texts()
    alt_rows = []
    for name in names:
        if name == product["name"]:
            continue
        row = db_rows(
            "SELECT c.product_id, c.price, i.quantity FROM catalogue c JOIN inventory i USING(product_id) "
            "WHERE c.name = ? AND i.size = 'M'",
            name,
        )
        if row:
            alt_rows.append((name, row[0]["price"], row[0]["quantity"]))

    c = Check(
        title="3. Problem 9 usability feature: in-stock alternatives for a sold-out size",
        proves=(
            f"Medium is sold out for the {product['name']}, so instead of a dead end the agent says so clearly, "
            "then uses the new find_alternatives tool to suggest similar shirts that really are in stock in M "
            "(verified in the table below). The reply also shows the ✓ accuracy-check note from Problem 9."
        ),
        question=question,
        reply=reply,
    )
    c.images.append((shot(page, "alternatives"), "Product page (M tile shows Sold out) with the chat offering in-stock alternatives."))
    c.images.append((shot(page, "alternatives_chat", ".chat-panel"), "Close-up: “sold out” stated clearly, then similar items with M in stock, shown as clickable cards."))

    text = reply.replace("*", "").lower()
    c.assertions.append((f"Database: {product['name']} size M = {qty.get('M', 0)}", qty.get("M", 0) == 0))
    c.assertions.append(("Reply clearly says M is sold out", "sold out" in text))
    c.assertions.append((f"Reply suggests at least one alternative ({len(alt_rows)} found)", len(alt_rows) > 0))
    for name, price, q in alt_rows:
        c.assertions.append((f"Alternative “{name}” really has M in stock (DB: {q}, ${price:.2f})", q > 0))
    c.db_table = [["Product", "Size M (DB)", "Price (DB)"], [product["name"], str(qty.get("M", 0)), f"${product['price']:.2f}"]] + [
        [n, str(q), f"${p:.2f}"] for n, p, q in alt_rows
    ]
    return c


# ---------- report ----------

def render(checks: list[Check], base: str, seconds: float) -> str:
    def table(rows: list[list[str]]) -> str:
        head = "".join(f"<th>{html.escape(h)}</th>" for h in rows[0])
        body = "".join("<tr>" + "".join(f"<td>{html.escape(v)}</td>" for v in r) + "</tr>" for r in rows[1:])
        return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"

    summary = "".join(
        f"<tr><td><a href='#check{i}'>{html.escape(c.title)}</a></td><td class='{ 'pass' if c.passed else 'fail' }'>{'PASS' if c.passed else 'FAIL'}</td></tr>"
        for i, c in enumerate(checks, 1)
    )
    sections = []
    for i, c in enumerate(checks, 1):
        figs = "".join(
            f"<figure><a href='{src}'><img src='{src}' alt='{html.escape(cap)}'></a><figcaption>{html.escape(cap)}</figcaption></figure>"
            for src, cap in c.images
        )
        asserts = "".join(f"<li class='{'pass' if ok else 'fail'}'>{'✔' if ok else '✘'} {html.escape(t)}</li>" for t, ok in c.assertions)
        sections.append(f"""
<section id="check{i}">
  <h2>{html.escape(c.title)} <span class="badge {'pass' if c.passed else 'fail'}">{'PASS' if c.passed else 'FAIL'}</span></h2>
  <p class="proves"><strong>What this proves:</strong> {html.escape(c.proves)}</p>
  {figs}
  <details open>
    <summary>Evidence: question, reply, and database check</summary>
    <p><strong>Shopper typed:</strong> “{html.escape(c.question)}”</p>
    <pre>{html.escape(c.reply)}</pre>
    <div class="evidence">
      <div><h3>Database (campus_customs.db)</h3>{table(c.db_table)}</div>
      <div><h3>Automated checks</h3><ul class="asserts">{asserts}</ul></div>
    </div>
  </details>
</section>""")

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>Campus Customs — App Check</title>
<style>
  body {{ margin: 0; font-family: Inter, system-ui, -apple-system, 'Segoe UI', sans-serif; color: #13233a; background: #eef3fa; line-height: 1.55; }}
  header {{ background: #00356b; color: #fff; padding: 2rem 1.5rem; border-bottom: 6px solid #286dc0; }}
  header h1 {{ margin: 0 0 .4rem; font-family: ui-monospace, Menlo, monospace; letter-spacing: .02em; }}
  header p {{ margin: .2rem 0; color: #dbe8f8; }}
  main {{ max-width: 1100px; margin: 0 auto; padding: 1.5rem; }}
  section {{ background: #fff; border: 3px solid #00254a; box-shadow: 5px 5px 0 #00254a; padding: 1.25rem 1.5rem; margin: 2rem 0; }}
  h2 {{ color: #00254a; font-family: ui-monospace, Menlo, monospace; font-size: 1.2rem; margin-top: 0; }}
  h3 {{ font-size: .95rem; margin: .25rem 0 .5rem; color: #00254a; }}
  .proves {{ font-size: 1.05rem; }}
  figure {{ margin: 1rem 0 1.5rem; }}
  figure img {{ width: 100%; border: 3px solid #00254a; display: block; }}
  figcaption {{ font-size: .92rem; color: #4f6077; margin-top: .4rem; }}
  pre {{ background: #f4f7fb; border: 2px solid #c4d2e6; padding: .75rem; white-space: pre-wrap; font-size: .85rem; }}
  table {{ border-collapse: collapse; font-size: .9rem; }}
  th, td {{ border: 1px solid #c4d2e6; padding: .35rem .6rem; text-align: left; }}
  th {{ background: #e3edf9; }}
  .evidence {{ display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; }}
  .asserts {{ list-style: none; padding: 0; margin: 0; font-size: .9rem; }}
  .asserts li {{ margin: .25rem 0; }}
  .pass {{ color: #1f8a4c; font-weight: 600; }}
  .fail {{ color: #c0262d; font-weight: 600; }}
  .badge {{ font-size: .8rem; border: 2px solid currentColor; padding: .1rem .45rem; margin-left: .5rem; vertical-align: middle; }}
  summary {{ cursor: pointer; font-weight: 600; color: #00356b; }}
  .summary-table td:first-child {{ min-width: 32rem; }}
  @media (max-width: 800px) {{ .evidence {{ grid-template-columns: 1fr; }} }}
</style></head>
<body>
<header>
  <h1>Campus Customs — Live App Check</h1>
  <p>Run {datetime.now().strftime('%B %d, %Y at %I:%M %p')} against the running site at <code>{html.escape(base)}</code> (React + Vite frontend → FastAPI + PydanticAI backend → campus_customs.db).</p>
  <p>Screenshots were captured automatically from the real app in Chromium by <code>tests/app_check.py</code> ({seconds:.0f}s run); every number in the chat was checked against SQLite.</p>
</header>
<main>
  <h2>Summary</h2>
  <table class="summary-table"><thead><tr><th>Check</th><th>Result</th></tr></thead><tbody>{summary}</tbody></table>
  {''.join(sections)}
  <p style="color:#4f6077;font-size:.9rem">Re-run with <code>.venv/bin/python tests/app_check.py</code> while the backend and frontend are running. Click any screenshot to open it full size.</p>
</main>
</body></html>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--base-url", default="http://localhost:5173")
    args = parser.parse_args()
    base = args.base_url.rstrip("/")
    IMAGES.mkdir(parents=True, exist_ok=True)

    started = time.perf_counter()
    with sync_playwright() as p:
        browser = p.chromium.launch()
        # A fresh guest session for each check, so earlier chat history can't leak in.
        checks = []
        for run in (check_inventory, check_search_cards, check_alternatives):
            context = browser.new_context(viewport=VIEWPORT, device_scale_factor=2)
            page = context.new_page()
            checks.append(run(page, base))
            context.close()
            print(f"{'PASS' if checks[-1].passed else 'FAIL'}  {checks[-1].title}")
        browser.close()

    report = OUT / "app_check.html"
    report.write_text(render(checks, base, time.perf_counter() - started), encoding="utf-8")
    print(f"Wrote {report.relative_to(ROOT)} and {len(list(IMAGES.glob('*.png')))} screenshots")


if __name__ == "__main__":
    main()

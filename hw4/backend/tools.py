"""Model setup and tools the Campus Customs agent can call."""

import os
import re
from dataclasses import dataclass, field

os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")

from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic_ai import ModelRetry, RunContext
from pydantic_ai.models.openai import OpenAIResponsesModel
from pydantic_ai.providers.openai import OpenAIProvider

from db import ROOT, all_inventory, all_products, category_of, product_with_inventory
from models import (
    Alternative,
    Alternatives,
    CatalogueQuery,
    Category,
    Customer,
    PageContext,
    PageType,
    ProductDetails,
    ProductSummary,
    SearchResults,
    Size,
    SizeStock,
    StockCheck,
    StockStatus,
)

# Local .env first, then the class-level .env two folders above Homework 4.
load_dotenv(ROOT / ".env")
load_dotenv(ROOT.parents[1] / ".env")

MODEL_NAME = os.getenv("CHAT_MODEL", "gpt-5.6-luna")
PORTKEY_BASE_URL = "https://api.portkey.ai/v1"


class MissingApiKey(RuntimeError):
    pass


def get_model() -> OpenAIResponsesModel:
    """OpenAI model through Portkey's OpenAI-compatible Responses API."""
    api_key = os.getenv("PORTKEY_API_KEY")
    if not api_key:
        raise MissingApiKey("PORTKEY_API_KEY is not set; add it to the class .env file.")
    client = AsyncOpenAI(api_key=api_key, base_url=PORTKEY_BASE_URL, timeout=60, max_retries=2)
    return OpenAIResponsesModel(MODEL_NAME, provider=OpenAIProvider(openai_client=client))


@dataclass
class PageView:
    """The shopper's current page, checked against the database by resolve_page()."""

    page_type: PageType
    path: str
    product: dict | None = None  # catalogue row when on a real product page
    results_title: str | None = None
    results_total: int = 0
    results_preview: list[dict] = field(default_factory=list)  # first few products on screen


@dataclass
class FactLedger:
    """Every price and stock number the tools showed the agent during this turn.
    The accuracy check (agent.py) only lets these numbers into a reply."""

    prices: set[float] = field(default_factory=set)
    counts: set[int] = field(default_factory=set)
    checked: int = 0  # numbers verified in the final reply
    corrections: int = 0  # replies sent back to the model for using an unverified number

    def add_product(self, p: dict, stock: dict[str, int] | None = None) -> None:
        self.prices.add(round(p["price"], 2))
        self.counts.add(p["total_stock"])
        if stock:
            self.counts.update(stock.values())


@dataclass
class ChatDeps:
    """Per-request context for the agent: who is chatting and what they're looking at."""

    customer: Customer | None = None
    page: PageView | None = None
    facts: FactLedger = field(default_factory=FactLedger)


# ---------- shared helpers ----------

SIZES: tuple[Size, ...] = ("XS", "S", "M", "L", "XL", "XXL")
LOW_STOCK_THRESHOLD = 5  # 1–5 units left counts as low stock
DEFAULT_RESULTS = 10
MAX_RESULTS = 20

SIZE_ALIASES = {
    "xs": "XS", "xsmall": "XS", "extrasmall": "XS",
    "s": "S", "sm": "S", "small": "S",
    "m": "M", "med": "M", "medium": "M",
    "l": "L", "lg": "L", "large": "L",
    "xl": "XL", "xlarge": "XL", "extralarge": "XL",
    "xxl": "XXL", "2xl": "XXL", "xxlarge": "XXL", "2xlarge": "XXL", "extraextralarge": "XXL",
}

# Multi-word phrases rewritten to single tokens before splitting into words.
PHRASES = [
    (r"\bt[\s-]?shirts?\b", "tshirt"),
    (r"\b(1[\s/]?4|quarter)[\s-]?zips?\b", "quarterzip"),
    (r"\bfull[\s-]?zips?\b", "fullzip"),
    (r"\blong[\s-]?sleeves?\b|\bl s\b", "longsleeve"),
    (r"\bcrew[\s-]?necks?\b", "crewneck"),
    (r"\bmock[\s-]?necks?\b", "mockneck"),
]
SYNONYMS = {
    "hood": "hoodie", "hooded": "hoodie", "hoody": "hoodie", "hoodies": "hoodie",
    "tee": "tshirt", "tees": "tshirt", "grey": "gray", "crew": "crewneck",
    "sweater": "sweatshirt", "sweatshirts": "sweatshirt",
}
STOPWORDS = {
    "yale", "the", "a", "an", "and", "or", "for", "with", "in", "of", "do", "you", "have",
    "any", "some", "i", "want", "me", "my", "something", "looking", "show", "item", "items",
}


def normalize_size(size: str) -> Size | None:
    key = re.sub(r"[^a-z0-9]", "", size.lower())
    return SIZE_ALIASES.get(key)  # type: ignore[return-value]


def tokens(text: str) -> set[str]:
    """Lowercase words with phrases, plurals and synonyms normalized."""
    text = text.lower()
    for pattern, token in PHRASES:
        text = re.sub(pattern, token, text)
    out = set()
    for w in re.findall(r"[a-z0-9]+", text):
        w = SYNONYMS.get(w, w)
        if w.endswith("s") and len(w) > 3 and not w.endswith("ss"):
            w = SYNONYMS.get(w[:-1], w[:-1])
        out.add(w)
    return out


def status_of(quantity: int) -> StockStatus:
    if quantity == 0:
        return "sold_out"
    return "low_stock" if quantity <= LOW_STOCK_THRESHOLD else "in_stock"


def size_stock(stock: dict[str, int]) -> list[SizeStock]:
    return [
        SizeStock(size=size, quantity=stock.get(size, 0), status=status_of(stock.get(size, 0)))
        for size in SIZES
    ]


def summary(p: dict, stock: dict[str, int]) -> ProductSummary:
    return ProductSummary(
        product_id=p["product_id"],
        name=p["name"],
        category=category_of(p["garment_type"]),
        garment_type=p["garment_type"],
        price=p["price"],
        colors=p["colors"],
        description=p["description"],
        total_stock=p["total_stock"],
        sizes_in_stock=[s for s in SIZES if stock.get(s, 0) > 0],
    )


def load_product(product_id: str) -> tuple[dict, dict[str, int]]:
    """Product row plus {size: quantity}; asks the model to retry on a bad id."""
    p = product_with_inventory(product_id.strip())
    if p is None:
        raise ModelRetry(
            f"No product with id '{product_id}'. Call search_products and use an exact product_id from its results."
        )
    return p, {s["size"]: s["quantity"] for s in p["inventory"]}


RESULTS_PREVIEW = 12


def resolve_page(page: PageContext | None) -> PageView | None:
    """Turn the browser's page report into facts from the database.

    The product id and search come from the browser, so they're treated as
    untrusted: an unknown product id is ignored, and result lists are rebuilt
    with run_search() rather than taken from the client."""
    if page is None:
        return None
    view = PageView(page_type=page.page_type, path=page.path)
    if page.page_type == "product" and page.product_id:
        view.product = product_with_inventory(page.product_id)
        if view.product is None:
            view.page_type = "other"
    if page.page_type == "products" and page.results_search is not None:
        matches = run_search(page.results_search).matches
        view.results_title = page.results_title or "Search results"
        view.results_total = len(matches)
        view.results_preview = [p for p, _ in matches[:RESULTS_PREVIEW]]
    return view


def describe_session(deps: ChatDeps) -> str:
    """Session context added to the agent's instructions on every turn."""
    lines = ["## Session context (from the website, not from the shopper)"]
    c = deps.customer
    if c:
        lines.append(
            f"- Signed-in customer: {c.first_name} {c.last_name}, email {c.email}, "
            f"member since {c.member_since}. Earlier messages in this chat are their saved history."
        )
    else:
        lines.append("- The shopper is a guest (not signed in). Their chat is not saved.")

    v = deps.page
    if v is None:
        lines.append("- Current page: unknown.")
    elif v.product:
        p = v.product
        lines.append(
            f"- Current page: the product page for **{p['name']}** "
            f"(product_id `{p['product_id']}`, ${p['price']:.2f}, colors: {', '.join(p['colors'])}). "
            'If the shopper says "this", "it" or "this one" without naming an item, they mean this product.'
        )
    elif v.results_title is not None:
        names = "; ".join(f"{p['name']} (`{p['product_id']}`)" for p in v.results_preview)
        more = f" and {v.results_total - len(v.results_preview)} more" if v.results_total > len(v.results_preview) else ""
        lines.append(
            f'- Current page: Products page showing chat results titled "{v.results_title}" '
            f"({v.results_total} items): {names}{more}. "
            '"These" or "the first one" refer to items in this list, in this order.'
        )
    else:
        labels = {
            "home": "the Home page",
            "products": "the Products page (full catalogue)",
            "about": "the About Us page",
            "login": "the Log in page",
            "create-account": "the Create account page",
            "other": f"`{v.path}`",
        }
        lines.append(f"- Current page: {labels[v.page_type]}.")
    return "\n".join(lines)


# ---------- tools ----------

@dataclass
class SearchOutcome:
    """Every match for a CatalogueQuery, best first, plus honesty notes."""

    matches: list[tuple[dict, dict[str, int]]]  # (product, {size: quantity})
    partial: bool  # no product matched every keyword
    hidden_by_stock: list[str]  # full keyword matches dropped by size / in-stock filters


def run_search(q: CatalogueQuery) -> SearchOutcome:
    """Score and filter the whole catalogue. Used by the search tool and the Products page."""
    color_tokens = tokens(q.color) if q.color else set()
    query_tokens = tokens(q.query) - STOPWORDS
    inventory = all_inventory()

    candidates = []
    hidden_by_stock = []
    for p in all_products():
        stock = inventory.get(p["product_id"], {})
        if q.category and category_of(p["garment_type"]) != q.category:
            continue
        if q.max_price is not None and p["price"] > q.max_price:
            continue
        if q.min_price is not None and p["price"] < q.min_price:
            continue
        if color_tokens and not color_tokens <= tokens(" ".join(p["colors"])):
            continue
        out_of_stock = (q.size and stock.get(q.size, 0) == 0) or (
            q.in_stock_only and p["total_stock"] == 0
        )

        primary = tokens(f"{p['name']} {p['garment_type']} {category_of(p['garment_type'])}")
        colors = tokens(" ".join(p["colors"]))
        tags = tokens(" ".join(p["search_tags"]))
        desc = tokens(p["description"])
        matched, score = 0, 0
        for t in query_tokens:
            weight = 3 if t in primary else 2 if t in colors or t in tags else 1 if t in desc else 0
            matched += weight > 0
            score += weight
        if out_of_stock:
            if query_tokens and matched == len(query_tokens):
                hidden_by_stock.append(p["name"])
            continue
        candidates.append((matched, score, p, stock))

    partial = False
    if query_tokens:
        full = [c for c in candidates if c[0] == len(query_tokens)]
        if full:
            candidates = full
        else:
            candidates = [c for c in candidates if c[0] > 0]
            partial = bool(candidates)
    # Best keyword match first, then in-stock items, then by name.
    candidates.sort(key=lambda c: (-c[0], -c[1], c[2]["total_stock"] == 0, c[2]["name"]))
    return SearchOutcome(
        matches=[(p, stock) for _, _, p, stock in candidates],
        partial=partial,
        hidden_by_stock=hidden_by_stock,
    )


def search_products(
    ctx: RunContext[ChatDeps],
    query: str = "",
    category: Category | None = None,
    color: str | None = None,
    max_price: float | None = None,
    min_price: float | None = None,
    size: str | None = None,
    in_stock_only: bool = False,
    limit: int = DEFAULT_RESULTS,
) -> SearchResults:
    """Find products in the Campus Customs catalogue.

    Use this to find items and their product_ids. Matches keywords against name,
    garment type, colors, tags and description ("baseball", "Branford", "Harvard",
    "left chest logo"). Use the filters for structured requests. Results include
    price, colors, total stock and the sizes currently in stock.

    Args:
        query: Keywords, e.g. "navy hoodie", "football tee", "Berkeley". Can be empty if filters are given.
        category: One of hoodie, sweatshirt (crewnecks and mocknecks), t-shirt, quarter-zip, jacket, long-sleeve shirt.
        color: Only items offered in this color, e.g. "navy", "gray", "white".
        max_price: Only items at or below this price in USD.
        min_price: Only items at or above this price in USD.
        size: Only items with stock in this size (XS, S, M, L, XL, XXL; "large" etc. also work).
        in_stock_only: Only items with stock in at least one size.
        limit: Max results to return (default 10, max 20).
    """
    wanted_size = normalize_size(size) if size else None
    if size and wanted_size is None:
        raise ModelRetry(f"Unknown size '{size}'. Sizes are {', '.join(SIZES)}.")
    outcome = run_search(
        CatalogueQuery(
            query=query[:200],
            category=category,
            color=color,
            min_price=min_price,
            max_price=max_price,
            size=wanted_size,
            in_stock_only=in_stock_only,
        )
    )
    total = len(outcome.matches)
    limit = max(1, min(limit, MAX_RESULTS))
    results = [summary(p, stock) for p, stock in outcome.matches[:limit]]
    for p, _ in outcome.matches[:limit]:
        ctx.deps.facts.add_product(p)
    ctx.deps.facts.counts.update({total, len(results)})

    notes = []
    if outcome.partial:
        notes.append("No product matched every keyword; these are the closest partial matches.")
    if not results:
        notes.append("No products matched. Try fewer keywords or looser filters.")
    elif total > limit:
        notes.append(f"Showing {limit} of {total} matches.")
    if outcome.hidden_by_stock:
        what = f"sold out in size {wanted_size}" if wanted_size else "sold out in every size"
        notes.append(
            f"These products match the keywords but are {what}, so they were left out: "
            + "; ".join(outcome.hidden_by_stock[:5])
            + ". If the shopper asked about one of them, tell them it's sold out."
        )
    return SearchResults(total_matches=total, products=results, note=" ".join(notes) or None)


def get_product_details(ctx: RunContext[ChatDeps], product_id: str) -> ProductDetails:
    """Get the full record for one product: description, price, colors, and stock for every size.

    Call this when the shopper asks about a specific item's details, price, or which sizes are available.

    Args:
        product_id: Exact product_id from search_products results.
    """
    p, stock = load_product(product_id)
    ctx.deps.facts.add_product(p, stock)
    return ProductDetails(
        product_id=p["product_id"],
        name=p["name"],
        category=category_of(p["garment_type"]),
        garment_type=p["garment_type"],
        price=p["price"],
        colors=p["colors"],
        description=p["description"],
        search_tags=p["search_tags"],
        total_stock=p["total_stock"],
        stock_by_size=size_stock(stock),
        sizes_in_stock=[s for s in SIZES if stock.get(s, 0) > 0],
        sizes_sold_out=[s for s in SIZES if stock.get(s, 0) == 0],
    )


def check_stock(ctx: RunContext[ChatDeps], product_id: str, size: str | None = None) -> StockCheck:
    """Check live stock for one product, optionally for one size.

    Call this whenever the shopper asks whether something is in stock, how many
    are left, or whether a size is available. Returns the exact quantity and a
    status (in_stock, low_stock = 1–5 left, sold_out) for every size.

    Args:
        product_id: Exact product_id from search_products results.
        size: Size asked about: XS, S, M, L, XL, XXL (words like "large" also work). Omit for all sizes.
    """
    p, stock = load_product(product_id)
    wanted = None
    if size:
        wanted = normalize_size(size)
        if wanted is None:
            raise ModelRetry(f"Unknown size '{size}'. Sizes are {', '.join(SIZES)}.")
    qty = stock.get(wanted, 0) if wanted else None
    ctx.deps.facts.add_product(p, stock)
    return StockCheck(
        product_id=p["product_id"],
        name=p["name"],
        price=p["price"],
        requested_size=wanted,
        requested_size_quantity=qty,
        requested_size_status=status_of(qty) if qty is not None else None,
        stock_by_size=size_stock(stock),
        sizes_in_stock=[s for s in SIZES if stock.get(s, 0) > 0],
        sizes_sold_out=[s for s in SIZES if stock.get(s, 0) == 0],
        total_stock=p["total_stock"],
    )


MAX_ALTERNATIVES = 5
COLOR_MODIFIERS = {"heather", "dusty", "light", "dark", "vintage"}


def find_alternatives(
    ctx: RunContext[ChatDeps], product_id: str, size: str | None = None
) -> Alternatives:
    """Suggest similar products that ARE available, for when the shopper's choice is sold out.

    Call this when a product (or the size they want) is sold out or low, so you
    can offer a real in-stock alternative instead of a dead end. Ranks products by
    similarity: same category, shared colors, close price, shared tags.

    Args:
        product_id: Exact product_id of the item they wanted.
        size: The size they need (XS, S, M, L, XL, XXL; "large" etc. also work). Omit if any size is fine.
    """
    original, original_stock = load_product(product_id)
    wanted = None
    if size:
        wanted = normalize_size(size)
        if wanted is None:
            raise ModelRetry(f"Unknown size '{size}'. Sizes are {', '.join(SIZES)}.")
    ctx.deps.facts.add_product(original, original_stock)

    category = category_of(original["garment_type"])
    color_words = lambda names: tokens(" ".join(names)) - COLOR_MODIFIERS
    colors = color_words(original["colors"])
    tags = tokens(" ".join(original["search_tags"])) - STOPWORDS - {"campus", "custom", "merch", "college"}
    inventory = all_inventory()
    scored = []
    for p in all_products():
        if p["product_id"] == original["product_id"]:
            continue
        stock = inventory.get(p["product_id"], {})
        if (stock.get(wanted, 0) if wanted else p["total_stock"]) == 0:
            continue  # must actually be available
        reasons, score = [], 0
        if category_of(p["garment_type"]) == category:
            score += 4
            reasons.append(f"also a {category}")
        shared_colors = [c for c in p["colors"] if color_words([c]) & colors]
        if shared_colors:
            score += 2
            reasons.append("also comes in " + ", ".join(shared_colors))
        if abs(p["price"] - original["price"]) <= 10:
            score += 1
            reasons.append("similar price")
        shared_tags = tags & tokens(" ".join(p["search_tags"]))
        score += min(len(shared_tags), 3)
        if score >= 4:  # same category, or several other things in common
            scored.append((score, p, stock, reasons))
    scored.sort(key=lambda x: (-x[0], -(x[2].get(wanted, 0) if wanted else x[1]["total_stock"]), x[1]["name"]))

    alternatives = []
    for _, p, stock, reasons in scored[:MAX_ALTERNATIVES]:
        ctx.deps.facts.add_product(p, stock)
        alternatives.append(
            Alternative(
                **summary(p, stock).model_dump(),
                size_quantity=stock.get(wanted, 0) if wanted else None,
                why_similar=reasons,
            )
        )
    return Alternatives(
        original_product_id=original["product_id"],
        original_name=original["name"],
        size=wanted,
        original_size_quantity=original_stock.get(wanted, 0) if wanted else None,
        alternatives=alternatives,
    )


TOOLS = [search_products, get_product_details, check_stock, find_alternatives]

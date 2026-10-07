"""Structured types for the Campus Customs chat API and agent."""

from typing import Literal

from pydantic import BaseModel, Field


class ProductCard(BaseModel):
    """A product card for the chat or the Products page. Always built from the
    database, never from model-written text, so price and stock are accurate."""

    product_id: str
    name: str
    garment_type: str
    description: str
    price: float
    colors: list[str]
    image_url: str
    total_stock: int
    category: str
    sizes_in_stock: list[str]


Size = Literal["XS", "S", "M", "L", "XL", "XXL"]
StockStatus = Literal["in_stock", "low_stock", "sold_out"]
Category = Literal["hoodie", "sweatshirt", "t-shirt", "quarter-zip", "jacket", "long-sleeve shirt"]


class SizeStock(BaseModel):
    """Stock for one size, as the agent sees it. `status` is computed in code
    (low_stock = 1–5 left) so the model never has to judge the numbers."""

    size: Size
    quantity: int = Field(ge=0, description="Units on hand right now, from the inventory table.")
    status: StockStatus


class ProductSummary(BaseModel):
    """One search hit: enough to recommend an item and compare options."""

    product_id: str
    name: str
    category: Category
    garment_type: str
    price: float = Field(description="Price in USD from the catalogue table.")
    colors: list[str]
    description: str
    total_stock: int
    sizes_in_stock: list[Size]


class SearchResults(BaseModel):
    """Result of search_products."""

    total_matches: int = Field(description="How many products matched before the limit was applied.")
    products: list[ProductSummary]
    note: str | None = Field(
        default=None, description="Explains an empty or truncated result, or a relaxed filter."
    )


class ProductDetails(BaseModel):
    """Full record for one product: everything the shopper might ask about."""

    product_id: str
    name: str
    category: Category
    garment_type: str
    price: float
    colors: list[str]
    description: str
    search_tags: list[str]
    total_stock: int
    stock_by_size: list[SizeStock]
    sizes_in_stock: list[Size]
    sizes_sold_out: list[Size]


class StockCheck(BaseModel):
    """Result of check_stock: stock for one product, optionally one size."""

    product_id: str
    name: str
    price: float
    requested_size: Size | None = Field(
        default=None, description="The size asked about, normalized (e.g. 'large' -> 'L')."
    )
    requested_size_quantity: int | None = None
    requested_size_status: StockStatus | None = None
    stock_by_size: list[SizeStock]
    sizes_in_stock: list[Size]
    sizes_sold_out: list[Size]
    total_stock: int


class Alternative(ProductSummary):
    """A similar product suggested when the shopper's choice is sold out."""

    size_quantity: int | None = Field(
        default=None, description="Units in the requested size (None if no size was given)."
    )
    why_similar: list[str] = Field(description="Plain reasons, e.g. 'also a hoodie', 'also comes in navy'.")


class Alternatives(BaseModel):
    """Result of find_alternatives."""

    original_product_id: str
    original_name: str
    size: Size | None
    original_size_quantity: int | None = Field(
        default=None, description="Units of the ORIGINAL product in that size (0 = sold out)."
    )
    alternatives: list[Alternative]


class CatalogueQuery(BaseModel):
    """A catalogue search: keywords plus optional filters. Shared by the
    search_products tool, the agent's page_search output, and GET /api/search."""

    query: str = Field(default="", max_length=200, description="Keywords, e.g. 'navy hoodie'. May be empty.")
    category: Category | None = None
    color: str | None = Field(default=None, max_length=40)
    min_price: float | None = Field(default=None, ge=0)
    max_price: float | None = Field(default=None, ge=0)
    size: Size | None = None
    in_stock_only: bool = False


class PageSearch(BaseModel):
    """Agent output asking the website to show a search's matches on the Products page."""

    title: str = Field(
        max_length=60,
        description="Short page heading for the results, e.g. 'Hoodies', 'Navy hoodies under $50'.",
    )
    search: CatalogueQuery = Field(
        description="The same keywords and filters you used in search_products for this request."
    )


class PageResults(BaseModel):
    """Every match for a PageSearch, as cards for the Products page."""

    title: str
    search: CatalogueQuery
    total: int
    products: list[ProductCard]


class ChatReply(BaseModel):
    """The agent's structured output for one turn."""

    message: str = Field(
        description="Reply to the shopper in Markdown. Short, friendly, in the Campus Customs voice."
    )
    product_ids: list[str] = Field(
        default_factory=list,
        max_length=6,
        description=(
            "product_ids (exact, from tool results) of the items this reply recommends or "
            "discusses, best match first. Empty if no specific products apply. These show "
            "as small cards inside the chat."
        ),
    )
    page_search: PageSearch | None = Field(
        default=None,
        description=(
            "Set when the shopper is browsing a type of product (category, color, team, budget, "
            "'what X do you have?'). The website then shows ALL matches as product cards on the "
            "Products page. Leave null for questions about one specific item, stock checks, or "
            "off-topic messages."
        ),
    )


class Customer(BaseModel):
    """The signed-in shopper, as the agent sees them (never the password hash)."""

    id: int
    first_name: str
    last_name: str
    email: str
    member_since: str = Field(description="Account creation date, YYYY-MM-DD.")


PageType = Literal["home", "products", "product", "about", "login", "create-account", "other"]


class PageContext(BaseModel):
    """What the browser says the shopper is looking at. Untrusted input: the
    backend re-checks product_id against the database before using it."""

    path: str = Field(max_length=300)
    page_type: PageType = "other"
    product_id: str | None = Field(default=None, max_length=120)
    results_title: str | None = Field(default=None, max_length=60)
    results_search: CatalogueQuery | None = None


class ChatTurn(BaseModel):
    """One earlier message sent back by the browser as conversation history."""

    role: Literal["user", "assistant"]
    content: str = Field(max_length=4000)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    # Only used for guests; signed-in shoppers' history is loaded from the database.
    history: list[ChatTurn] = Field(default_factory=list, max_length=40)
    page: PageContext | None = None


class ChatResponse(BaseModel):
    reply: str
    products: list[ProductCard]
    page_results: PageResults | None = None
    facts_checked: int = Field(
        default=0,
        description="How many prices / stock counts in the reply were verified against tool results.",
    )


class SavedMessage(BaseModel):
    """One stored chat message, as returned by GET /api/chat/history."""

    id: int
    role: Literal["user", "assistant"]
    content: str
    products: list[ProductCard]
    created_at: str


# ---------- audit trail (output/audit_trail.json) ----------

StopReason = Literal[
    "tool_calls",  # the model called tools; the loop continues
    "output_retry",  # the reply failed a safety/accuracy check and was sent back to the model
    "final_output",  # a reply was accepted and sent to the shopper
    "usage_limit",  # hit the per-turn request / tool-call / token cap
    "timeout",  # the whole turn took longer than the time limit
    "content_filter",  # the model provider blocked the message
    "checks_failed",  # the reply still failed checks after all retries; a safe fallback was sent
    "rate_limited",  # too many messages from this shopper; the agent didn't run
    "error",  # any other failure (details in result_summary)
]


class AuditToolCall(BaseModel):
    tool_name: str
    args: dict = Field(description="Tool arguments, with long strings and lists shortened.")
    status: Literal["ok", "retry", "error", "pending"]
    result_summary: str = Field(description="One-line summary of what the tool returned (or why it was retried).")


class AuditEntry(BaseModel):
    """One step of the agent loop (one model response, or a turn that ended before the model ran).
    Appended to output/audit_trail.json; earlier entries are never rewritten or removed."""

    run_id: str = Field(description="Shared by every step of the same chat turn.")
    iteration: int = Field(description="1-based model response number within the turn (0 = no model response).")
    timestamp: str = Field(description="UTC time (ISO 8601).")
    customer: str = Field(description="'user:<id>' or 'guest'. No names, emails or passwords are logged.")
    page: str | None = Field(default=None, description="Path the shopper was on.")
    user_message: str = Field(description="The shopper's message, shortened to 200 characters.")
    model: str
    tool_calls: list[AuditToolCall] = Field(default_factory=list)
    stop_reason: StopReason
    detail: str | None = Field(default=None, description="Extra context for non-normal stops.")
    provider_finish_reason: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0

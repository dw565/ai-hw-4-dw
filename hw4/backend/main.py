"""Campus Customs API: products, images, accounts, and the shop chatbot.

Run from backend/:  uvicorn main:app --reload --port 8000
"""

import logging
import os

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import Field

from agent import MAX_HISTORY_TURNS, chat, page_results
from audit import AuditRecorder
from auth import current_user, optional_user, router as auth_router
from db import DATA_DIR, all_products, product_with_inventory
from memory import clear_history, ensure_schema, get_customer, load_saved_messages, load_turns, save_turn
from models import CatalogueQuery, ChatRequest, ChatResponse, PageResults, SavedMessage
from safety import RateLimiter
from tools import MODEL_NAME, ChatDeps, MissingApiKey, resolve_page

log = logging.getLogger("campus_customs")
ensure_schema()
# Per shopper (user id, or IP for guests): at most 12 chat messages a minute.
CHAT_RATE_LIMIT = RateLimiter(max_requests=12, window_seconds=60)

app = FastAPI(title="Campus Customs API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_router)
app.mount("/images", StaticFiles(directory=DATA_DIR / "products"), name="images")


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/products")
def list_products() -> list[dict]:
    return all_products()


@app.get("/api/products/{product_id}")
def get_product(product_id: str) -> dict:
    product = product_with_inventory(product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


class SearchParams(CatalogueQuery):
    title: str = Field(default="Search results", max_length=60)


@app.get("/api/search")
def search(params: SearchParams = Query()) -> PageResults:
    """All catalogue matches for a search; the Products page calls this to show chat results."""
    return page_results(params.title, CatalogueQuery(**params.model_dump(exclude={"title"})))


@app.post("/api/chat")
async def chat_route(
    req: ChatRequest, request: Request, user: dict | None = Depends(optional_user)
) -> ChatResponse:
    shopper = f"user:{user['id']}" if user else "guest"
    if not CHAT_RATE_LIMIT.allow(shopper if user else f"ip:{request.client.host if request.client else '?'}"):
        AuditRecorder(shopper, req.page.path if req.page else None, req.message, MODEL_NAME).stop(
            "rate_limited", "more than 12 messages in 60s"
        )
        raise HTTPException(status_code=429, detail="Whoa, that's a lot of messages! Please wait a minute and try again.")
    customer = get_customer(user["id"]) if user else None
    deps = ChatDeps(customer=customer, page=resolve_page(req.page))
    # Signed-in shoppers: history comes from the database, not the browser.
    # Guests: the browser sends the turns it has, and nothing is saved.
    history = load_turns(customer.id, MAX_HISTORY_TURNS) if customer else req.history
    try:
        response = await chat(req.message, history, deps)
    except MissingApiKey as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception:
        log.exception("chat failed")
        raise HTTPException(
            status_code=502,
            detail="Sorry, the assistant is having trouble right now. Please try again.",
        )
    if customer:
        save_turn(customer.id, req.message, response.reply, response.products)
    return response


@app.get("/api/chat/history")
def chat_history(user: dict = Depends(current_user)) -> list[SavedMessage]:
    """The signed-in shopper's recent chat messages, oldest first."""
    return load_saved_messages(user["id"])


@app.delete("/api/chat/history")
def delete_chat_history(user: dict = Depends(current_user)) -> dict:
    return {"deleted": clear_history(user["id"])}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=int(os.getenv("PORT", "8000")), reload=False)

"""Customer memory: saved chat history (chat_messages table) and customer lookup."""

import json

from db import get_db, products_by_ids
from models import ChatTurn, Customer, ProductCard, SavedMessage

HISTORY_PAGE_SIZE = 50  # messages sent back to the browser on reload


def ensure_schema() -> None:
    """Create chat_messages if missing (fresh databases) and index it by user."""
    conn = get_db()
    try:
        with conn:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS chat_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    products_json TEXT,
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )"""
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_chat_messages_user ON chat_messages (user_id, id)"
            )
    finally:
        conn.close()


def get_customer(user_id: int) -> Customer | None:
    conn = get_db(readonly=True)
    try:
        row = conn.execute(
            "SELECT id, name, email, first_name, last_name, created_at FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        return None
    first, _, last = row["name"].partition(" ")
    return Customer(
        id=row["id"],
        first_name=row["first_name"] or first,
        last_name=row["last_name"] or last,
        email=row["email"],
        member_since=row["created_at"][:10],
    )


def save_turn(user_id: int, user_message: str, reply: str, products: list[ProductCard]) -> None:
    """Store one exchange (shopper message + assistant reply) in a single transaction."""
    conn = get_db()
    try:
        with conn:
            conn.execute(
                "INSERT INTO chat_messages (user_id, role, content) VALUES (?, 'user', ?)",
                (user_id, user_message),
            )
            conn.execute(
                "INSERT INTO chat_messages (user_id, role, content, products_json) VALUES (?, 'assistant', ?, ?)",
                (
                    user_id,
                    reply,
                    json.dumps([p.model_dump() for p in products]) if products else None,
                ),
            )
    finally:
        conn.close()


def _recent_rows(user_id: int, limit: int) -> list:
    conn = get_db(readonly=True)
    try:
        rows = conn.execute(
            """SELECT id, role, content, products_json, created_at FROM chat_messages
               WHERE user_id = ? AND role IN ('user', 'assistant')
               ORDER BY id DESC LIMIT ?""",
            (user_id, limit),
        ).fetchall()
    finally:
        conn.close()
    return list(reversed(rows))


def _product_ids(products_json: str | None) -> list[str]:
    try:
        return [p["product_id"] for p in json.loads(products_json or "[]") if "product_id" in p]
    except (json.JSONDecodeError, TypeError):
        return []


def load_turns(user_id: int, limit: int) -> list[ChatTurn]:
    """The most recent messages as plain turns, for the agent's message history."""
    return [ChatTurn(role=r["role"], content=r["content"]) for r in _recent_rows(user_id, limit)]


def load_saved_messages(user_id: int, limit: int = HISTORY_PAGE_SIZE) -> list[SavedMessage]:
    """Recent messages for the chat widget. Product cards are rebuilt from the
    catalogue by id, so reloaded cards show today's price and stock."""
    rows = _recent_rows(user_id, limit)
    ids = {pid for r in rows for pid in _product_ids(r["products_json"])}
    cards = {p["product_id"]: ProductCard(**p) for p in products_by_ids(sorted(ids))}
    return [
        SavedMessage(
            id=r["id"],
            role=r["role"],
            content=r["content"],
            products=[cards[pid] for pid in _product_ids(r["products_json"]) if pid in cards],
            created_at=r["created_at"],
        )
        for r in rows
    ]


def clear_history(user_id: int) -> int:
    conn = get_db()
    try:
        with conn:
            return conn.execute("DELETE FROM chat_messages WHERE user_id = ?", (user_id,)).rowcount
    finally:
        conn.close()

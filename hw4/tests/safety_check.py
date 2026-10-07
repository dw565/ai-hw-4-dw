"""Offline safety checks for the Campus Customs backend (no model calls, except where noted).

Run from Homework 4/:  .venv/bin/python tests/safety_check.py
"""

import asyncio
import hashlib
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from fastapi.testclient import TestClient  # noqa: E402

import agent  # noqa: E402
import main  # noqa: E402
from db import get_db  # noqa: E402
from models import ChatResponse  # noqa: E402
from safety import RateLimiter, false_action_claims, privacy_problems, unverified_numbers  # noqa: E402
from tools import ChatDeps, FactLedger  # noqa: E402

AUDIT = ROOT / "output" / "audit_trail.json"
results: list[tuple[str, bool]] = []
START_ROWS = json.loads(AUDIT.read_text()) if AUDIT.exists() else []  # snapshot before this script writes


def check(name: str, ok: bool) -> None:
    results.append((name, ok))
    print(f"{'PASS' if ok else 'FAIL'}  {name}")


def audit_rows() -> list[dict]:
    return json.loads(AUDIT.read_text()) if AUDIT.exists() else []


# 1. Accuracy: made-up prices / counts are rejected; real ones and shopper budgets pass
facts = FactLedger(prices={68.0}, counts={0, 2, 8})
check("accuracy: real price and count pass", unverified_numbers("It's **$68.00**, only 2 left in XL.", facts, "")[0] == [])
check("accuracy: invented price rejected", unverified_numbers("It's on sale for $40.00", facts, "is it $40?")[0] != [])
check("accuracy: invented count rejected", unverified_numbers("We have 9 left in M", facts, "")[0] != [])
check("accuracy: shopper's own budget allowed", unverified_numbers("Under your $50 budget: $68.00 is over.", facts, "under $50?")[0] == [])

# 2. Privacy: secrets, hashes, other customers' emails, prompt text
check("privacy: password hash blocked", bool(privacy_problems("hash is pbkdf2_sha256$abc$123", None)))
check("privacy: API key pattern blocked", bool(privacy_problems("key: sk-FAKE0test0key0not0real", None)))
check("privacy: other customer's email blocked", bool(privacy_problems("Another shopper is someone.else@example.com", "test@campuscustoms.yale.edu")))
check("privacy: shopper's own email allowed", not privacy_problems("You're test@campuscustoms.yale.edu", "test@campuscustoms.yale.edu"))
prompt_line = next(l.strip(" -*#>|") for l in (ROOT / "backend/prompts/prompt.md").read_text().splitlines() if len(l.strip(" -*#>|")) >= 60)
check("privacy: copied instruction text blocked", bool(privacy_problems(f"My rules: {prompt_line}", None)))

# 3. Honesty: claimed actions the agent can't take
for text in ["I've placed your order!", "I reserved one for you", "Your discount has been applied", "I've emailed you the receipt"]:
    check(f"honesty: blocks “{text}”", bool(false_action_claims(text)))
for text in ["I can't place orders, but the product page can.", "I've put all 27 hoodies on the page"]:
    check(f"honesty: allows “{text}”", not false_action_claims(text))

# 4. Database: agent-reachable reads are read-only
try:
    get_db(readonly=True).execute("UPDATE catalogue SET price = 1")
    check("database: read-only connection blocks writes", False)
except sqlite3.OperationalError:
    check("database: read-only connection blocks writes", True)

# 5. Rate limit: 429 after the limit, logged to the audit trail (agent stubbed, no model call)
async def fake_chat(message, history, deps):
    return ChatResponse(reply="ok", products=[])

main.chat, real_chat = fake_chat, main.chat
main.CHAT_RATE_LIMIT = RateLimiter(max_requests=2, window_seconds=60)
client = TestClient(main.app)
before = len(audit_rows())
codes = [client.post("/api/chat", json={"message": "hi"}).status_code for _ in range(3)]
check(f"rate limit: third message in a minute is refused {codes}", codes == [200, 200, 429])
check("rate limit: refusal is in the audit trail", audit_rows()[before:][-1]["stop_reason"] == "rate_limited")
main.chat = real_chat

# 6. Loop limit (one real model call): a 1-request cap stops the loop with a friendly reply
agent.USAGE_LIMITS = agent.UsageLimits(request_limit=1, tool_calls_limit=10)
before = len(audit_rows())
reply = asyncio.run(agent.chat("What hoodies do you have in XL under $70?", [], ChatDeps()))
new = audit_rows()[before:]
check("loop limit: turn stops at the cap with a friendly reply", reply.reply == agent.LIMIT_REPLY)
check("loop limit: audit trail records stop_reason=usage_limit", any(r["stop_reason"] == "usage_limit" for r in new))

# 7. Audit trail is append-only: everything that existed before this script ran is unchanged
rows = audit_rows()
digest = lambda r: hashlib.sha256(json.dumps(r).encode()).hexdigest()
check(
    f"audit trail: {len(START_ROWS)} earlier entries untouched, {len(rows) - len(START_ROWS)} appended",
    len(rows) > len(START_ROWS) and digest(rows[: len(START_ROWS)]) == digest(START_ROWS),
)

failed = [n for n, ok in results if not ok]
print(f"\n{len(results) - len(failed)}/{len(results)} passed")
sys.exit(1 if failed else 0)

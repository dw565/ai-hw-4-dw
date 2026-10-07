"""Backend safety checks for the Campus Customs agent.

Prompt rules ask the model to behave; these checks enforce the important ones
in code, whatever the model writes:
  * accuracy  - every price / stock count in a reply came from a tool this turn
  * privacy   - no secrets, password hashes, prompt text, or other people's emails
  * honesty   - no claims of actions the agent can't take (orders, holds, refunds...)
  * abuse     - per-shopper rate limit on chat messages
"""

import os
import re
import time
from collections import defaultdict, deque
from pathlib import Path

from tools import FactLedger

# ---------- accuracy check: numbers in a reply must come from tool results ----------

PRICE_RE = re.compile(r"\$\s?(\d{1,4}(?:,\d{3})*(?:\.\d{1,2})?)")
SIZE = r"(?:XXL|XL|XS|S|M|L)"
COUNT_RES = [
    re.compile(r"\b(\d+)\s+(?:left|in stock|available|remaining|units?|on hand)\b", re.I),
    re.compile(r"\b(?:only|just)\s+(\d+)\b", re.I),
    re.compile(r"\blow:?\s*(\d+)\b", re.I),
    re.compile(rf"\b(\d+)\s+in\s+(?:size\s+)?{SIZE}\b"),
    re.compile(rf"(?:^|[\s(]){SIZE}\s*[:=–—-]\s*(\d+)\b", re.M),
]


def numbers_in(text: str) -> set[float]:
    return {float(n.replace(",", "")) for n in re.findall(r"\d[\d,]*(?:\.\d+)?", text)}


# A number the shopper typed may be repeated only when the reply is echoing their
# request ("under $50", "you need 4"), never as a stated price or stock fact.
FILLER = r"(\s+(your|a|the|of|about))*"
BUDGET_WORDS = re.compile(rf"(under|below|less than|budget|up to|within|max(imum)?|over|above|cheaper than){FILLER}\W*$", re.I)
REQUEST_WORDS = re.compile(rf"(need|want|wanted|asked for|looking for|order|buy|get|for){FILLER}\W*$", re.I)


def _echoes_request(text: str, start: int, pattern: re.Pattern) -> bool:
    return bool(pattern.search(text[max(0, start - 20):start]))


def unverified_numbers(message: str, facts: FactLedger, user_message: str) -> tuple[list[str], int]:
    """Prices and stock counts in `message` that no tool returned this turn.

    Returns (problems, how many distinct numbers were checked)."""
    text = message.replace("*", "").replace("_", "")
    typed = numbers_in(user_message)
    problems: set[str] = set()
    checked: set[tuple[str, float]] = set()
    for m in PRICE_RE.finditer(text):
        value = round(float(m.group(1).replace(",", "")), 2)
        checked.add(("price", value))
        echo = value in typed and _echoes_request(text, m.start(), BUDGET_WORDS)
        if value not in facts.prices and not echo:
            problems.add(f"price ${value:.2f}")
    for pattern in COUNT_RES:
        for m in pattern.finditer(text):
            value = int(m.group(1))
            checked.add(("count", value))
            echo = value in typed and _echoes_request(text, m.start(), REQUEST_WORDS)
            if value not in facts.counts and not echo:
                problems.add(f"stock count {value}")
    return sorted(problems), len(checked)



# ---------- privacy: secrets, hashes, prompt text, other customers ----------

PROMPT_FILE = Path(__file__).resolve().parent / "prompts" / "prompt.md"
SECRET_PATTERNS = [
    (re.compile(r"pbkdf2_sha256\$"), "a password hash"),
    (re.compile(r"password_hash", re.I), "the password_hash field"),
    (re.compile(r"\bsk-[A-Za-z0-9_-]{16,}"), "an API key"),
    (re.compile(r"\b(PORTKEY_API_KEY|SESSION_SECRET)\b"), "a secret's name"),
]
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")


def _secret_values() -> list[str]:
    return [v for v in (os.getenv("PORTKEY_API_KEY"), os.getenv("SESSION_SECRET")) if v and len(v) >= 8]


def _prompt_lines() -> list[str]:
    """Long lines of the system prompt; a reply quoting one is leaking the prompt."""
    lines = [l.strip(" -*#>|") for l in PROMPT_FILE.read_text().splitlines()]
    return [l for l in lines if len(l) >= 60]


def privacy_problems(message: str, customer_email: str | None) -> list[str]:
    problems = [what for pattern, what in SECRET_PATTERNS if pattern.search(message)]
    if any(v in message for v in _secret_values()):
        problems.append("a secret key value")
    others = {e.lower() for e in EMAIL_RE.findall(message)} - {(customer_email or "").lower()}
    if others:
        problems.append("an email address that isn't the signed-in shopper's own")
    if any(line in message for line in _prompt_lines()):
        problems.append("text copied from your instructions")
    return problems


# ---------- honesty: no pretending to do things the agent can't do ----------

_DID = r"\b(?:I|I've|I have|I'll|I will|we've|we have)\s+(?:just\s+|now\s+|already\s+|gone ahead and\s+)?"
_DEAL = r"(?:order|purchase|checkout|payment|refund|return|exchange|reservation|discount|coupon|promo(?: code)?|credit)"
FALSE_ACTION_RES = [
    # "I've placed your order", "I've processed the refund", "I applied a 10% discount"
    re.compile(_DID + rf"(?:placed|submitted|processed|completed|confirmed|cancel+ed|applied|issued)\b.{{0,30}}\b{_DEAL}", re.I),
    # "I've reserved one for you", "I'll hold it", "I added it to your cart"
    re.compile(_DID + r"(?:reserved|held|hold|set aside|put\b.{0,30}\bon hold|added\b.{0,40}\bto your (?:cart|bag|order))", re.I),
    # "I've emailed you", "I've shipped it", "I charged your card", "I updated your account / the price"
    re.compile(_DID + r"(?:emailed|sent you|shipped|charged|refunded|updated your|changed your|updated the (?:price|stock|inventory|database))", re.I),
    re.compile(rf"\byour {_DEAL}\s+(?:has been|is|was)\s+(?:placed|confirmed|processed|applied|reserved|approved)", re.I),
]


def false_action_claims(message: str) -> list[str]:
    return [m.group(0) for r in FALSE_ACTION_RES if (m := r.search(message))]


# ---------- abuse: rate limit ----------

class RateLimiter:
    """Sliding-window limit per shopper (user id, or client IP for guests). In-memory,
    so it resets on restart; fine for one server process."""

    def __init__(self, max_requests: int, window_seconds: float):
        self.max, self.window = max_requests, window_seconds
        self.hits: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        q = self.hits[key]
        while q and now - q[0] > self.window:
            q.popleft()
        if len(q) >= self.max:
            return False
        q.append(now)
        return True

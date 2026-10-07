"""Account creation, login, and session tokens for Campus Customs.

Password hashes use PBKDF2-HMAC-SHA256 with a random per-user salt:
  new accounts:  pbkdf2_sha256$<iterations>$<salt>$<hex digest>
  seed accounts: pbkdf2_sha256$<salt>$<hex digest>   (120,000 iterations)
"""

import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import time

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field, field_validator

from db import ROOT, get_db as _db

# Class-level .env (two folders up from Homework 4) plus an optional local one.
load_dotenv(ROOT.parent.parent / ".env")
load_dotenv(ROOT / ".env")

ALGORITHM = "pbkdf2_sha256"
ITERATIONS = 600_000  # OWASP 2023+ recommendation for PBKDF2-SHA256
LEGACY_ITERATIONS = 120_000  # what the seed database used
SALT_BYTES = 16
MIN_PASSWORD_LENGTH = 8
TOKEN_TTL_SECONDS = 7 * 24 * 3600
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# Signs session tokens. Set SESSION_SECRET in .env to keep sessions across
# restarts; otherwise a random key is used and everyone is logged out on restart.
SESSION_SECRET = os.getenv("SESSION_SECRET") or secrets.token_hex(32)


# ---------- password hashing ----------

def _pbkdf2(password: str, salt: str, iterations: int) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt.encode(), iterations
    ).hex()


def hash_password(password: str) -> str:
    salt = secrets.token_hex(SALT_BYTES)
    return f"{ALGORITHM}${ITERATIONS}${salt}${_pbkdf2(password, salt, ITERATIONS)}"


def verify_password(password: str, stored: str) -> bool:
    parts = stored.split("$")
    if len(parts) == 4:
        algo, iterations, salt, digest = parts
        iterations = int(iterations)
    elif len(parts) == 3:
        algo, salt, digest = parts
        iterations = LEGACY_ITERATIONS
    else:
        return False
    if algo != ALGORITHM:
        return False
    return hmac.compare_digest(_pbkdf2(password, salt, iterations), digest)


# Used to spend the same time on unknown emails, so response timing
# doesn't reveal which emails have accounts.
_DUMMY_HASH = hash_password(secrets.token_hex(8))


# ---------- session tokens ----------

def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _sign(payload: str) -> str:
    return _b64(hmac.new(SESSION_SECRET.encode(), payload.encode(), hashlib.sha256).digest())


def create_token(user_id: int) -> str:
    payload = _b64(json.dumps({"uid": user_id, "exp": int(time.time()) + TOKEN_TTL_SECONDS}).encode())
    return f"{payload}.{_sign(payload)}"


def read_token(token: str) -> int | None:
    try:
        payload, sig = token.split(".")
        if not hmac.compare_digest(sig, _sign(payload)):
            return None
        data = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
        if data["exp"] < time.time():
            return None
        return int(data["uid"])
    except (ValueError, KeyError, json.JSONDecodeError):
        return None


# ---------- database helpers ----------

def public_user(row: sqlite3.Row) -> dict:
    """User fields that are safe to send to the browser (never the hash)."""
    first = row["first_name"] or row["name"].split(" ")[0]
    return {
        "id": row["id"],
        "email": row["email"],
        "first_name": first,
        "last_name": row["last_name"] or "",
        "name": row["name"],
    }


# ---------- request models ----------

def _clean_email(v: str) -> str:
    v = v.strip().lower()
    if not EMAIL_RE.match(v):
        raise ValueError("Enter a valid email address.")
    return v


class SignupRequest(BaseModel):
    first_name: str = Field(min_length=1, max_length=50)
    last_name: str = Field(min_length=1, max_length=50)
    email: str
    password: str = Field(max_length=128)
    confirm_password: str

    @field_validator("email")
    @classmethod
    def _check_email(cls, v: str) -> str:
        return _clean_email(v)

    @field_validator("first_name", "last_name")
    @classmethod
    def _strip_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Name can't be blank.")
        return v


class LoginRequest(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def _normalize(cls, v: str) -> str:
        return v.strip().lower()


# ---------- routes ----------

router = APIRouter(prefix="/api/auth", tags=["auth"])


def current_user(authorization: str | None = Header(default=None)) -> dict:
    """FastAPI dependency: the signed-in user, or 401."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not signed in.")
    user_id = read_token(authorization.removeprefix("Bearer "))
    if user_id is None:
        raise HTTPException(status_code=401, detail="Session expired. Please log in again.")
    conn = _db()
    try:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    finally:
        conn.close()
    if row is None:
        raise HTTPException(status_code=401, detail="Account not found.")
    return public_user(row)


def optional_user(authorization: str | None = Header(default=None)) -> dict | None:
    """FastAPI dependency: the signed-in user, or None for guests."""
    try:
        return current_user(authorization)
    except HTTPException:
        return None


@router.post("/signup")
def signup(req: SignupRequest) -> dict:
    if len(req.password) < MIN_PASSWORD_LENGTH:
        raise HTTPException(400, f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")
    if req.password != req.confirm_password:
        raise HTTPException(400, "Passwords don't match.")

    conn = _db()
    try:
        exists = conn.execute(
            "SELECT 1 FROM users WHERE lower(email) = ?", (req.email,)
        ).fetchone()
        if exists:
            raise HTTPException(409, "An account with that email already exists.")
        with conn:
            cur = conn.execute(
                """INSERT INTO users (name, email, password_hash, first_name, last_name)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    f"{req.first_name} {req.last_name}",
                    req.email,
                    hash_password(req.password),
                    req.first_name,
                    req.last_name,
                ),
            )
        row = conn.execute("SELECT * FROM users WHERE id = ?", (cur.lastrowid,)).fetchone()
    except sqlite3.IntegrityError:
        raise HTTPException(409, "An account with that email already exists.")
    finally:
        conn.close()
    return {"token": create_token(row["id"]), "user": public_user(row)}


@router.post("/login")
def login(req: LoginRequest) -> dict:
    conn = _db()
    try:
        row = conn.execute(
            "SELECT * FROM users WHERE lower(email) = ?", (req.email,)
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        verify_password(req.password, _DUMMY_HASH)
        raise HTTPException(401, "Incorrect email or password.")
    if not verify_password(req.password, row["password_hash"]):
        raise HTTPException(401, "Incorrect email or password.")
    return {"token": create_token(row["id"]), "user": public_user(row)}


@router.get("/me")
def me(user: dict = Depends(current_user)) -> dict:
    return user

import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import bcrypt
import requests
from bson import ObjectId
from pymongo.errors import DuplicateKeyError

from src.database import get_db, init_indexes


# ── Collection helpers ────────────────────────────────────────────────────────

def _users():
    return get_db().users

def _sessions():
    return get_db().sessions

def _profiles():
    return get_db().music_profiles


# ── User management ───────────────────────────────────────────────────────────

def create_user(username: str, password: str) -> dict | None:
    """Create a new user. Returns the user doc, or None if username is taken."""
    init_indexes()
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
    try:
        result = _users().insert_one({
            "username": username,
            "hashed_password": hashed,
            "created_at": datetime.now(timezone.utc),
        })
        return {"_id": result.inserted_id, "username": username}
    except DuplicateKeyError:
        return None


def authenticate_user(username: str, password: str) -> dict | None:
    """Verify credentials. Returns the user doc, or None if invalid."""
    user = _users().find_one({"username": username})
    if user and bcrypt.checkpw(password.encode(), user["hashed_password"]):
        return {"_id": user["_id"], "username": user["username"]}
    return None


# ── Session management ────────────────────────────────────────────────────────

SESSION_TTL_HOURS = 24


def create_session(user_id: ObjectId) -> str:
    """Create a session for the user and return the session token."""
    token = str(uuid.uuid4())
    _sessions().insert_one({
        "session_token": token,
        "user_id": user_id,
        "created_at": datetime.now(timezone.utc),
        "expires_at": datetime.now(timezone.utc) + timedelta(hours=SESSION_TTL_HOURS),
    })
    return token


def get_user_from_session(token: str) -> dict | None:
    """Validate a session token and return the associated user, or None if expired/missing."""
    session = _sessions().find_one({
        "session_token": token,
        "expires_at": {"$gt": datetime.now(timezone.utc)},
    })
    if not session:
        return None
    user = _users().find_one({"_id": session["user_id"]})
    if user:
        return {"_id": user["_id"], "username": user["username"]}
    return None


def delete_session(token: str) -> None:
    """Invalidate a session (logout)."""
    _sessions().delete_one({"session_token": token})


# ── Music taste profile ───────────────────────────────────────────────────────

def save_music_profile(user_id: ObjectId, profile: dict) -> None:
    """Upsert a user's music taste profile."""
    _profiles().update_one(
        {"user_id": user_id},
        {"$set": {
            "user_id": user_id,
            "favorite_genre": profile.get("favorite_genre"),
            "favorite_mood": profile.get("favorite_mood"),
            "target_energy": profile.get("target_energy"),
            "likes_acoustic": profile.get("likes_acoustic"),
            "updated_at": datetime.now(timezone.utc),
        }},
        upsert=True,
    )


def get_music_profile(user_id: ObjectId) -> dict | None:
    """Return the user's saved music taste profile, or None if none saved."""
    doc = _profiles().find_one({"user_id": user_id})
    if doc:
        return {
            "favorite_genre": doc.get("favorite_genre"),
            "favorite_mood": doc.get("favorite_mood"),
            "target_energy": doc.get("target_energy", 0.6),
            "likes_acoustic": doc.get("likes_acoustic", False),
        }
    return None


# ── Google OAuth ──────────────────────────────────────────────────────────────

_GOOGLE_AUTH_URL     = "https://accounts.google.com/o/oauth2/auth"
_GOOGLE_TOKEN_URL    = "https://oauth2.googleapis.com/token"
_GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


def build_google_auth_url(redirect_uri: str) -> tuple[str, str]:
    """Build the Google OAuth authorization URL. Returns (url, state)."""
    state = secrets.token_urlsafe(32)
    params = {
        "client_id":     os.getenv("GOOGLE_CLIENT_ID"),
        "redirect_uri":  redirect_uri,
        "response_type": "code",
        "scope":         "openid email profile",
        "state":         state,
        "access_type":   "offline",
        "prompt":        "select_account",
    }
    return _GOOGLE_AUTH_URL + "?" + urlencode(params), state


def exchange_code_for_user_info(code: str, redirect_uri: str) -> dict:
    """Exchange an OAuth authorization code for Google user info."""
    token_resp = requests.post(_GOOGLE_TOKEN_URL, data={
        "code":          code,
        "client_id":     os.getenv("GOOGLE_CLIENT_ID"),
        "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
        "redirect_uri":  redirect_uri,
        "grant_type":    "authorization_code",
    })
    token_resp.raise_for_status()
    access_token = token_resp.json()["access_token"]

    userinfo_resp = requests.get(
        _GOOGLE_USERINFO_URL,
        headers={"Authorization": f"Bearer {access_token}"},
    )
    userinfo_resp.raise_for_status()
    return userinfo_resp.json()


def store_oauth_state(state: str) -> None:
    """Persist a short-lived CSRF state token in MongoDB."""
    get_db().oauth_states.insert_one({
        "state":      state,
        "expires_at": datetime.now(timezone.utc) + timedelta(minutes=10),
    })


def verify_and_consume_oauth_state(state: str) -> bool:
    """Check and atomically delete the state token. Returns False if missing or expired."""
    result = get_db().oauth_states.find_one_and_delete({
        "state":      state,
        "expires_at": {"$gt": datetime.now(timezone.utc)},
    })
    return result is not None


def find_or_create_google_user(google_id: str, email: str, name: str) -> dict:
    """Return an existing Google-linked user or create a new one."""
    init_indexes()
    user = _users().find_one({"google_id": google_id})
    if user:
        return {"_id": user["_id"], "username": user["username"]}

    base = name or (email.split("@")[0] if email else "user")
    username, n = base, 1
    while _users().find_one({"username": username}):
        username = f"{base}{n}"
        n += 1

    result = _users().insert_one({
        "username":      username,
        "email":         email,
        "google_id":     google_id,
        "auth_provider": "google",
        "created_at":    datetime.now(timezone.utc),
    })
    return {"_id": result.inserted_id, "username": username}

import os
from pymongo import MongoClient, ASCENDING
from pymongo.database import Database

_client: MongoClient | None = None


def get_db() -> Database:
    global _client
    if _client is None:
        uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
        _client = MongoClient(uri)
    return _client["music_recommender"]


def init_indexes() -> None:
    db = get_db()
    db.users.create_index("username", unique=True)
    db.users.create_index("google_id", unique=True, sparse=True)
    db.sessions.create_index("session_token", unique=True)
    db.sessions.create_index("expires_at", expireAfterSeconds=0)  # TTL auto-cleanup
    db.music_profiles.create_index("user_id", unique=True)
    db.oauth_states.create_index("expires_at", expireAfterSeconds=0)  # TTL auto-cleanup
    db.oauth_states.create_index("state", unique=True)

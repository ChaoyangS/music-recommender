"""
Unit tests for src/auth.py.

All MongoDB I/O is replaced with MagicMock so no running database is needed.
Every test patches `src.auth.get_db` to return a controlled mock database
object and, where relevant, `src.auth.init_indexes` to skip the index setup.
"""

import os
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch, call

import bcrypt
import pytest
from bson import ObjectId
from pymongo.errors import DuplicateKeyError

from src.auth import (
    authenticate_user,
    build_google_auth_url,
    create_session,
    create_user,
    delete_session,
    dislike_song,
    find_or_create_google_user,
    get_disliked_song_ids,
    get_liked_song_ids,
    get_liked_songs,
    get_music_profile,
    get_user_from_session,
    like_song,
    save_music_profile,
    store_oauth_state,
    undislike_song,
    unlike_song,
    verify_and_consume_oauth_state,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _mock_db():
    """Return a fresh MagicMock that mimics a PyMongo database."""
    return MagicMock()


def _hashed(password: str) -> bytes:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt())


# ── create_user ───────────────────────────────────────────────────────────────

class TestCreateUser:
    def test_returns_user_doc_on_success(self):
        db = _mock_db()
        new_id = ObjectId()
        db.users.insert_one.return_value = MagicMock(inserted_id=new_id)

        with patch("src.auth.get_db", return_value=db), patch("src.auth.init_indexes"):
            result = create_user("alice", "secret123")

        assert result is not None
        assert result["username"] == "alice"
        assert result["_id"] == new_id

    def test_returns_none_on_duplicate_username(self):
        db = _mock_db()
        db.users.insert_one.side_effect = DuplicateKeyError("duplicate")

        with patch("src.auth.get_db", return_value=db), patch("src.auth.init_indexes"):
            result = create_user("alice", "secret123")

        assert result is None

    def test_password_is_hashed_before_storage(self):
        db = _mock_db()
        db.users.insert_one.return_value = MagicMock(inserted_id=ObjectId())

        with patch("src.auth.get_db", return_value=db), patch("src.auth.init_indexes"):
            create_user("bob", "plaintext")

        stored = db.users.insert_one.call_args[0][0]
        assert "hashed_password" in stored
        assert bcrypt.checkpw(b"plaintext", stored["hashed_password"])

    def test_plain_password_not_stored(self):
        db = _mock_db()
        db.users.insert_one.return_value = MagicMock(inserted_id=ObjectId())

        with patch("src.auth.get_db", return_value=db), patch("src.auth.init_indexes"):
            create_user("carol", "mypassword")

        stored = db.users.insert_one.call_args[0][0]
        assert "mypassword" not in str(stored)


# ── authenticate_user ─────────────────────────────────────────────────────────

class TestAuthenticateUser:
    def test_valid_credentials_returns_user(self):
        db = _mock_db()
        uid = ObjectId()
        db.users.find_one.return_value = {
            "_id": uid, "username": "alice", "hashed_password": _hashed("secret"),
        }

        with patch("src.auth.get_db", return_value=db):
            result = authenticate_user("alice", "secret")

        assert result is not None
        assert result["username"] == "alice"

    def test_wrong_password_returns_none(self):
        db = _mock_db()
        db.users.find_one.return_value = {
            "_id": ObjectId(), "username": "alice", "hashed_password": _hashed("secret"),
        }

        with patch("src.auth.get_db", return_value=db):
            result = authenticate_user("alice", "wrong")

        assert result is None

    def test_unknown_username_returns_none(self):
        db = _mock_db()
        db.users.find_one.return_value = None

        with patch("src.auth.get_db", return_value=db):
            result = authenticate_user("nobody", "pass")

        assert result is None


# ── create_session / get_user_from_session / delete_session ───────────────────

class TestSessionManagement:
    def test_create_session_returns_string_token(self):
        db = _mock_db()
        with patch("src.auth.get_db", return_value=db):
            token = create_session(ObjectId())

        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_session_inserts_to_db(self):
        db = _mock_db()
        uid = ObjectId()
        with patch("src.auth.get_db", return_value=db):
            token = create_session(uid)

        db.sessions.insert_one.assert_called_once()
        stored = db.sessions.insert_one.call_args[0][0]
        assert stored["user_id"] == uid
        assert stored["session_token"] == token

    def test_get_user_from_session_valid_token_returns_user(self):
        db = _mock_db()
        uid = ObjectId()
        db.sessions.find_one.return_value = {"session_token": "tok", "user_id": uid}
        db.users.find_one.return_value = {"_id": uid, "username": "alice"}

        with patch("src.auth.get_db", return_value=db):
            result = get_user_from_session("tok")

        assert result["username"] == "alice"

    def test_get_user_from_session_expired_returns_none(self):
        db = _mock_db()
        db.sessions.find_one.return_value = None  # expired / missing

        with patch("src.auth.get_db", return_value=db):
            result = get_user_from_session("old-token")

        assert result is None

    def test_get_user_from_session_missing_user_returns_none(self):
        db = _mock_db()
        uid = ObjectId()
        db.sessions.find_one.return_value = {"session_token": "tok", "user_id": uid}
        db.users.find_one.return_value = None  # user deleted

        with patch("src.auth.get_db", return_value=db):
            result = get_user_from_session("tok")

        assert result is None

    def test_delete_session_removes_correct_token(self):
        db = _mock_db()
        with patch("src.auth.get_db", return_value=db):
            delete_session("my-token")

        db.sessions.delete_one.assert_called_once_with({"session_token": "my-token"})


# ── save_music_profile / get_music_profile ────────────────────────────────────

class TestMusicProfile:
    def test_save_upserts_with_correct_fields(self):
        db = _mock_db()
        uid = ObjectId()
        profile = {"favorite_genre": "pop", "favorite_mood": "happy",
                   "target_energy": 0.8, "likes_acoustic": False}

        with patch("src.auth.get_db", return_value=db):
            save_music_profile(uid, profile)

        db.music_profiles.update_one.assert_called_once()
        _, set_doc, kwargs = db.music_profiles.update_one.call_args[0][0], \
                              db.music_profiles.update_one.call_args[0][1], \
                              db.music_profiles.update_one.call_args[1]
        assert kwargs.get("upsert") is True

    def test_save_stores_all_profile_fields(self):
        db = _mock_db()
        uid = ObjectId()
        profile = {"favorite_genre": "jazz", "favorite_mood": "chill",
                   "target_energy": 0.5, "likes_acoustic": True}

        with patch("src.auth.get_db", return_value=db):
            save_music_profile(uid, profile)

        set_clause = db.music_profiles.update_one.call_args[0][1]["$set"]
        assert set_clause["favorite_genre"] == "jazz"
        assert set_clause["favorite_mood"] == "chill"
        assert set_clause["target_energy"] == 0.5
        assert set_clause["likes_acoustic"] is True

    def test_get_profile_returns_none_when_missing(self):
        db = _mock_db()
        db.music_profiles.find_one.return_value = None

        with patch("src.auth.get_db", return_value=db):
            result = get_music_profile(ObjectId())

        assert result is None

    def test_get_profile_returns_correct_fields(self):
        db = _mock_db()
        uid = ObjectId()
        db.music_profiles.find_one.return_value = {
            "user_id": uid, "favorite_genre": "rock", "favorite_mood": "intense",
            "target_energy": 0.9, "likes_acoustic": False,
        }

        with patch("src.auth.get_db", return_value=db):
            result = get_music_profile(uid)

        assert result["favorite_genre"] == "rock"
        assert result["target_energy"] == 0.9

    def test_get_profile_defaults_energy_and_acoustic(self):
        db = _mock_db()
        db.music_profiles.find_one.return_value = {"user_id": ObjectId()}

        with patch("src.auth.get_db", return_value=db):
            result = get_music_profile(ObjectId())

        assert result["target_energy"] == 0.6
        assert result["likes_acoustic"] is False


# ── like_song / unlike_song / get_liked_song_ids / get_liked_songs ───────────

class TestLikedSongs:
    def test_like_song_inserts_correct_fields(self):
        db = _mock_db()
        uid = ObjectId()
        song_data = {"title": "Hit", "artist": "Band", "genre": "pop", "mood": "happy"}

        with patch("src.auth.get_db", return_value=db):
            like_song(uid, 7, song_data)

        stored = db.liked_songs.insert_one.call_args[0][0]
        assert stored["user_id"] == uid
        assert stored["song_id"] == 7
        assert stored["title"] == "Hit"

    def test_like_song_duplicate_is_silently_ignored(self):
        db = _mock_db()
        db.liked_songs.insert_one.side_effect = DuplicateKeyError("dup")

        with patch("src.auth.get_db", return_value=db):
            like_song(ObjectId(), 1, {})  # should not raise

    def test_unlike_song_deletes_correct_document(self):
        db = _mock_db()
        uid = ObjectId()

        with patch("src.auth.get_db", return_value=db):
            unlike_song(uid, 42)

        db.liked_songs.delete_one.assert_called_once_with({"user_id": uid, "song_id": 42})

    def test_get_liked_song_ids_returns_set(self):
        db = _mock_db()
        uid = ObjectId()
        db.liked_songs.find.return_value = [{"song_id": 1}, {"song_id": 5}, {"song_id": 9}]

        with patch("src.auth.get_db", return_value=db):
            result = get_liked_song_ids(uid)

        assert result == {1, 5, 9}

    def test_get_liked_song_ids_empty_when_none_liked(self):
        db = _mock_db()
        db.liked_songs.find.return_value = []

        with patch("src.auth.get_db", return_value=db):
            result = get_liked_song_ids(ObjectId())

        assert result == set()

    def test_get_liked_songs_returns_expected_keys(self):
        db = _mock_db()
        uid = ObjectId()
        ts = datetime.now(timezone.utc)
        db.liked_songs.find.return_value.sort.return_value = [
            {"song_id": 3, "title": "T", "artist": "A",
             "genre": "pop", "mood": "happy", "liked_at": ts}
        ]

        with patch("src.auth.get_db", return_value=db):
            results = get_liked_songs(uid)

        assert len(results) == 1
        assert results[0]["title"] == "T"
        assert results[0]["liked_at"] == ts


# ── dislike_song / undislike_song / get_disliked_song_ids ────────────────────

class TestDislikedSongs:
    def test_dislike_song_inserts_to_disliked(self):
        db = _mock_db()
        uid = ObjectId()

        with patch("src.auth.get_db", return_value=db):
            dislike_song(uid, 5, {"title": "T", "artist": "A", "genre": "pop", "mood": "happy"})

        stored = db.disliked_songs.insert_one.call_args[0][0]
        assert stored["song_id"] == 5

    def test_dislike_song_also_removes_from_liked(self):
        db = _mock_db()
        uid = ObjectId()

        with patch("src.auth.get_db", return_value=db):
            dislike_song(uid, 5, {})

        db.liked_songs.delete_one.assert_called_once_with({"user_id": uid, "song_id": 5})

    def test_dislike_duplicate_is_silently_ignored(self):
        db = _mock_db()
        db.disliked_songs.insert_one.side_effect = DuplicateKeyError("dup")

        with patch("src.auth.get_db", return_value=db):
            dislike_song(ObjectId(), 1, {})  # should not raise

    def test_undislike_removes_correct_document(self):
        db = _mock_db()
        uid = ObjectId()

        with patch("src.auth.get_db", return_value=db):
            undislike_song(uid, 10)

        db.disliked_songs.delete_one.assert_called_once_with({"user_id": uid, "song_id": 10})

    def test_get_disliked_song_ids_returns_set(self):
        db = _mock_db()
        db.disliked_songs.find.return_value = [{"song_id": 2}, {"song_id": 8}]

        with patch("src.auth.get_db", return_value=db):
            result = get_disliked_song_ids(ObjectId())

        assert result == {2, 8}


# ── Google OAuth helpers ──────────────────────────────────────────────────────

class TestBuildGoogleAuthUrl:
    def test_returns_url_and_state_tuple(self):
        with patch.dict(os.environ, {"GOOGLE_CLIENT_ID": "test-client-id"}):
            url, state = build_google_auth_url("http://localhost:8501")

        assert isinstance(url, str)
        assert isinstance(state, str)

    def test_url_contains_google_domain(self):
        with patch.dict(os.environ, {"GOOGLE_CLIENT_ID": "test-id"}):
            url, _ = build_google_auth_url("http://localhost:8501")

        assert "accounts.google.com" in url

    def test_url_contains_client_id(self):
        with patch.dict(os.environ, {"GOOGLE_CLIENT_ID": "my-client-id"}):
            url, _ = build_google_auth_url("http://localhost:8501")

        assert "my-client-id" in url

    def test_url_contains_redirect_uri(self):
        with patch.dict(os.environ, {"GOOGLE_CLIENT_ID": "id"}):
            url, _ = build_google_auth_url("http://example.com/callback")

        assert "example.com" in url

    def test_state_is_unique_per_call(self):
        with patch.dict(os.environ, {"GOOGLE_CLIENT_ID": "id"}):
            _, state1 = build_google_auth_url("http://localhost")
            _, state2 = build_google_auth_url("http://localhost")

        assert state1 != state2


class TestOAuthState:
    def test_store_oauth_state_inserts_to_db(self):
        db = _mock_db()
        with patch("src.auth.get_db", return_value=db):
            store_oauth_state("abc123")

        db.oauth_states.insert_one.assert_called_once()
        stored = db.oauth_states.insert_one.call_args[0][0]
        assert stored["state"] == "abc123"

    def test_verify_valid_state_returns_true(self):
        db = _mock_db()
        db.oauth_states.find_one_and_delete.return_value = {"state": "valid"}

        with patch("src.auth.get_db", return_value=db):
            result = verify_and_consume_oauth_state("valid")

        assert result is True

    def test_verify_invalid_state_returns_false(self):
        db = _mock_db()
        db.oauth_states.find_one_and_delete.return_value = None

        with patch("src.auth.get_db", return_value=db):
            result = verify_and_consume_oauth_state("wrong")

        assert result is False

    def test_verify_consumes_state_atomically(self):
        db = _mock_db()
        db.oauth_states.find_one_and_delete.return_value = {"state": "tok"}

        with patch("src.auth.get_db", return_value=db):
            verify_and_consume_oauth_state("tok")

        db.oauth_states.find_one_and_delete.assert_called_once()


# ── find_or_create_google_user ────────────────────────────────────────────────

class TestFindOrCreateGoogleUser:
    def test_returns_existing_user_if_found(self):
        db = _mock_db()
        uid = ObjectId()
        db.users.find_one.return_value = {"_id": uid, "username": "guser", "google_id": "g1"}

        with patch("src.auth.get_db", return_value=db), patch("src.auth.init_indexes"):
            result = find_or_create_google_user("g1", "g@g.com", "G User")

        assert result["username"] == "guser"
        db.users.insert_one.assert_not_called()

    def test_creates_new_user_when_not_found(self):
        db = _mock_db()
        new_id = ObjectId()
        # first call: google_id lookup → None; second: username availability → None
        db.users.find_one.side_effect = [None, None]
        db.users.insert_one.return_value = MagicMock(inserted_id=new_id)

        with patch("src.auth.get_db", return_value=db), patch("src.auth.init_indexes"):
            result = find_or_create_google_user("g2", "new@g.com", "New User")

        assert result["_id"] == new_id
        db.users.insert_one.assert_called_once()

    def test_new_user_uses_name_as_username(self):
        db = _mock_db()
        db.users.find_one.side_effect = [None, None]
        db.users.insert_one.return_value = MagicMock(inserted_id=ObjectId())

        with patch("src.auth.get_db", return_value=db), patch("src.auth.init_indexes"):
            find_or_create_google_user("g3", "x@g.com", "Jane Doe")

        stored = db.users.insert_one.call_args[0][0]
        assert stored["username"] == "Jane Doe"

    def test_falls_back_to_email_prefix_when_no_name(self):
        db = _mock_db()
        db.users.find_one.side_effect = [None, None]
        db.users.insert_one.return_value = MagicMock(inserted_id=ObjectId())

        with patch("src.auth.get_db", return_value=db), patch("src.auth.init_indexes"):
            find_or_create_google_user("g4", "jane@example.com", "")

        stored = db.users.insert_one.call_args[0][0]
        assert stored["username"] == "jane"

    def test_appends_number_when_username_taken(self):
        db = _mock_db()
        # google_id check → None; username "Alice" → taken; "Alice1" → available
        db.users.find_one.side_effect = [None, {"_id": ObjectId()}, None]
        db.users.insert_one.return_value = MagicMock(inserted_id=ObjectId())

        with patch("src.auth.get_db", return_value=db), patch("src.auth.init_indexes"):
            find_or_create_google_user("g5", "a@g.com", "Alice")

        stored = db.users.insert_one.call_args[0][0]
        assert stored["username"] == "Alice1"

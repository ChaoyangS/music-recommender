"""
Unit tests for src/widgets.py.

Streamlit calls are replaced with MagicMock so no running Streamlit server
is needed. Tests focus on observable behaviour: what gets called, with what
arguments, and under what conditions.
"""

from unittest.mock import MagicMock, patch, call

import pytest
from bson import ObjectId

from src.widgets import MAX_SCORE, render_results


# ── Shared helpers ────────────────────────────────────────────────────────────

def _rec(title="Song", artist="Artist", score=8.0, genre="pop", mood="happy",
         reasons=None, song_id=1, preview_url=""):
    return {
        "title": title, "artist": artist, "score": score,
        "genre": genre, "mood": mood,
        "reasons": reasons if reasons is not None else [],
        "song_id": song_id, "preview_url": preview_url,
    }


def _ctx():
    """A MagicMock that works as a context manager (for st.expander / st.columns)."""
    m = MagicMock()
    m.__enter__ = MagicMock(return_value=m)
    m.__exit__ = MagicMock(return_value=False)
    return m


def _run(recs, user_id=None, key_prefix="", liked=None, disliked=None):
    """
    Run render_results with all Streamlit and DB calls mocked.
    Returns the mock `st` module so callers can assert on it.
    """
    liked   = set() if liked   is None else liked
    disliked = set() if disliked is None else disliked
    ctx = _ctx()

    with patch("src.widgets.st") as mock_st, \
         patch("src.widgets.get_liked_song_ids",    return_value=liked), \
         patch("src.widgets.get_disliked_song_ids", return_value=disliked):
        mock_st.expander.return_value  = ctx
        mock_st.columns.return_value   = [ctx, ctx, ctx, ctx]
        mock_st.button.return_value    = False
        render_results(recs, user_id=user_id, key_prefix=key_prefix)
        return mock_st


# ── MAX_SCORE constant ────────────────────────────────────────────────────────

class TestMaxScore:
    def test_value_is_twelve(self):
        assert MAX_SCORE == 12.0

    def test_is_float(self):
        assert isinstance(MAX_SCORE, float)

    def test_genre_plus_mood_plus_energy_plus_acoustic_matches_max(self):
        # Scoring formula: genre(5) + mood(4) + energy(2) + acoustic(1) = 12
        assert MAX_SCORE == 5 + 4 + 2 + 1


# ── Confidence clamping (pure logic from render_results) ─────────────────────

class TestConfidenceClamp:
    def test_perfect_score_gives_one(self):
        assert min(MAX_SCORE / MAX_SCORE, 1.0) == 1.0

    def test_zero_score_gives_zero(self):
        assert min(0.0 / MAX_SCORE, 1.0) == 0.0

    def test_over_max_clamped_to_one(self):
        assert min(20.0 / MAX_SCORE, 1.0) == 1.0

    def test_half_score_gives_half(self):
        assert abs(min((MAX_SCORE / 2) / MAX_SCORE, 1.0) - 0.5) < 1e-9


# ── Empty recommendations ─────────────────────────────────────────────────────

class TestRenderResultsEmpty:
    def test_shows_info_message(self):
        mock_st = _run([])
        mock_st.info.assert_called_once_with("No recommendations returned.")

    def test_no_expanders_created(self):
        mock_st = _run([])
        mock_st.expander.assert_not_called()


# ── Expander label format ─────────────────────────────────────────────────────

class TestExpanderLabel:
    def test_contains_title(self):
        mock_st = _run([_rec(title="Bohemian Rhapsody")])
        label = mock_st.expander.call_args[0][0]
        assert "Bohemian Rhapsody" in label

    def test_contains_artist(self):
        mock_st = _run([_rec(artist="Queen")])
        label = mock_st.expander.call_args[0][0]
        assert "Queen" in label

    def test_contains_formatted_score(self):
        mock_st = _run([_rec(score=9.5)])
        label = mock_st.expander.call_args[0][0]
        assert "9.50" in label

    def test_contains_max_score(self):
        mock_st = _run([_rec()])
        label = mock_st.expander.call_args[0][0]
        assert "12" in label

    def test_one_expander_per_recommendation(self):
        recs = [_rec(title="A", song_id=1), _rec(title="B", song_id=2), _rec(title="C", song_id=3)]
        mock_st = _run(recs)
        assert mock_st.expander.call_count == 3


# ── Like / dislike button labels ──────────────────────────────────────────────

class TestLikeDislikeButtons:
    def test_liked_song_shows_filled_heart(self):
        uid = ObjectId()
        mock_st = _run([_rec(song_id=1)], user_id=uid, liked={1})
        button_labels = [str(c) for c in mock_st.button.call_args_list]
        assert any("❤️" in lbl for lbl in button_labels)

    def test_unliked_song_shows_empty_heart(self):
        uid = ObjectId()
        mock_st = _run([_rec(song_id=1)], user_id=uid, liked=set())
        button_labels = [str(c) for c in mock_st.button.call_args_list]
        assert any("🤍" in lbl for lbl in button_labels)

    def test_disliked_song_shows_filled_thumbsdown(self):
        uid = ObjectId()
        mock_st = _run([_rec(song_id=1)], user_id=uid, disliked={1})
        button_labels = [str(c) for c in mock_st.button.call_args_list]
        assert any("👎" in lbl for lbl in button_labels)

    def test_no_buttons_without_user_id(self):
        mock_st = _run([_rec(song_id=1)], user_id=None)
        mock_st.button.assert_not_called()

    def test_no_buttons_when_song_id_is_none(self):
        rec = _rec()
        rec["song_id"] = None
        uid = ObjectId()
        mock_st = _run([rec], user_id=uid)
        mock_st.button.assert_not_called()


# ── Like action (button click) ────────────────────────────────────────────────

class TestLikeAction:
    def test_clicking_like_calls_like_song(self):
        uid = ObjectId()
        rec = _rec(song_id=99)
        ctx = _ctx()

        with patch("src.widgets.st") as mock_st, \
             patch("src.widgets.get_liked_song_ids",    return_value=set()), \
             patch("src.widgets.get_disliked_song_ids", return_value=set()), \
             patch("src.widgets.like_song") as mock_like, \
             patch("src.widgets.unlike_song") as mock_unlike:
            mock_st.expander.return_value  = ctx
            mock_st.columns.return_value   = [ctx, ctx, ctx, ctx]
            # First button call (like) returns True → simulates click
            mock_st.button.side_effect = [True, False]
            render_results([rec], user_id=uid)

        mock_like.assert_called_once_with(uid, 99, rec)
        mock_unlike.assert_not_called()

    def test_clicking_unlike_calls_unlike_song(self):
        uid = ObjectId()
        rec = _rec(song_id=99)
        ctx = _ctx()

        with patch("src.widgets.st") as mock_st, \
             patch("src.widgets.get_liked_song_ids",    return_value={99}), \
             patch("src.widgets.get_disliked_song_ids", return_value=set()), \
             patch("src.widgets.like_song") as mock_like, \
             patch("src.widgets.unlike_song") as mock_unlike:
            mock_st.expander.return_value  = ctx
            mock_st.columns.return_value   = [ctx, ctx, ctx, ctx]
            mock_st.button.side_effect = [True, False]
            render_results([rec], user_id=uid)

        mock_unlike.assert_called_once_with(uid, 99)
        mock_like.assert_not_called()


# ── Audio preview ─────────────────────────────────────────────────────────────

class TestAudioPreview:
    def test_audio_rendered_when_preview_url_present(self):
        mock_st = _run([_rec(preview_url="http://example.com/song.mp3")])
        mock_st.audio.assert_called_once_with("http://example.com/song.mp3", format="audio/mp3")

    def test_no_audio_when_preview_url_empty(self):
        mock_st = _run([_rec(preview_url="")])
        mock_st.audio.assert_not_called()

    def test_no_audio_when_preview_url_missing(self):
        rec = _rec()
        del rec["preview_url"]
        mock_st = _run([rec])
        mock_st.audio.assert_not_called()


# ── DB error resilience ───────────────────────────────────────────────────────

class TestDbErrorResilience:
    def test_db_error_fetching_liked_ids_does_not_crash(self):
        rec = _rec(song_id=1)
        ctx = _ctx()

        with patch("src.widgets.st") as mock_st, \
             patch("src.widgets.get_liked_song_ids",    side_effect=Exception("DB down")), \
             patch("src.widgets.get_disliked_song_ids", side_effect=Exception("DB down")):
            mock_st.expander.return_value = ctx
            mock_st.columns.return_value  = [ctx, ctx, ctx, ctx]
            mock_st.button.return_value   = False
            render_results([rec], user_id=ObjectId())  # should not raise

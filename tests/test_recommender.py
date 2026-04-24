"""
Comprehensive test suite for the Music Recommender system.

Covers:
  - score_song         : every scoring dimension in isolation
  - recommend_songs    : sorting, top-K, and edge cases
  - load_songs         : CSV parsing and numeric field conversion
  - _execute_tool      : agent tool dispatcher (browse_catalog,
                         get_recommendations, evaluate_quality)
  - Recommender / Song / UserProfile OOP layer
"""

import json
from pathlib import Path

import pytest

from src.recommender import (
    Song,
    UserProfile,
    Recommender,
    load_songs,
    score_song,
    recommend_songs,
)
from src.agent import _execute_tool

DATA_CSV = str(Path(__file__).parent.parent / "data" / "songs.csv")


# ── Shared fixtures ───────────────────────────────────────────────────────────

@pytest.fixture
def sample_songs():
    """Small three-song in-memory catalog used across multiple tests."""
    return [
        {
            "id": 1, "title": "Pop Track", "artist": "A",
            "genre": "pop", "mood": "happy",
            "energy": 0.8, "tempo_bpm": 120, "valence": 0.9,
            "danceability": 0.8, "acousticness": 0.2,
        },
        {
            "id": 2, "title": "Lofi Loop", "artist": "B",
            "genre": "lofi", "mood": "chill",
            "energy": 0.4, "tempo_bpm": 80, "valence": 0.6,
            "danceability": 0.5, "acousticness": 0.9,
        },
        {
            "id": 3, "title": "Rock Storm", "artist": "C",
            "genre": "rock", "mood": "intense",
            "energy": 0.95, "tempo_bpm": 150, "valence": 0.4,
            "danceability": 0.6, "acousticness": 0.1,
        },
    ]


@pytest.fixture
def pop_prefs():
    return {
        "favorite_genre": "pop",
        "favorite_mood": "happy",
        "target_energy": 0.8,
        "likes_acoustic": False,
    }


# ── score_song ────────────────────────────────────────────────────────────────

class TestScoreSong:

    def _song(self, genre="other", mood="other", energy=0.5, acousticness=0.2):
        return {"genre": genre, "mood": mood, "energy": energy, "acousticness": acousticness}

    def _prefs(self, genre="pop", mood="happy", energy=0.5, acoustic=False):
        return {
            "favorite_genre": genre,
            "favorite_mood": mood,
            "target_energy": energy,
            "likes_acoustic": acoustic,
        }

    def test_genre_match_adds_five_points(self):
        score, reasons = score_song(self._prefs(genre="pop"), self._song(genre="pop"))
        assert score >= 5.0
        assert any("genre match" in r for r in reasons)

    def test_genre_mismatch_adds_zero(self):
        score, reasons = score_song(self._prefs(genre="pop"), self._song(genre="jazz"))
        assert not any("genre match" in r for r in reasons)

    def test_mood_match_adds_four_points(self):
        score, reasons = score_song(self._prefs(mood="chill"), self._song(mood="chill"))
        assert score >= 4.0
        assert any("mood match" in r for r in reasons)

    def test_mood_mismatch_adds_zero(self):
        score, reasons = score_song(self._prefs(mood="happy"), self._song(mood="intense"))
        assert not any("mood match" in r for r in reasons)

    def test_genre_and_mood_match_adds_nine_base_points(self):
        score, reasons = score_song(
            self._prefs(genre="rock", mood="intense", energy=0.9),
            self._song(genre="rock", mood="intense", energy=0.9),
        )
        assert score >= 9.0
        assert any("genre match" in r for r in reasons)
        assert any("mood match" in r for r in reasons)

    def test_energy_exact_match_adds_two_points(self):
        score, reasons = score_song(
            self._prefs(energy=0.6),
            self._song(energy=0.6),
        )
        assert any("energy closeness (+2.00)" in r for r in reasons)

    def test_energy_far_miss_adds_zero(self):
        score, reasons = score_song(
            self._prefs(energy=0.0),
            self._song(energy=1.0),
        )
        assert any("energy closeness (+0.00)" in r for r in reasons)

    def test_energy_partial_closeness_is_between_zero_and_two(self):
        score, reasons = score_song(
            self._prefs(energy=0.5),
            self._song(energy=0.8),
        )
        energy_reasons = [r for r in reasons if "energy closeness" in r]
        assert len(energy_reasons) == 1
        bonus = float(energy_reasons[0].split("(+")[1].rstrip(")"))
        assert 0.0 < bonus < 2.0

    def test_acoustic_bonus_when_acousticness_at_least_0_7(self):
        score, reasons = score_song(
            self._prefs(acoustic=True),
            self._song(acousticness=0.8),
        )
        assert any("acoustic match (+1" in r for r in reasons)

    def test_no_acoustic_bonus_below_threshold(self):
        score, reasons = score_song(
            self._prefs(acoustic=True),
            self._song(acousticness=0.3),
        )
        assert not any("acoustic match (+1" in r for r in reasons)

    def test_acoustic_not_checked_when_likes_acoustic_false(self):
        score, reasons = score_song(
            self._prefs(acoustic=False),
            self._song(acousticness=0.9),
        )
        assert not any("acoustic" in r for r in reasons)

    def test_no_matches_returns_fallback_reason(self):
        score, reasons = score_song(
            {"favorite_genre": "pop", "favorite_mood": "happy", "target_energy": 0.5},
            {"genre": "jazz", "mood": "sad", "energy": 0.5, "acousticness": 0.5},
        )
        assert len(reasons) > 0

    def test_score_never_negative(self):
        score, _ = score_song(
            self._prefs(genre="pop", mood="happy", energy=0.0),
            self._song(genre="jazz", mood="sad", energy=1.0),
        )
        assert score >= 0.0


# ── recommend_songs ───────────────────────────────────────────────────────────

class TestRecommendSongs:

    def test_returns_top_k_results(self, sample_songs, pop_prefs):
        results = recommend_songs(pop_prefs, sample_songs, k=2)
        assert len(results) == 2

    def test_results_sorted_by_score_descending(self, sample_songs, pop_prefs):
        results = recommend_songs(pop_prefs, sample_songs, k=3)
        scores = [score for _, score, _ in results]
        assert scores == sorted(scores, reverse=True)

    def test_best_matching_song_ranks_first(self, sample_songs, pop_prefs):
        results = recommend_songs(pop_prefs, sample_songs, k=3)
        top_song, _, _ = results[0]
        assert top_song["genre"] == "pop"
        assert top_song["mood"] == "happy"

    def test_k_larger_than_catalog_returns_all(self, sample_songs, pop_prefs):
        results = recommend_songs(pop_prefs, sample_songs, k=100)
        assert len(results) == len(sample_songs)

    def test_k_one_returns_single_best(self, sample_songs, pop_prefs):
        results = recommend_songs(pop_prefs, sample_songs, k=1)
        assert len(results) == 1
        song, _, _ = results[0]
        assert song["genre"] == "pop"

    def test_explanation_is_non_empty_string(self, sample_songs, pop_prefs):
        results = recommend_songs(pop_prefs, sample_songs, k=1)
        _, _, explanation = results[0]
        assert isinstance(explanation, str)
        assert explanation.strip() != ""

    def test_different_profile_returns_different_top_song(self, sample_songs):
        lofi_prefs = {"favorite_genre": "lofi", "favorite_mood": "chill", "target_energy": 0.4}
        results = recommend_songs(lofi_prefs, sample_songs, k=1)
        top_song, _, _ = results[0]
        assert top_song["genre"] == "lofi"


# ── load_songs ────────────────────────────────────────────────────────────────

class TestLoadSongs:

    def test_loads_correct_count(self):
        songs = load_songs(DATA_CSV)
        assert len(songs) == 18

    def test_energy_is_float(self):
        songs = load_songs(DATA_CSV)
        assert all(isinstance(s["energy"], float) for s in songs)

    def test_acousticness_is_float(self):
        songs = load_songs(DATA_CSV)
        assert all(isinstance(s["acousticness"], float) for s in songs)

    def test_id_is_int(self):
        songs = load_songs(DATA_CSV)
        assert all(isinstance(s["id"], int) for s in songs)

    def test_required_keys_present(self):
        songs = load_songs(DATA_CSV)
        required = {"id", "title", "artist", "genre", "mood", "energy", "acousticness"}
        for song in songs:
            assert required.issubset(song.keys()), f"Missing keys in song: {song}"

    def test_energy_values_in_range(self):
        songs = load_songs(DATA_CSV)
        for song in songs:
            assert 0.0 <= song["energy"] <= 1.0, f"Energy out of range: {song}"

    def test_acousticness_values_in_range(self):
        songs = load_songs(DATA_CSV)
        for song in songs:
            assert 0.0 <= song["acousticness"] <= 1.0, f"Acousticness out of range: {song}"


# ── _execute_tool  (agent tool dispatcher) ────────────────────────────────────

class TestExecuteTool:

    # browse_catalog
    def test_browse_catalog_returns_all_songs(self, sample_songs):
        result = json.loads(_execute_tool("browse_catalog", {}, sample_songs))
        assert result["total"] == 3
        assert len(result["songs"]) == 3

    def test_browse_catalog_includes_key_fields(self, sample_songs):
        result = json.loads(_execute_tool("browse_catalog", {}, sample_songs))
        fields = set(result["songs"][0].keys())
        assert {"title", "artist", "genre", "mood", "energy"}.issubset(fields)

    # get_recommendations
    def test_get_recommendations_returns_top_k(self, sample_songs):
        params = {
            "favorite_genre": "pop", "favorite_mood": "happy",
            "target_energy": 0.8, "num_recommendations": 2,
        }
        result = json.loads(_execute_tool("get_recommendations", params, sample_songs))
        assert len(result["recommendations"]) == 2

    def test_get_recommendations_sorted_by_score(self, sample_songs):
        params = {"favorite_genre": "pop", "favorite_mood": "happy", "target_energy": 0.8}
        result = json.loads(_execute_tool("get_recommendations", params, sample_songs))
        scores = [r["score"] for r in result["recommendations"]]
        assert scores == sorted(scores, reverse=True)

    def test_get_recommendations_top_is_genre_match(self, sample_songs):
        params = {"favorite_genre": "pop", "favorite_mood": "happy", "target_energy": 0.8}
        result = json.loads(_execute_tool("get_recommendations", params, sample_songs))
        assert result["recommendations"][0]["genre"] == "pop"

    def test_get_recommendations_echoes_params_used(self, sample_songs):
        params = {"favorite_genre": "lofi", "favorite_mood": "chill", "target_energy": 0.4}
        result = json.loads(_execute_tool("get_recommendations", params, sample_songs))
        assert result["params_used"]["favorite_genre"] == "lofi"

    # evaluate_quality
    def test_evaluate_quality_good_for_diverse_high_scores(self, sample_songs):
        recs = [
            {"genre": "pop",  "mood": "happy",   "score": 9.0},
            {"genre": "lofi", "mood": "chill",   "score": 8.0},
            {"genre": "rock", "mood": "intense", "score": 7.0},
        ]
        result = json.loads(
            _execute_tool("evaluate_quality", {"recommendations": recs, "user_request": "test"}, sample_songs)
        )
        assert result["quality"] == "good"
        assert result["genre_diversity"] == 3

    def test_evaluate_quality_flags_single_genre(self, sample_songs):
        recs = [
            {"genre": "pop", "mood": "happy",   "score": 8.5},
            {"genre": "pop", "mood": "intense", "score": 7.5},
        ]
        result = json.loads(
            _execute_tool("evaluate_quality", {"recommendations": recs, "user_request": "test"}, sample_songs)
        )
        assert any("diversity" in issue.lower() for issue in result["issues"])

    def test_evaluate_quality_flags_low_average_score(self, sample_songs):
        recs = [
            {"genre": "pop",  "mood": "happy", "score": 1.5},
            {"genre": "lofi", "mood": "chill", "score": 1.0},
        ]
        result = json.loads(
            _execute_tool("evaluate_quality", {"recommendations": recs, "user_request": "test"}, sample_songs)
        )
        assert result["quality"] in ("acceptable", "poor")
        assert any("score" in issue.lower() for issue in result["issues"])

    def test_evaluate_quality_empty_returns_poor(self, sample_songs):
        result = json.loads(
            _execute_tool("evaluate_quality", {"recommendations": [], "user_request": "test"}, sample_songs)
        )
        assert result["quality"] == "poor"

    def test_unknown_tool_returns_error(self, sample_songs):
        result = json.loads(_execute_tool("nonexistent_tool", {}, sample_songs))
        assert "error" in result


# ── OOP layer — Recommender / Song / UserProfile ──────────────────────────────

def _make_recommender() -> Recommender:
    songs = [
        Song(id=1, title="Test Pop Track", artist="Test Artist",
             genre="pop", mood="happy", energy=0.8, tempo_bpm=120,
             valence=0.9, danceability=0.8, acousticness=0.2),
        Song(id=2, title="Chill Lofi Loop", artist="Test Artist",
             genre="lofi", mood="chill", energy=0.4, tempo_bpm=80,
             valence=0.6, danceability=0.5, acousticness=0.9),
    ]
    return Recommender(songs)


def test_recommend_returns_songs_sorted_by_score():
    user = UserProfile(
        favorite_genre="pop", favorite_mood="happy",
        target_energy=0.8, likes_acoustic=False,
    )
    rec = _make_recommender()
    results = rec.recommend(user, k=2)

    assert len(results) == 2
    assert results[0].genre == "pop"
    assert results[0].mood == "happy"


def test_recommend_lofi_user_returns_lofi_first():
    user = UserProfile(
        favorite_genre="lofi", favorite_mood="chill",
        target_energy=0.4, likes_acoustic=True,
    )
    rec = _make_recommender()
    results = rec.recommend(user, k=2)
    assert results[0].genre == "lofi"


def test_explain_recommendation_returns_non_empty_string():
    user = UserProfile(
        favorite_genre="pop", favorite_mood="happy",
        target_energy=0.8, likes_acoustic=False,
    )
    rec = _make_recommender()
    explanation = rec.explain_recommendation(user, rec.songs[0])
    assert isinstance(explanation, str)
    assert explanation.strip() != ""


def test_explain_recommendation_mentions_genre_match():
    user = UserProfile(
        favorite_genre="pop", favorite_mood="happy",
        target_energy=0.8, likes_acoustic=False,
    )
    rec = _make_recommender()
    explanation = rec.explain_recommendation(user, rec.songs[0])
    assert "genre match" in explanation

#!/usr/bin/env python3
"""
Evaluation harness for the Music Recommender system.

Runs the rule-based scoring engine and agent tool dispatcher on a set of
predefined inputs, checks results against expected criteria, and prints a
formatted pass/fail summary with confidence scores.

No API key required — all checks use local scoring logic only.

Usage:
    python evaluate.py
"""

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))
from src.recommender import load_songs, recommend_songs, score_song
from src.agent import _execute_tool

# ── Constants ─────────────────────────────────────────────────────────────────

DATA_CSV    = str(Path(__file__).parent / "data" / "songs.csv")
MAX_SCORE   = 12.0   # genre(5) + mood(4) + energy(2) + acoustic(1)
PASS  = "✅ PASS"
FAIL  = "❌ FAIL"

# ── Result types ──────────────────────────────────────────────────────────────

@dataclass
class Check:
    label: str
    passed: bool
    detail: str = ""

@dataclass
class CaseResult:
    id: str
    name: str
    checks: list[Check] = field(default_factory=list)
    top_score: float = 0.0

    @property
    def passed(self) -> bool:
        return all(c.passed for c in self.checks)

    @property
    def confidence(self) -> float:
        return round(min(1.0, self.top_score / MAX_SCORE), 2)

# ── Helpers ───────────────────────────────────────────────────────────────────

def check(label: str, cond: bool, detail: str = "") -> Check:
    return Check(label=label, passed=cond, detail=detail)

# ── Test cases: scoring engine ────────────────────────────────────────────────

def run_scoring_cases(songs: list[dict]) -> list[CaseResult]:
    cases = [
        {
            "id": "SC-01",
            "name": "Pop / happy / high energy",
            "prefs": {"favorite_genre": "pop", "favorite_mood": "happy",
                      "target_energy": 0.85},
            "k": 5,
            "expect_top_genre": "pop",
            "expect_top_mood":  "happy",
            "expect_min_score": 9.0,
        },
        {
            "id": "SC-02",
            "name": "Lofi / chill / study (acoustic)",
            "prefs": {"favorite_genre": "lofi", "favorite_mood": "chill",
                      "target_energy": 0.40, "likes_acoustic": True},
            "k": 5,
            "expect_top_genre": "lofi",
            "expect_top_mood":  "chill",
            "expect_min_score": 10.0,
        },
        {
            "id": "SC-03",
            "name": "Rock / intense / workout",
            "prefs": {"favorite_genre": "rock", "favorite_mood": "intense",
                      "target_energy": 0.90},
            "k": 5,
            "expect_top_genre": "rock",
            "expect_top_mood":  "intense",
            "expect_min_score": 9.0,
        },
        {
            "id": "SC-04",
            "name": "Jazz / relaxed / evening (acoustic)",
            "prefs": {"favorite_genre": "jazz", "favorite_mood": "relaxed",
                      "target_energy": 0.40, "likes_acoustic": True},
            "k": 3,
            "expect_top_genre": "jazz",
            "expect_top_mood":  "relaxed",
            "expect_min_score": 10.0,
        },
        {
            "id": "SC-05",
            "name": "Folk / melancholic / acoustic — perfect match",
            "prefs": {"favorite_genre": "folk", "favorite_mood": "melancholic",
                      "target_energy": 0.45, "likes_acoustic": True},
            "k": 3,
            "expect_top_genre": "folk",
            "expect_top_mood":  "melancholic",
            "expect_min_score": 11.5,
        },
        {
            "id": "SC-06",
            "name": "Synthwave / moody / night drive",
            "prefs": {"favorite_genre": "synthwave", "favorite_mood": "moody",
                      "target_energy": 0.75},
            "k": 5,
            "expect_top_genre": "synthwave",
            "expect_top_mood":  "moody",
            "expect_min_score": 10.0,
        },
        {
            "id": "SC-07",
            "name": "Classical / dreamy / acoustic — perfect match",
            "prefs": {"favorite_genre": "classical", "favorite_mood": "dreamy",
                      "target_energy": 0.30, "likes_acoustic": True},
            "k": 3,
            "expect_top_genre": "classical",
            "expect_top_mood":  "dreamy",
            "expect_min_score": 11.5,
        },
        {
            "id": "SC-08",
            "name": "Metal / energetic / max energy",
            "prefs": {"favorite_genre": "metal", "favorite_mood": "energetic",
                      "target_energy": 0.95},
            "k": 5,
            "expect_top_genre": "metal",
            "expect_top_mood":  "energetic",
            "expect_min_score": 10.0,
        },
        {
            "id": "SC-09",
            "name": "Sort order integrity (pop profile, k=10)",
            "prefs": {"favorite_genre": "pop", "favorite_mood": "happy",
                      "target_energy": 0.80},
            "k": 10,
            "expect_top_genre": None,
            "expect_top_mood":  None,
            "expect_min_score": 0.0,
        },
        {
            "id": "SC-10",
            "name": "Score range validity — no negative scores",
            "prefs": {"favorite_genre": "pop", "favorite_mood": "happy",
                      "target_energy": 0.80},
            "k": len(songs),
            "expect_top_genre": None,
            "expect_top_mood":  None,
            "expect_min_score": 0.0,
        },
        {
            "id": "SC-11",
            "name": "Unknown genre — still returns k results",
            "prefs": {"favorite_genre": "unknown_genre", "favorite_mood": "happy",
                      "target_energy": 0.50},
            "k": 5,
            "expect_top_genre": None,
            "expect_top_mood":  None,
            "expect_min_score": 0.0,
        },
        {
            "id": "SC-12",
            "name": "Energy targeting — top song within 0.2 of target",
            "prefs": {"favorite_genre": "ambient", "favorite_mood": "chill",
                      "target_energy": 0.30},
            "k": 1,
            "expect_top_genre": "ambient",
            "expect_top_mood":  None,
            "expect_min_score": 5.0,
        },
    ]

    results = []
    for tc in cases:
        r = CaseResult(id=tc["id"], name=tc["name"])
        recs = recommend_songs(tc["prefs"], songs, k=tc["k"])

        if not recs:
            r.checks.append(check("has results", False, "recommend_songs returned empty list"))
            results.append(r)
            continue

        top_song, top_score, _ = recs[0]
        r.top_score = top_score
        scores = [s for _, s, _ in recs]

        # Check: minimum top score
        r.checks.append(check(
            f"top score ≥ {tc['expect_min_score']}",
            top_score >= tc["expect_min_score"],
            f"got {top_score:.2f}",
        ))

        # Check: correct number of results returned
        r.checks.append(check(
            f"returns {tc['k']} result(s)",
            len(recs) == tc["k"],
            f"got {len(recs)}",
        ))

        # Check: top song genre (if specified)
        if tc["expect_top_genre"]:
            r.checks.append(check(
                f"top genre = {tc['expect_top_genre']}",
                top_song["genre"] == tc["expect_top_genre"],
                f"got \"{top_song['genre']}\"",
            ))

        # Check: top song mood (if specified)
        if tc["expect_top_mood"]:
            r.checks.append(check(
                f"top mood = {tc['expect_top_mood']}",
                top_song["mood"] == tc["expect_top_mood"],
                f"got \"{top_song['mood']}\"",
            ))

        # Always check: results sorted descending
        r.checks.append(check(
            "sorted descending",
            scores == sorted(scores, reverse=True),
            f"scores: {[round(s,2) for s in scores]}",
        ))

        # Always check: no negative scores
        r.checks.append(check(
            "no negative scores",
            all(s >= 0 for s in scores),
            f"min score: {min(scores):.2f}",
        ))

        # SC-12 extra: energy within 0.2 of target
        if tc["id"] == "SC-12":
            target = tc["prefs"]["target_energy"]
            diff = abs(top_song["energy"] - target)
            r.checks.append(check(
                "top song energy within 0.2 of target",
                diff <= 0.2,
                f"|{top_song['energy']:.2f} - {target}| = {diff:.2f}",
            ))

        results.append(r)
    return results


# ── Test cases: agent tool dispatcher ────────────────────────────────────────

def run_agent_tool_cases(songs: list[dict]) -> list[CaseResult]:
    cases_raw = []

    # AT-01: browse_catalog
    expected_total = len(songs)
    r = CaseResult(id="AT-01", name="browse_catalog — returns full catalog")
    result = json.loads(_execute_tool("browse_catalog", {}, songs))
    r.checks.append(check(f"total = {expected_total}", result.get("total") == expected_total, f"got {result.get('total')}"))
    r.checks.append(check(f"songs list = {expected_total}", len(result.get("songs", [])) == expected_total))
    r.checks.append(check("has title field",  "title" in result["songs"][0]))
    r.checks.append(check("has energy field", "energy" in result["songs"][0]))
    cases_raw.append(r)

    # AT-02: get_recommendations sorted
    r = CaseResult(id="AT-02", name="get_recommendations — sorted by score")
    params = {"favorite_genre": "pop", "favorite_mood": "happy", "target_energy": 0.8}
    result = json.loads(_execute_tool("get_recommendations", params, songs))
    recs = result.get("recommendations", [])
    scores = [rec["score"] for rec in recs]
    r.top_score = scores[0] if scores else 0.0
    r.checks.append(check("returns 5 results",     len(recs) == 5,                          f"got {len(recs)}"))
    r.checks.append(check("sorted descending",     scores == sorted(scores, reverse=True),  f"{scores}"))
    r.checks.append(check("top genre = pop",       recs[0]["genre"] == "pop",               f"got \"{recs[0]['genre']}\""))
    r.checks.append(check("echoes params_used",    "params_used" in result))
    cases_raw.append(r)

    # AT-03: get_recommendations with num_recommendations
    r = CaseResult(id="AT-03", name="get_recommendations — honours num_recommendations=3")
    params = {"favorite_genre": "lofi", "favorite_mood": "chill",
              "target_energy": 0.4, "num_recommendations": 3}
    result = json.loads(_execute_tool("get_recommendations", params, songs))
    recs = result.get("recommendations", [])
    r.top_score = recs[0]["score"] if recs else 0.0
    r.checks.append(check("returns exactly 3", len(recs) == 3, f"got {len(recs)}"))
    r.checks.append(check("top genre = lofi",  recs[0]["genre"] == "lofi", f"got \"{recs[0]['genre']}\""))
    cases_raw.append(r)

    # AT-04: evaluate_quality — good result
    r = CaseResult(id="AT-04", name="evaluate_quality — good for diverse high-score recs")
    recs_in = [
        {"genre": "pop",       "mood": "happy",   "score": 10.0},
        {"genre": "lofi",      "mood": "chill",   "score": 9.0},
        {"genre": "rock",      "mood": "intense", "score": 8.0},
        {"genre": "jazz",      "mood": "relaxed", "score": 7.5},
        {"genre": "synthwave", "mood": "moody",   "score": 7.0},
    ]
    result = json.loads(_execute_tool("evaluate_quality", {"recommendations": recs_in, "user_request": "test"}, songs))
    r.top_score = recs_in[0]["score"]
    r.checks.append(check("quality = good",         result["quality"] == "good",    f"got \"{result['quality']}\""))
    r.checks.append(check("genre_diversity = 5",    result["genre_diversity"] == 5, f"got {result.get('genre_diversity')}"))
    r.checks.append(check("no issues reported",     len(result.get("issues", [])) == 0))
    cases_raw.append(r)

    # AT-05: evaluate_quality — flags low diversity
    r = CaseResult(id="AT-05", name="evaluate_quality — flags single-genre result")
    recs_in = [
        {"genre": "lofi", "mood": "chill",   "score": 8.0},
        {"genre": "lofi", "mood": "focused", "score": 7.5},
        {"genre": "lofi", "mood": "chill",   "score": 7.0},
    ]
    result = json.loads(_execute_tool("evaluate_quality", {"recommendations": recs_in, "user_request": "test"}, songs))
    r.checks.append(check("quality ≠ good",          result["quality"] != "good"))
    r.checks.append(check("diversity issue flagged",
                          any("diversity" in i.lower() for i in result.get("issues", [])),
                          f"issues: {result.get('issues')}"))
    cases_raw.append(r)

    # AT-06: evaluate_quality — empty input
    r = CaseResult(id="AT-06", name="evaluate_quality — empty recommendations → poor")
    result = json.loads(_execute_tool("evaluate_quality", {"recommendations": [], "user_request": "test"}, songs))
    r.checks.append(check("quality = poor", result["quality"] == "poor", f"got \"{result['quality']}\""))
    r.checks.append(check("has issues",     len(result.get("issues", [])) > 0))
    cases_raw.append(r)

    # AT-07: unknown tool
    r = CaseResult(id="AT-07", name="unknown tool — returns error, not exception")
    result = json.loads(_execute_tool("nonexistent", {}, songs))
    r.checks.append(check("error key present", "error" in result, f"got keys: {list(result.keys())}"))
    cases_raw.append(r)

    return cases_raw


# ── Printer ───────────────────────────────────────────────────────────────────

def print_group(title: str, results: list[CaseResult]) -> tuple[int, int]:
    width = 64
    passed = sum(1 for r in results if r.passed)
    total  = len(results)

    print(f"\n  {title}")
    print(f"  {'─' * (width - 2)}")

    for r in results:
        status = PASS if r.passed else FAIL
        conf   = f"confidence={r.confidence:.2f}" if r.top_score > 0 else ""
        header = f"  {status}  {r.id}  {r.name}"
        print(f"{header:<60}  {conf}")

        for c in r.checks:
            sym    = "    ·" if c.passed else "    !"
            detail = f"  ({c.detail})" if c.detail else ""
            print(f"{sym}  {c.label}{detail}")

    print(f"\n  {passed}/{total} passed")
    return passed, total


def print_report(scoring: list[CaseResult], tools: list[CaseResult]) -> None:
    width = 64
    songs_count = len(load_songs(DATA_CSV))

    print()
    print("  " + "═" * width)
    print("  Music Recommender — Evaluation Report")
    print(f"  {songs_count} songs loaded  ·  "
          f"{len(scoring)} scoring cases  ·  {len(tools)} tool cases")
    print("  " + "═" * width)

    sp, st = print_group("SCORING ENGINE CHECKS", scoring)
    tp, tt = print_group("AGENT TOOL CHECKS", tools)

    total_passed = sp + tp
    total_cases  = st + tt

    sc_scores = [r.top_score for r in scoring if r.top_score > 0]
    avg_score  = sum(sc_scores) / len(sc_scores) if sc_scores else 0.0
    avg_conf   = round(avg_score / MAX_SCORE, 2)
    pct        = int(100 * total_passed / total_cases) if total_cases else 0

    print()
    print("  " + "═" * width)
    print("  SUMMARY")
    print(f"  Scoring engine : {sp}/{st} passed  "
          f"avg top-score={avg_score:.2f}  avg confidence={avg_conf:.2f}")
    print(f"  Agent tools    : {tp}/{tt} passed")
    print(f"  Overall        : {total_passed}/{total_cases} passed  ({pct}%)")
    print("  " + "═" * width)
    print()

    sys.exit(0 if total_passed == total_cases else 1)


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    songs = load_songs(DATA_CSV)
    scoring_results  = run_scoring_cases(songs)
    tool_results     = run_agent_tool_cases(songs)
    print_report(scoring_results, tool_results)

import json
import sys
from pathlib import Path
from typing import Any

import anthropic
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")  # music-recommender/.env
load_dotenv(dotenv_path=Path(__file__).parent.parent.parent / ".env")  # music-recommander/.env

# Support both `python -m src.agent` (from project root) and `python src/agent.py` (directly)
if __package__ is None:
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from recommender import load_songs, score_song
else:
    from src.recommender import load_songs, score_song

SONGS_PATH = Path(__file__).parent.parent / "data" / "songs.csv"

SYSTEM_PROMPT = """You are a music recommendation agent. For every request, follow these four phases:

1. PLAN: Understand the user's taste from their natural language request.
   Identify genre, mood, energy (0.0–1.0), and acoustic preference.
   Browse the catalog first if you are unsure what is available.

2. ACT: Call get_recommendations with your inferred preferences.

3. CHECK: Call evaluate_quality on the results to assess diversity and relevance.

4. FIX: If quality is "poor" or "acceptable" with issues, adjust your parameters
   and call get_recommendations again. Up to 2 retries are allowed.

End with a clear explanation of your final recommendations and why they fit the request.

Available genres: pop, lofi, rock, ambient, jazz, synthwave, indie pop, classical, folk, reggae, blues, metal, electronic, country, world
Available moods: happy, chill, intense, melancholic, relaxed, focused, moody, dreamy, upbeat, soulful, energetic, peaceful, playful, dreamlike"""

TOOLS = [
    {
        "name": "browse_catalog",
        "description": "Browse the full song catalog to see what genres, moods, and artists are available.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_recommendations",
        "description": "Score and rank songs by user preferences. Returns top K songs with scores and match reasons.",
        "input_schema": {
            "type": "object",
            "properties": {
                "favorite_genre": {
                    "type": "string",
                    "description": "User's preferred genre (e.g. pop, rock, lofi)",
                },
                "favorite_mood": {
                    "type": "string",
                    "description": "Preferred mood (e.g. happy, chill, intense)",
                },
                "target_energy": {
                    "type": "number",
                    "description": "Target energy 0.0 (calm) to 1.0 (intense)",
                },
                "likes_acoustic": {
                    "type": "boolean",
                    "description": "Whether the user prefers acoustic songs",
                },
                "num_recommendations": {
                    "type": "integer",
                    "description": "How many songs to return (default 5)",
                },
            },
            "required": ["favorite_genre", "favorite_mood", "target_energy"],
        },
    },
    {
        "name": "evaluate_quality",
        "description": "Check recommendation quality: diversity, score distribution, and fit with the request.",
        "input_schema": {
            "type": "object",
            "properties": {
                "recommendations": {
                    "type": "array",
                    "description": "Recommendation objects returned by get_recommendations",
                    "items": {"type": "object"},
                },
                "user_request": {
                    "type": "string",
                    "description": "The original user request for context",
                },
            },
            "required": ["recommendations", "user_request"],
        },
    },
]


def _execute_tool(name: str, tool_input: dict[str, Any], songs: list[dict]) -> str:
    if name == "browse_catalog":
        catalog = [
            {
                "title": s["title"],
                "artist": s["artist"],
                "genre": s["genre"],
                "mood": s["mood"],
                "energy": s["energy"],
                "acousticness": s["acousticness"],
            }
            for s in songs
        ]
        return json.dumps({"total": len(catalog), "songs": catalog})

    if name == "get_recommendations":
        user_prefs = {
            "favorite_genre": tool_input["favorite_genre"],
            "favorite_mood": tool_input["favorite_mood"],
            "target_energy": tool_input["target_energy"],
            "likes_acoustic": tool_input.get("likes_acoustic", False),
        }
        k = tool_input.get("num_recommendations", 5)

        scored = []
        for song in songs:
            score, reasons = score_song(user_prefs, song)
            scored.append(
                {
                    "title": song["title"],
                    "artist": song["artist"],
                    "genre": song["genre"],
                    "mood": song["mood"],
                    "score": round(score, 2),
                    "reasons": reasons,
                }
            )
        scored.sort(key=lambda x: x["score"], reverse=True)
        return json.dumps({"recommendations": scored[:k], "params_used": user_prefs})

    if name == "evaluate_quality":
        recs = tool_input.get("recommendations", [])
        if not recs:
            return json.dumps({"quality": "poor", "issues": ["No recommendations to evaluate"]})

        genres = {r["genre"] for r in recs}
        scores = [r["score"] for r in recs]
        avg_score = sum(scores) / len(scores)

        issues = []
        if len(genres) == 1:
            issues.append(f"Low genre diversity — all songs are {next(iter(genres))}")
        if avg_score < 3.0:
            issues.append(f"Low average match score ({avg_score:.1f}); consider adjusting genre or mood")
        if scores[0] < 5.0:
            issues.append("Top song has no strong genre/mood match; params may need tuning")

        quality = "good" if not issues else ("acceptable" if len(issues) == 1 else "poor")
        return json.dumps(
            {
                "quality": quality,
                "issues": issues,
                "genre_diversity": len(genres),
                "unique_genres": sorted(genres),
                "avg_score": round(avg_score, 2),
                "top_score": round(scores[0], 2),
            }
        )

    return json.dumps({"error": f"Unknown tool: {name}"})


def run_agent(user_request: str, verbose: bool = True) -> str:
    """
    Run the agentic music recommendation workflow.

    Uses a plan → act → check → fix loop driven by Claude's tool_use.
    The agent infers preferences from natural language, fetches recommendations,
    self-evaluates quality, and retries with adjusted params if needed.
    """
    client = anthropic.Anthropic()
    songs = load_songs(str(SONGS_PATH))

    messages: list[dict] = [{"role": "user", "content": user_request}]

    if verbose:
        print(f"\n[Agent] Request: {user_request!r}\n")

    STEP_LABELS = {
        "browse_catalog":      "PLAN  — browse catalog",
        "get_recommendations": "ACT   — get recommendations",
        "evaluate_quality":    "CHECK — evaluate quality",
    }

    for iteration in range(10):
        if verbose:
            print(f"{'─' * 60}")
            print(f"  Iteration {iteration + 1}")
            print(f"{'─' * 60}")

        response = client.messages.create(
            model="claude-opus-4-7",
            max_tokens=4096,
            # Cache the stable system prompt to reduce costs on repeated calls
            system=[
                {
                    "type": "text",
                    "text": SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            tools=TOOLS,
            messages=messages,
        )

        messages.append({"role": "assistant", "content": response.content})

        # Show every block in order: reasoning text first, then tool calls.
        # This makes the full PLAN → ACT → CHECK → FIX chain observable.
        if verbose:
            for block in response.content:
                if hasattr(block, "text") and block.text.strip():
                    # Claude's planning / reasoning narration
                    for line in block.text.strip().splitlines():
                        print(f"  💭 {line}")
                    print()

        if response.stop_reason == "end_turn":
            final_text = "".join(
                block.text for block in response.content if hasattr(block, "text")
            )
            if verbose:
                print(f"[Agent] Done in {iteration + 1} iteration(s).\n")
            return final_text

        # Execute all tool calls and collect results
        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue

            label = STEP_LABELS.get(block.name, block.name)

            if verbose:
                print(f"  ▶ {label}")
                print(f"    input : {json.dumps(block.input)[:200]}")

            result_str = _execute_tool(block.name, block.input, songs)

            if verbose:
                result = json.loads(result_str)
                if "recommendations" in result:
                    top = result["recommendations"][0] if result["recommendations"] else {}
                    print(
                        f"    result: {len(result['recommendations'])} songs returned — "
                        f"top: \"{top.get('title')}\" (score={top.get('score')})"
                    )
                elif "quality" in result:
                    quality = result["quality"]
                    issues  = result.get("issues") or []
                    verdict = "✔ no issues" if not issues else "✘ " + "; ".join(issues)
                    print(f"    result: quality={quality} — {verdict}")
                    if quality in ("acceptable", "poor"):
                        print(f"    FIX   — adjusting parameters and retrying …")
                else:
                    print(f"    result: {result.get('total', '?')} songs in catalog")
                print()

            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result_str,
                }
            )

        if tool_results:
            messages.append({"role": "user", "content": tool_results})

    return "Agent reached maximum iterations without a final answer."


if __name__ == "__main__":
    request = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "I want energetic music to work out to!"
    print(run_agent(request))

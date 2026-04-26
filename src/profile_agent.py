"""
Profile agent: reads a user's liked/disliked song history and calls Claude to
infer a structured taste profile (genre, mood, energy, acoustic preference).
The result is saved back to music_profiles so Quick Recommend and the AI Agent
can use it for pre-filling and seeding recommendations.
"""

import anthropic
from bson import ObjectId
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")
load_dotenv(dotenv_path=Path(__file__).parent.parent.parent / ".env")

_PROFILE_TOOL = {
    "name": "update_user_profile",
    "description": (
        "Set the inferred user taste profile based on their like/dislike history. "
        "Call this once with your final analysis."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "favorite_genre": {
                "type": "string",
                "description": "The genre the user most prefers (must be one of the available genres)",
            },
            "favorite_mood": {
                "type": "string",
                "description": "The mood they prefer most (must be one of the available moods)",
            },
            "target_energy": {
                "type": "number",
                "description": "Preferred energy level: 0.0 (very calm) to 1.0 (very intense)",
            },
            "likes_acoustic": {
                "type": "boolean",
                "description": "True if the user tends to prefer acoustic songs",
            },
            "confidence": {
                "type": "string",
                "enum": ["low", "medium", "high"],
                "description": "Confidence based on amount and consistency of history",
            },
            "reasoning": {
                "type": "string",
                "description": "One or two sentences explaining how the profile was inferred",
            },
        },
        "required": [
            "favorite_genre", "favorite_mood", "target_energy",
            "likes_acoustic", "confidence", "reasoning",
        ],
    },
}

_SYSTEM_TEMPLATE = (
    "You are a music taste analyst. Analyze the user's liked and disliked songs to infer "
    "their taste profile. Treat likes as positive signals and dislikes as negative signals — "
    "if a genre or mood appears often in dislikes, down-weight it even if it also appears in likes. "
    "Use the energy values (0.0–1.0) of liked songs to estimate target_energy. "
    "Set likes_acoustic=true only if liked songs consistently have high acousticness (≥0.6). "
    "Available genres: {genres}. "
    "Available moods: {moods}. "
    "Call update_user_profile exactly once with your final analysis."
)

MIN_HISTORY = 2


def build_user_profile(user_id: ObjectId, songs_catalog: list[dict]) -> dict | None:
    """
    Infer a taste profile from the user's like/dislike history using Claude.

    Returns the profile dict on success, or None if there is not enough history
    or no API key is configured.
    """
    from src.auth import get_liked_songs, get_disliked_songs, save_music_profile

    liked    = get_liked_songs(user_id)
    disliked = get_disliked_songs(user_id)

    if len(liked) + len(disliked) < MIN_HISTORY:
        return None

    # Enrich like/dislike records with energy + acousticness from the catalog
    catalog_by_id = {s["id"]: s for s in songs_catalog}

    def _enrich(records: list[dict]) -> list[dict]:
        out = []
        for r in records:
            cat = catalog_by_id.get(r["song_id"], {})
            out.append({
                "title":        r["title"],
                "artist":       r["artist"],
                "genre":        r["genre"],
                "mood":         r["mood"],
                "energy":       cat.get("energy", "?"),
                "acousticness": cat.get("acousticness", "?"),
            })
        return out

    liked_rich    = _enrich(liked)
    disliked_rich = _enrich(disliked)

    def _fmt(songs: list[dict]) -> str:
        return "\n".join(
            f"  • {s['title']} by {s['artist']} | genre={s['genre']} mood={s['mood']} "
            f"energy={s['energy']} acousticness={s['acousticness']}"
            for s in songs
        )

    history = ""
    if liked_rich:
        history += f"LIKED ({len(liked_rich)} songs):\n{_fmt(liked_rich)}\n"
    if disliked_rich:
        history += f"\nDISLIKED ({len(disliked_rich)} songs):\n{_fmt(disliked_rich)}\n"

    genres = ", ".join(sorted({s["genre"] for s in songs_catalog}))
    moods  = ", ".join(sorted({s["mood"]  for s in songs_catalog}))
    system = _SYSTEM_TEMPLATE.format(genres=genres, moods=moods)

    client = anthropic.Anthropic()
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=system,
        tools=[_PROFILE_TOOL],
        tool_choice={"type": "any"},
        messages=[{
            "role": "user",
            "content": (
                f"Here is my music history:\n\n{history}\n"
                "Please infer my taste profile and call update_user_profile."
            ),
        }],
    )

    for block in response.content:
        if block.type == "tool_use" and block.name == "update_user_profile":
            profile = block.input
            save_music_profile(user_id, profile)
            return profile

    return None

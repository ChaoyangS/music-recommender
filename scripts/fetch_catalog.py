"""
One-time script to build data/songs.csv from real iTunes tracks.

Usage:
    python scripts/fetch_catalog.py

No API key required — uses the free iTunes Search API.
"""

import csv
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

ITUNES_SEARCH = "https://itunes.apple.com/search"
SONGS_PER_GENRE = 10

FIELDNAMES = [
    "id", "title", "artist", "genre", "mood",
    "energy", "tempo_bpm", "valence", "danceability", "acousticness",
    "preview_url",
]

# Search term + audio feature defaults per genre.
GENRE_CONFIG: dict[str, dict] = {
    "pop":        {"term": "pop",              "mood": "happy",       "energy": 0.78, "valence": 0.80, "acousticness": 0.18, "danceability": 0.78, "tempo": 118},
    "lofi":       {"term": "lofi chill",       "mood": "chill",       "energy": 0.38, "valence": 0.55, "acousticness": 0.75, "danceability": 0.60, "tempo":  78},
    "rock":       {"term": "rock",             "mood": "intense",     "energy": 0.88, "valence": 0.52, "acousticness": 0.12, "danceability": 0.62, "tempo": 148},
    "ambient":    {"term": "ambient",          "mood": "relaxed",     "energy": 0.28, "valence": 0.60, "acousticness": 0.88, "danceability": 0.35, "tempo":  62},
    "jazz":       {"term": "jazz",             "mood": "soulful",     "energy": 0.42, "valence": 0.65, "acousticness": 0.82, "danceability": 0.52, "tempo":  92},
    "synthwave":  {"term": "synthwave",        "mood": "moody",       "energy": 0.76, "valence": 0.50, "acousticness": 0.08, "danceability": 0.72, "tempo": 112},
    "indie pop":  {"term": "indie pop",        "mood": "dreamy",      "energy": 0.65, "valence": 0.70, "acousticness": 0.38, "danceability": 0.68, "tempo": 122},
    "classical":  {"term": "classical piano",  "mood": "peaceful",    "energy": 0.28, "valence": 0.58, "acousticness": 0.95, "danceability": 0.22, "tempo":  68},
    "folk":       {"term": "folk acoustic",    "mood": "melancholic", "energy": 0.42, "valence": 0.48, "acousticness": 0.85, "danceability": 0.40, "tempo":  98},
    "reggae":     {"term": "reggae",           "mood": "upbeat",      "energy": 0.62, "valence": 0.72, "acousticness": 0.48, "danceability": 0.68, "tempo":  88},
    "blues":      {"term": "blues",            "mood": "soulful",     "energy": 0.52, "valence": 0.45, "acousticness": 0.68, "danceability": 0.48, "tempo":  84},
    "metal":      {"term": "heavy metal",      "mood": "energetic",   "energy": 0.95, "valence": 0.22, "acousticness": 0.05, "danceability": 0.52, "tempo": 168},
    "electronic": {"term": "electronic dance", "mood": "playful",     "energy": 0.84, "valence": 0.72, "acousticness": 0.06, "danceability": 0.88, "tempo": 128},
    "country":    {"term": "country",          "mood": "relaxed",     "energy": 0.58, "valence": 0.65, "acousticness": 0.62, "danceability": 0.52, "tempo":  96},
    "world":      {"term": "world music",      "mood": "dreamlike",   "energy": 0.55, "valence": 0.65, "acousticness": 0.58, "danceability": 0.55, "tempo": 104},
}


def fetch_itunes(term: str, limit: int = 20) -> list[dict]:
    resp = requests.get(
        ITUNES_SEARCH,
        params={"term": term, "media": "music", "entity": "song", "limit": limit},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json().get("results", [])


def main() -> None:
    out_path = ROOT / "data" / "songs.csv"
    rows: list[dict] = []
    song_id = 1
    seen: set[str] = set()

    for genre, cfg in GENRE_CONFIG.items():
        print(f"Fetching '{genre}'…", end=" ", flush=True)

        try:
            results = fetch_itunes(cfg["term"], limit=SONGS_PER_GENRE * 3)
        except Exception as e:
            print(f"✗ {e}")
            continue

        added = 0
        for track in results:
            if added >= SONGS_PER_GENRE:
                break

            preview_url = track.get("previewUrl", "")
            title       = track.get("trackName", "").strip()
            artist      = track.get("artistName", "").strip()
            key         = f"{title}|{artist}".lower()

            if not preview_url or not title or not artist or key in seen:
                continue

            rows.append({
                "id":           song_id,
                "title":        title,
                "artist":       artist,
                "genre":        genre,
                "mood":         cfg["mood"],
                "energy":       cfg["energy"],
                "tempo_bpm":    cfg["tempo"],
                "valence":      cfg["valence"],
                "danceability": cfg["danceability"],
                "acousticness": cfg["acousticness"],
                "preview_url":  preview_url,
            })
            seen.add(key)
            song_id += 1
            added += 1

        print(f"✓ {added} songs")
        time.sleep(0.3)

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nWrote {len(rows)} songs → {out_path}")


if __name__ == "__main__":
    main()

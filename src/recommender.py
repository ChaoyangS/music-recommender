import csv
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

@dataclass
class Song:
    """
    Represents a song and its attributes.
    Required by tests/test_recommender.py
    """
    id: int
    title: str
    artist: str
    genre: str
    mood: str
    energy: float
    tempo_bpm: float
    valence: float
    danceability: float
    acousticness: float

@dataclass
class UserProfile:
    """
    Represents a user's taste preferences.
    Required by tests/test_recommender.py
    """
    favorite_genre: str
    favorite_mood: str
    target_energy: float
    likes_acoustic: bool

class Recommender:
    """
    OOP implementation of the recommendation logic.
    Required by tests/test_recommender.py
    """
    def __init__(self, songs: List[Song]):
        self.songs = songs

    def recommend(self, user: UserProfile, k: int = 5) -> List[Song]:
        user_prefs = {
            "favorite_genre": user.favorite_genre,
            "favorite_mood": user.favorite_mood,
            "target_energy": user.target_energy,
            "likes_acoustic": user.likes_acoustic,
        }
        song_dicts = [vars(s) for s in self.songs]
        scored = []
        for song, s_dict in zip(self.songs, song_dicts):
            score, _ = score_song(user_prefs, s_dict)
            scored.append((score, song))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [song for _, song in scored[:k]]

    def explain_recommendation(self, user: UserProfile, song: Song) -> str:
        user_prefs = {
            "favorite_genre": user.favorite_genre,
            "favorite_mood": user.favorite_mood,
            "target_energy": user.target_energy,
            "likes_acoustic": user.likes_acoustic,
        }
        _, reasons = score_song(user_prefs, vars(song))
        return "; ".join(reasons)

def load_songs(csv_path: str) -> List[Dict]:
    """Load songs from a CSV file and convert numeric fields."""
    songs: List[Dict] = []
    csv_file = Path(csv_path)
    if not csv_file.is_absolute():
        csv_file = Path(__file__).resolve().parent.parent / csv_path

    with csv_file.open(newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            song = {
                "id":           int(row["id"]),
                "title":        row["title"],
                "artist":       row["artist"],
                "genre":        row["genre"],
                "mood":         row["mood"],
                "energy":       float(row["energy"]),
                "tempo_bpm":    float(row["tempo_bpm"]),
                "valence":      float(row["valence"]),
                "danceability": float(row["danceability"]),
                "acousticness": float(row["acousticness"]),
                "preview_url":  row.get("preview_url", ""),
            }
            songs.append(song)

    return songs

def score_song(user_prefs: Dict, song: Dict) -> Tuple[float, List[str]]:
    """Score a song against user preferences and return score details."""
    reasons: List[str] = []
    score = 0.0

    genre_pref = user_prefs.get("genre") or user_prefs.get("favorite_genre")
    mood_pref = user_prefs.get("mood") or user_prefs.get("favorite_mood")
    target_energy = user_prefs.get("energy") if "energy" in user_prefs else user_prefs.get("target_energy")
    likes_acoustic = user_prefs.get("likes_acoustic", False)

    if genre_pref and song.get("genre") == genre_pref:
        score += 5.0
        reasons.append("genre match (+5.0)")

    if mood_pref and song.get("mood") == mood_pref:
        score += 4.0
        reasons.append("mood match (+4.0)")

    if target_energy is not None:
        energy_diff = abs(song.get("energy", 0.0) - float(target_energy))
        energy_score = max(0.0, 2.0 - energy_diff * 2.0)
        score += energy_score
        reasons.append(f"energy closeness (+{energy_score:.2f})")

    if likes_acoustic:
        acousticness = song.get("acousticness", 0.0)
        if acousticness >= 0.7:
            score += 1.0
            reasons.append("acoustic match (+1.0)")
        else:
            reasons.append("acoustic preference (+0.0)")

    if not reasons:
        reasons.append("no strong matches found")

    return score, reasons

def recommend_songs(user_prefs: Dict, songs: List[Dict], k: int = 5) -> List[Tuple[Dict, float, str]]:
    """Rank songs using score_song and return the top K recommendations with genre diversity."""
    scored_songs: List[Tuple[Dict, float, str]] = []
    for song in songs:
        score, reasons = score_song(user_prefs, song)
        scored_songs.append((song, score, "; ".join(reasons)))

    scored_songs.sort(key=lambda item: item[1], reverse=True)

    # Cap per-genre so results span multiple genres
    max_per_genre = max(1, (k + 2) // 3)
    results: List[Tuple[Dict, float, str]] = []
    genre_counts: Dict[str, int] = {}
    for item in scored_songs:
        if len(results) >= k:
            break
        genre = item[0]["genre"]
        if genre_counts.get(genre, 0) < max_per_genre:
            genre_counts[genre] = genre_counts.get(genre, 0) + 1
            results.append(item)

    return results

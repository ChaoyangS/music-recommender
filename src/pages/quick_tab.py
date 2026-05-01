import streamlit as st
from src.auth import get_music_profile, save_music_profile
from src.recommender import recommend_songs
from src.widgets import render_results, MAX_SCORE


def render_quick_tab(current_user: dict, songs: list[dict], genres: list, moods: list) -> None:
    st.markdown(
        "Fill in a taste profile and get instant results. "
        "No API key needed — runs the scoring engine directly."
    )

    # Load saved profile for pre-fill
    try:
        saved_profile = get_music_profile(current_user["_id"])
    except Exception:
        saved_profile = None

    col_left, col_right = st.columns(2)

    with col_left:
        saved_genre = saved_profile.get("favorite_genre") if saved_profile else None
        genre_index = genres.index(saved_genre) if saved_genre in genres else 0
        genre = st.selectbox("Favorite genre", genres, index=genre_index)

        saved_mood = saved_profile.get("favorite_mood") if saved_profile else None
        mood_index = moods.index(saved_mood) if saved_mood in moods else 0
        mood = st.selectbox("Favorite mood", moods, index=mood_index)

    with col_right:
        saved_energy = saved_profile.get("target_energy", 0.6) if saved_profile else 0.6
        energy = st.slider("Target energy", 0.0, 1.0, float(saved_energy), step=0.05,
                           help="0 = very calm · 1 = very intense")

        saved_acoustic = saved_profile.get("likes_acoustic", False) if saved_profile else False
        acoustic = st.checkbox("Prefer acoustic songs", value=bool(saved_acoustic))

        k = st.slider("Songs to return", 1, 10, 5)

    if saved_profile:
        st.caption("↑ Pre-filled from your saved taste profile.")

    if st.button("Find Songs", type="primary"):
        user_prefs = {
            "favorite_genre": genre,
            "favorite_mood":  mood,
            "target_energy":  energy,
            "likes_acoustic": acoustic,
        }

        try:
            save_music_profile(current_user["_id"], user_prefs)
        except Exception:
            pass

        raw_results = recommend_songs(user_prefs, songs, k=k)
        recs = [
            {
                "song_id":     song["id"],
                "title":       song["title"],
                "artist":      song["artist"],
                "genre":       song["genre"],
                "mood":        song["mood"],
                "score":       round(score, 2),
                "reasons":     [r.strip() for r in explanation.split(";") if r.strip()],
                "preview_url": song.get("preview_url", ""),
            }
            for song, score, explanation in raw_results
        ]
        st.session_state.quick_recs = recs
        st.session_state.quick_meta = {
            "k": k, "genre": genre, "mood": mood,
            "top_score": recs[0]["score"] if recs else 0.0,
            "avg_score": sum(r["score"] for r in recs) / len(recs) if recs else 0.0,
        }

    if st.session_state.get("quick_recs"):
        meta = st.session_state.quick_meta
        st.subheader(f"Top {meta['k']} songs for **{meta['genre']}** / **{meta['mood']}**")
        m1, m2, m3 = st.columns(3)
        m1.metric("Top score",  f"{meta['top_score']:.2f} / {MAX_SCORE:.0f}")
        m2.metric("Avg score",  f"{meta['avg_score']:.2f}")
        m3.metric("Confidence", f"{meta['top_score'] / MAX_SCORE:.0%}")
        st.divider()
        render_results(st.session_state.quick_recs, user_id=current_user["_id"], key_prefix="quick")

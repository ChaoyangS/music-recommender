import streamlit as st
from src.auth import (
    like_song, unlike_song, dislike_song, undislike_song,
    get_liked_song_ids, get_disliked_song_ids,
)

MAX_SCORE = 12.0


def render_results(recs: list[dict], user_id=None, key_prefix: str = "") -> None:
    if not recs:
        st.info("No recommendations returned.")
        return

    liked_ids: set = set()
    disliked_ids: set = set()
    if user_id:
        try:
            liked_ids = get_liked_song_ids(user_id)
            disliked_ids = get_disliked_song_ids(user_id)
        except Exception:
            pass

    for i, rec in enumerate(recs, 1):
        score   = rec.get("score", 0.0)
        reasons = rec.get("reasons") or []
        conf    = min(score / MAX_SCORE, 1.0)
        song_id = rec.get("song_id")
        label   = f"{i}.  {rec['title']} — {rec['artist']}  |  score {score:.2f} / {MAX_SCORE:.0f}"

        with st.expander(label, expanded=True):
            col_info, col_score, col_like, col_dislike = st.columns([4, 2, 1, 1])

            with col_info:
                st.caption(f"`{rec['genre']}`  ·  `{rec['mood']}`")
                for r in reasons:
                    st.caption(f"• {r}")

            with col_score:
                st.metric("Score", f"{score:.2f} / {MAX_SCORE:.0f}")
                st.progress(conf)

            with col_like:
                if user_id and song_id is not None:
                    is_liked = song_id in liked_ids
                    btn_label = "❤️" if is_liked else "🤍"
                    if st.button(btn_label, key=f"like_{key_prefix}_{i}_{song_id}"):
                        if is_liked:
                            unlike_song(user_id, song_id)
                        else:
                            like_song(user_id, song_id, rec)
                        st.experimental_rerun()

            with col_dislike:
                if user_id and song_id is not None:
                    is_disliked = song_id in disliked_ids
                    dislike_label = "👎" if is_disliked else "👎🏻"
                    dislike_help = "Remove dislike" if is_disliked else "Dislike this song"
                    if st.button(dislike_label, key=f"dislike_{key_prefix}_{i}_{song_id}", help=dislike_help):
                        if is_disliked:
                            undislike_song(user_id, song_id)
                        else:
                            dislike_song(user_id, song_id, rec)
                        st.experimental_rerun()

            preview_url = rec.get("preview_url", "")
            if preview_url:
                st.audio(preview_url, format="audio/mp3")

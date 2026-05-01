import os
import streamlit as st
from src.auth import (
    get_profile_photo_b64, save_profile_photo,
    get_liked_song_ids, get_disliked_song_ids,
    delete_session, save_music_profile,
)


def render_sidebar(current_user: dict, songs: list[dict]) -> None:
    with st.sidebar:
        # ── Profile photo ──────────────────────────────────────────────────────────
        _photo_b64 = get_profile_photo_b64(current_user["_id"])
        if _photo_b64:
            _photo_inner = (
                f'<img src="data:image/jpeg;base64,{_photo_b64}" '
                f'style="width:80px;height:80px;border-radius:50%;object-fit:cover;display:block;">'
            )
        else:
            _photo_inner = (
                '<div style="width:80px;height:80px;border-radius:50%;background:#555;'
                'display:flex;align-items:center;justify-content:center;font-size:36px;">👤</div>'
            )

        # Photo with clickable "+" badge; anchor targets the hidden trigger button via CSS
        st.markdown(
            f'<div class="profile-photo-wrap">'
            f'  {_photo_inner}'
            f'  <div class="profile-photo-plus">{"+" if st.session_state.get("show_photo_upload") else "−"}</div>'
            f'</div>'
            f'<span class="photo-btn-anchor"></span>',
            unsafe_allow_html=True,
        )

        # Hidden Streamlit trigger — JS wires the "+" badge click to this button
        if st.button("+photo", key="btn_photo_toggle"):
            st.session_state.show_photo_upload = not st.session_state.get("show_photo_upload", False)

        st.markdown(f"<div style='text-align:center;margin-top:8px'><b>{current_user['username']}</b></div>",
                    unsafe_allow_html=True)

        if st.session_state.get("show_photo_upload"):
            _upload = st.file_uploader("Upload image", type=["png", "jpg", "jpeg"],
                                       key="photo_upload", label_visibility="collapsed")
            if _upload:
                try:
                    save_profile_photo(current_user["_id"], _upload.read())
                    st.success("Photo updated!")
                    st.session_state.show_photo_upload = False
                    st.experimental_rerun()
                except Exception as _e:
                    st.error(f"Upload failed: {_e}")

        if st.button("Log Out", key="btn_logout"):
            delete_session(st.session_state.session_token)
            st.session_state.session_token = None
            st.session_state.current_user = None
            st.session_state.pop("google_auth_url", None)
            st.experimental_rerun()

        st.divider()

        # ── Taste Profile ──────────────────────────────────────────────────────────
        st.subheader("🎧 Taste Profile")

        try:
            _liked_count    = len(get_liked_song_ids(current_user["_id"]))
            _disliked_count = len(get_disliked_song_ids(current_user["_id"]))
        except Exception:
            _liked_count = _disliked_count = 0

        st.caption(f"❤️ {_liked_count} liked  ·  👎 {_disliked_count} disliked")

        _enough_history = (_liked_count + _disliked_count) >= 2

        if not os.getenv("ANTHROPIC_API_KEY"):
            st.caption("Add `ANTHROPIC_API_KEY` to enable taste analysis.")
        elif not _enough_history:
            st.caption("Like or dislike at least 2 songs to enable taste analysis.")
        else:
            if st.button("Analyze My Taste", key="btn_analyze_taste"):
                with st.spinner("Analyzing your history…"):
                    try:
                        from src.profile_agent import build_user_profile
                        _profile = build_user_profile(current_user["_id"], songs)
                        if _profile:
                            st.session_state.inferred_profile = _profile
                        else:
                            st.warning("Could not infer a profile — try liking more songs.")
                    except Exception as _e:
                        st.error(f"Analysis failed: {_e}")

        if st.session_state.get("inferred_profile"):
            _p = st.session_state.inferred_profile
            _conf = _p.get("confidence", "")
            st.success(f"Profile ready ({_conf} confidence)" if _conf else "Profile ready")
            st.caption(f"Genre: **{_p.get('favorite_genre')}**")
            st.caption(f"Mood: **{_p.get('favorite_mood')}**")
            st.caption(f"Energy: **{_p.get('target_energy', 0):.2f}**")
            st.caption(f"Acoustic: **{'yes' if _p.get('likes_acoustic') else 'no'}**")
            if _p.get("reasoning"):
                st.caption(f"_{_p['reasoning']}_")
            st.caption("Profile saved — Quick Recommend is now pre-filled.")

        st.divider()
        st.header("About")
        st.markdown("""
    **Two modes:**
    - **AI Agent** — describe what you want in plain English. Claude infers your preferences, fetches recommendations, self-evaluates quality, and retries if needed.
    - **Quick Recommend** — fill in a structured profile for instant results. No API key needed.

    **Scoring formula:**
    | Signal | Points |
    |---|---|
    | Genre match | +5 |
    | Mood match | +4 |
    | Energy closeness | 0–2 |
    | Acoustic bonus | +1 |
    | **Max possible** | **12** |
    """)
        st.divider()
        st.caption(f"Catalog: {len(songs)} songs")
        if os.getenv("ANTHROPIC_API_KEY"):
            st.success("API key loaded ✔")
        else:
            st.warning("No API key — AI Agent tab disabled")

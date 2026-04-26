"""
Streamlit web frontend for the Music Recommender system.

Two modes (shown after login):
  🤖 AI Agent      — natural language request → PLAN→ACT→CHECK→FIX loop with live steps
  🎚️ Quick Recommend — structured form → instant rule-based results, no API key needed

Run with:
    streamlit run app.py
"""

import json
import os
import sys
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

load_dotenv(dotenv_path=ROOT / ".env")
load_dotenv(dotenv_path=ROOT.parent / ".env")

from src.recommender import load_songs, recommend_songs
from src.agent import _execute_tool, TOOLS, SYSTEM_PROMPT
from src.auth import (
    authenticate_user,
    create_user,
    create_session,
    get_user_from_session,
    delete_session,
    save_music_profile,
    get_music_profile,
    build_google_auth_url,
    exchange_code_for_user_info,
    store_oauth_state,
    verify_and_consume_oauth_state,
    find_or_create_google_user,
)

# ── Constants ─────────────────────────────────────────────────────────────────

SONGS_PATH = str(ROOT / "data" / "songs.csv")
MAX_SCORE  = 12.0

STEP_LABELS = {
    "browse_catalog":      "PLAN  — browse catalog",
    "get_recommendations": "ACT   — get recommendations",
    "evaluate_quality":    "CHECK — evaluate quality",
}

# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Music Recommender",
    page_icon="🎵",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Cached data ───────────────────────────────────────────────────────────────

@st.cache_data
def get_songs():
    return load_songs(SONGS_PATH)

songs  = get_songs()
genres = sorted({s["genre"] for s in songs})
moods  = sorted({s["mood"]  for s in songs})

# ── Session state init ────────────────────────────────────────────────────────

if "session_token" not in st.session_state:
    st.session_state.session_token = None
if "current_user" not in st.session_state:
    st.session_state.current_user = None

# Validate existing session on each rerun
if st.session_state.session_token:
    try:
        user = get_user_from_session(st.session_state.session_token)
        if user:
            st.session_state.current_user = user
        else:
            st.session_state.session_token = None
            st.session_state.current_user = None
    except Exception:
        st.session_state.session_token = None
        st.session_state.current_user = None

# ── Google OAuth callback ─────────────────────────────────────────────────────
# Handle the redirect from Google before rendering any UI.

_params = st.experimental_get_query_params()
if "code" in _params and not st.session_state.current_user:
    _code = _params["code"][0]
    # Guard: only process each code once — st.experimental_set_query_params() may
    # not clear the URL before the next rerun in Streamlit 1.22, so the same code
    # can appear repeatedly in query params.
    if st.session_state.get("_oauth_handled_code") != _code:
        st.session_state["_oauth_handled_code"] = _code
        _state        = _params.get("state", [""])[0]
        _redirect_uri = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8501")
        try:
            if verify_and_consume_oauth_state(_state):
                _guser = exchange_code_for_user_info(_code, _redirect_uri)
                _user  = find_or_create_google_user(
                    google_id=_guser["sub"],
                    email=_guser.get("email", ""),
                    name=_guser.get("name", _guser.get("email", "user").split("@")[0]),
                )
                st.session_state.session_token = create_session(_user["_id"])
                st.session_state.current_user  = _user
            else:
                st.session_state["_oauth_error"] = "Google sign-in failed — please try again."
        except Exception as _e:
            st.session_state["_oauth_error"] = f"Google sign-in failed: {_e}"
        st.session_state.pop("google_auth_url", None)
        st.experimental_set_query_params()
        st.experimental_rerun()

# ── Auth page (shown when not logged in) ──────────────────────────────────────

if not st.session_state.current_user:
    st.title("🎵 Music Recommender")

    col_center = st.columns([1, 2, 1])[1]
    with col_center:
        st.markdown("### Welcome — please sign in or create an account")
        tab_login, tab_signup = st.tabs(["Log In", "Sign Up"])

        with tab_login:
            login_username = st.text_input("Username", key="login_username")
            login_password = st.text_input("Password", type="password", key="login_password")

            if st.button("Log In", type="primary", key="btn_login"):
                if not login_username or not login_password:
                    st.error("Please enter both username and password.")
                else:
                    try:
                        user = authenticate_user(login_username, login_password)
                        if user:
                            token = create_session(user["_id"])
                            st.session_state.session_token = token
                            st.session_state.current_user = user
                            st.experimental_rerun()
                        else:
                            st.error("Invalid username or password.")
                    except Exception as e:
                        st.error(f"Could not connect to the database. Check MONGODB_URI.\n\n{e}")

        with tab_signup:
            signup_username = st.text_input("Username", key="signup_username")
            signup_password = st.text_input("Password", type="password", key="signup_password")
            signup_confirm  = st.text_input("Confirm password", type="password", key="signup_confirm")

            if st.button("Create Account", type="primary", key="btn_signup"):
                if not signup_username or not signup_password:
                    st.error("Please enter a username and password.")
                elif signup_password != signup_confirm:
                    st.error("Passwords do not match.")
                elif len(signup_password) < 6:
                    st.error("Password must be at least 6 characters.")
                else:
                    try:
                        user = create_user(signup_username, signup_password)
                        if user:
                            token = create_session(user["_id"])
                            st.session_state.session_token = token
                            st.session_state.current_user = user
                            st.experimental_rerun()
                        else:
                            st.error("Username already taken. Please choose another.")
                    except Exception as e:
                        st.error(f"Could not connect to the database. Check MONGODB_URI.\n\n{e}")

        # ── Google sign-in (shown only when credentials are configured) ────────
        if os.getenv("GOOGLE_CLIENT_ID") and os.getenv("GOOGLE_CLIENT_SECRET"):
            st.divider()
            _redirect_uri = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8501")
            if "google_auth_url" not in st.session_state:
                try:
                    _auth_url, _state = build_google_auth_url(_redirect_uri)
                    store_oauth_state(_state)
                    st.session_state.google_auth_url = _auth_url
                except Exception:
                    pass
            if "google_auth_url" in st.session_state:
                st.markdown(
                    f'<div style="text-align:center">'
                    f'<a href="{st.session_state.google_auth_url}" target="_self" style="text-decoration:none">'
                    f'<button style="background:#fff;color:#444;border:1px solid #dadce0;'
                    f'border-radius:4px;padding:9px 16px;cursor:pointer;font-size:14px;width:100%">'
                    f'<img src="https://www.gstatic.com/firebasejs/ui/2.0.0/images/auth/google.svg" '
                    f'style="height:18px;vertical-align:middle;margin-right:8px">'
                    f'Sign in with Google</button></a></div>',
                    unsafe_allow_html=True,
                )

        if st.session_state.get("_oauth_error"):
            st.error(st.session_state.pop("_oauth_error"))

    st.stop()

# ── Logged-in state ───────────────────────────────────────────────────────────

current_user = st.session_state.current_user

# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown(f"**👤 {current_user['username']}**")
    if st.button("Log Out", key="btn_logout"):
        delete_session(st.session_state.session_token)
        st.session_state.session_token = None
        st.session_state.current_user = None
        st.session_state.pop("google_auth_url", None)
        st.experimental_rerun()

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

# ── Header ────────────────────────────────────────────────────────────────────

st.title("🎵 Music Recommender")
st.caption("Rule-based scoring engine · Claude agentic workflow · PLAN → ACT → CHECK → FIX")

# ── Shared renderer ───────────────────────────────────────────────────────────

def render_results(recs: list[dict]) -> None:
    if not recs:
        st.info("No recommendations returned.")
        return

    for i, rec in enumerate(recs, 1):
        score   = rec.get("score", 0.0)
        reasons = rec.get("reasons") or []
        conf    = min(score / MAX_SCORE, 1.0)
        label   = f"{i}.  {rec['title']} — {rec['artist']}  |  score {score:.2f} / {MAX_SCORE:.0f}"

        with st.expander(label, expanded=True):
            col_info, col_score = st.columns([4, 2])

            with col_info:
                st.caption(f"`{rec['genre']}`  ·  `{rec['mood']}`")
                for r in reasons:
                    st.caption(f"• {r}")

            with col_score:
                st.metric("Score", f"{score:.2f} / {MAX_SCORE:.0f}")
                st.progress(conf)

# ── Tabs ──────────────────────────────────────────────────────────────────────

tab_agent, tab_quick = st.tabs(["🤖 AI Agent", "🎚️ Quick Recommend"])

# ─────────────────────────────────────────────────────────────────────────────
# TAB 1 — AI Agent
# ─────────────────────────────────────────────────────────────────────────────

with tab_agent:
    if not os.getenv("ANTHROPIC_API_KEY"):
        st.warning(
            "Add `ANTHROPIC_API_KEY` to your `.env` file and restart the app to use this tab."
        )
        st.info("The **Quick Recommend** tab works without an API key.")
    else:
        st.markdown(
            "Describe what you want in plain English. "
            "The agent will infer your preferences, fetch recommendations, "
            "evaluate quality, and retry if needed — showing every step."
        )

        user_request = st.text_input(
            "What kind of music are you looking for?",
            placeholder="e.g. Something chill to study to late at night",
        )

        col_btn, col_k = st.columns([3, 1])
        with col_btn:
            run_clicked = st.button(
                "Get Recommendations",
                type="primary",
                disabled=not (user_request or "").strip(),
            )
        with col_k:
            num_recs = st.number_input("Songs to return", min_value=1, max_value=10, value=5)

        if run_clicked and (user_request or "").strip():
            import anthropic

            client   = anthropic.Anthropic()
            messages: list[dict] = [{"role": "user", "content": user_request}]

            final_text = ""
            final_recs: list[dict] = []
            last_inferred_profile: dict | None = None

            banner = st.empty()
            banner.info("⏳ Agent running…")
            log = st.container()

            for iteration in range(10):
                with log:
                    st.markdown(f"**── Iteration {iteration + 1} ──**")

                response = client.messages.create(
                    model="claude-opus-4-7",
                    max_tokens=4096,
                    system=[{
                        "type": "text",
                        "text": SYSTEM_PROMPT,
                        "cache_control": {"type": "ephemeral"},
                    }],
                    tools=TOOLS,
                    messages=messages,
                )

                messages.append({"role": "assistant", "content": response.content})

                for block in response.content:
                    if hasattr(block, "text") and block.text.strip():
                        with log:
                            st.markdown(
                                f"<span style='color:grey'>💭 {block.text.strip()}</span>",
                                unsafe_allow_html=True,
                            )

                if response.stop_reason == "end_turn":
                    final_text = "".join(
                        b.text for b in response.content if hasattr(b, "text")
                    )
                    banner.success(f"✔ Done in {iteration + 1} iteration(s)")
                    break

                tool_results = []
                for block in response.content:
                    if block.type != "tool_use":
                        continue

                    label = STEP_LABELS.get(block.name, block.name)
                    with log:
                        st.markdown(f"▶ **{label}**")

                    result_str = _execute_tool(block.name, block.input, songs)
                    result     = json.loads(result_str)

                    if "recommendations" in result:
                        recs = result["recommendations"]
                        if len(recs) != num_recs:
                            block.input["num_recommendations"] = num_recs
                            result_str = _execute_tool(block.name, block.input, songs)
                            result     = json.loads(result_str)
                            recs       = result["recommendations"]
                        final_recs = recs
                        last_inferred_profile = {
                            k: block.input[k]
                            for k in ("favorite_genre", "favorite_mood", "target_energy", "likes_acoustic")
                            if k in block.input
                        }
                        top = recs[0] if recs else {}
                        with log:
                            st.caption(
                                f"→ {len(recs)} songs returned — "
                                f"top: **{top.get('title')}** (score={top.get('score')})"
                            )
                    elif "quality" in result:
                        quality = result["quality"]
                        issues  = result.get("issues") or []
                        with log:
                            if quality == "good":
                                st.success(f"quality = {quality} — ✔ no issues")
                            elif quality == "acceptable":
                                st.warning(f"quality = {quality} — {'; '.join(issues)}")
                                st.caption("FIX — adjusting parameters and retrying…")
                            else:
                                st.error(f"quality = {quality} — {'; '.join(issues)}")
                                st.caption("FIX — adjusting parameters and retrying…")
                    else:
                        with log:
                            st.caption(f"→ {result.get('total', '?')} songs in catalog")

                    tool_results.append({
                        "type":        "tool_result",
                        "tool_use_id": block.id,
                        "content":     result_str,
                    })

                if tool_results:
                    messages.append({"role": "user", "content": tool_results})

            if final_text:
                st.subheader("Claude's Recommendation")
                st.markdown(final_text)

            if final_recs:
                if last_inferred_profile:
                    try:
                        save_music_profile(current_user["_id"], last_inferred_profile)
                    except Exception:
                        pass
                st.subheader("Top Songs")
                render_results(final_recs)

# ─────────────────────────────────────────────────────────────────────────────
# TAB 2 — Quick Recommend
# ─────────────────────────────────────────────────────────────────────────────

with tab_quick:
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

        # Persist the profile for next time
        try:
            save_music_profile(current_user["_id"], user_prefs)
        except Exception:
            pass

        raw_results = recommend_songs(user_prefs, songs, k=k)
        recs = [
            {
                "title":   song["title"],
                "artist":  song["artist"],
                "genre":   song["genre"],
                "mood":    song["mood"],
                "score":   round(score, 2),
                "reasons": [r.strip() for r in explanation.split(";") if r.strip()],
            }
            for song, score, explanation in raw_results
        ]

        top_score = recs[0]["score"] if recs else 0.0
        avg_score = sum(r["score"] for r in recs) / len(recs) if recs else 0.0

        st.subheader(f"Top {k} songs for **{genre}** / **{mood}**")

        m1, m2, m3 = st.columns(3)
        m1.metric("Top score",  f"{top_score:.2f} / {MAX_SCORE:.0f}")
        m2.metric("Avg score",  f"{avg_score:.2f}")
        m3.metric("Confidence", f"{top_score / MAX_SCORE:.0%}")

        st.divider()
        render_results(recs)

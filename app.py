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
import streamlit.components.v1 as components
from dotenv import load_dotenv

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

load_dotenv(dotenv_path=ROOT / ".env")
load_dotenv(dotenv_path=ROOT.parent / ".env")

from src.recommender import load_songs, recommend_songs
from src.agent import _execute_tool, TOOLS, build_system_prompt
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
    like_song,
    unlike_song,
    get_liked_song_ids,
    get_liked_songs,
    dislike_song,
    undislike_song,
    get_disliked_song_ids,
    save_profile_photo,
    get_profile_photo_b64,
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
    menu_items=None,
)

# ── Global styles ─────────────────────────────────────────────────────────────

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700&display=swap');

/* ── Base ── */
html, body, [class*="css"], .stApp {
    font-family: 'DM Sans', sans-serif !important;
    background-color: #212121;
    color: #F2E3CF;
}

/* ── Sidebar ── */
section[data-testid="stSidebar"] {
    background-color: #171717 !important;
    border-right: 1px solid #2e2e2e;
}
section[data-testid="stSidebar"] * { color: #F2E3CF !important; }
section[data-testid="stSidebar"] .stButton button {
    width: 100%;
    background: transparent !important;
    border: 1px solid #3a3a3a !important;
    color: #B8A898 !important;
    font-size: 13px;
}
section[data-testid="stSidebar"] .stButton button:hover {
    border-color: #E35341 !important;
    color: #F2E3CF !important;
}

/* ── Typography ── */
h1 {
    font-size: 2.4rem !important;
    font-weight: 700 !important;
    letter-spacing: -0.04em !important;
    color: #F2E3CF !important;
    line-height: 1.1 !important;
}
h2, h3 {
    font-weight: 600 !important;
    letter-spacing: -0.03em !important;
    color: #F2E3CF !important;
}
p, span, label, .stMarkdown { color: #F2E3CF; }
.stCaption, small { color: #B8A898 !important; font-size: 13px !important; }

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    background: transparent;
    border-bottom: 1px solid #2e2e2e;
    gap: 4px;
}
.stTabs [data-baseweb="tab"] {
    background: transparent !important;
    color: #888 !important;
    border-radius: 0 !important;
    font-weight: 500;
    letter-spacing: -0.02em;
    padding: 10px 20px;
    border-bottom: 2px solid transparent;
}
.stTabs [data-baseweb="tab"]:hover { color: #F2E3CF !important; }
.stTabs [aria-selected="true"] {
    color: #F2E3CF !important;
    border-bottom: 2px solid #E35341 !important;
    background: transparent !important;
}
.stTabs [data-baseweb="tab-highlight"] { display: none; }
.stTabs [data-baseweb="tab-border"] { display: none; }

/* ── Buttons ── */
.stButton button {
    background-color: #E35341 !important;
    color: #fff !important;
    border: none !important;
    border-radius: 6px !important;
    font-weight: 600 !important;
    letter-spacing: -0.02em !important;
    padding: 8px 20px !important;
    transition: background 0.15s ease !important;
}
.stButton button:hover {
    background-color: #c94432 !important;
    color: #fff !important;
}
/* Clear any dark background injected into button children */
.stButton button div,
.stButton button p,
.stButton button span {
    background: transparent !important;
    background-color: transparent !important;
}
/* Small icon buttons (like/dislike) — scoped to inside song card expanders only */
[data-testid="stExpander"] [data-testid="column"] .stButton button {
    background: transparent !important;
    color: #F2E3CF !important;
    border: none !important;
    box-shadow: none !important;
    padding: 4px 8px !important;
    font-size: 18px !important;
    transition: transform 0.1s ease !important;
}
[data-testid="stExpander"] [data-testid="column"] .stButton button:hover {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    transform: scale(1.25) !important;
}

/* ── Song cards (expanders) ── */
.stExpander {
    background-color: #1e1e1e !important;
    border: 1px solid #2e2e2e !important;
    border-radius: 10px !important;
    margin-bottom: 8px !important;
}
.stExpander summary {
    color: #F2E3CF !important;
    font-weight: 500 !important;
    letter-spacing: -0.02em !important;
}
.stExpander summary:hover { color: #E35341 !important; }
details[data-testid="stExpander"] { border: 1px solid #2e2e2e !important; }

/* ── Metrics ── */
[data-testid="stMetric"] {
    background: #1e1e1e;
    border: 1px solid #2e2e2e;
    border-radius: 8px;
    padding: 12px 16px !important;
}
[data-testid="stMetricValue"] {
    color: #F2E3CF !important;
    font-size: 1.4rem !important;
    font-weight: 600 !important;
    letter-spacing: -0.03em !important;
}
[data-testid="stMetricLabel"] { color: #B8A898 !important; font-size: 12px !important; }

/* ── Progress bar ── */
.stProgress > div > div > div > div { background-color: #E35341 !important; }
.stProgress > div > div > div { background-color: #2e2e2e !important; }

/* ── Inputs ── */
.stTextInput input, .stTextArea textarea {
    background-color: #1e1e1e !important;
    color: #F2E3CF !important;
    border: 1px solid #3a3a3a !important;
    border-radius: 6px !important;
}
.stTextInput input:focus, .stTextArea textarea:focus {
    border-color: #E35341 !important;
    box-shadow: 0 0 0 2px rgba(227,83,65,0.2) !important;
}

/* ── Selectbox / Dropdown ── */
.stSelectbox > div > div, [data-baseweb="select"] > div {
    background-color: #1e1e1e !important;
    border-color: #3a3a3a !important;
    color: #F2E3CF !important;
}

/* ── Slider ── */
.stSlider [data-baseweb="slider"] [data-testid="stThumb"] { background: #E35341 !important; }
.stSlider [data-baseweb="slider"] [role="progressbar"] { background: #E35341 !important; }

/* ── Checkbox ── */
.stCheckbox label span { color: #F2E3CF !important; }

/* ── Dividers ── */
hr { border-color: #2e2e2e !important; }

/* ── Alert boxes ── */
[data-baseweb="notification"] {
    background-color: #1e1e1e !important;
    border-color: #3a3a3a !important;
    color: #F2E3CF !important;
}
[data-testid="stNotification"],
div[role="alert"] {
    background-color: #1e1e1e !important;
    color: #F2E3CF !important;
}
/* Success → blue left border; Warning/Error → coral */
div[data-testid="stNotification"][kind="success"],
.stAlert [kind="success"] { border-left: 4px solid #0099FF !important; }
div[data-testid="stNotification"][kind="info"]    { border-left: 4px solid #0099FF !important; }
div[data-testid="stNotification"][kind="warning"] { border-left: 4px solid #E35341 !important; }
div[data-testid="stNotification"][kind="error"]   { border-left: 4px solid #E35341 !important; }
/* Catch-all for any remaining green/coloured alert backgrounds */
.stAlert, .stAlert > div { background-color: #1e1e1e !important; color: #F2E3CF !important; }

/* ── Number input ── */
.stNumberInput input {
    background-color: #1e1e1e !important;
    color: #F2E3CF !important;
    border: 1px solid #3a3a3a !important;
}

/* ── Audio player ── */
audio { width: 100%; accent-color: #E35341; margin-top: 8px; }

/* ── Hamburger menu — hidden ── */
#MainMenu { display: none !important; }

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #1a1a1a; }
::-webkit-scrollbar-thumb { background: #3a3a3a; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #E35341; }

/* ── Profile photo "+" badge ── */
.profile-photo-wrap {
    position: relative;
    width: 80px;
    margin: 0 auto;
}
.profile-photo-plus {
    position: absolute;
    bottom: 0;
    right: 0;
    width: 22px;
    height: 22px;
    border-radius: 50%;
    background: #E35341;
    border: 2px solid #171717;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 15px;
    font-weight: 700;
    color: white;
    cursor: pointer;
    line-height: 1;
    user-select: none;
    transition: background 0.15s ease;
}
.profile-photo-plus:hover { background: #c94432; }
/* Push the hidden Streamlit trigger button off-screen */
.element-container:has(.photo-btn-anchor) + .element-container {
    position: fixed !important;
    top: -9999px !important;
    left: -9999px !important;
    width: 0 !important;
    height: 0 !important;
    overflow: hidden !important;
}
</style>
""", unsafe_allow_html=True)

# ── Cached data ───────────────────────────────────────────────────────────────

@st.cache_data
def get_songs(mtime: float):
    return load_songs(SONGS_PATH)



songs  = get_songs(Path(SONGS_PATH).stat().st_mtime)
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
    st.markdown("""
    <h1 style='letter-spacing:-0.04em;text-align:center;margin-bottom:4px'>Music Recommender</h1>
    <p style='color:#B8A898;text-align:center;font-size:14px;margin-top:0'>Your AI-powered music companion</p>
    """, unsafe_allow_html=True)

    col_center = st.columns([1, 2, 1])[1]
    with col_center:
        st.markdown("### Sign in or create an account")
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

# ── Header ────────────────────────────────────────────────────────────────────

st.markdown("""
<h1 style='letter-spacing:-0.04em;margin-bottom:2px'>Music Recommender</h1>
<p style='color:#B8A898;font-size:14px;margin-top:0;letter-spacing:-0.01em'>
  AI-powered · PLAN → ACT → CHECK → FIX
</p>
""", unsafe_allow_html=True)


# ── Shared renderer ───────────────────────────────────────────────────────────

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

# ── Tabs ──────────────────────────────────────────────────────────────────────

# Inject JS via iframe so it actually executes (st.markdown strips <script> tags).
# Uses a DOM anchor element (#liked-songs-anchor) placed inside the Liked Songs tab
# to reliably find the correct tab panel without depending on ARIA or index ordering.
# MutationObserver re-attaches after every Streamlit rerun or tab switch.
components.html("""
<script>
(function () {
    function getLikedPanel(doc) {
        // Primary: traverse up from the anchor element we placed inside the liked tab.
        var anchor = doc.getElementById('liked-songs-anchor');
        if (anchor) {
            var panel = anchor.closest('[role="tabpanel"]') ||
                        anchor.closest('[data-testid="stTabContent"]') ||
                        anchor.closest('[data-baseweb="tab-panel"]');
            if (panel) return panel;
        }
        // Fallback: find by tab text + index (covers lazy-render case).
        var tabs = Array.from(doc.querySelectorAll('[role="tab"]'));
        var idx  = tabs.findIndex(function (t) {
            return (t.textContent || '').indexOf('Liked') !== -1;
        });
        if (idx === -1) return null;
        var panels = doc.querySelectorAll('[role="tabpanel"]');
        return panels[idx] || null;
    }

    // Wire the profile photo "+" badge to the hidden Streamlit toggle button.
    function attachPhotoBtn(doc) {
        var sidebar = doc.querySelector('[data-testid="stSidebar"]');
        if (!sidebar) return;
        var plus = sidebar.querySelector('.profile-photo-plus');
        if (!plus || plus._wired) return;
        plus._wired = true;
        plus.addEventListener('click', function () {
            var btns = sidebar.querySelectorAll('button');
            for (var i = 0; i < btns.length; i++) {
                if ((btns[i].textContent || '').trim() === '+photo') {
                    btns[i].click();
                    break;
                }
            }
        });
    }

    function attach() {
        try {
            var doc   = window.parent.document;
            var panel = getLikedPanel(doc);
            if (!panel) return;
            panel.querySelectorAll('button').forEach(function (btn) {
                if (btn._heartHover) return;
                // Match buttons whose text contains the red heart (U+2764).
                if ((btn.textContent || '').indexOf('❤') === -1) return;
                btn._heartHover = true;
                btn.addEventListener('mouseenter', function () {
                    var el = btn.querySelector('p') || btn.querySelector('div') || btn;
                    el.textContent = '🤍'; // 🤍
                });
                btn.addEventListener('mouseleave', function () {
                    var el = btn.querySelector('p') || btn.querySelector('div') || btn;
                    el.textContent = '❤️'; // ❤️
                });
            });
        } catch (e) {}
    }
    attach();
    attachPhotoBtn(window.parent.document);
    try {
        new MutationObserver(function () {
            attach();
            attachPhotoBtn(window.parent.document);
        }).observe(window.parent.document.body, { childList: true, subtree: true });
    } catch (e) {}
})();
</script>
""", height=0)

tab_agent, tab_quick, tab_liked = st.tabs(["🤖 AI Agent", "🎚️ Quick Recommend", "❤️ Liked Songs"])

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
            st.session_state.pop("agent_recs",  None)
            st.session_state.pop("agent_text", None)

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
                        "text": build_system_prompt(songs),
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

            if final_recs:
                if last_inferred_profile:
                    try:
                        save_music_profile(current_user["_id"], last_inferred_profile)
                    except Exception:
                        pass
                st.session_state.agent_recs  = final_recs
                st.session_state.agent_text = final_text

        if st.session_state.get("agent_text"):
            st.subheader("Claude's Recommendation")
            st.markdown(st.session_state.agent_text)
        if st.session_state.get("agent_recs"):
            st.subheader("Top Songs")
            render_results(st.session_state.agent_recs, user_id=current_user["_id"], key_prefix="agent")

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

# ─────────────────────────────────────────────────────────────────────────────
# TAB 3 — Liked Songs
# ─────────────────────────────────────────────────────────────────────────────

with tab_liked:
    # Anchor element used by the JS hover-effect to locate this tab's panel.
    st.markdown('<span id="liked-songs-anchor"></span>', unsafe_allow_html=True)

    try:
        liked = get_liked_songs(current_user["_id"])
    except Exception:
        liked = []

    if not liked:
        st.info("No liked songs yet — click 🤍 on any recommendation to save it here.")
    else:
        st.subheader(f"{len(liked)} liked song{'s' if len(liked) != 1 else ''}")
        for song in liked:
            label = f"{song['title']} — {song['artist']}"
            with st.expander(label, expanded=True):
                col_info, col_unlike = st.columns([5, 1])
                with col_info:
                    st.caption(f"`{song['genre']}`  ·  `{song['mood']}`")
                    st.caption(f"Liked {song['liked_at'].strftime('%b %d, %Y')}")
                with col_unlike:
                    if st.button("❤️", key=f"unlike_tab_{song['song_id']}",
                                 help="Remove from liked songs"):
                        try:
                            unlike_song(current_user["_id"], song["song_id"])
                        except Exception:
                            pass
                        st.experimental_rerun()

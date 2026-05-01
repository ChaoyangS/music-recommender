"""
Streamlit web frontend for the Music Recommender system.

Two modes (shown after login):
  🤖 AI Agent      — natural language request → PLAN→ACT→CHECK→FIX loop with live steps
  🎚️ Quick Recommend — structured form → instant rule-based results, no API key needed

Run with:
    streamlit run app.py
"""

import sys
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

load_dotenv(dotenv_path=ROOT / ".env")
load_dotenv(dotenv_path=ROOT.parent / ".env")

from src.recommender import load_songs
from src.auth import get_user_from_session
from src.styles import STYLES
from src.background import inject_floating_background
from src.pages.auth_page import render_auth_page, handle_oauth_callback
from src.pages.sidebar import render_sidebar
from src.pages.agent_tab import render_agent_tab
from src.pages.quick_tab import render_quick_tab
from src.pages.liked_tab import render_liked_tab, inject_page_js

SONGS_PATH = str(ROOT / "data" / "songs.csv")

st.set_page_config(
    page_title="Music Recommender",
    page_icon="🎵",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items=None,
)

st.markdown(STYLES, unsafe_allow_html=True)
inject_floating_background()

@st.cache_data
def get_songs(mtime: float):
    return load_songs(SONGS_PATH)

songs  = get_songs(Path(SONGS_PATH).stat().st_mtime)
genres = sorted({s["genre"] for s in songs})
moods  = sorted({s["mood"]  for s in songs})

# ── Session state ─────────────────────────────────────────────────────────────
if "session_token" not in st.session_state:
    st.session_state.session_token = None
if "current_user" not in st.session_state:
    st.session_state.current_user = None

if st.session_state.session_token:
    try:
        user = get_user_from_session(st.session_state.session_token)
        if user:
            st.session_state.current_user = user
        else:
            st.session_state.session_token = None
            st.session_state.current_user  = None
    except Exception:
        st.session_state.session_token = None
        st.session_state.current_user  = None

# ── Google OAuth callback ─────────────────────────────────────────────────────
_params = st.experimental_get_query_params()
if "code" in _params and not st.session_state.current_user:
    handle_oauth_callback(_params)

# ── Auth gate ─────────────────────────────────────────────────────────────────
if not st.session_state.current_user:
    render_auth_page()
    st.stop()

# ── Main app ──────────────────────────────────────────────────────────────────
current_user = st.session_state.current_user
render_sidebar(current_user, songs)

st.markdown("""
<h1 style='letter-spacing:-0.04em;margin-bottom:2px'>Music Recommender</h1>
<p style='color:#B8A898;font-size:14px;margin-top:0;letter-spacing:-0.01em'>
  AI-powered · PLAN → ACT → CHECK → FIX
</p>
""", unsafe_allow_html=True)

inject_page_js()

tab_agent, tab_quick, tab_liked = st.tabs(["🤖 AI Agent", "🎚️ Quick Recommend", "❤️ Liked Songs"])

with tab_agent:
    render_agent_tab(current_user, songs)
with tab_quick:
    render_quick_tab(current_user, songs, genres, moods)
with tab_liked:
    render_liked_tab(current_user)

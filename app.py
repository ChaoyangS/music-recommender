"""
Streamlit web frontend for the Music Recommender system.

Two tabs:
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

# ── Constants ─────────────────────────────────────────────────────────────────

SONGS_PATH = str(ROOT / "data" / "songs.csv")
MAX_SCORE  = 12.0   # genre(5) + mood(4) + energy(2) + acoustic(1)

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

# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
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
    """Render a list of recommendation dicts as scored song cards."""
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

    col_left, col_right = st.columns(2)

    with col_left:
        genre   = st.selectbox("Favorite genre", genres)
        mood    = st.selectbox("Favorite mood",  moods)

    with col_right:
        energy   = st.slider("Target energy", 0.0, 1.0, 0.6, step=0.05,
                             help="0 = very calm · 1 = very intense")
        acoustic = st.checkbox("Prefer acoustic songs")
        k        = st.slider("Songs to return", 1, 10, 5)

    if st.button("Find Songs", type="primary"):
        user_prefs = {
            "favorite_genre": genre,
            "favorite_mood":  mood,
            "target_energy":  energy,
            "likes_acoustic": acoustic,
        }

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

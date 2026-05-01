import json
import os
import anthropic
import streamlit as st
from src.agent import _execute_tool, TOOLS, build_system_prompt
from src.auth import save_music_profile
from src.widgets import render_results

STEP_LABELS = {
    "browse_catalog":      "PLAN  — browse catalog",
    "get_recommendations": "ACT   — get recommendations",
    "evaluate_quality":    "CHECK — evaluate quality",
}


def render_agent_tab(current_user: dict, songs: list[dict]) -> None:
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

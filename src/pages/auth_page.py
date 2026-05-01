import os
import streamlit as st
from src.auth import (
    authenticate_user, create_user, create_session,
    build_google_auth_url, store_oauth_state,
    exchange_code_for_user_info, verify_and_consume_oauth_state,
    find_or_create_google_user,
)


def handle_oauth_callback(params: dict) -> None:
    """Handle Google OAuth redirect — reads/writes st.session_state."""
    _code = params["code"][0]
    # Guard: only process each code once — st.experimental_set_query_params() may
    # not clear the URL before the next rerun in Streamlit 1.22, so the same code
    # can appear repeatedly in query params.
    if st.session_state.get("_oauth_handled_code") != _code:
        st.session_state["_oauth_handled_code"] = _code
        _state        = params.get("state", [""])[0]
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


def render_auth_page() -> None:
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

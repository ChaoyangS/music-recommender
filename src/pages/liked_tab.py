import streamlit as st
import streamlit.components.v1 as components
from src.auth import get_liked_songs, unlike_song


def inject_page_js() -> None:
    """Inject the MutationObserver JS for heart-hover and photo-badge wiring."""
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


def render_liked_tab(current_user: dict) -> None:
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

GRAIN_SVG = (
    "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='250' height='250'%3E"
    "%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.68' numOctaves='4' "
    "stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='250' height='250' filter='url(%23n)' "
    "opacity='0.045'/%3E%3C/svg%3E\")"
)

STYLES = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,700;1,400;1,700&family=DM+Mono:ital,wght@0,300;0,400;1,300&family=DM+Sans:opsz,wght@9..40,300;9..40,400;9..40,500&display=swap');

/* ── Tokens ── */
:root {{
  --bg:         #171310;
  --surface:    #1e1814;
  --surface-2:  #252019;
  --accent:     #BF5A34;
  --cream:      #EAE0CC;
  --sand:       #A89880;
  --faded:      #6B5C4A;
  --border:     #2e2620;
  --border-dim: #231e19;
  --grain:      {GRAIN_SVG};
  --mono:       'DM Mono', 'Courier New', monospace;
  --serif:      'Playfair Display', Georgia, serif;
  --sans:       'DM Sans', system-ui, sans-serif;
}}

/* ── Base ── */
html, body, [class*="css"], .stApp {{
  font-family: var(--sans) !important;
  background-color: var(--bg) !important;
  color: var(--cream) !important;
}}
.stApp::after {{
  content: '';
  position: fixed;
  inset: 0;
  background-image: var(--grain);
  background-repeat: repeat;
  pointer-events: none;
  z-index: 9999;
  opacity: 1;
}}

/* ── Sidebar — second sheet of paper ── */
section[data-testid="stSidebar"] {{
  background-color: #110f0c !important;
  border-right: 1px solid var(--border) !important;
}}
section[data-testid="stSidebar"] * {{ color: var(--cream) !important; }}

/* Sidebar buttons: flat, rectangular, mono */
section[data-testid="stSidebar"] .stButton button {{
  width: 100%;
  background: transparent !important;
  border: none !important;
  border-top: 1px solid var(--border) !important;
  border-radius: 0 !important;
  color: var(--sand) !important;
  font-family: var(--mono) !important;
  font-size: 11px !important;
  letter-spacing: 0.08em !important;
  text-transform: uppercase !important;
  padding: 10px 4px !important;
  text-align: left !important;
  transition: color 0.15s, padding-left 0.15s !important;
}}
section[data-testid="stSidebar"] .stButton button:hover {{
  color: var(--cream) !important;
  padding-left: 10px !important;
  background: transparent !important;
}}

/* ── Typography ── */
h1 {{
  font-family: var(--serif) !important;
  font-size: 3rem !important;
  font-weight: 700 !important;
  font-style: italic !important;
  letter-spacing: -0.03em !important;
  color: var(--cream) !important;
  line-height: 1.0 !important;
  border-bottom: 1px solid var(--border) !important;
  padding-bottom: 0.4em !important;
  margin-bottom: 0.2em !important;
}}
h2 {{
  font-family: var(--serif) !important;
  font-size: 1.6rem !important;
  font-weight: 400 !important;
  font-style: italic !important;
  color: var(--cream) !important;
  letter-spacing: -0.01em !important;
  border-left: 2px solid var(--accent) !important;
  padding-left: 10px !important;
  border-radius: 0 !important;
  margin-top: 1.2rem !important;
}}
h3 {{
  font-family: var(--mono) !important;
  font-size: 10px !important;
  font-weight: 400 !important;
  color: var(--sand) !important;
  letter-spacing: 0.12em !important;
  text-transform: uppercase !important;
  margin-bottom: 0.6rem !important;
}}
p, span, label, .stMarkdown {{ color: var(--cream); }}
.stCaption, small {{
  font-family: var(--mono) !important;
  color: var(--faded) !important;
  font-size: 11px !important;
  letter-spacing: 0.02em !important;
  line-height: 1.7 !important;
}}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {{
  background: transparent;
  border-bottom: 1px solid var(--border);
  gap: 0;
  padding: 0;
}}
.stTabs [data-baseweb="tab"] {{
  background: transparent !important;
  color: var(--faded) !important;
  border-radius: 0 !important;
  font-family: var(--mono) !important;
  font-size: 10px !important;
  font-weight: 400 !important;
  letter-spacing: 0.12em !important;
  text-transform: uppercase !important;
  padding: 14px 20px !important;
  border-bottom: 1px solid transparent !important;
  transition: color 0.2s !important;
}}
.stTabs [data-baseweb="tab"]:hover {{ color: var(--cream) !important; }}
.stTabs [aria-selected="true"] {{
  color: var(--cream) !important;
  border-bottom: 1px solid var(--accent) !important;
  background: transparent !important;
}}
.stTabs [data-baseweb="tab-highlight"],
.stTabs [data-baseweb="tab-border"] {{ display: none !important; }}

/* ── Buttons — no radius, shift on hover ── */
.stButton button {{
  background-color: transparent !important;
  color: var(--cream) !important;
  border: 1px solid var(--sand) !important;
  border-radius: 0 !important;
  font-family: var(--mono) !important;
  font-size: 11px !important;
  font-weight: 400 !important;
  letter-spacing: 0.1em !important;
  text-transform: uppercase !important;
  padding: 10px 20px !important;
  transition: border-color 0.15s, transform 0.1s, box-shadow 0.1s !important;
  position: relative !important;
}}
.stButton button:hover {{
  border-color: var(--accent) !important;
  color: var(--cream) !important;
  background: transparent !important;
  transform: translate(-2px, -2px) !important;
  box-shadow: 2px 2px 0 var(--accent) !important;
}}
.stButton button:active {{
  transform: translate(0, 0) !important;
  box-shadow: none !important;
}}
.stButton button div,
.stButton button p,
.stButton button span {{
  background: transparent !important;
  background-color: transparent !important;
}}

/* Icon buttons inside expanders */
[data-testid="stExpander"] [data-testid="column"] .stButton button {{
  background: transparent !important;
  color: var(--faded) !important;
  border: none !important;
  border-radius: 0 !important;
  box-shadow: none !important;
  padding: 4px 6px !important;
  font-size: 16px !important;
  font-family: inherit !important;
  letter-spacing: 0 !important;
  text-transform: none !important;
  transition: color 0.15s, transform 0.1s !important;
}}
[data-testid="stExpander"] [data-testid="column"] .stButton button:hover {{
  color: var(--accent) !important;
  transform: none !important;
  box-shadow: none !important;
  border: none !important;
  background: transparent !important;
}}

/* ── Song cards — ruled lines, not boxes ── */
.stExpander {{
  background: transparent !important;
  border: none !important;
  border-top: 1px solid var(--border) !important;
  border-radius: 0 !important;
  margin-bottom: 0 !important;
  padding: 0 !important;
  position: relative !important;
}}
.stExpander::before {{
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 2px;
  background: transparent;
  transition: background 0.2s;
}}
.stExpander:hover::before {{
  background: var(--accent);
}}
.stExpander:last-child {{
  border-bottom: 1px solid var(--border) !important;
}}
.stExpander summary {{
  color: var(--cream) !important;
  font-family: var(--sans) !important;
  font-weight: 400 !important;
  font-size: 14px !important;
  letter-spacing: -0.01em !important;
  padding: 14px 0 14px 12px !important;
}}
.stExpander summary:hover {{ color: var(--accent) !important; }}
details[data-testid="stExpander"] {{ border: none !important; }}

/* ── Metrics — mono data style ── */
[data-testid="stMetric"] {{
  background: transparent;
  border: none;
  border-top: 1px solid var(--border);
  border-radius: 0;
  padding: 12px 4px !important;
}}
[data-testid="stMetricValue"] {{
  font-family: var(--mono) !important;
  color: var(--cream) !important;
  font-size: 1.6rem !important;
  font-weight: 300 !important;
  letter-spacing: -0.02em !important;
}}
[data-testid="stMetricLabel"] {{
  font-family: var(--mono) !important;
  color: var(--faded) !important;
  font-size: 9px !important;
  text-transform: uppercase !important;
  letter-spacing: 0.12em !important;
}}

/* ── Progress bar ── */
.stProgress > div > div > div > div {{
  background: var(--accent) !important;
  border-radius: 0 !important;
}}
.stProgress > div > div > div {{
  background-color: var(--border) !important;
  border-radius: 0 !important;
  height: 2px !important;
}}

/* ── Inputs ── */
.stTextInput input, .stTextArea textarea {{
  background-color: transparent !important;
  color: var(--cream) !important;
  border: none !important;
  border-bottom: 1px solid var(--border) !important;
  border-radius: 0 !important;
  font-family: var(--sans) !important;
  padding-left: 0 !important;
}}
.stTextInput input::placeholder, .stTextArea textarea::placeholder {{
  color: var(--faded) !important;
  font-style: italic;
  font-family: var(--sans) !important;
}}
.stTextInput input:focus, .stTextArea textarea:focus {{
  border-bottom-color: var(--accent) !important;
  box-shadow: none !important;
  outline: none !important;
}}

/* ── Selectbox ── */
.stSelectbox > div > div, [data-baseweb="select"] > div {{
  background-color: transparent !important;
  border: none !important;
  border-bottom: 1px solid var(--border) !important;
  border-radius: 0 !important;
  color: var(--cream) !important;
  font-family: var(--sans) !important;
}}

/* ── Slider ── */
.stSlider [data-baseweb="slider"] [data-testid="stThumb"] {{
  background: var(--cream) !important;
  border: 1px solid var(--accent) !important;
  border-radius: 0 !important;
  width: 10px !important;
  height: 10px !important;
  box-shadow: none !important;
}}
.stSlider [data-baseweb="slider"] [role="progressbar"] {{
  background: var(--accent) !important;
  border-radius: 0 !important;
}}

/* ── Checkbox ── */
.stCheckbox label span {{ color: var(--cream) !important; }}

/* ── Dividers ── */
hr {{
  border: none !important;
  border-top: 1px solid var(--border) !important;
  margin: 1.4rem 0 !important;
}}

/* ── Alert boxes ── */
[data-baseweb="notification"],
[data-testid="stNotification"],
div[role="alert"],
.stAlert,
.stAlert > div {{
  background-color: transparent !important;
  border: none !important;
  border-left: 2px solid var(--border) !important;
  border-radius: 0 !important;
  color: var(--cream) !important;
  font-family: var(--mono) !important;
  font-size: 12px !important;
  padding-left: 12px !important;
}}
div[data-testid="stNotification"][kind="success"],
.stAlert [kind="success"] {{ border-left-color: #7A9E6A !important; }}
div[data-testid="stNotification"][kind="info"]    {{ border-left-color: #6B8FAD !important; }}
div[data-testid="stNotification"][kind="warning"] {{ border-left-color: var(--accent) !important; }}
div[data-testid="stNotification"][kind="error"]   {{ border-left-color: #B04A3A !important; }}

/* ── Number input ── */
.stNumberInput input {{
  background-color: transparent !important;
  color: var(--cream) !important;
  border: none !important;
  border-bottom: 1px solid var(--border) !important;
  border-radius: 0 !important;
  font-family: var(--mono) !important;
}}

/* ── Audio player ── */
audio {{
  width: 100%;
  accent-color: var(--accent);
  margin-top: 10px;
  opacity: 0.85;
  filter: sepia(0.2);
}}

/* ── Hide hamburger ── */
#MainMenu {{ display: none !important; }}

/* ── Scrollbar ── */
::-webkit-scrollbar {{ width: 3px; height: 3px; }}
::-webkit-scrollbar-track {{ background: transparent; }}
::-webkit-scrollbar-thumb {{ background: var(--border); }}
::-webkit-scrollbar-thumb:hover {{ background: var(--faded); }}

/* ── Profile photo badge ── */
.profile-photo-wrap {{
  position: relative;
  width: 80px;
  margin: 0 auto;
}}
.profile-photo-plus {{
  position: absolute;
  bottom: 0;
  right: 0;
  width: 18px;
  height: 18px;
  border-radius: 0;
  background: var(--accent);
  border: 1px solid #110f0c;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 400;
  font-family: var(--mono);
  color: var(--cream);
  cursor: pointer;
  user-select: none;
  transition: background 0.15s;
}}
.profile-photo-plus:hover {{ background: #9E4E2E; }}
.element-container:has(.photo-btn-anchor) + .element-container {{
  position: fixed !important;
  top: -9999px !important;
  left: -9999px !important;
  width: 0 !important;
  height: 0 !important;
  overflow: hidden !important;
}}

/* ── Inline code ── */
code {{
  font-family: var(--mono) !important;
  background: transparent !important;
  color: var(--sand) !important;
  border-radius: 0 !important;
  font-size: 11px !important;
  border-bottom: 1px solid var(--border) !important;
  padding: 0 2px !important;
}}

/* ── Sidebar subheaders ── */
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 {{
  font-family: var(--mono) !important;
  font-size: 9px !important;
  font-style: normal !important;
  font-weight: 400 !important;
  letter-spacing: 0.15em !important;
  text-transform: uppercase !important;
  color: var(--faded) !important;
  border-left: none !important;
  padding-left: 0 !important;
  border-bottom: 1px solid var(--border) !important;
  padding-bottom: 6px !important;
  margin-bottom: 8px !important;
}}
</style>
"""

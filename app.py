# ══════════════════════════════════════════════════════════════════
#  STAGE-4 | SMART CITY ANALYTICS DASHBOARD
#  Real-Time Intelligence Platform — Streamlit Multi-Page Dashboard
# ══════════════════════════════════════════════════════════════════

import os
import time
import json
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
from datetime import datetime, timedelta
from scipy import stats

# ── Page Config ───────────────────────────────────────────────────
st.set_page_config(
    page_title="SmartCity Analytics",
    page_icon="🏙️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ══════════════════════════════════════════════════════════════════
#  THEME & GLOBAL CSS
# ══════════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Sans:wght@300;400;500&display=swap');

/* ── Root variables ── */
:root {
    --bg:        #07090f;
    --surface:   #0d1117;
    --card:      #111620;
    --border:    #1e2633;
    --accent1:   #00d4ff;   /* cyan  — traffic  */
    --accent2:   #00ff99;   /* green — energy   */
    --accent3:   #ff6b6b;   /* coral — pollution*/
    --accent4:   #a78bfa;   /* violet— city     */
    --accent5:   #fbbf24;   /* gold  — general  */
    --text:      #e2e8f0;
    --muted:     #64748b;
    --warning:   #fbbf24;
    --danger:    #ef4444;
    --success:   #22c55e;
}

/* ── Global reset ── */
html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
    background-color: var(--bg);
    color: var(--text);
}

/* Hide default streamlit chrome */
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 1.5rem 2rem 3rem; max-width: 1600px; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0a0f1a 0%, #07090f 100%);
    border-right: 1px solid var(--border);
}
[data-testid="stSidebar"] .stRadio > label {
    font-family: 'Syne', sans-serif;
    font-size: 0.78rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--muted);
}
[data-testid="stSidebar"] .stRadio [data-testid="stMarkdownContainer"] p {
    color: var(--text) !important;
}

/* ── Page header ── */
.page-header {
    display: flex;
    align-items: center;
    gap: 1rem;
    margin-bottom: 1.8rem;
    padding-bottom: 1rem;
    border-bottom: 1px solid var(--border);
}
.page-icon {
    font-size: 2rem;
    line-height: 1;
}
.page-title {
    font-family: 'Syne', sans-serif;
    font-size: 1.8rem;
    font-weight: 800;
    color: var(--text);
    margin: 0;
    letter-spacing: -0.02em;
}
.page-sub {
    font-size: 0.85rem;
    color: var(--muted);
    margin-top: 0.1rem;
}

/* ── KPI card ── */
.kpi-grid { display: grid; gap: 1rem; margin-bottom: 1.5rem; }
.kpi-card {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1.2rem 1.4rem;
    position: relative;
    overflow: hidden;
    transition: border-color .2s;
    min-height: 110px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    box-sizing: border-box;
}
.kpi-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
}
.kpi-card.cyan::before  { background: var(--accent1); }
.kpi-card.green::before { background: var(--accent2); }
.kpi-card.coral::before { background: var(--accent3); }
.kpi-card.violet::before{ background: var(--accent4); }
.kpi-card.gold::before  { background: var(--accent5); }
.kpi-card:hover { border-color: #2d3a4f; }
.kpi-label {
    font-size: 0.72rem;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--muted);
    margin-bottom: 0.5rem;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis
}
.kpi-value {
    font-family: 'Syne', sans-serif;
    font-size: clamp(1.1rem, 2.2vw, 1.7rem);
    font-weight: 700;
    color: var(--text);
    line-height: 1;
    margin-bottom: 0.3rem;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.kpi-delta {
    font-size: 0.73rem;
    font-weight: 500;
    min-height: 1.1em;
}
.kpi-delta.good   { color: var(--success); }
.kpi-delta.bad { color: var(--danger); }
.kpi-delta.neutral { color: var(--muted); }
.kpi-icon {
    position: absolute;
    right: 1rem;
    top: 1rem;
    font-size: 1.5rem;
    opacity: 0.13;
    pointer-events: none;
}

/* ── Section header ── */
.section-title {
    font-family: 'Syne', sans-serif;
    font-size: 0.8rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: var(--muted);
    margin: 1.6rem 0 0.8rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}
.section-title::after {
    content: '';
    flex: 1;
    height: 1px;
    background: var(--border);
}

/* ── Alert / badge ── */
.alert {
    border-radius: 8px;
    padding: 0.65rem 1rem;
    font-size: 0.83rem;
    font-weight: 500;
    margin-bottom: 0.5rem;
    display: flex;
    align-items: center;
    gap: 0.6rem;
}
.alert-danger  { background: rgba(239,68,68,.12);  border-left: 3px solid var(--danger);  color: #fca5a5; }
.alert-warning { background: rgba(251,191,36,.10); border-left: 3px solid var(--warning); color: #fde68a; }
.alert-success { background: rgba(34,197,94,.10);  border-left: 3px solid var(--success); color: #86efac; }
.alert-info    { background: rgba(0,212,255,.08);  border-left: 3px solid var(--accent1); color: #67e8f9; }

/* ── Anomaly badge ── */
.anomaly-badge {
    display: inline-block;
    padding: 0.15rem 0.5rem;
    border-radius: 6px;
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.05em;
    text-transform: uppercase;
}
.anomaly-high   { background: rgba(239,68,68,.18);  color: #fca5a5; border: 1px solid #ef4444; }
.anomaly-medium { background: rgba(251,191,36,.14); color: #fde68a; border: 1px solid #fbbf24; }
.anomaly-low    { background: rgba(34,197,94,.12);  color: #86efac; border: 1px solid #22c55e; }
            
/* ── Sidebar logo ── */
.sidebar-logo {
    font-family: 'Syne', sans-serif;
    font-size: 1.1rem;
    font-weight: 800;
    letter-spacing: -0.02em;
    color: var(--text);
    padding: 0.5rem 0 1.2rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}
.sidebar-logo span { color: var(--accent1); }

/* ── Selectbox, slider styling | Input widgets ── */

/* Selectbox and multiselect input boxews */
.stSelectbox > div > div,
.stMultiSelect > div > div {
    background: #1a2235 !important;
    border-color:#2d3a4f !important;
    color: #e2e8f0 !important;
}

/* Text inside the select/multiselect input */
.stSelectbox > div > div > div,
.stMultiSelect > div > div > div,
.stSelectbox [data-baseweb="select"] > div,
.stMultiSelect [data-baseweb="select"] > div {
    color: #e2e8f0 !important;
    background: transparent !important;
}

/* The placeholder text */
.stSelectbox [data-baseweb="select"] input,
.stMultiSelect [data-baseweb="select"] input {
    color: #e2e8f0 !important;
}

/* Selected tags/pills in multiselect */
.stMultiSelect [data-baseweb="tag"] {
    background-color: #1e3a5f !important;
    color: #e2e8f0 !important;
    border: 1px solid #00d4ff !important;
}
.stMultiSelect [data-baseweb="tag"] span {
    color: #e2e8f0 !important;
}

/* Dropdown menu (popover) background */
[data-baseweb="popover"],
[data-baseweb="menu"],
[role="listbox"],
ul[data-baseweb="menu"] {
    background-color: #111620 !important;
    border: 1px solid #2d3a4f !important;
    border-radius: 8px !important;
}

/* Fix dropdown max-height so all 40+ options are scrollable */
[data-baseweb="popover"] ul,
[data-baseweb="menu"] ul,
[role="listbox"],
ul[data-baseweb="menu"] {
    max-height: 320px !important;
    overflow-y: auto !important;
}

/* Individual dropdown options */
[data-baseweb="menu"] li,
[role="option"],
[data-baseweb="option"] {
    background-color: #111620 !important;
    color: #e2e8f0 !important;
}

/* Hovered dropdown option */
[data-baseweb="menu"] li:hover,
[role="option"]:hover,
[data-baseweb="option"]:hover {
    background-color: #1e2d45 !important;
    color: #00d4ff !important;
}

/* Focused/selected option */
[data-baseweb="menu"] li[aria-selected="true"],
[role="option"][aria-selected="true"] {
    background-color: #0f2040 !important;
    color: #00d4ff !important;
}

/* KPI cards — ensure text is visible (not inheriting dark bg) */
.kpi-card {
    color: #e2e8f0 !important;
}
.kpi-value {
    color: #e2e8f0 !important;
}
.kpi-label {
    color: #94a3b8 !important;
}

/* Slider label and value text */
.stSlider label, .stSlider [data-testid="stMarkdownContainer"] {
    color: #e2e8f0 !important;
}

/* Multiselect label */
.stMultiSelect label,
.stSelectbox label {
    color: #e2e8f0 !important;
}

/* Sidebar widget labels */
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] .stMarkdown p,
[data-testid="stSidebar"] .stMarkdown strong {
    color: #e2e8f0 !important;
}

/* Scrollbar styling for dropdowns */
[data-baseweb="popover"] ul::-webkit-scrollbar,
[role="listbox"]::-webkit-scrollbar {
    width: 6px;
}
[data-baseweb="popover"] ul::-webkit-scrollbar-track,
[role="listbox"]::-webkit-scrollbar-track {
    background: #0d1117;
}
[data-baseweb="popover"] ul::-webkit-scrollbar-thumb,
[role="listbox"]::-webkit-scrollbar-thumb {
    background: #2d3a4f;
    border-radius: 3px;
}
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════
#  PLOTLY DARK TEMPLATE
# ══════════════════════════════════════════════════════════════════
CHART_THEME = dict(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="DM Sans", color="#94a3b8", size=12),
    margin=dict(l=10, r=10, t=40, b=10),
)
GRIDCOLOR = "rgba(30,38,51,0.8)"

def apply_theme(fig, title="", height=380):
    """
    Apply dark dashboard theme + consistent hover styling to any figure.
    hovermode='closest' ensures only the nearest point shows its tooltip.
    hoverlabel gives a dark semi-transparent card with clear text.
    """
    fig.update_layout(
        **CHART_THEME,
        title=dict(
            text=title,
            font=dict(family="Syne", size=13, color="#e2e8f0"),
            x=0
        ),
        height=height,
        legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor="rgba(0,0,0,0)"),
        # ── Hover config ─────────────────────────────────────────
        hovermode="closest",          # show tooltip for nearest point only
        hoverlabel=dict(
            bgcolor="#1e2633",        # dark card background
            bordercolor="#00d4ff",    # cyan border for visibility
            font=dict(
                family="DM Sans",
                size=13,
                color="#e2e8f0",      # light text on dark card
            ),
            namelength=-1,            # show full trace name, never truncate
        ),
    )
    fig.update_xaxes(gridcolor=GRIDCOLOR, zeroline=False)
    fig.update_yaxes(gridcolor=GRIDCOLOR, zeroline=False)
    return fig

# Colors
C_CYAN   = "#00d4ff"
C_GREEN  = "#00ff99"
C_CORAL  = "#ff6b6b"
C_VIOLET = "#a78bfa"
C_GOLD   = "#fbbf24"
PALETTE  = [C_CYAN, C_GREEN, C_CORAL, C_VIOLET, C_GOLD, "#f472b6", "#34d399", "#fb923c"]

# ══════════════════════════════════════════════════════════════════
#  PATHS
#  CLEAN_DIR  → Stage-1 cleaned CSVs  (historical 500k rows)
#  OUTPUT_DIR → Stage-3 prediction CSVs (streaming results)
# ══════════════════════════════════════════════════════════════════
CLEAN_DIR = "clean_data"
OUTPUT_DIR = "output"
RT_FILES = ["traffic_predictions.csv", "energy_predictions.csv", "pollution_predictions.csv"]

# ══════════════════════════════════════════════════════════════════
#  DATA LOADING
# ══════════════════════════════════════════════════════════════════
def _ensure_time_cols(df):
    """Derive hour/dayofweek/month/year from timestamp if not already present."""
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        if "hour" not in df.columns:
            df["hour"]      = df["timestamp"].dt.hour
            df["day"]       = df["timestamp"].dt.day
            df["dayofweek"] = (df["timestamp"].dt.dayofweek + 5) % 7
            df["month"]     = df["timestamp"].dt.month
            df["year"]      = df["timestamp"].dt.year
    return df

# ── Static EDA loader (Stage-1) ───────────────────────────────────
# TTL = 1 hour because the cleaned data rarely changes after Stage-1
@st.cache_data(ttl=None)
def load_static_data():
    """
    PURPOSE: Load Stage-1 cleaned CSVs (historical 500k rows).
    SOURCE : clean_data/traffic_clean.csv
             clean_data/energy_clean.csv
             clean_data/pollution_clean.csv
    USED FOR: Static EDA mode showing historical patterns.
    """
    dfs = {} 
    files = {
        "traffic"  : "traffic_clean.csv",
        "energy"   : "energy_clean.csv",
        "pollution": "pollution_clean.csv",
    }
    for key, fname in files.items():
        path = os.path.join(CLEAN_DIR, fname)
        if os.path.exists(path):
            df = pd.read_csv(path)
            df = _ensure_time_cols(df)
            dfs[key] = df
        else:
            dfs[key] = None
    return dfs

# ── Real-time loader (Stage-3) ────────────────────────────────────
# TTL = 15 seconds so Streamlit re-reads output/ files frequently
@st.cache_data(ttl=15)
def load_realtime_data():
    """
    PURPOSE: Load Stage-3 prediction CSVs written by spark_streaming.py.
    SOURCE : output/traffic_predictions.csv
             output/energy_predictions.csv
             output/pollution_predictions.csv
    USED FOR: Real-Time mode. ttl=15 means Streamlit re-reads every 15s.
              Combined with the auto-refresh engine, this makes the
              dashboard update automatically as new batches arrive.
    """
    dfs = {}
    files = {
        "traffic"  : "traffic_predictions.csv",
        "energy"   : "energy_predictions.csv",
        "pollution": "pollution_predictions.csv",
    }
    for key, fname in files.items():
        path = os.path.join(OUTPUT_DIR, fname)
        if os.path.exists(path):
            df = pd.read_csv(path)
            df = _ensure_time_cols(df)
            dfs[key] = df
        else:
            dfs[key] = None
    return dfs

def latest_mtime():
    """Return the most recent modification time across all 3 prediction files."""
    times = [os.path.getmtime(os.path.join(OUTPUT_DIR, f))
             for f in RT_FILES if os.path.exists(os.path.join(OUTPUT_DIR, f))]
    return max(times) if times else 0.0

def merge_static_and_rt(static_df, rt_df, target_col):
    """
    Real-Time mode: merge historical (static) rows with new streaming rows.
    Streaming rows carry predicted_* columns; historical rows don't.
    Result: all rows visible in charts, predictions shown only where available.
    """
    frames = []
    if static_df is not None:
        # Limit static data to last 10000 rows to avoid memory issues
        frames.append(static_df.tail(10000))
    if rt_df is not None:
        frames.append(rt_df)
    if not frames:
        return None
    merged = pd.concat(frames, ignore_index=True, sort=False)
    if "timestamp" in merged.columns:
        ts = pd.to_datetime(merged["timestamp"], errors="coerce")
        merged["timestamp"] = ts.dt.tz_convert(None) if ts.dt.tz is not None else ts
        merged = merged.sort_values("timestamp").reset_index(drop=True)
    return merged

# ══════════════════════════════════════════════════════════════════
#  GLOBAL CONSTANTS
# ══════════════════════════════════════════════════════════════════
ALL_AREAS = [
    "Whitefield","Electronic City","MG Road","Indiranagar","Yelahanka","Silk Board",
    "Hebbal","Marathahalli","BTM Layout","Jayanagar","Rajajinagar","Banashankari",
    "Koramangala","HSR Layout","Bellandur","KR Puram","Malleshwaram","Basavanagudi",
    "Ulsoor","Domlur","Kengeri","Magadi Road","Peenya","Nagawara","Thanisandra",
    "Hennur","Varthur","Sarjapur","Devanahalli","Chandapura","Attibele",
    "Bommanahalli","Kadugodi","Bidadi","Rajarajeshwari Nagar","Yeshwanthpur",
    "Shivajinagar","Majestic","Cubbon Park","JP Nagar","Bannerghatta Road"
]  # 41 Bangalore areas

# ══════════════════════════════════════════════════════════════════
#  LOAD STATIC DATA EARLY — needed by the sidebar date-range filter
#  (static_raw must exist before `with st.sidebar:` runs because the
#   date_input widget reads min/max timestamps from it at line ~621)
# ══════════════════════════════════════════════════════════════════
static_raw = load_static_data()

# ══════════════════════════════════════════════════════════════════
#  SIDEBAR NAVIGATION (rendered first - sets data_mode, auto_refresh, filters)
# ══════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("""
    <div class="sidebar-logo">
        🏙️ Smart<span>City</span>
    </div>
    """, unsafe_allow_html=True)

    # ── Navigation ────────────────────────────────────────────────
    # WHAT THIS DOES: controls which dashboard page is shown.
    # All 4 pages share the same data and filters.
    st.markdown("**Navigation**")
    page = st.radio("", [
        "🏙️  City Overview",
        "🚦  Traffic",
        "⚡  Energy",
        "🌫️  Pollution",
        "🔍  Anomaly Detection",
    ], label_visibility="collapsed")
 
    st.divider()
 
    # ── Data Source ───────────────────────────────────────────────
    # WHAT THIS DOES: switches between 3 data modes.
    #   📊 Static EDA   — reads Stage-1 cleaned_data/ CSVs (500k rows)
    #                     Best for exploring historical patterns
    #   🔴 Real-Time    — loads cleaned_data/ MERGED with output/ predictions
    #                     UPrediction charts shown. Auto-refresh available
    st.markdown("**Data Source**")
    data_mode = st.radio("", [
        "📊  Static EDA (Stage-1)",
        "🔴  Real-Time Stream (Stage-3)",
    ], label_visibility="collapsed")
 
    st.divider()
 
    # ── Auto-Refresh (Real-Time mode only) ────────────────────────
    # WHAT THIS DOES: enables live polling of output/ folder
    # HOW IT WORKS: after the full page renders, a blocking sleep
    # runs at the bottom of the script, then st.rerun() is called.
    # This avoids the infinite-loop problem of calling rerun() during setup.
    # File-mtime tracking detects new data instantly; the timer is a fallback
    auto_refresh    = False
    refresh_interval = 30
 
    if "Real-Time" in data_mode:
        st.markdown("**Auto-Refresh**")
        auto_refresh = st.toggle("Enable Auto-Refresh", value=True,
            help="Automatically reload when new prediction files arrive in output/")
        if auto_refresh:
            refresh_interval = st.slider("Refresh interval (s)", 10, 120, 30, 5,
                help="Polling frequency. Lower = more responsive but more CPU.")
            st.markdown(f"""
            <div class="alert alert-success">
                🟢 Live · polling every {refresh_interval}s
            </div>""", unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="alert alert-warning">
                ⏸ Auto-refresh OFF · click Refresh Now to update
            </div>""", unsafe_allow_html=True)
        st.divider()
 
    # ── Filters ───────────────────────────────────────────────────
    # WHAT THIS DOES: applies to every chart on every page simultaneously.
    # Leave empty to show all values.
    st.subheader("Filters", divider=False)

    # Initialise session_state defaults on first run
    if "sel_areas"   not in st.session_state: st.session_state.sel_areas   = []
    if "sel_zones"   not in st.session_state: st.session_state.sel_zones   = []
    if "sel_seasons" not in st.session_state: st.session_state.sel_seasons = []
    if "date_start"  not in st.session_state: st.session_state.date_start  = None
    if "date_end"    not in st.session_state: st.session_state.date_end    = None

    sel_areas   = st.multiselect("Areas",   ALL_AREAS,
                                 key="sel_areas",
                                 help="Empty = show all areas")
    sel_zones   = st.multiselect("Zones",   ["Central","East","West","North","South"],
                                 key="sel_zones",
                                 help="Empty = show all zones")
    sel_seasons = st.multiselect("Seasons", ["Summer","Monsoon","Winter"],
                                 key="sel_seasons",
                                 help="Empty = show all seasons")
    
    # Derives min/max from staticst.subheader("Date Range", divider=False)
    st.subheader("Date Range", divider=False)
    _all_ts = []
    _rt_raw_sidebar = load_realtime_data() if "Real-Time" in data_mode else {}
    for _df in [static_raw.get("traffic"), static_raw.get("energy"), static_raw.get("pollution"),
                _rt_raw_sidebar.get("traffic"), _rt_raw_sidebar.get("energy"), _rt_raw_sidebar.get("pollution")]:
        if _df is not None and "timestamp" in _df.columns:
            _ts_col = pd.to_datetime(_df["timestamp"], errors="coerce").dropna()
            # Strip timezone so all timestamps are tz-naive before comparing
            if _ts_col.dt.tz is not None:
                _ts_col = _ts_col.dt.tz_convert(None)
            if len(_ts_col) > 0:
                _all_ts.extend([_ts_col.min(), _ts_col.max()])
    if _all_ts:
        _ts_min = pd.to_datetime(min(_all_ts)).date()
        _ts_max = max(pd.to_datetime(max(_all_ts)).date(), datetime.now().date())
        date_range = st.date_input(
            "Date range",
            value=(st.session_state.date_start or _ts_min,
                   st.session_state.date_end   or _ts_max),
            min_value=_ts_min,
            max_value=_ts_max,
            help="Filter all charts to this date window. Reset to full range by clearing.",
        )
        if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
            st.session_state.date_start, st.session_state.date_end = date_range
            sel_date_start = pd.Timestamp(date_range[0])
            sel_date_end   = pd.Timestamp(date_range[1]) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
        else:
            sel_date_start = sel_date_end = None
    else:
        sel_date_start = sel_date_end = None
 
    st.divider()

    # ── Manual refresh ────────────────────────────────────────────
    # WHAT THIS DOES: forces immediate cache clear + page rerun.
    # Use this if you want to reload data right now in any mode.
    if st.button("🔄  Refresh Now", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
 
    st.markdown(f"""
    <div style="font-size:0.7rem;color:#334155;margin-top:0.8rem;">
        Last render: {datetime.now().strftime('%H:%M:%S')}
    </div>""", unsafe_allow_html=True)
 
# ══════════════════════════════════════════════════════════════════
#  LOAD DATA BASED ON SELECTED MODE
# ══════════════════════════════════════════════════════════════════
is_realtime = "Real-Time" in data_mode
 
if is_realtime:
    rt_raw = load_realtime_data()
    # Merge hostorical + streaming for all 3 datasets
    ft = merge_static_and_rt(static_raw.get("traffic"), rt_raw.get("traffic"), "vehicle_count")
    fe = merge_static_and_rt(static_raw.get("energy"), rt_raw.get("energy"), "energy_consumption")
    fp = merge_static_and_rt(static_raw.get("pollution"), rt_raw.get("pollution"), "AQI")
    has_rt_data = any(v is not None for v in rt_raw.values())
else:
    # Static EDA mode - only cleaned data is loaded
    ft = static_raw.get("traffic")
    fe = static_raw.get("energy")
    fp = static_raw.get("pollution")
    rt_raw = {"traffic": None, "energy": None, "pollution": None}
    has_rt_data = False

# Warn if static files missing
static_missing = any(v is None for v in static_raw.values())
if static_missing and not is_realtime:
    st.error("⚠️ clean_data/ folder not found or incomplete. "
             "Run Stage-1 data.ipynb first to generate cleaned CSVs.")
    st.stop()
 
# ── Apply sidebar filters ─────────────────────────────────────────
# WHAT THIS DOES: subsets ft, fe, fp to the selected areas/zones/seasons.
# An empty selection means "show everything" (no filter applied).
def apply_filters(df, areas, zones, seasons, date_start=None, date_end=None):
    if df is None:
        return None
    if areas   and "area"   in df.columns: df = df[df["area"].isin(areas)]
    if zones   and "zone"   in df.columns: df = df[df["zone"].isin(zones)]
    if seasons and "season" in df.columns: df = df[df["season"].isin(seasons)]

    # date range filter applied when timestamps are available.
    # Guard against tz-aware column vs tz-naive Timestamp mismatch:
    # if the column carries timezone info, localize the filter bounds to
    # the same timezone before comparing; otherwise strip tz from bounds.
    if date_start is not None and "timestamp" in df.columns:
        col_tz = df["timestamp"].dt.tz
        ds = pd.Timestamp(date_start)
        de = pd.Timestamp(date_end) if date_end is not None else None
        if col_tz is not None:
            # column is tz-aware → make bounds tz-aware
            ds = ds.tz_localize(col_tz) if ds.tzinfo is None else ds.tz_convert(col_tz)
            if de is not None:
                de = de.tz_localize(col_tz) if de.tzinfo is None else de.tz_convert(col_tz)
        else:
            # column is tz-naive → strip tz from bounds if present
            if ds.tzinfo is not None:
                ds = ds.tz_localize(None)
            if de is not None and de.tzinfo is not None:
                de = de.tz_localize(None)
        df = df[df["timestamp"] >= ds]
        if de is not None:
            df = df[df["timestamp"] <= de]
    elif date_end is not None and "timestamp" in df.columns:
        col_tz = df["timestamp"].dt.tz
        de = pd.Timestamp(date_end)
        if col_tz is not None:
            de = de.tz_localize(col_tz) if de.tzinfo is None else de.tz_convert(col_tz)
        elif de.tzinfo is not None:
            de = de.tz_localize(None)
        df = df[df["timestamp"] <= de]
    return df
 
ft = apply_filters(ft, sel_areas, sel_zones, sel_seasons, sel_date_start, sel_date_end)
fe = apply_filters(fe, sel_areas, sel_zones, sel_seasons, sel_date_start, sel_date_end)
fp = apply_filters(fp, sel_areas, sel_zones, sel_seasons, sel_date_start, sel_date_end)

# Guard - ensure we have atleast something to show
_missing = [name for name, df in [("Traffic",ft),("Energy",fe),("Pollution",fp)]
            if df is None or len(df) == 0]
if _missing:
    st.warning(f"⚠️ {', '.join(_missing)} dataset(s) empty after filtering. "
               "Clear filters or check that Stage-1 has run.")
    # Only stop if ALL three are missing — one missing still lets others render
    if len(_missing) == 3:
        st.stop()

# Predicted columns: only present in streaming rows.
# Check column existence against raw RT data (before filters) so that
# a date-range filter that excludes streaming timestamps doesn't hide charts.
_rt_t = rt_raw.get("traffic")
_rt_e = rt_raw.get("energy")
_rt_p = rt_raw.get("pollution")
has_pred_t = (_rt_t is not None and "predicted_vehicle_count"      in _rt_t.columns) or \
             (ft    is not None and "predicted_vehicle_count"      in ft.columns)
has_pred_e = (_rt_e is not None and "predicted_energy_consumption" in _rt_e.columns) or \
             (fe    is not None and "predicted_energy_consumption" in fe.columns)
has_pred_p = (_rt_p is not None and "predicted_AQI"                in _rt_p.columns) or \
             (fp    is not None and "predicted_AQI"                in fp.columns)

# For prediction charts: use filtered ft/fe/fp rows where predictions exist.
# If filters leave ft_pred empty but raw RT has predictions, fall back to raw RT rows.
def _make_pred_df(filtered_df, raw_rt_df, col):
    if filtered_df is not None and col in filtered_df.columns:
        sub = filtered_df.dropna(subset=[col])
        if len(sub) > 0:
            return sub
    if raw_rt_df is not None and col in raw_rt_df.columns:
        return raw_rt_df.dropna(subset=[col])
    return None

ft_pred = _make_pred_df(ft, _rt_t, "predicted_vehicle_count")
fe_pred = _make_pred_df(fe, _rt_e, "predicted_energy_consumption")
fp_pred = _make_pred_df(fp, _rt_p, "predicted_AQI")

# ══════════════════════════════════════════════════════════════════
#  UTILITY — ERROR BOUNDARY & SPINNER
# ══════════════════════════════════════════════════════════════════
def safe_chart(fn, *args, label="chart", **kwargs):
    """
    Point 1 — Error boundary: wraps any chart-rendering call so a single
    bad column or empty slice shows a graceful 'unavailable' card instead
    of crashing the whole page with a raw Python traceback.
    Point 9 — Loading spinner: shows a spinner while the chart renders,
    making cold-cache loads feel responsive instead of frozen.
    """
    try:
        with st.spinner(f"Loading {label}…"):
            return fn(*args, **kwargs)
    except Exception as e:
        st.markdown(
            f'<div class="alert alert-warning" style="font-size:0.8rem;">'
            f'⚠️ <strong>{label}</strong> could not render: '
            f'<code style="font-size:0.75rem">{e}</code></div>',
            unsafe_allow_html=True)
 
# ══════════════════════════════════════════════════════════════════
#  UTILITY FUNCTIONS
# ══════════════════════════════════════════════════════════════════
# Model metrics loader and renderer
@st.cache_data(ttl=15)
def load_model_metrics():
    """
    Point 2 — Model metadata: reads model_metrics.json written by
    spark_streaming.py alongside prediction CSVs.
    Expected schema:
      { "traffic":   {"model":"DecisionTree","mae":…,"rmse":…,"r2":…,
                      "trained_rows":…,"trained_at":"…","features":…},
        "energy":    { … },
        "pollution": { … } }
    Returns {} if file not found (graceful degradation).
    """
    path = os.path.join(OUTPUT_DIR, "model_metrics.json")
    if not os.path.exists(path):
        return {}
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return {}

def render_model_metrics(stream_key, accent_color):
    """Render a compact model metadata card for one stream."""
    metrics = load_model_metrics()
    m = metrics.get(stream_key)
    if not m:
        st.caption("ℹ️ No model_metrics.json found — spark_streaming.py hasn't written metrics yet.")
        return
    trained_at = m.get("trained_at", "unknown")
    _tr = m.get("trained_rows")
    trained_rows_str = f"{int(_tr):,}" if isinstance(_tr, (int, float)) else "—"
    # Format numeric metrics safely
    def _fmt(val, d=4):
        if val is None: return "—"
        try: return f"{float(val):.{d}f}"
        except: return str(val)
    mae_str  = _fmt(m.get("mae"))
    rmse_str = _fmt(m.get("rmse"))
    r2_str   = _fmt(m.get("r2"))
    feats = m.get("features", "—")
    feats_str = ", ".join(str(f) for f in feats) if isinstance(feats, list) else (str(feats) if feats else "—")
    model_name = m.get("model") or "—"
    st.markdown(f"""
    <div style="background:#0d1117;border:1px solid #1e2633;border-left:3px solid {accent_color};
                border-radius:8px;padding:0.7rem 1rem;font-size:0.8rem;margin-bottom:0.5rem;">
        <span style="color:#94a3b8;">Model:</span>
        <strong style="color:#e2e8f0;">{model_name}</strong> &nbsp;|&nbsp;
        <span style="color:#94a3b8;">MAE:</span>
        <strong style="color:{accent_color};">{mae_str}</strong> &nbsp;|&nbsp;
        <span style="color:#94a3b8;">RMSE:</span>
        <strong style="color:{accent_color};">{rmse_str}</strong> &nbsp;|&nbsp;
        <span style="color:#94a3b8;">R²:</span>
        <strong style="color:{accent_color};">{r2_str}</strong> &nbsp;|&nbsp;
        <span style="color:#94a3b8;">Trained on:</span>
        <strong style="color:#e2e8f0;">{trained_rows_str} rows</strong> &nbsp;|&nbsp;
        <span style="color:#94a3b8;">Features:</span>
        <strong style="color:#e2e8f0;">{feats_str}</strong> &nbsp;|&nbsp;
        <span style="color:#94a3b8;">As of:</span>
        <strong style="color:#e2e8f0;">{trained_at}</strong>
    </div>""", unsafe_allow_html=True)

# KPI card
def kpi(label, value, delta=None, icon="", color="cyan", fmt="{:.0f}", lower_is_better=False):
    """
    Renders a styled KPI card.
    label : title shown above the number
    value : numeric value (displayed large)
    delta : % change vs previous period (positive=green, negative=red)
    icon  : emoji shown in background
    color : card accent color (cyan/green/coral/violet/gold)
    fmt   : python format string for value
    lower_is_better : True  → a RISE is BAD  (red ▲) — e.g. AQI, Congestion %,
                               Vehicle Count, Wait Time, PM2.5, Energy, Outages
                      False → a RISE is GOOD (green ▲) — e.g. Speed, Renewable %,
                               City Score, Predicted values

    Colour logic:
        lower_is_better=True  → delta > 0: BAD (red ▲)   | delta < 0: GOOD (green ▼)
        lower_is_better=False → delta > 0: GOOD (green ▲) | delta < 0: BAD (red ▼)
    """
    try:
        v_str = fmt.format(value)
    except Exception:
        v_str = str(value)

    delta_html = '<div class="kpi-delta neutral">&nbsp;</div>'   # keeps card height uniform
    if delta is not None:
        rising = delta >= 0
        # determine if this direction is good or bad for the city
        is_good = (not lower_is_better and rising) or (lower_is_better and not rising)
        css_cls = "good" if is_good else "bad"
        arrow   = "▲"   if rising    else "▼"
        delta_html = (
            f'<div class="kpi-delta {css_cls}">'
            f'{arrow} {abs(delta):.1f}% vs prev'
            f'</div>'
        )

    return (
        f'<div class="kpi-card {color}">'
        f'<div class="kpi-icon">{icon}</div>'
        f'<div class="kpi-label">{label}</div>'
        f'<div class="kpi-value">{v_str}</div>'
        f'{delta_html}'
        f'</div>'
    )

# Prediction notice
def show_prediction_notice(has_pred, df_pred, filename):
    """
    Displays an info message if prediction data is not yet available.
    has_pred : bool — whether the predicted_* column exists
    df_pred  : DataFrame or None — filtered prediction rows
    filename : str — name of the expected CSV file
    """
    if not has_pred or df_pred is None or len(df_pred) == 0:
        st.info(f"Prediction charts will appear once spark_streaming.py writes output/{filename}")

# AQI color
def aqi_color(v):
    """
    Returns hex colour matching the AQI severity band.
    Used to colour-code bars, treemaps and alerts consistently.
    """
    if v <= 50:   return C_GREEN
    if v <= 100:  return C_GOLD
    if v <= 150:  return "#f97316"
    if v <= 200:  return C_CORAL
    return "#dc2626"

# AQI label
def aqi_label(v):
    """Returns human-readable AQI category."""
    if v <= 50:   return "Good"
    if v <= 100:  return "Moderate"
    if v <= 150:  return "Unhealthy (Sensitive)"
    if v <= 200:  return "Unhealthy"
    return "Hazardous"

# ── City Smart Score ──────────────────────────────────────────────
def compute_city_score(ft, fe, fp):
    """
    Composite 0-100 city health score derived from all 3 domains.

    TRAFFIC (30 %):
      - Penalises high average vehicle volume (normalised to 1000 veh/hr)
      - Penalises % of records with High congestion
      - Penalises % of records with any active incident

    ENERGY (25 %):
      - Rewards low average consumption (normalised to max 9000 kWh)
      - Rewards absence of power outages
      - Rewards renewable energy share (normalised to max 50 %)

    POLLUTION (35 %):
      - Penalises high average AQI (normalised to max 300)
      - Directly the single biggest driver of city liveability

    STABILITY (10 %):
      - Rewards low coefficient-of-variation across all 3 domains
      - A city with steady, predictable readings scores higher than
        one with extreme spikes even if the averages are similar

    All four sub-scores are clipped to [0, 100] before combining.
    The final score is also clipped to [0, 100].

    Score bands:
        80–100  Excellent  ✅ city operating well
        60–79   Good       🟡 minor issues present
        40–59   Fair       🟠 noticeable problems
         0–39   Poor       🔴 urgent intervention needed
    """
    # ---------- TRAFFIC ----------
    traffic_norm       = ft["vehicle_count"].mean() / 1000
    congestion_penalty = (ft["congestion_level"] == "High").mean() \
                         if "congestion_level" in ft.columns else 0
    incident_col       = "incident" if "incident" in ft.columns else None
    incident_penalty   = (ft[incident_col] != "No Incident").mean() \
                         if incident_col else 0

    traffic_score = max(0, min(100, 100 * (
        1 - (0.5 * traffic_norm +
             0.3 * congestion_penalty +
             0.2 * incident_penalty)
    )))

    # ---------- ENERGY ----------
    energy_norm    = fe["energy_consumption"].mean() / 9000
    outage_penalty = fe["power_outage"].mean() \
                     if "power_outage" in fe.columns else 0
    renewable_bonus = fe["renewable_usage"].mean() / 50 \
                      if "renewable_usage" in fe.columns else 0

    energy_score = max(0, min(100, 100 * (
        (1 - energy_norm)    * 0.6 +
        (1 - outage_penalty) * 0.3 +
        renewable_bonus      * 0.1
    )))

    # ---------- POLLUTION ----------
    aqi_norm        = fp["AQI"].mean() / 300
    pollution_score = max(0, min(100, 100 * (1 - aqi_norm)))

    # ---------- STABILITY ----------
    def safe_cv(s):
        """Coefficient of variation, capped at 1.0 to avoid outlier inflation."""
        mu = s.mean()
        return min(s.std() / mu, 1.0) if mu > 0 else 0.0

    traffic_var = safe_cv(ft["vehicle_count"])
    energy_var  = safe_cv(fe["energy_consumption"])
    aqi_var     = safe_cv(fp["AQI"])

    stability_score = max(0, min(100,
        100 * (1 - (traffic_var + energy_var + aqi_var) / 3)
    ))

    # ---------- WEIGHTED FINAL SCORE ----------
    city_score = (
        0.30 * traffic_score   +
        0.25 * energy_score    +
        0.35 * pollution_score +
        0.10 * stability_score
    )
    return max(0.0, min(100.0, city_score))

def city_score_grade(score):
    """Return (grade_label, alert_css_class) for the City Score."""
    if score >= 80: return "Excellent", "alert-success"
    if score >= 60: return "Good",      "alert-info"
    if score >= 40: return "Fair",      "alert-warning"
    return "Poor", "alert-danger"

# AQI description
def render_mode_banner():
    """
    WHAT THIS SHOWS:
    A banner at the top of every page indicating:
    - Which data mode is active
    - How many rows are loaded per dataset
    - When data was last updated (Real-Time mode only)
    - Whether auto-refresh is enabled
    """
    if is_realtime:
        last_update = "—"
        for f in RT_FILES:
            p = os.path.join(OUTPUT_DIR, f)
            if os.path.exists(p):
                last_update = datetime.fromtimestamp(os.path.getmtime(p)).strftime("%H:%M:%S")
                break
        rt_note = ""
        if not has_rt_data:
            rt_note = " · ⚠️ No streaming output yet — start spark_streaming.py + producer.py"
        ar_note = f" · auto-refresh every {refresh_interval}s" if auto_refresh else " · auto-refresh OFF"
        n_rt_t = len(rt_raw["traffic"]) if rt_raw.get("traffic") is not None else 0
        n_rt_e = len(rt_raw["energy"]) if rt_raw.get("energy") is not None else 0
        n_rt_p = len(rt_raw["pollution"]) if rt_raw.get("pollution") is not None else 0
        st.markdown(f"""
        <div class="alert alert-success">
            🔴 <strong>Real-Time Mode</strong> — Historical + Streaming data ·
            Traffic: {len(ft):,} rows ({n_rt_t} live) ·
            Energy: {len(fe):,} rows ({n_rt_e} live) ·
            Pollution: {len(fp):,} rows ({n_rt_p} live) ·
            Last file update: <strong>{last_update}</strong>{ar_note}{rt_note}
        </div>""", unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="alert alert-info">
            📊 <strong>Static EDA Mode</strong> — Stage-1 historical data only ·
            Traffic: {len(ft):,} · Energy: {len(fe):,} · Pollution: {len(fp):,} rows ·
            Prediction charts hidden (switch to Real-Time to see predictions)
        </div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════
#  ANOMALY DETECTION ENGINE
#  Pure statistical approach — no extra ML dependencies.
#  Uses three complementary methods per stream:
#
#  1. Z-Score     : flags records > z_thresh standard deviations from mean
#                   Best for: symmetric, near-normal distributions
#  2. IQR Fence   : flags records outside [Q1-k*IQR, Q3+k*IQR]
#                   Best for: skewed distributions, robust to outliers
#  3. Rolling σ   : flags records > rolling_thresh σ from local rolling mean
#                   Best for: detecting sudden spikes in time-ordered data
#
#  A record is flagged as anomalous when ANY method raises the flag.
#  Severity is assigned based on how extreme the deviation is:
#      HIGH   — z-score > 4.0  (extremely rare under normal distribution)
#      MEDIUM — z-score > 3.0
#      LOW    — flagged by IQR or rolling σ only
# ══════════════════════════════════════════════════════════════════
def detect_anomalies(
    df: pd.DataFrame,
    col: str,
    z_thresh: float = 3.0,
    iqr_k: float = 2.0,
    rolling_window: int = 24,
    rolling_thresh: float = 2.5,
) -> pd.DataFrame:
    """
    Flag anomalies in `col` using Z-score, IQR, and rolling-σ methods.

    Returns the input df with three new columns:
      anomaly_zscore   : bool — flagged by Z-score
      anomaly_iqr      : bool — flagged by IQR fence
      anomaly_rolling  : bool — flagged by rolling standard deviation
      is_anomaly       : bool — flagged by ANY of the three methods
      anomaly_severity : str  — "HIGH" / "MEDIUM" / "LOW" / ""
      anomaly_zscore_val: float — raw z-score (used for severity banding)
    """
    if col not in df.columns or len(df) < 5:
        for c in ["anomaly_zscore","anomaly_iqr","anomaly_rolling","is_anomaly",
                  "anomaly_severity","anomaly_zscore_val"]:
            df[c] = False if "severity" not in c else ""
        return df

    s = df[col].copy()
    mu, sigma = s.mean(), s.std()

    # ── Z-Score ──────────────────────────────────────────────────
    z = np.abs((s - mu) / sigma) if sigma > 0 else pd.Series(0.0, index=s.index)
    df["anomaly_zscore_val"] = z
    df["anomaly_zscore"]     = z > z_thresh

    # ── IQR Fence ────────────────────────────────────────────────
    Q1, Q3 = s.quantile(0.25), s.quantile(0.75)
    IQR     = Q3 - Q1
    lower   = Q1 - iqr_k * IQR
    upper   = Q3 + iqr_k * IQR
    df["anomaly_iqr"] = (s < lower) | (s > upper)

    # ── Rolling σ ────────────────────────────────────────────────
    roll_mean = s.rolling(rolling_window, min_periods=3, center=True).mean()
    roll_std  = s.rolling(rolling_window, min_periods=3, center=True).std()
    roll_std  = roll_std.replace(0, np.nan).fillna(sigma)
    df["anomaly_rolling"] = np.abs(s - roll_mean) > rolling_thresh * roll_std

    # ── Combined flag ────────────────────────────────────────────
    df["is_anomaly"] = (
        df["anomaly_zscore"] | df["anomaly_iqr"] | df["anomaly_rolling"]
    )

    # ── Severity ─────────────────────────────────────────────────
    def _severity(row):
        if not row["is_anomaly"]:
            return ""
        if row["anomaly_zscore_val"] > 4.0:
            return "HIGH"
        if row["anomaly_zscore_val"] > 3.0:
            return "MEDIUM"
        return "LOW"

    df["anomaly_severity"] = df.apply(_severity, axis=1)
    return df

def get_anomaly_summary(df: pd.DataFrame, metric_col: str, label: str) -> dict:
    """Compute top-level anomaly statistics for one metric."""
    total   = len(df)
    n_anom  = df["is_anomaly"].sum()
    pct     = n_anom / total * 100 if total > 0 else 0
    high    = (df["anomaly_severity"] == "HIGH").sum()
    medium  = (df["anomaly_severity"] == "MEDIUM").sum()
    low     = (df["anomaly_severity"] == "LOW").sum()
    worst   = df.loc[df["is_anomaly"], metric_col].max() if n_anom > 0 else None
    worst_area = None
    if n_anom > 0 and "area" in df.columns:
        worst_area = (
            df[df["is_anomaly"]].groupby("area")["is_anomaly"].sum()
            .idxmax()
        )
    return dict(label=label, total=total, n_anom=int(n_anom), pct=round(pct,1),
                high=int(high), medium=int(medium), low=int(low),
                worst=worst, worst_area=worst_area)

# ══════════════════════════════════════════════════════════════════
#  PAGE 1: CITY OVERVIEW
#
#  WHAT THIS PAGE SHOWS:
#   ▸ KPIs     — one headline number per domain for quick city health read
#   ▸ Alerts   — automatic threshold-based warnings (AQI, congestion, outages)
#   ▸ Corr.    — cross-domain scatter: traffic→AQI, energy→AQI, traffic→energy
#   ▸ Risk     — composite risk score per area (traffic 30% + energy 30% + AQI 40%)
#   ▸ Area KPIs— top-8 areas ranked by vehicle count, energy, and AQI
# ══════════════════════════════════════════════════════════════════
# ══════════════════════════════════════════════════════════════════
#  DELTA HELPER — computes % change for KPI cards from real data
# ══════════════════════════════════════════════════════════════════
def compute_delta(df: pd.DataFrame, col: str, n_recent: int = 200):
    """
    Compare mean of the most recent `n_recent` rows vs the earlier rows
    for a given column.  Returns a % change float, or None when there is
    not enough data for a meaningful split.
    """
    if df is None or col not in df.columns or len(df) < n_recent * 2:
        return None
    # Sort by timestamp if available so recent/prior split is time-correct
    if "timestamp" in df.columns:
        df = df.sort_values("timestamp")
    recent = df.iloc[-n_recent:][col].mean()
    prior  = df.iloc[:-n_recent][col].mean()
    if prior == 0 or pd.isna(prior) or pd.isna(recent):
        return None
    return round((recent - prior) / abs(prior) * 100, 1)

# ══════════════════════════════════════════════════════════════════
#  CITY SMART SCORE  — computed once, used on Overview page KPI row
#  Must be after ft / fe / fp are filtered so it reflects the same
#  data the user is currently viewing.
# ══════════════════════════════════════════════════════════════════
city_score = compute_city_score(ft, fe, fp)

# Pre-compute deltas from real data (used across multiple pages)
delta_vc   = compute_delta(ft, "vehicle_count")
delta_spd  = compute_delta(ft, "avg_speed")
delta_wait = compute_delta(ft, "signal_wait_time")
delta_ec   = compute_delta(fe, "energy_consumption")
delta_ren  = compute_delta(fe, "renewable_usage")
delta_tmp  = compute_delta(fe, "temperature")
delta_hum  = compute_delta(fe, "humidity")
delta_aqi  = compute_delta(fp, "AQI")
delta_pm25 = compute_delta(fp, "PM2_5" if fp is not None and "PM2_5" in fp.columns else "PM2.5")
delta_pm10 = compute_delta(fp, "PM10")
delta_no2  = compute_delta(fp, "NO2")
delta_co   = compute_delta(fp, "CO")

if page == "🏙️  City Overview":
    # browser tab title reflects current page (set_page_config already called globally)
    st.markdown("<script>document.title='City Overview · SmartCity Analytics'</script>",
                unsafe_allow_html=True)
    st.markdown("""
    <div class="page-header">
        <div class="page-icon">🏙️</div>
        <div>
            <div class="page-title">City Overview</div>
            <div class="page-sub">Cross-domain intelligence · City health · Area risk scoring</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    render_mode_banner()

    # ── City-wide KPIs ────────────────────────────────────────────
    # PURPOSE: One number per domain for an immediate pulse check.
    # In Real-Time mode these values update with each new batch.
    # ----------------------------------------------------------------
    st.markdown('<div class="section-title">City-Wide KPIs</div>', unsafe_allow_html=True)
    k1,k2,k3,k4,k5,k6,k7 = st.columns(7)
    high_cong = (ft["congestion_level"]=="High").mean()*100 if "congestion_level" in ft.columns else 0
    with k1: st.markdown(kpi("City Score",city_score,None,"🏙️","violet","{:.1f}",lower_is_better=False),unsafe_allow_html=True)
    with k2: st.markdown(kpi("Avg Vehicles/hr",ft["vehicle_count"].mean(),delta_vc,"🚗","cyan","{:.0f}",lower_is_better=True),unsafe_allow_html=True)
    with k3: st.markdown(kpi("Avg Speed km/h",ft["avg_speed"].mean(),delta_spd,"🏎️","cyan","{:.1f}",lower_is_better=False),unsafe_allow_html=True)
    with k4: st.markdown(kpi("Avg Energy kWh",fe["energy_consumption"].mean(),delta_ec, "⚡", "green","{:.0f}",  lower_is_better=True),  unsafe_allow_html=True)
    with k5: st.markdown(kpi("Renewable %",fe["renewable_usage"].mean(),delta_ren,  "🌿", "green",  "{:.1f}%", lower_is_better=False), unsafe_allow_html=True)
    with k6: st.markdown(kpi("Avg AQI",fp["AQI"].mean(),delta_aqi,  "🌫️", "coral",  "{:.0f}",  lower_is_better=True),  unsafe_allow_html=True)
    with k7: st.markdown(kpi("High Congestion %",high_cong,None, "🔴", "coral",  "{:.1f}%", lower_is_better=True),  unsafe_allow_html=True)

    # ── Live Alerts ───────────────────────────────────────────────
    # PURPOSE: Automatically triggered warnings based on city thresholds.
    # In Real-Time mode these reflect the latest streaming data,
    # alerting operators to issues without manual monitoring.
    # -------------------------------------------------------------------
    st.markdown('<div class="section-title">Live City Alerts</div>', unsafe_allow_html=True)
    # City Score grade banner — shown directly below the KPI row
    _grade, _grade_cls = city_score_grade(city_score)
    _grade_icons = {"Excellent": "✅", "Good": "🟡", "Fair": "🟠", "Poor": "🔴"}
    st.markdown(
        f'<div class="alert {_grade_cls}" style="margin-top:0.6rem;">'
        f'{_grade_icons.get(_grade,"🏙️")} <strong>City Smart Score: {city_score:.1f} / 100</strong>'
        f' — Overall city health is <strong>{_grade}</strong> · '
        f'Traffic {0.30*100:.0f}% · Energy {0.25*100:.0f}% · '
        f'Air Quality {0.35*100:.0f}% · Stability {0.10*100:.0f}%'
        f'</div>',
        unsafe_allow_html=True,
    )
    avg_aqi = fp["AQI"].mean()
    outage_pct = (fe["power_outage"]==1).mean()*100 if "power_outage" in fe.columns else 0
    n_alerts = 0
 
    if avg_aqi > 200:
        st.markdown(f'<div class="alert alert-danger">🚨 Hazardous AQI: {avg_aqi:.0f} — Restrict all outdoor activity immediately</div>', unsafe_allow_html=True)
        n_alerts += 1
    elif avg_aqi > 150:
        st.markdown(f'<div class="alert alert-warning">⚠️ Unhealthy AQI: {avg_aqi:.0f} — Sensitive groups should limit outdoor exposure</div>', unsafe_allow_html=True)
        n_alerts += 1
    elif avg_aqi > 100:
        st.markdown(f'<div class="alert alert-warning">⚠️ Moderate AQI: {avg_aqi:.0f} — Unusually sensitive individuals may react</div>', unsafe_allow_html=True)
        n_alerts += 1
 
    if high_cong > 40:
        st.markdown(f'<div class="alert alert-danger">🚗 Severe congestion: {high_cong:.0f}% of monitored roads at High level</div>', unsafe_allow_html=True)
        n_alerts += 1
    elif high_cong > 25:
        st.markdown(f'<div class="alert alert-warning">🚗 Elevated congestion: {high_cong:.0f}% of roads — consider alternate routing advisories</div>', unsafe_allow_html=True)
        n_alerts += 1
 
    if outage_pct > 5:
        st.markdown(f'<div class="alert alert-danger">⚡ Power outages in {outage_pct:.0f}% of records — grid stress detected</div>', unsafe_allow_html=True)
        n_alerts += 1
 
    if n_alerts == 0:
        st.markdown('<div class="alert alert-success">✅ All city systems operating within normal parameters</div>', unsafe_allow_html=True)

    # ── Cross-domain Correlation ───────────────────────────────────
    # PURPOSE: Shows how traffic, energy, and pollution relate at area level.
    # High-traffic areas tend to have higher AQI (vehicle emissions).
    # Industrial areas with high energy also correlate with AQI.
    st.markdown('<div class="section-title">Domain Correlation Intelligence</div>', unsafe_allow_html=True)
    c1,c2,c3 = st.columns(3)
    with c1:
        m = ft.groupby("area")["vehicle_count"].mean().reset_index().merge(
            fp.groupby("area")["AQI"].mean().reset_index(), on="area")
        if len(m)>=3:
            fig = px.scatter(m, x="vehicle_count", y="AQI", text="area",color_discrete_sequence=[C_VIOLET])
            fig.update_traces(textposition="top center", textfont_size=9,
                hovertemplate="<b>Area: %{text}</b><br>Avg Vehicle Count: %{x:.0f}<br>Avg AQI: %{y:.0f}<extra></extra>")
            fig = apply_theme(fig,"Traffic Volume → AQI Relationship",300)
            st.plotly_chart(fig,use_container_width=True)
 
    with c2:
        m = fe.groupby("area")["energy_consumption"].mean().reset_index().merge(
            fp.groupby("area")["AQI"].mean().reset_index(), on="area")
        if len(m)>=3:
            fig = px.scatter(m, x="energy_consumption", y="AQI", text="area",color_discrete_sequence=[C_GOLD])
            fig.update_traces(textposition="top center", textfont_size=9,
                hovertemplate="<b>Area: %{text}</b><br>Avg Energy: %{x:.0f} kWh<br>Avg AQI: %{y:.0f}<extra></extra>")
            fig = apply_theme(fig,"Energy Consumption → AQI Relationship",300)
            st.plotly_chart(fig,use_container_width=True)
 
    with c3:
        m = ft.groupby("area")["vehicle_count"].mean().reset_index().merge(
            fe.groupby("area")["energy_consumption"].mean().reset_index(), on="area")
        if len(m)>=3:
            fig = px.scatter(m, x="vehicle_count", y="energy_consumption", text="area",color_discrete_sequence=[C_CYAN])
            fig.update_traces(textposition="top center", textfont_size=9,
                hovertemplate="<b>Area: %{text}</b><br>Avg Vehicle Count: %{x:.0f}<br>Avg Energy: %{y:.0f} kWh<extra></extra>")
            fig = apply_theme(fig,"Traffic Volume → Energy Demand",300)
            st.plotly_chart(fig,use_container_width=True)

    # ── Area Risk Matrix ───────────────────────────────────────────
    # PURPOSE: Composite risk score per area.
    # Formula: (traffic/1000)*0.3 + (energy/9000)*0.3 + (AQI/300)*0.4 × 100
    # Helps city planners prioritise which areas need immediate attention.
    st.markdown('<div class="section-title">Area Risk Matrix</div>', unsafe_allow_html=True)
    risk_areas = sel_areas if sel_areas else ALL_AREAS
    rows = []
    for area in risk_areas:
        rt = ft[ft["area"]==area]["vehicle_count"].mean()     if len(ft[ft["area"]==area])>0 else 0
        re = fe[fe["area"]==area]["energy_consumption"].mean() if len(fe[fe["area"]==area])>0 else 0
        rp = fp[fp["area"]==area]["AQI"].mean()               if len(fp[fp["area"]==area])>0 else 0
        score = (rt/1000*0.3 + re/9000*0.3 + rp/300*0.4)*100
        rows.append({"Area":area,"Vehicles":f"{rt:.0f}","Energy kWh":f"{re:.0f}",
                     "AQI":f"{rp:.0f}","Risk Score":score})
    if rows:
        rdf = pd.DataFrame(rows).sort_values("Risk Score",ascending=False)
        st.dataframe(rdf, use_container_width=True, hide_index=True,
            column_config={"Risk Score": st.column_config.ProgressColumn(
                "Risk Score", min_value=0, max_value=100, format="%.0f")})
        
    # ── Area-Level KPI Bars ────────────────────────────────────────
    # PURPOSE: Top-8 areas ranked independently by each domain metric.
    # Helps identify which areas are traffic hotspots, energy heavy users,
    # and most polluted — they're not always the same areas.
    st.markdown('<div class="section-title">Area-Level KPIs</div>', unsafe_allow_html=True)
    c1,c2,c3 = st.columns(3)
    with c1:
        d = ft.groupby("area")["vehicle_count"].mean().sort_values(ascending=False).head(8).reset_index()
        fig = px.bar(d, x="vehicle_count", y="area", orientation="h",color="vehicle_count",
                     color_continuous_scale=["#0a3d5e","#00d4ff"],hover_data={"vehicle_count": ":.0f", "area": True})
        fig.update_traces(hovertemplate="<b>Area: %{y}</b><br>Avg Vehicle Count: %{x:.0f}<extra></extra>")
        fig = apply_theme(fig,"Avg Vehicle Count by Area")
        fig.update_layout(height=320,coloraxis_showscale=False,yaxis=dict(categoryorder="total ascending"))
        st.plotly_chart(fig,use_container_width=True)

    with c2:
        d = fe.groupby("area")["energy_consumption"].mean().sort_values(ascending=False).head(8).reset_index()
        fig = px.bar(d, x="energy_consumption", y="area", orientation="h",color="energy_consumption",color_continuous_scale=["#0a3d2a","#00ff99"])
        fig.update_traces(hovertemplate="<b>Area: %{y}</b><br>Avg Energy: %{x:.0f} kWh<extra></extra>")
        fig = apply_theme(fig,"Avg Energy Consumption by Area")
        fig.update_layout(height=320,coloraxis_showscale=False,yaxis=dict(categoryorder="total ascending"))
        st.plotly_chart(fig,use_container_width=True)

    with c3:
        d = fp.groupby("area")["AQI"].mean().sort_values(ascending=False).head(8).reset_index()
        fig = px.bar(d, x="AQI", y="area", orientation="h",color="AQI",color_continuous_scale=["#3b0a0a", "#ff6b6b"])
        fig.update_traces(hovertemplate="<b>Area: %{y}</b><br>Avg AQI: %{x:.0f}<extra></extra>")
        fig = apply_theme(fig, "Avg AQI by Area")
        fig.update_layout(height=320,coloraxis_showscale=False,yaxis=dict(categoryorder="total ascending"))
        st.plotly_chart(fig, use_container_width=True)

    # Download current view (City Overview)
    st.markdown('<div class="section-title">Export Current View</div>', unsafe_allow_html=True)
    dl_c1, dl_c2, dl_c3 = st.columns(3)
    with dl_c1:
        if ft is not None:
            st.download_button("⬇️ Traffic Data (CSV)", ft.to_csv(index=False).encode(),
                file_name=f"traffic_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv", mime="text/csv")
    with dl_c2:
        if fe is not None:
            st.download_button("⬇️ Energy Data (CSV)", fe.to_csv(index=False).encode(),
                file_name=f"energy_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv", mime="text/csv")
    with dl_c3:
        if fp is not None:
            st.download_button("⬇️ Pollution Data (CSV)", fp.to_csv(index=False).encode(),
                file_name=f"pollution_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv", mime="text/csv")

# ══════════════════════════════════════════════════════════════════
#  PAGE 2: TRAFFIC
#
#  WHAT THIS PAGE SHOWS:
#   ▸ KPIs         — vehicles/hr, speed, wait time, congestion%, incidents
#   ▸ Hour×DoW     — heatmap showing rush-hour and weekend patterns
#   ▸ Congestion   — donut chart of Low/Medium/High split
#   ▸ Speed deep   — speed by hour+road type, zone boxplot, weather impact
#   ▸ Prediction   — actual vs predicted scatter + residual histogram
#   ▸ Area/Incident— top areas by volume+speed, incident type frequency
# ══════════════════════════════════════════════════════════════════
elif page == "🚦  Traffic":
    # dynamic browser tab title
    st.markdown("<script>document.title='Traffic · SmartCity Analytics'</script>",
                unsafe_allow_html=True)
    st.markdown("""
    <div class="page-header">
        <div class="page-icon">🚦</div>
        <div>
            <div class="page-title">Traffic Intelligence</div>
            <div class="page-sub">Vehicle flow · Congestion · Speed patterns · ML demand forecasting</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    render_mode_banner()

    # ── KPIs ──────────────────────────────────────────────────────
    # PURPOSE: instant read on traffic health.
    # In Real-Time mode, these numbers change with every new Kafka batch.
    k1,k2,k3,k4,k5,k6 = st.columns(6)
    avg_vc   = ft["vehicle_count"].mean()
    avg_spd  = ft["avg_speed"].mean()
    avg_wait = ft["signal_wait_time"].mean()
    h_pct    = (ft["congestion_level"]=="High").mean()*100 if "congestion_level" in ft.columns else 0
    pred_vc  = ft_pred["predicted_vehicle_count"].mean() if ft_pred is not None and len(ft_pred)>0 else None
    incidents= (ft["incident"]!="No Incident").sum() if "incident" in ft.columns else 0
 
    with k1: st.markdown(kpi("Avg Vehicles/hr",   avg_vc,    delta_vc,   "🚗", "cyan",   "{:.0f}",  lower_is_better=True),  unsafe_allow_html=True)
    with k2: st.markdown(kpi("Avg Speed km/h",    avg_spd,   delta_spd,  "🏎️", "cyan",   "{:.1f}",  lower_is_better=False), unsafe_allow_html=True)
    with k3: st.markdown(kpi("Avg Wait Time (s)", avg_wait,  delta_wait, "⏱️", "gold",   "{:.0f}",  lower_is_better=True),  unsafe_allow_html=True)
    with k4: st.markdown(kpi("High Congestion %", h_pct,     None,       "🔴", "coral",  "{:.1f}%", lower_is_better=True),  unsafe_allow_html=True)
    with k5: st.markdown(kpi("ML Predicted Vol.", pred_vc if pred_vc is not None else 0, None, "🤖", "violet", "{:.0f}" if pred_vc is not None else "N/A", lower_is_better=False), unsafe_allow_html=True)
    with k6: st.markdown(kpi("Active Incidents",  incidents, None,       "⚠️", "gold",   "{:.0f}",  lower_is_better=True),  unsafe_allow_html=True)


    # ── Temporal Patterns ─────────────────────────────────────────
    # PURPOSE:
    #   Heatmap → reveals double rush-hour peaks (8-10am, 5-8pm)
    #             and the weekend traffic drop visible in Sat/Sun rows.
    #   Donut   → how much time the city spends in each congestion band.
    st.markdown('<div class="section-title">Temporal Patterns</div>', unsafe_allow_html=True)
    c1,c2 = st.columns([3,2])
    with c1:
        if "dayofweek" in ft.columns and "hour" in ft.columns:
            pivot = ft.pivot_table(index="dayofweek", columns="hour",
                values="vehicle_count", aggfunc="mean")
            days = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
            pivot.index = [days[int(i)] if int(i) < len(days) else str(int(i)) for i in pivot.index]
            fig = px.imshow(pivot,
                color_continuous_scale=[[0,"#07090f"],[0.3,"#003d5e"],[1,"#00d4ff"]],
                aspect="auto")
            fig.update_traces(hovertemplate="<b>Hour: %{x}:00</b><br>Day: %{y}<br>Avg Vehicles: %{z:.0f}<extra></extra>")
            fig = apply_theme(fig, "Vehicle Count Heatmap — Hour × Day of Week", 320)
            fig.update_layout(xaxis_title="Hour of Day", yaxis_title="Day of Week",
                              coloraxis_colorbar=dict(title="Vehicles"))
            st.plotly_chart(fig, use_container_width=True)

    with c2:
        cd = ft["congestion_level"].value_counts().reset_index()
        cd.columns = ["level","count"]
        fig = px.pie(cd, names="level", values="count", hole=0.65,
            color="level",
            color_discrete_map={"Low": C_GREEN, "Medium": C_GOLD, "High": C_CORAL})
        fig.update_traces(textinfo="label+percent", textfont_size=11,
            hovertemplate="<b>Congestion Level: %{label}</b><br>Count: %{value:,}<br>Share: %{percent}<extra></extra>")
        fig.add_annotation(text=f"{h_pct:.0f}%<br><span style='font-size:10px'>High</span>",
            x=0.5, y=0.5, font_size=20, showarrow=False, font_color="#e2e8f0")
        fig = apply_theme(fig, "Congestion Level Distribution", 320)
        st.plotly_chart(fig, use_container_width=True)

    # ── Speed & Volume Deep Dive ───────────────────────────────────
    # PURPOSE:
    #   Line chart → speed varies by road type; highways maintain speed better
    #   Box chart  → zone-level vehicle count spread (Central is highest)
    #   Scatter    → weather conditions cluster — rain reduces both speed and volume
    st.markdown('<div class="section-title">Speed & Volume Deep Dive</div>', unsafe_allow_html=True)
    c1,c2,c3 = st.columns(3)
    with c1:
        if "road_type" in ft.columns and "hour" in ft.columns:
            d = ft.groupby(["hour","road_type"])["avg_speed"].mean().reset_index()
            fig = px.line(d, x="hour", y="avg_speed", color="road_type",
                color_discrete_sequence=[C_CYAN, C_GREEN, C_GOLD],
                labels={"hour":"Hour of Day","avg_speed":"Avg Speed (km/h)","road_type":"Road Type"})
            fig.update_traces(hovertemplate="<b>Road Type: %{fullData.name}</b><br>Hour: %{x}:00<br>Avg Speed: %{y:.1f} km/h<extra></extra>")
            fig = apply_theme(fig,"Avg Speed by Hour & Road Type")
            st.plotly_chart(fig,use_container_width=True)

    with c2:
        fig = px.box(ft, x="zone", y="vehicle_count",
            color="zone", color_discrete_sequence=PALETTE,
            labels={"zone":"Zone","vehicle_count":"Vehicle Count"},
            points=False)
        fig.update_traces(boxmean=True,
            hovertemplate="<b>Zone: %{x}</b><br>Vehicle Count: %{y:.0f}<extra></extra>")
        fig = apply_theme(fig, "Vehicle Count Distribution by Zone")
        fig.update_layout(xaxis_title="Zone", yaxis_title="Vehicle Count",
                          showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    with c3:
        if "weather" in ft.columns:
            d = ft.groupby("weather").agg(vehicle_count=("vehicle_count","mean"),
                avg_speed=("avg_speed","mean")).reset_index()
            fig = px.scatter(d,x="avg_speed",y="vehicle_count",text="weather",
                size=[30]*len(d),color="weather",color_discrete_sequence=PALETTE)
            fig.update_traces(textposition="top center", textfont_size=9,
                hovertemplate="<b>Weather: %{text}</b><br>Avg Speed: %{x:.1f} km/h<br>Avg Vehicles: %{y:.0f}<extra></extra>")
            fig = apply_theme(fig,"Weather → Speed & Volume Impact")
            st.plotly_chart(fig,use_container_width=True)
    
    # ── ML Prediction Performance (Real-Time only) ─────────────────────────────────
    # Only shown when predicted_vehicle_count column exists (streaming rows).
    # PURPOSE:
    #   Scatter → points on the diagonal = perfect prediction.
    #             Spread = model uncertainty. Color can show bias patterns.
    #   Residuals → should be centered at 0, bell-shaped.
    #              Skewed residuals suggest the model systematically over/under-predicts.
    if is_realtime and ft_pred is not None and len(ft_pred) >= 1:
        st.markdown('<div class="section-title">Decision Tree Prediction Performance</div>', unsafe_allow_html=True)
        c1,c2 = st.columns(2)
        with c1:
            samp = ft_pred.sample(min(600, len(ft_pred)), random_state=1)
            mn, mx = samp["vehicle_count"].min(), samp["vehicle_count"].max()
            samp = samp.copy()
            samp["abs_error_t"] = (samp["vehicle_count"] - samp["predicted_vehicle_count"]).abs()
            fig = px.scatter(samp, x="vehicle_count", y="predicted_vehicle_count",
                opacity=0.5, color_discrete_sequence=[C_CYAN],
                custom_data=["abs_error_t"],
                labels={"vehicle_count":"Actual Vehicle Count","predicted_vehicle_count":"Predicted Vehicle Count"})
            fig.update_traces(hovertemplate="Actual: <b>%{x:.0f}</b><br>Predicted: <b>%{y:.0f}</b><br>Abs Error: <b>%{customdata[0]:.0f}</b><extra></extra>")
            fig.add_shape(type="line", x0=mn, y0=mn, x1=mx, y1=mx,
                line=dict(color=C_CORAL, dash="dash", width=2))
            fig.add_annotation(x=mx, y=mx, text="Perfect fit",
                showarrow=False, font=dict(color=C_CORAL, size=10), xanchor="right")
            fig = apply_theme(fig, "Actual vs Predicted — Vehicle Count")
            fig.update_layout(xaxis_title="Actual Vehicle Count",
                              yaxis_title="Predicted Vehicle Count")
            st.plotly_chart(fig, use_container_width=True)

        with c2:
            res = ft_pred["vehicle_count"] - ft_pred["predicted_vehicle_count"]
            res_df = res.rename("Residual").to_frame()
            fig = px.histogram(res_df, x="Residual", nbins=60,
                color_discrete_sequence=[C_CYAN],
                labels={"Residual": "Residual (Actual − Predicted)", "count": "Frequency"})
            fig.update_traces(opacity=0.8,
                hovertemplate="Residual Range: %{x}<br>Frequency: %{y}<extra></extra>")
            fig.add_vline(x=0, line_dash="dash", line_color=C_CORAL, line_width=2)
            fig.add_vline(x=res.mean(), line_dash="dot", line_color=C_GOLD, line_width=1.5,
                annotation_text=f"Mean: {res.mean():.1f}", annotation_position="top right")
            fig = apply_theme(fig, "Residual Distribution (Actual − Predicted)")
            fig.update_layout(xaxis_title="Residual (Actual − Predicted)",
                              yaxis_title="Frequency")
            st.plotly_chart(fig, use_container_width=True)

    elif is_realtime:
        show_prediction_notice(has_pred_t, ft_pred, "traffic_predictions.csv")
 
    # ── Area & Incident Analysis ───────────────────────────────────
    # PURPOSE:
    #   Dual-axis → busiest areas by volume with their avg speed overlaid.
    #               If a busy area also has low speed → congestion hotspot.
    #   Incident bar → which incident types occur most. Accidents spike AQI.
    st.markdown('<div class="section-title">Area & Incident Analysis</div>', unsafe_allow_html=True)
    c1,c2 = st.columns(2)
    with c1:
        d = ft.groupby("area").agg(vehicle_count=("vehicle_count","mean"),
            avg_speed=("avg_speed","mean")).reset_index()             .sort_values("vehicle_count", ascending=False).head(10)
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(go.Bar(x=d["area"], y=d["vehicle_count"], name="Vehicle Count",
            marker_color=C_CYAN, opacity=0.8, hovertemplate="<b>%{x}</b><br>Avg Vehicle Count: %{y:.0f}<extra></extra>"), secondary_y=False)
        fig.add_trace(go.Scatter(x=d["area"], y=d["avg_speed"], name="Avg Speed (km/h)",
            mode="lines+markers", line=dict(color=C_CORAL, width=2),
            marker=dict(size=8), hovertemplate="<b>Area: %{x}</b><br>Avg Speed: %{y:.1f} km/h<extra></extra>"), secondary_y=True)
        fig.update_layout(**CHART_THEME, height=380,
            title=dict(text="Top Areas — Volume & Speed",
                       font=dict(family="Syne", size=13, color="#e2e8f0"), x=0),
                       legend=dict(bgcolor="rgba(0,0,0,0)"))
        fig.update_yaxes(title_text="Avg Vehicle Count", secondary_y=False,
                         gridcolor=GRIDCOLOR, title_font=dict(color=C_CYAN))
        fig.update_yaxes(title_text="Avg Speed (km/h)", secondary_y=True,
                         gridcolor=GRIDCOLOR, title_font=dict(color=C_CORAL))
        fig.update_xaxes(title_text="Area", gridcolor=GRIDCOLOR, zeroline=False)
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        if "incident" in ft.columns:
            d = ft[ft["incident"]!="No Incident"]["incident"].value_counts().head(8).reset_index()
            d.columns = ["incident","count"]
            fig = px.bar(d, x="count", y="incident", orientation="h",
                color="count", color_continuous_scale=["#3b1414","#ef4444"],
                labels={"count":"Number of Incidents","incident":"Incident Type"})
            fig.update_traces(hovertemplate="<b>Incident: %{y}</b><br>Incidents: %{x:,}<extra></extra>")
            fig = apply_theme(fig, "Incident Type Frequency")
            fig.update_layout(coloraxis_showscale=False,height=380,
                yaxis=dict(categoryorder="total ascending"))
            st.plotly_chart(fig,use_container_width=True)

    # Model metadata card
    if is_realtime:
        st.markdown('<div class="section-title">Model Metadata</div>', unsafe_allow_html=True)
        render_model_metrics("traffic", C_CYAN)
    
    # Download current filtered traffic view
    st.markdown('<div class="section-title">Export Current View</div>', unsafe_allow_html=True)
    st.download_button("⬇️ Download Traffic Data (CSV)",
        ft.to_csv(index=False).encode(),
        file_name=f"traffic_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv", use_container_width=True)

# ══════════════════════════════════════════════════════════════════
#  PAGE 3: ENERGY
#
#  WHAT THIS PAGE SHOWS:
#   ▸ KPIs         — consumption, renewable%, temperature, humidity, outages
#   ▸ Hour×Type    — heatmap showing when each load type peaks
#   ▸ Demand       — donut chart of Low/Medium/High demand split
#   ▸ Environment  — temperature and humidity vs energy scatters
#   ▸ Renewable    — usage by area with city average reference line
#   ▸ Weekday/Season — hourly weekday vs weekend + season×zone heatmap
#   ▸ Prediction   — actual vs predicted + APE distribution
#   ▸ Outages      — outage rate by area and zone impact
# ══════════════════════════════════════════════════════════════════
elif page == "⚡  Energy":
    # dynamic browser tab title
    st.markdown("<script>document.title='Energy · SmartCity Analytics'</script>",
                unsafe_allow_html=True)
    st.markdown("""
    <div class="page-header">
        <div class="page-icon">⚡</div>
        <div>
            <div class="page-title">Energy Intelligence</div>
            <div class="page-sub">Consumption monitoring · Renewable tracking · Demand forecasting</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    render_mode_banner()

    k1,k2,k3,k4,k5,k6 = st.columns(6)
    avg_ec     = fe["energy_consumption"].mean()
    avg_ren    = fe["renewable_usage"].mean()
    avg_tmp    = fe["temperature"].mean()
    avg_hum    = fe["humidity"].mean()
    out_pct    = (fe["power_outage"]==1).mean()*100 if "power_outage" in fe.columns else 0
    pred_ec    = fe_pred["predicted_energy_consumption"].mean() if fe_pred is not None and len(fe_pred) > 0 else None

    with k1: st.markdown(kpi("Avg Consumption",   avg_ec,  delta_ec,  "⚡", "green",  "{:.0f}",  lower_is_better=True),  unsafe_allow_html=True)
    with k2: st.markdown(kpi("Renewable %",        avg_ren, delta_ren, "🌿", "green",  "{:.1f}%", lower_is_better=False), unsafe_allow_html=True)
    with k3: st.markdown(kpi("Avg Temperature °C", avg_tmp, delta_tmp, "🌡️", "gold",   "{:.1f}",  lower_is_better=True),  unsafe_allow_html=True)
    with k4: st.markdown(kpi("Avg Humidity %",     avg_hum, delta_hum, "💧", "cyan",   "{:.1f}",  lower_is_better=True),  unsafe_allow_html=True)
    with k5: st.markdown(kpi("Power Outage %",     out_pct, None,      "⚠️", "coral",  "{:.1f}%", lower_is_better=True),  unsafe_allow_html=True)
    with k6: st.markdown(kpi("ML Predicted kWh",   pred_ec if pred_ec else 0, None, "🤖", "violet", "{:.0f}", lower_is_better=False), unsafe_allow_html=True)
    # ── Consumption Patterns ───────────────────────────────────────
    # PURPOSE:
    #   Heatmap → identifies when each sector peaks.
    #             Industrial peaks at night, Commercial peaks midday,
    #             Residential peaks evenings — critical for grid balancing.
    #   Donut   → how often demand is High/Medium/Low.
    st.markdown('<div class="section-title">Consumption Patterns</div>', unsafe_allow_html=True)
    c1,c2 = st.columns([2,1])
    with c1:
        if "hour" in fe.columns and "load_type" in fe.columns:
            pivot = fe.pivot_table(index="load_type", columns="hour",
                values="energy_consumption", aggfunc="mean")
            fig = px.imshow(pivot,
                color_continuous_scale=[[0,"#071a10"],[0.4,"#004d20"],[1,"#00ff99"]],
                labels={"x": "Hour of Day", "y": "Load Type", "color": "Avg Energy (kWh)"},
                aspect="auto")
            fig = apply_theme(fig, "Avg Energy Consumption — Hour × Load Type", 320)
            fig.update_layout(xaxis_title="Hour of Day", yaxis_title="Load Type",
                              coloraxis_colorbar=dict(title="kWh"))
            st.plotly_chart(fig, use_container_width=True)

    with c2:
        if "demand_level" in fe.columns:
            d = fe["demand_level"].value_counts().reset_index()
            d.columns = ["level","count"]
            hd = (fe["demand_level"]=="High").mean()*100
            fig = px.pie(d, names="level", values="count", hole=0.65,
                color="level",
                color_discrete_map={"Low": C_GREEN, "Medium": C_GOLD, "High": C_CORAL},
                labels={"level": "Demand Level", "count": "Records"})
            fig.update_traces(textinfo="label+percent", textfont_size=11)
            fig.add_annotation(text=f"{hd:.0f}%<br><span style='font-size:10px'>High</span>",
                x=0.5, y=0.5, font_size=18, showarrow=False, font_color="#e2e8f0")
            fig = apply_theme(fig, "Demand Level Distribution", 320)
            st.plotly_chart(fig, use_container_width=True)
 
    # ── Environment & Renewable ────────────────────────────────────
    # PURPOSE:
    #   Temp scatter → reveals U-shaped pattern: cold spikes heating,
    #                  hot spikes AC — both raise consumption
    #   Renewable   → areas above the avg line are clean energy leaders
    st.markdown('<div class="section-title">Environment & Renewable Analysis</div>', unsafe_allow_html=True)
    c1,c2,c3 = st.columns(3)
    with c1:
        samp = fe.sample(min(500, len(fe)), random_state=2)
        fig = px.scatter(samp, x="temperature", y="energy_consumption",
            color="load_type" if "load_type" in samp.columns else None,
            opacity=0.4, color_discrete_sequence=PALETTE,
            labels={"temperature":"Temperature (°C)","energy_consumption":"Energy (kWh)","load_type":"Load Type"})
        fig.update_traces(hovertemplate="Temp: %{x:.1f}°C<br>Energy: %{y:.0f} kWh<extra></extra>")
        fig = apply_theme(fig, "Temperature → Energy (U-shaped relationship)")
        st.plotly_chart(fig,use_container_width=True)

    with c2:
        samp2 = fe.sample(min(500, len(fe)), random_state=3)
        fig = px.scatter(samp2, x="renewable_usage", y="energy_consumption",
            color="season" if "season" in samp2.columns else None,
            opacity=0.4, color_discrete_sequence=PALETTE,
            labels={"renewable_usage":"Renewable Usage (%)","energy_consumption":"Energy (kWh)","season":"Season"})
        fig.update_traces(hovertemplate="Renewable: %{x:.1f}%<br>Energy: %{y:.0f} kWh<extra></extra>")
        fig = apply_theme(fig, "Renewable Usage → Energy Demand")
        st.plotly_chart(fig,use_container_width=True)

    with c3:
        if "area" in fe.columns:
            d = fe.groupby("area")["renewable_usage"].mean().sort_values(ascending=False).head(8).reset_index()
            d["tier"] = d["renewable_usage"].apply(
                lambda v: "High (>15%)" if v > 15 else ("Mid (8-15%)" if v > 8 else "Low (<8%)"))
            fig = px.bar(d, x="area", y="renewable_usage",
                color="tier",
                color_discrete_map={"High (>15%)": C_GREEN, "Mid (8-15%)": C_GOLD, "Low (<8%)": C_CORAL},
                labels={"area": "Area", "renewable_usage": "Renewable Usage (%)", "tier": "Tier"},
                category_orders={"area": d.sort_values("renewable_usage", ascending=False)["area"].tolist()})
            fig.update_traces(hovertemplate="<b>Area: %{x}</b><br>Renewable: %{y:.1f}%<extra></extra>")
            fig.add_hline(y=fe["renewable_usage"].mean(), line_dash="dash",
                line_color=C_CYAN, annotation_text="city avg", annotation_position="top right")
            fig = apply_theme(fig, "Renewable Usage % by Area")
            fig.update_layout(xaxis_title="Area", yaxis_title="Renewable Usage (%)")
            st.plotly_chart(fig, use_container_width=True)
 
    # ── Weekday vs Weekend & Season ────────────────────────────────
    # PURPOSE:
    #   Line → weekday shows two energy peaks (morning commute + evening).
    #          Weekend is flatter — less commercial/industrial load.
    #   Season×Zone heatmap → summer is highest everywhere (AC load),
    #          Central zone is highest all year (dense commercial activity).
    st.markdown('<div class="section-title">Weekday vs Weekend & Season Analysis</div>', unsafe_allow_html=True)
    c1,c2 = st.columns(2)
    with c1:
        if "is_weekend" in fe.columns and "hour" in fe.columns:
            d = fe.groupby(["hour","is_weekend"])["energy_consumption"].mean().reset_index()
            d["Day Type"] = d["is_weekend"].map({0:"Weekday",1:"Weekend"})
            fig = px.line(d,x="hour",y="energy_consumption",color="Day Type",
                color_discrete_sequence=[C_GREEN,C_GOLD])
            fig.update_traces(line_width=2.5,
                hovertemplate="<b>Day Type: %{fullData.name}</b><br>Hour: %{x}:00<br>Avg Energy: %{y:.0f} kWh<extra></extra>")
            fig = apply_theme(fig, "Hourly Energy — Weekday vs Weekend")
            st.plotly_chart(fig,use_container_width=True)

    with c2:
        if "season" in fe.columns and "zone" in fe.columns:
            piv = fe.pivot_table(index="season", columns="zone",
                values="energy_consumption", aggfunc="mean")
            fig = px.imshow(piv,
                color_continuous_scale=[[0,"#071a10"],[1,"#00ff99"]],
                text_auto=".0f",
                labels={"x": "Zone", "y": "Season", "color": "Avg Energy (kWh)"},
                aspect="auto")
            fig = apply_theme(fig, "Energy Consumption — Season × Zone", 380)
            fig.update_layout(xaxis_title="Zone", yaxis_title="Season",
                              coloraxis_colorbar=dict(title="kWh"))
            fig.update_traces(textfont_size=11)
            st.plotly_chart(fig, use_container_width=True)

    # ── Correlation Heatmap ────────────────────────────────────────
    corr_pd = fe[["energy_consumption","temperature","humidity","renewable_usage"]].corr()
    fig = px.imshow(corr_pd,
        color_continuous_scale=[[0,"#0a1a2e"],[0.5,"#1e3a5f"],[1,"#00d4ff"]],
        zmin=-1, zmax=1, text_auto=".2f",
        labels={"color": "Correlation"},
        aspect="auto")
    fig = apply_theme(fig, "Energy Feature Correlation")
    fig.update_layout(xaxis_title="Feature", yaxis_title="Feature",
                      coloraxis_colorbar=dict(title="Corr"))
    fig.update_traces(textfont_size=11)
    st.plotly_chart(fig, use_container_width=True)
 
    # ── ML Prediction Performance (real-Time only) ─────────────────────────────────
    # PURPOSE:
    #   Scatter → energy predictions scatter along the diagonal.
    #             Points above = over-prediction, below = under-prediction.
    #   APE hist → Mean Absolute % Error gives a single interpretable
    #              accuracy number (e.g. "model is within 8% on average").
    if is_realtime and fe_pred is not None and len(fe_pred) >=1:
        st.markdown('<div class="section-title">GBT Regressor Prediction Performance</div>', unsafe_allow_html=True)
        c1,c2 = st.columns(2)
        with c1:
            samp = fe_pred.sample(min(600, len(fe_pred)), random_state=4)
            mn, mx = samp["energy_consumption"].min(), samp["energy_consumption"].max()
            samp = samp.copy()
            samp["abs_err_e"] = (samp["energy_consumption"] - samp["predicted_energy_consumption"]).abs()
            fig = px.scatter(samp, x="energy_consumption", y="predicted_energy_consumption",
                opacity=0.5, color_discrete_sequence=[C_GREEN],
                custom_data=["abs_err_e"],
                labels={"energy_consumption":"Actual Energy (kWh)","predicted_energy_consumption":"Predicted Energy (kWh)"})
            fig.update_traces(hovertemplate="Actual: <b>%{x:.0f} kWh</b><br>Predicted: <b>%{y:.0f} kWh</b><br>Abs Error: <b>%{customdata[0]:.0f}</b><extra></extra>")
            fig.add_shape(type="line", x0=mn, y0=mn, x1=mx, y1=mx,
                line=dict(color=C_CORAL, dash="dash", width=2))
            fig.add_annotation(x=mx, y=mx, text="Perfect fit",
                showarrow=False, font=dict(color=C_CORAL, size=10), xanchor="right")
            fig = apply_theme(fig, "Actual vs Predicted — Energy Consumption")
            fig.update_layout(xaxis_title="Actual Energy (kWh)",
                              yaxis_title="Predicted Energy (kWh)")
            st.plotly_chart(fig, use_container_width=True)

        with c2:
            err = ((fe_pred["predicted_energy_consumption"] - fe_pred["energy_consumption"]).abs()
                   / fe_pred["energy_consumption"].abs() * 100).clip(0, 50)
            err_df = err.rename("APE").to_frame()
            fig = px.histogram(err_df, x="APE", nbins=50,
                color_discrete_sequence=[C_GREEN],
                labels={"APE": "Absolute % Error", "count": "Frequency"})
            fig.update_traces(opacity=0.8,
                hovertemplate="APE Range: %{x}<br>Frequency: %{y}<extra></extra>")
            fig.add_vline(x=err.mean(), line_dash="dash", line_color=C_GOLD,
                annotation_text=f"Mean APE: {err.mean():.1f}%",
                annotation_position="top right")
            fig = apply_theme(fig, "Absolute Percentage Error Distribution")
            fig.update_layout(xaxis_title="Absolute % Error",
                              yaxis_title="Frequency")
            st.plotly_chart(fig, use_container_width=True)

    elif is_realtime:
        show_prediction_notice(has_pred_e, fe_pred, "energy_predictions.csv")
 
    # ── Power Outage Analysis ─────────────────────────────────────
    # PURPOSE:
    #   Bar → areas with highest outage rates need infrastructure investment.
    #   Group bar → compares normal vs outage energy readings by zone.
    if "power_outage" in fe.columns and "area" in fe.columns:
        st.markdown('<div class="section-title">Power Outage Analysis</div>', unsafe_allow_html=True)
        c1,c2 = st.columns(2)
        with c1:
            d = fe.groupby("area")["power_outage"].mean().sort_values(ascending=False).head(8).reset_index()
            d["pct"] = d["power_outage"] * 100
            d["risk"] = d["pct"].apply(
                lambda v: "Critical (>10%)" if v > 10 else ("Moderate (5-10%)" if v > 5 else "Normal (<5%)"))
            fig = px.bar(d, x="area", y="pct",
                color="risk",
                color_discrete_map={"Critical (>10%)": C_CORAL, "Moderate (5-10%)": C_GOLD, "Normal (<5%)": C_GREEN},
                labels={"area": "Area", "pct": "Outage Rate (%)", "risk": "Risk Level"},
                category_orders={"area": d.sort_values("pct", ascending=False)["area"].tolist()})
            fig.update_traces(hovertemplate="<b>Area: %{x}</b><br>Outage Rate: %{y:.1f}%<extra></extra>")
            fig = apply_theme(fig, "Power Outage Rate by Area (%)")
            fig.update_layout(xaxis_title="Area", yaxis_title="Outage Rate (%)")
            st.plotly_chart(fig, use_container_width=True)

        with c2:
            d = fe.groupby(["zone","power_outage"])["energy_consumption"].mean().reset_index()
            d["Status"] = d["power_outage"].map({0:"Normal",1:"Outage"})
            fig = px.bar(d, x="zone", y="energy_consumption", color="Status", barmode="group",
                color_discrete_map={"Normal":C_GREEN,"Outage":C_CORAL},
                labels={"zone":"Zone","energy_consumption":"Avg Energy (kWh)","Status":"Grid Status"})
            fig.update_traces(hovertemplate="<b>Zone: %{x}</b> — %{data.name}<br>Avg Energy: %{y:.0f} kWh<extra></extra>")
            fig = apply_theme(fig, "Energy — Normal vs Outage by Zone")
            st.plotly_chart(fig,use_container_width=True)

    # Model metadata card
    if is_realtime:
        st.markdown('<div class="section-title">Model Metadata</div>', unsafe_allow_html=True)
        render_model_metrics("energy", C_GREEN)

    # Download current filtered energy view
    st.markdown('<div class="section-title">Export Current View</div>', unsafe_allow_html=True)
    st.download_button("⬇️ Download Energy Data (CSV)",
        fe.to_csv(index=False).encode(),
        file_name=f"energy_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv", use_container_width=True)    

# ══════════════════════════════════════════════════════════════════
#  PAGE 4: POLLUTION
#
#  WHAT THIS PAGE SHOWS:
#   ▸ KPIs         — AQI, PM2.5, PM10, NO2, CO, predicted AQI
#   ▸ AQI alert    — color-coded status banner (Good → Hazardous)
#   ▸ Treemap      — geographic AQI hierarchy: zone → area
#   ▸ Category bar — count of records in each AQI category
#   ▸ Pollutants   — PM scatter vs AQI, KDE density, weather error bars
#   ▸ Time series  — AQI by hour×season + day-of-week bar
#   ▸ Prediction   — scatter + per-zone error boxplot
#   ▸ Insights     — IT hub vs non-IT, weekday vs weekend, correlation matrix
# ══════════════════════════════════════════════════════════════════
elif page == "🌫️  Pollution":
    # dynamic browser tab title
    st.markdown("<script>document.title='Pollution · SmartCity Analytics'</script>",
                unsafe_allow_html=True)
    st.markdown("""
    <div class="page-header">
        <div class="page-icon">🌫️</div>
        <div>
            <div class="page-title">Air Quality Intelligence</div>
            <div class="page-sub">AQI monitoring · Pollutant tracking · ML air quality forecasting</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    render_mode_banner()

    k1,k2,k3,k4,k5,k6 = st.columns(6)
    avg_aqi  = fp["AQI"].mean()
    avg_pm25 = fp["PM2_5"].mean()
    avg_pm10 = fp["PM10"].mean()
    avg_no2  = fp["NO2"].mean()
    avg_co   = fp["CO"].mean()
    pred_aqi = fp_pred["predicted_AQI"].mean() if fp_pred is not None and len(fp_pred) > 0 else None

    with k1: st.markdown(kpi("Avg AQI",          avg_aqi,  delta_aqi,  "🌫️", "coral",  "{:.0f}",  lower_is_better=True),  unsafe_allow_html=True)
    with k2: st.markdown(kpi("Avg PM2_5",        avg_pm25, delta_pm25, "💨", "coral",  "{:.1f}",  lower_is_better=True),  unsafe_allow_html=True)
    with k3: st.markdown(kpi("Avg PM10",         avg_pm10, delta_pm10, "💨", "gold",   "{:.1f}",  lower_is_better=True),  unsafe_allow_html=True)
    with k4: st.markdown(kpi("Avg NO₂",          avg_no2,  delta_no2,  "🔬", "violet", "{:.1f}",  lower_is_better=True),  unsafe_allow_html=True)
    with k5: st.markdown(kpi("Avg CO",            avg_co,   delta_co,  "☁️", "violet", "{:.2f}",  lower_is_better=True),  unsafe_allow_html=True)
    with k6: st.markdown(kpi("ML Predicted AQI", pred_aqi if pred_aqi else 0, None, "🤖", "cyan", "{:.0f}", lower_is_better=True), unsafe_allow_html=True)

    # AQI status banner
    # PURPOSE: instant read of current city air quality standard.
    # Color-coded and text-labelled to match WHO AQI categories.
    aqi_lbl = aqi_label(avg_aqi)
    aqi_clr = aqi_color(avg_aqi)
    ac = ("alert-danger" if avg_aqi>200 else "alert-warning" if avg_aqi>100 else "alert-success")
    st.markdown(
        f'<div class="alert {ac}" style="border-left-color:{aqi_clr}">'
        f'🏙️ City Air Quality Status: <strong>{aqi_lbl}</strong> '
        f'— Avg AQI {avg_aqi:.0f}</div>', unsafe_allow_html=True)
 
    # ── AQI Spatial & Temporal ────────────────────────────────────
    # PURPOSE:
    #   Treemap → hierarchical geographic view. Red tiles = danger zones.
    #             Drill from zone to area to see spatial pollution gradients.
    #   Bar     → how many records fall in each AQI health category.
    st.markdown('<div class="section-title">AQI Spatial & Temporal Analysis</div>', unsafe_allow_html=True)
    c1,c2 = st.columns([3,2])
    with c1:
        if "area" in fp.columns and "zone" in fp.columns:
            d = fp.groupby(["zone","area"])["AQI"].mean().reset_index()
            fig = px.treemap(d,path=["zone","area"],values="AQI",color="AQI",
                color_continuous_scale=[[0,"#003a00"],[0.3,"#fbbf24"],[0.6,"#f97316"],[1,"#dc2626"]],
                color_continuous_midpoint=150)
            fig = apply_theme(fig, "AQI by Zone → Area (Treemap)", 380)
            fig.update_traces(
                hovertemplate="<b>Area: %{label}</b><br>Avg AQI: %{value:.0f}<br>Parent: %{parent}<extra></extra>")
            st.plotly_chart(fig,use_container_width=True)

    with c2:
        fp2 = fp.copy()
        fp2["AQI_cat"] = fp2["AQI"].apply(aqi_label)
        d = fp2["AQI_cat"].value_counts().reset_index()
        d.columns = ["cat","count"]
        cat_ord = ["Good","Moderate","Unhealthy (Sensitive)","Unhealthy","Hazardous"]
        clr_map = {"Good":C_GREEN,"Moderate":C_GOLD,"Unhealthy (Sensitive)":"#f97316",
                   "Unhealthy":C_CORAL,"Hazardous":"#dc2626"}
        d["cat"] = pd.Categorical(d["cat"],categories=cat_ord,ordered=True)
        d = d.sort_values("cat")
        fig = px.bar(d, x="cat", y="count",
            color="cat", color_discrete_map=clr_map,
            labels={"cat":"AQI Category","count":"Number of Records"},
            category_orders={"cat": cat_ord})
        fig.update_traces(hovertemplate="<b>AQI Category: %{x}</b><br>Records: %{y:,}<extra></extra>")
        fig = apply_theme(fig, "AQI Category Distribution", 380)
        fig.update_layout(xaxis_title="AQI Category", yaxis_title="Number of Records",
                          showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
 
    # ── Pollutant Deep Dive ────────────────────────────────────────
    # PURPOSE:
    #   Scatter → PM2.5 and PM10 vs AQI. Should show near-linear lines
    #             (generator derives both from AQI with fixed ratios).
    #   KDE     → density overlay of all pollutants shows relative scale.
    #   Weather → error bars show variability. Heavy Rain washes pollution,
    #             reducing AQI — visible as lowest mean bar.
    st.markdown('<div class="section-title">Pollutant Deep Dive</div>', unsafe_allow_html=True)
    c1,c2,c3 = st.columns(3)
    with c1:
        samp = fp.sample(min(500, len(fp)), random_state=5)
        samp_m = pd.melt(samp, id_vars=["AQI"], value_vars=["PM2_5", "PM10"],
                         var_name="Pollutant", value_name="Concentration")
        fig = px.scatter(samp_m, x="Concentration", y="AQI",
            color="Pollutant",
            color_discrete_map={"PM2_5": C_CORAL, "PM10": C_GOLD},
            opacity=0.5,
            labels={"Concentration": "Pollutant Concentration (µg/m³)",
                    "AQI": "AQI", "Pollutant": "Pollutant"})
        fig.update_traces(marker_size=4,
            hovertemplate="<b>Pollutant: %{fullData.name}</b><br>Concentration: %{x:.1f} µg/m³<br>AQI: %{y:.0f}<extra></extra>")
        fig = apply_theme(fig, "PM2_5 & PM10 → AQI")
        fig.update_layout(xaxis_title="Pollutant Concentration (µg/m³)", yaxis_title="AQI")
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        dens_df = fp[["AQI","PM2_5","NO2"]].melt(var_name="Pollutant", value_name="Value")
        fig = px.histogram(dens_df, x="Value", color="Pollutant",
            barmode="overlay", histnorm="probability density", nbins=60,
            color_discrete_map={"AQI": C_CORAL, "PM2_5": C_GOLD, "NO2": C_VIOLET},
            labels={"Value": "Concentration / Index", "Pollutant": "Pollutant",
                    "probability density": "Density"})
        fig.update_traces(opacity=0.55,
            hovertemplate="<b>Pollutant: %{fullData.name}</b><br>Value: %{x:.1f}<br>Density: %{y:.4f}<extra></extra>")
        fig = apply_theme(fig, "Pollutant Density Distribution")
        fig.update_layout(xaxis_title="Concentration / Index", yaxis_title="Density",
                          bargap=0)
        st.plotly_chart(fig, use_container_width=True)

    with c3:
        if "weather" in fp.columns:
            d = fp.groupby("weather")["AQI"].agg(["mean","std"]).reset_index()
            d.columns = ["weather", "mean_AQI", "std_AQI"]
            d["AQI_category"] = d["mean_AQI"].apply(aqi_label)
            fig = px.bar(d, x="weather", y="mean_AQI",
                error_y="std_AQI",
                color="AQI_category",
                color_discrete_map={
                    "Good": C_GREEN, "Moderate": C_GOLD,
                    "Unhealthy (Sensitive)": "#f97316",
                    "Unhealthy": C_CORAL, "Hazardous": "#dc2626"},
                labels={"weather": "Weather Condition", "mean_AQI": "Avg AQI",
                        "AQI_category": "Category"})
            fig.update_traces(hovertemplate="<b>Weather: %{x}</b><br>Avg AQI: %{y:.1f}<extra></extra>")
            fig = apply_theme(fig, "Avg AQI by Weather (with Std Dev)")
            fig.update_layout(xaxis_title="Weather Condition", yaxis_title="Avg AQI")
            st.plotly_chart(fig, use_container_width=True)

    # ── Time Series & Seasonality ─────────────────────────────────
    # PURPOSE:
    #   Line chart → AQI by hour per season. Winter shows highest peak at
    #                dawn (thermal inversion traps particles overnight).
    #   DoW bar   → Weekdays are higher due to industrial/vehicle emissions.
    #               Weekend drop validates the generator's is_weekend logic.
    #               WHO Limit reference line shows how often we exceed it.
    st.markdown('<div class="section-title">Time Series & Seasonality</div>', unsafe_allow_html=True)
    c1,c2 = st.columns(2)
    with c1:
        if "hour" in fp.columns and "season" in fp.columns:
            d_hr = fp.groupby(["hour","season"])["AQI"].mean().reset_index()
            fig = px.line(d_hr, x="hour", y="AQI", color="season",
                color_discrete_map={"Summer": C_GOLD, "Monsoon": C_CYAN, "Winter": C_CORAL},
                labels={"hour": "Hour of Day", "AQI": "Avg AQI", "season": "Season"})
            fig.update_traces(line_width=2,
                hovertemplate="<b>Season: %{fullData.name}</b><br>Hour: %{x}:00<br>Avg AQI: %{y:.1f}<extra></extra>")
            fig = apply_theme(fig, "AQI by Hour × Season")
            fig.update_layout(xaxis_title="Hour of Day", yaxis_title="Avg AQI")
            st.plotly_chart(fig, use_container_width=True)

    with c2:
        if "dayofweek" in fp.columns:
            d = fp.groupby("dayofweek")["AQI"].mean().reset_index()
            dm = {0:"Mon",1:"Tue",2:"Wed",3:"Thu",4:"Fri",5:"Sat",6:"Sun"}
            d["day"] = d["dayofweek"].map(dm)
            d["AQI_category"] = d["AQI"].apply(aqi_label)
            day_order = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
            fig = px.bar(d, x="day", y="AQI",
                color="AQI_category",
                color_discrete_map={
                    "Good": C_GREEN, "Moderate": C_GOLD,
                    "Unhealthy (Sensitive)": "#f97316",
                    "Unhealthy": C_CORAL, "Hazardous": "#dc2626"},
                category_orders={"day": day_order},
                labels={"day": "Day of Week", "AQI": "Avg AQI", "AQI_category": "Category"})
            fig.update_traces(hovertemplate="<b>Day: %{x}</b><br>Avg AQI: %{y:.1f}<extra></extra>")
            fig.add_hline(y=100, line_dash="dash", line_color=C_GOLD,
                          annotation_text="WHO Limit", annotation_position="top right")
            fig = apply_theme(fig, "Avg AQI by Day of Week")
            fig.update_layout(xaxis_title="Day of Week", yaxis_title="Avg AQI")
            st.plotly_chart(fig, use_container_width=True)
 
    # ── ML Prediction Performance ─────────────────────────────────
    # PURPOSE:
    #   Scatter → AQI is easier to predict than energy (less noise).
    #             Points should cluster tightly on the diagonal.
    #   Zone error → Industrial zones (Peenya, Yeshwanthpur) have higher
    #                prediction error due to irregular emission spikes.
    if is_realtime and fp_pred is not None and len(fp_pred) >= 1:
        st.markdown('<div class="section-title">GBT Regressor Prediction Performance</div>', unsafe_allow_html=True)
        c1,c2 = st.columns(2)
        with c1:
            samp = fp_pred.sample(min(600, len(fp_pred)), random_state=6)
            mn, mx = samp["AQI"].min(), samp["AQI"].max()
            samp = samp.copy()
            samp["abs_err_p"] = (samp["AQI"] - samp["predicted_AQI"]).abs()
            fig = px.scatter(samp, x="AQI", y="predicted_AQI",
                opacity=0.5, color_discrete_sequence=[C_CORAL],
                custom_data=["abs_err_p"],
                labels={"AQI":"Actual AQI","predicted_AQI":"Predicted AQI"})
            fig.update_traces(hovertemplate="Actual AQI: <b>%{x:.0f}</b><br>Predicted AQI: <b>%{y:.0f}</b><br>Abs Error: <b>%{customdata[0]:.1f}</b><extra></extra>")
            fig.add_shape(type="line", x0=mn, y0=mn, x1=mx, y1=mx,
                line=dict(color=C_CYAN, dash="dash", width=2))
            fig.add_annotation(x=mx, y=mx, text="Perfect fit",
                showarrow=False, font=dict(color=C_CYAN, size=10), xanchor="right")
            fig = apply_theme(fig, "Actual vs Predicted — AQI")
            fig.update_layout(xaxis_title="Actual AQI", yaxis_title="Predicted AQI")
            st.plotly_chart(fig, use_container_width=True)

        with c2:
            if "zone" in fp_pred.columns:
                fp_err = fp_pred.copy()
                fp_err["abs_error"] = (fp_err["predicted_AQI"] - fp_err["AQI"]).abs()
                fig = px.box(fp_err, x="zone", y="abs_error",
                    color="zone", color_discrete_sequence=PALETTE,
                    points=False,
                    labels={"zone": "Zone", "abs_error": "Absolute Prediction Error (AQI)"})
                fig.update_traces(boxmean=True,
                    hovertemplate="<b>Zone: %{x}</b><br>Abs Error: %{y:.1f}<extra></extra>")
                fig = apply_theme(fig, "Prediction Error (Abs) by Zone")
                fig.update_layout(xaxis_title="Zone",
                                  yaxis_title="Absolute Prediction Error (AQI)",
                                  showlegend=False)
                st.plotly_chart(fig, use_container_width=True)

    elif is_realtime:
        show_prediction_notice(has_pred_p, fp_pred, "pollution_predictions.csv")
 
    # ── Advanced Insights ─────────────────────────────────────────
    # PURPOSE:
    #   IT Hub → commercial IT areas emit more due to data centres + traffic.
    #            Shows that AQI, PM2.5 and NO2 are all higher in IT hubs.
    #   Weekend → validates emission pattern — weekday industrial output
    #             clearly visible as higher pollution.
    #   Corr matrix → PM2.5 and PM10 are nearly perfectly correlated (0.98+)
    #                 because both are derived from AQI in the generator.
    #                 Temperature has moderate negative correlation with humidity.
    st.markdown('<div class="section-title">Advanced Insights</div>', unsafe_allow_html=True)
    c1,c2,c3 = st.columns(3)
    with c1:
        if "is_it_hub" in fp.columns:
            d = fp.groupby("is_it_hub")[["AQI","PM2_5","NO2"]].mean().reset_index()
            d["Area Type"] = d["is_it_hub"].map({0:"Non-IT Hub",1:"IT Hub"})
            fig = px.bar(d.melt(id_vars=["Area Type"],value_vars=["AQI","PM2_5","NO2"]),
                x="variable", y="value", color="Area Type", barmode="group",
                color_discrete_map={"IT Hub":C_CORAL,"Non-IT Hub":C_GREEN},
                labels={"variable":"Pollutant","value":"Avg Value","Area Type":"Area Type"})
            fig.update_traces(hovertemplate="<b>Pollutant: %{x}</b><br>%{data.name}: %{y:.1f}<extra></extra>")
            fig = apply_theme(fig,"IT Hub vs Non-IT Hub Pollution")
            st.plotly_chart(fig,use_container_width=True)

    with c2:
        if "is_weekend" in fp.columns:
            d = fp.groupby("is_weekend")[["AQI","PM2_5","PM10"]].mean().reset_index()
            d["Day Type"] = d["is_weekend"].map({0:"Weekday",1:"Weekend"})
            fig = px.bar(d.melt(id_vars=["Day Type"],value_vars=["AQI","PM2_5","PM10"]),
                x="variable", y="value", color="Day Type", barmode="group",
                color_discrete_map={"Weekday":C_CORAL,"Weekend":C_GREEN},
                labels={"variable":"Pollutant","value":"Avg Value","Day Type":"Day Type"})
            fig.update_traces(hovertemplate="<b>Pollutant: %{x}</b><br>%{data.name}: %{y:.1f}<extra></extra>")
            fig = apply_theme(fig,"Weekday vs Weekend Pollution Levels")
            st.plotly_chart(fig,use_container_width=True)

    with c3:
        cc = ["AQI","PM2_5","PM10","NO2","CO","temperature","humidity"]
        av = [c for c in cc if c in fp.columns]
        corr = fp[av].corr()
        fig = px.imshow(corr,
            color_continuous_scale=[[0,"#0a0022"],[0.5,"#1e1040"],[1,"#a78bfa"]],
            zmin=-1, zmax=1, text_auto=".2f",
            labels={"color": "Correlation"},
            aspect="auto")
        fig = apply_theme(fig, "Pollutant Correlation Matrix", 380)
        fig.update_layout(xaxis_title="Pollutant / Feature",
                          yaxis_title="Pollutant / Feature",
                          coloraxis_colorbar=dict(title="Corr"))
        fig.update_traces(textfont_size=10)
        st.plotly_chart(fig, use_container_width=True)

    # Point 8 — Model metadata card
    if is_realtime:
        st.markdown('<div class="section-title">Model Metadata</div>', unsafe_allow_html=True)
        render_model_metrics("pollution", C_CORAL)

    # Download current filtered pollution view
    st.markdown('<div class="section-title">Export Current View</div>', unsafe_allow_html=True)
    st.download_button("⬇️ Download Pollution Data (CSV)",
        fp.to_csv(index=False).encode(),
        file_name=f"pollution_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv", use_container_width=True)

# ══════════════════════════════════════════════════════════════════
#  PAGE 5: ANOMALY DETECTION
#
#  WHAT THIS PAGE SHOWS:
#   ▸ Summary KPIs — anomaly counts and rates per stream
#   ▸ Time-series  — actual vs normal band; anomalies highlighted
#   ▸ Area heatmap — which areas produce the most anomalies
#   ▸ Severity dist — histogram of z-scores for flagged records
#   ▸ Method breakdown — how many anomalies each detection method found
#   ▸ Anomaly log   — sortable table of recent anomalous records
# ══════════════════════════════════════════════════════════════════
elif page == "🔍  Anomaly Detection":
    # dynamic browser tab title
    st.markdown("<script>document.title='Anomaly Detection · SmartCity Analytics'</script>",
                unsafe_allow_html=True)
    st.markdown("""
    <div class="page-header">
        <div class="page-icon">🔍</div>
        <div>
            <div class="page-title">Anomaly Detection</div>
            <div class="page-sub">Statistical spike detection · Z-Score · IQR Fence · Rolling σ · All three data streams</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    render_mode_banner()

    # ── Sidebar controls for this page (rendered inline) ─────────
    st.markdown('<div class="section-title">Detection Settings</div>', unsafe_allow_html=True)
    ad_c1, ad_c2, ad_c3 = st.columns(3)
    with ad_c1:
        z_thresh = st.slider("Z-Score threshold", 2.0, 5.0, 3.0, 0.1,
            help="Records with |z| above this value are flagged. Lower = more sensitive.")
    with ad_c2:
        iqr_k = st.slider("IQR multiplier (k)", 1.0, 3.5, 2.0, 0.1,
            help="Fence = Q1 - k×IQR to Q3 + k×IQR. Lower k catches more anomalies.")
    with ad_c3:
        roll_w = st.slider("Rolling window (records)", 6, 72, 24, 6,
            help="Window for computing local mean/σ. Larger = smoother baseline.")

    # ── Stream / metric selectors ─────────────────────────────────
    st.markdown('<div class="section-title">Stream & Metric Selection</div>', unsafe_allow_html=True)
    sel_c1, sel_c2 = st.columns(2)
    with sel_c1:
        stream_choice = st.selectbox(
            "Select data stream",
            ["Traffic — Vehicle Count", "Traffic — Avg Speed",
             "Energy — Consumption", "Energy — Renewable Usage",
             "Pollution — AQI", "Pollution — PM2.5"])
    with sel_c2:
        area_ad = st.selectbox(
            "Filter by area (optional)",
            ["All Areas"] + sorted(ALL_AREAS))

    # ── Map selection to dataframe + column ──────────────────────
    _stream_map = {
        "Traffic — Vehicle Count":   (ft, "vehicle_count",       "Vehicles/hr",  C_CYAN,   "Traffic"),
        "Traffic — Avg Speed":       (ft, "avg_speed",           "km/h",         C_CYAN,   "Traffic"),
        "Energy — Consumption":      (fe, "energy_consumption",  "kWh",          C_GREEN,  "Energy"),
        "Energy — Renewable Usage":  (fe, "renewable_usage",     "%",            C_GREEN,  "Energy"),
        "Pollution — AQI":           (fp, "AQI",                 "AQI",          C_CORAL,  "Pollution"),
        "Pollution — PM2.5":         (fp, "PM2_5" if "PM2_5" in fp.columns else "PM2.5", "µg/m³", C_CORAL, "Pollution"),
    }

    df_ad_raw, metric_col, unit_label, stream_color, stream_name = _stream_map[stream_choice]

    # Rename PM2.5 if needed
    if metric_col not in df_ad_raw.columns:
        alt = "PM2.5" if "PM2.5" in df_ad_raw.columns else "PM2_5"
        metric_col = alt if alt in df_ad_raw.columns else metric_col

    # Apply area filter
    if area_ad != "All Areas":
        df_ad_raw = df_ad_raw[df_ad_raw["area"] == area_ad].copy()

    # Sort by timestamp for rolling window to work correctly
    df_ad = df_ad_raw.copy()
    if "timestamp" in df_ad.columns:
        df_ad = df_ad.sort_values("timestamp").reset_index(drop=True)

    # Guard: need the column to exist
    if metric_col not in df_ad.columns or len(df_ad) < 10:
        st.warning(f"⚠️ Not enough data for '{metric_col}' in the selected stream/area. "
                   "Clear filters or generate more data.")
        st.stop()

    # Drop NaN in the metric column before detection
    df_ad = df_ad.dropna(subset=[metric_col]).reset_index(drop=True)

    # ── Run anomaly detection ─────────────────────────────────────
    df_ad = detect_anomalies(df_ad, metric_col,
                             z_thresh=z_thresh, iqr_k=iqr_k,
                             rolling_window=roll_w)

    anom_df = df_ad[df_ad["is_anomaly"]]
    normal_df = df_ad[~df_ad["is_anomaly"]]
    summary = get_anomaly_summary(df_ad, metric_col, stream_choice)

    # ── KPI Row ───────────────────────────────────────────────────
    st.markdown('<div class="section-title">Anomaly Summary</div>', unsafe_allow_html=True)
    ak1,ak2,ak3,ak4,ak5 = st.columns(5)
    with ak1: st.markdown(kpi("Records Analyzed", summary["total"], None, "📊","violet","{:.0f}"),unsafe_allow_html=True)
    with ak2: st.markdown(kpi("Anomalies Found",  summary["n_anom"],None,"🚨","coral", "{:.0f}", lower_is_better=True),unsafe_allow_html=True)
    with ak3: st.markdown(kpi("Anomaly Rate %",   summary["pct"],  None,"📈","coral", "{:.1f}%",lower_is_better=True),unsafe_allow_html=True)
    with ak4: st.markdown(kpi("HIGH Severity",    summary["high"], None,"🔴","coral", "{:.0f}", lower_is_better=True),unsafe_allow_html=True)
    with ak5: st.markdown(kpi("MEDIUM Severity",  summary["medium"],None,"🟡","gold","{:.0f}",  lower_is_better=True),unsafe_allow_html=True)

    if summary["worst_area"]:
        st.markdown(
            f'<div class="alert alert-warning">⚠️ Most anomalous area: '
            f'<strong>{summary["worst_area"]}</strong> · '
            f'Peak value: <strong>{summary["worst"]:.1f} {unit_label}</strong> · '
            f'HIGH: {summary["high"]} · MEDIUM: {summary["medium"]} · LOW: {summary["low"]}</div>',
            unsafe_allow_html=True)

    # ── Time-Series: actual value with anomaly overlays ───────────
    # PURPOSE: Shows how the metric behaves over time, with:
    #   • A shaded normal band (mean ± z_thresh·σ) as the baseline
    #   • Normal points in stream color
    #   • Anomaly points color-coded by severity (red=HIGH, amber=MEDIUM, green=LOW)
    st.markdown('<div class="section-title">Time-Series Anomaly View</div>', unsafe_allow_html=True)

    if "timestamp" in df_ad.columns and len(df_ad) >= 5:
        mu_val  = df_ad[metric_col].mean()
        sig_val = df_ad[metric_col].std()
        band_lo = mu_val - z_thresh * sig_val
        band_hi = mu_val + z_thresh * sig_val

        fig_ts = go.Figure()

        # Normal band shading
        ts_vals = df_ad["timestamp"]
        fig_ts.add_trace(go.Scatter(
            x=pd.concat([ts_vals, ts_vals[::-1]]),
            y=[band_hi]*len(ts_vals) + [band_lo]*len(ts_vals),
            fill="toself",
            fillcolor="rgba(100,116,139,0.08)",
            line=dict(color="rgba(0,0,0,0)"),
            name=f"Normal band (±{z_thresh}σ)",
            hoverinfo="skip",
        ))
        # Normal band border lines
        fig_ts.add_trace(go.Scatter(
            x=ts_vals, y=[band_hi]*len(ts_vals),
            mode="lines", line=dict(color="#334155", dash="dot", width=1),
            name=f"Upper bound ({band_hi:.1f})", hoverinfo="skip"))
        fig_ts.add_trace(go.Scatter(
            x=ts_vals, y=[band_lo]*len(ts_vals),
            mode="lines", line=dict(color="#334155", dash="dot", width=1),
            name=f"Lower bound ({band_lo:.1f})", hoverinfo="skip"))

        # Normal points
        if len(normal_df) > 0:
            fig_ts.add_trace(go.Scatter(
                x=normal_df["timestamp"], y=normal_df[metric_col],
                mode="markers",
                marker=dict(color=stream_color, size=3, opacity=0.4),
                name="Normal",
                hovertemplate="<b>%{x}</b><br>" + metric_col + ": %{y:.1f}<extra>Normal</extra>",
            ))

        # Anomaly points by severity
        sev_style = {
            "HIGH":   ("#ef4444", 9, "diamond"),
            "MEDIUM": ("#fbbf24", 7, "triangle-up"),
            "LOW":    ("#22c55e", 6, "circle"),
        }
        for sev, (clr, sz, sym) in sev_style.items():
            sdf = anom_df[anom_df["anomaly_severity"] == sev]
            if len(sdf) > 0:
                area_col = sdf["area"] if "area" in sdf.columns else pd.Series(["—"]*len(sdf))
                fig_ts.add_trace(go.Scatter(
                    x=sdf["timestamp"], y=sdf[metric_col],
                    mode="markers",
                    marker=dict(color=clr, size=sz, symbol=sym,
                                line=dict(color="white", width=0.8)),
                    name=f"{sev} anomaly ({len(sdf)})",
                    customdata=np.stack([
                        area_col.values,
                        sdf["anomaly_zscore_val"].round(2).values
                    ], axis=-1),
                    hovertemplate=(
                        "<b>%{x}</b><br>"
                        f"{metric_col}: %{{y:.1f}} {unit_label}<br>"
                        "Area: %{customdata[0]}<br>"
                        "Z-score: %{customdata[1]:.2f}"
                        f"<extra>{sev}</extra>"
                    ),
                ))

        fig_ts = apply_theme(fig_ts,
            f"{stream_name} · {metric_col} — Time Series with Anomalies", 420)
        fig_ts.update_layout(
            xaxis_title="Timestamp",
            yaxis_title=f"{metric_col} ({unit_label})",
            legend=dict(orientation="h", y=-0.18),
        )
        st.plotly_chart(fig_ts, use_container_width=True)

    # ── Area Heatmap + Z-score Distribution ───────────────────────
    # PURPOSE:
    #   Heatmap → which areas produce most anomalies per severity level
    #   Histogram → distribution of z-scores; shows how extreme the outliers are
    st.markdown('<div class="section-title">Spatial & Statistical Distribution</div>', unsafe_allow_html=True)
    hm_c1, hm_c2 = st.columns(2)

    with hm_c1:
        if "area" in anom_df.columns and len(anom_df) > 0:
            area_sev = (
                anom_df.groupby(["area","anomaly_severity"])
                .size().reset_index(name="count")
            )
            sev_order = ["HIGH","MEDIUM","LOW"]
            area_sev["anomaly_severity"] = pd.Categorical(
                area_sev["anomaly_severity"], categories=sev_order, ordered=True)
            top_areas = (
                anom_df.groupby("area").size()
                .sort_values(ascending=False).head(15).index.tolist()
            )
            area_sev_top = area_sev[area_sev["area"].isin(top_areas)]
            if len(area_sev_top) > 0:
                fig_hm = px.bar(
                    area_sev_top.sort_values("count", ascending=True),
                    x="count", y="area", color="anomaly_severity",
                    orientation="h",
                    color_discrete_map={"HIGH":"#ef4444","MEDIUM":"#fbbf24","LOW":"#22c55e"},
                    category_orders={"anomaly_severity": sev_order},
                    labels={"count":"Anomaly Count","area":"Area",
                            "anomaly_severity":"Severity"},
                )
                fig_hm.update_traces(
                    hovertemplate="<b>%{y}</b><br>Count: %{x}<extra>%{fullData.name}</extra>")
                fig_hm = apply_theme(fig_hm, "Anomalies by Area & Severity (Top 15)", 400)
                fig_hm.update_layout(xaxis_title="Anomaly Count",
                                     yaxis_title="Area", showlegend=True)
                st.plotly_chart(fig_hm, use_container_width=True)
            else:
                st.info("No anomalies detected in the selected stream/filter.")
        else:
            st.info("No anomalies detected — try lowering the Z-Score threshold.")

    with hm_c2:
        # Z-score distribution of ALL records
        fig_zd = go.Figure()
        # Normal records z-scores
        if len(normal_df) > 0:
            fig_zd.add_trace(go.Histogram(
                x=normal_df["anomaly_zscore_val"],
                name="Normal", marker_color=stream_color,
                opacity=0.6, nbinsx=40,
                hovertemplate="Z-score bin: %{x:.1f}<br>Count: %{y}<extra>Normal</extra>"))
        # Anomaly z-scores
        if len(anom_df) > 0:
            fig_zd.add_trace(go.Histogram(
                x=anom_df["anomaly_zscore_val"],
                name="Anomaly", marker_color="#ef4444",
                opacity=0.8, nbinsx=20,
                hovertemplate="Z-score bin: %{x:.1f}<br>Count: %{y}<extra>Anomaly</extra>"))
        # Threshold line
        fig_zd.add_vline(x=z_thresh, line_dash="dash", line_color=C_GOLD,
                         annotation_text=f"Threshold ({z_thresh}σ)",
                         annotation_position="top right")
        fig_zd = apply_theme(fig_zd, "Z-Score Distribution — Normal vs Anomaly", 400)
        fig_zd.update_layout(
            barmode="overlay",
            xaxis_title="Z-Score (|deviation from mean|)",
            yaxis_title="Record Count",
        )
        st.plotly_chart(fig_zd, use_container_width=True)

    # ── Detection Method Breakdown ─────────────────────────────────
    # PURPOSE: Shows what fraction of anomalies each method caught.
    # All three methods often overlap; this reveals which is most active.
    st.markdown('<div class="section-title">Detection Method Breakdown</div>', unsafe_allow_html=True)
    mb_c1, mb_c2, mb_c3 = st.columns(3)

    method_counts = {
        "Z-Score":  df_ad["anomaly_zscore"].sum(),
        "IQR Fence":df_ad["anomaly_iqr"].sum(),
        "Rolling σ":df_ad["anomaly_rolling"].sum(),
    }
    method_colors = [C_CYAN, C_GOLD, C_VIOLET]

    with mb_c1:
        fig_mb = go.Figure(go.Bar(
            x=list(method_counts.keys()),
            y=list(method_counts.values()),
            marker_color=method_colors,
            hovertemplate="<b>%{x}</b><br>Flagged: %{y}<extra></extra>",
        ))
        fig_mb = apply_theme(fig_mb, "Records Flagged per Method", 320)
        fig_mb.update_layout(xaxis_title="Detection Method",
                              yaxis_title="Records Flagged", showlegend=False)
        st.plotly_chart(fig_mb, use_container_width=True)

    with mb_c2:
        # Overlap: how many anomalies were caught by multiple methods
        if len(anom_df) > 0:
            overlap_counts = (
                anom_df[["anomaly_zscore","anomaly_iqr","anomaly_rolling"]]
                .sum(axis=1).value_counts().sort_index()
            )
            labels = {1:"1 method only", 2:"2 methods", 3:"All 3 methods"}
            fig_ov = go.Figure(go.Pie(
                labels=[labels.get(i, str(i)) for i in overlap_counts.index],
                values=overlap_counts.values,
                hole=0.45,
                marker_colors=[C_GOLD, C_CORAL, "#ef4444"],
                hovertemplate="<b>%{label}</b><br>Anomalies: %{value} (%{percent})<extra></extra>",
            ))
            fig_ov = apply_theme(fig_ov, "Detection Method Overlap", 320)
            fig_ov.update_traces(textinfo="percent+label", textfont_size=10)
            st.plotly_chart(fig_ov, use_container_width=True)
        else:
            st.info("No anomalies to show overlap for.")

    with mb_c3:
        # Anomaly rate over time (rolling 50-record window)
        if len(df_ad) >= 20 and "timestamp" in df_ad.columns:
            df_ad_time = df_ad.copy()
            df_ad_time["anom_rate_roll"] = (
                df_ad_time["is_anomaly"].astype(int)
                .rolling(50, min_periods=10).mean() * 100
            )
            fig_rate = go.Figure(go.Scatter(
                x=df_ad_time["timestamp"],
                y=df_ad_time["anom_rate_roll"],
                mode="lines",
                line=dict(color=C_CORAL, width=2),
                fill="tozeroy",
                fillcolor="rgba(255,107,107,0.08)",
                hovertemplate="<b>%{x}</b><br>Rolling Anomaly Rate: %{y:.1f}%<extra></extra>",
            ))
            fig_rate = apply_theme(fig_rate, "Rolling Anomaly Rate % (window=50)", 320)
            fig_rate.update_layout(xaxis_title="Timestamp",
                                   yaxis_title="Anomaly Rate %")
            st.plotly_chart(fig_rate, use_container_width=True)
        else:
            st.info("Need more records for rolling anomaly rate chart.")

    # ── Anomaly Log Table ─────────────────────────────────────────
    # PURPOSE: Full sortable table of every detected anomaly so the
    # user can drill into individual records and export them.
    st.markdown('<div class="section-title">Anomaly Log</div>', unsafe_allow_html=True)

    if len(anom_df) > 0:
        log_cols = ["timestamp","area","zone",metric_col,
                    "anomaly_severity","anomaly_zscore_val",
                    "anomaly_zscore","anomaly_iqr","anomaly_rolling"]
        log_cols_present = [c for c in log_cols if c in anom_df.columns]
        anom_display = (
            anom_df[log_cols_present]
            .rename(columns={
                "anomaly_severity":   "Severity",
                "anomaly_zscore_val": "Z-Score",
                "anomaly_zscore":     "By Z-Score",
                "anomaly_iqr":        "By IQR",
                "anomaly_rolling":    "By Rolling-σ",
                metric_col:           f"{metric_col} ({unit_label})",
            })
            .sort_values("Severity",
                         key=lambda s: s.map({"HIGH":0,"MEDIUM":1,"LOW":2}))
            .reset_index(drop=True)
        )
        if "Z-Score" in anom_display.columns:
            anom_display["Z-Score"] = anom_display["Z-Score"].round(2)

        st.dataframe(
            anom_display,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Severity": st.column_config.TextColumn("Severity", width="small"),
                "Z-Score":  st.column_config.NumberColumn("Z-Score", format="%.2f"),
            },
        )
        st.caption(f"Showing {len(anom_display)} anomalous records out of {len(df_ad):,} total. "
                   f"Sorted by severity (HIGH first).")

        # Download button
        csv_bytes = anom_display.to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇️  Download Anomaly Log (CSV)",
            data=csv_bytes,
            file_name=f"anomalies_{stream_name.lower()}_{metric_col}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
        )
    else:
        st.markdown(
            '<div class="alert alert-success">✅ No anomalies detected in the current stream/filter/thresholds. '
            'Try lowering the Z-Score threshold or IQR multiplier for more sensitivity.</div>',
            unsafe_allow_html=True)

# ── Footer ────────────────────────────────────────────────────────
st.markdown("""
<div style="text-align:center;padding:2rem 0 1rem;color:#475569;font-size:0.75rem;">
    SmartCity Analytics Platform · Stage-4 Dashboard ·
    Apache Kafka + PySpark + Streamlit + Plotly · Real-Time Big Data Intelligence
</div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════
#  AUTO-REFRESH ENGINE  (runs AFTER full page render)
#
#  WHY IT'S HERE:
#    Calling st.rerun() during setup (before page body) causes an
#    infinite loop where Streamlit never finishes rendering.
#    Placing it at the bottom means: render fully → sleep → rerun.
#    This gives the browser a complete page on every cycle.
#
#  HOW IT WORKS:
#    1. session_state tracks last_mtime (newest output/ file timestamp)
#       and last_refresh_ts (wall-clock time of last forced rerun).
#    2. If output/ files are newer than last_mtime → new data arrived
#       from spark_streaming.py → clear cache and rerun immediately.
#    3. Otherwise wait until refresh_interval seconds have elapsed
#       then rerun regardless (catches delayed or partial writes).
#    4. st.empty() is used as a non-blocking sleep placeholder so
#       the page doesn't freeze while waiting.
# ══════════════════════════════════════════════════════════════════
if auto_refresh and is_realtime:
    # Initialise session state on first run
    if "last_mtime"      not in st.session_state: st.session_state.last_mtime      = 0.0
    if "last_refresh_ts" not in st.session_state: st.session_state.last_refresh_ts = time.time()
 
    current_mtime = latest_mtime()
 
    # New file detected — rerun immediately
    if current_mtime > st.session_state.last_mtime:
        st.session_state.last_mtime      = current_mtime
        st.session_state.last_refresh_ts = time.time()
        load_realtime_data.clear()
        st.rerun()
 
    # Timer-based fallback — rerun after interval
    elapsed = time.time() - st.session_state.last_refresh_ts
    remaining = refresh_interval - elapsed
 
    if remaining <= 0:
        st.session_state.last_refresh_ts = time.time()
        load_realtime_data.clear()
        st.rerun()
    else:
        # Show countdown and sleep; rerun when timer expires
        placeholder = st.empty()
        placeholder.markdown(
            f'<div style="position:fixed;bottom:1rem;right:1.5rem;'
            f'background:#111620;border:1px solid #1e2633;border-radius:8px;'
            f'padding:.4rem .9rem;font-size:.72rem;color:#64748b;">'
            f'🔄 Refreshing in {int(remaining)}s</div>',
            unsafe_allow_html=True)
        time.sleep(min(remaining, 5))   # sleep in 5s chunks so page stays responsive
        st.session_state.last_refresh_ts = time.time()
        load_realtime_data.clear()
        st.rerun()
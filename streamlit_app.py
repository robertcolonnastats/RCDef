"""
RCDef - Composite Defensive Metric
===================================
A comprehensive baseball defensive analytics tool combining:
- Statcast OAA, FRV, Arm Runs, Framing, Blocking, Sprint Speed
- Baseball Reference DRS (attributed to Sports Info Solutions)
- Original components: RRAA, BAP, Attempt Range with neighbor adjustment
- Composite RCDef (runs above average) and RCDef+ (percentile)

Data sources refresh automatically via GitHub Actions nightly during season.
Run locally: streamlit run rcdef_app.py
Deploy: Push to GitHub, connect Streamlit Community Cloud
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import requests
import io
import json
import os
import time
from datetime import datetime, date
from io import BytesIO
import warnings
warnings.filterwarnings('ignore')

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="RCDef | Defensive Analytics",
    page_icon="🧤",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Keep-alive: handled by GitHub Actions pinging the URL every 4 hours ──────
# See .github/workflows/refresh_data.yml
# No background thread needed — threads cause issues on Streamlit Cloud

# ─────────────────────────────────────────────
# STYLING
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=IBM+Plex+Mono:wght@300;400;500;600&family=IBM+Plex+Sans:wght@300;400;500;600&display=swap');

:root {
    --bg-primary: #0a0e1a;
    --bg-secondary: #111827;
    --bg-card: #1a2235;
    --bg-card-hover: #1f2a40;
    --accent-green: #00d084;
    --accent-red: #ff4757;
    --accent-yellow: #ffd32a;
    --accent-blue: #3498db;
    --accent-purple: #a29bfe;
    --text-primary: #e8eaf0;
    --text-secondary: #8892a4;
    --text-muted: #4a5568;
    --border: #1e2d42;
    --border-bright: #2d4060;
}

html, body, [class*="css"] {
    font-family: 'IBM Plex Sans', monospace;
    background-color: var(--bg-primary);
    color: var(--text-primary);
}

.stApp {
    background-color: var(--bg-primary);
}

/* Header */
.rcdef-header {
    background: linear-gradient(135deg, #0a0e1a 0%, #0d1829 50%, #0a0e1a 100%);
    border-bottom: 2px solid var(--accent-green);
    padding: 2rem 0 1.5rem 0;
    margin-bottom: 2rem;
    text-align: center;
    position: relative;
    overflow: hidden;
}

.rcdef-header::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0; bottom: 0;
    background: repeating-linear-gradient(
        90deg,
        transparent,
        transparent 40px,
        rgba(0, 208, 132, 0.03) 40px,
        rgba(0, 208, 132, 0.03) 41px
    );
    pointer-events: none;
}

.rcdef-logo {
    font-family: 'Bebas Neue', sans-serif;
    font-size: 5rem;
    letter-spacing: 0.15em;
    color: var(--accent-green);
    text-shadow: 0 0 40px rgba(0, 208, 132, 0.4);
    line-height: 1;
    margin-bottom: 0.25rem;
}

.rcdef-tagline {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.75rem;
    color: var(--text-secondary);
    letter-spacing: 0.3em;
    text-transform: uppercase;
}

/* Metric cards */
.metric-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 1.25rem 1.5rem;
    margin-bottom: 1rem;
    transition: border-color 0.2s;
}

.metric-card:hover {
    border-color: var(--border-bright);
}

.metric-label {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.65rem;
    color: var(--text-secondary);
    letter-spacing: 0.2em;
    text-transform: uppercase;
    margin-bottom: 0.4rem;
}

.metric-value {
    font-family: 'Bebas Neue', sans-serif;
    font-size: 2.5rem;
    line-height: 1;
    color: var(--text-primary);
}

.metric-value.positive { color: var(--accent-green); }
.metric-value.negative { color: var(--accent-red); }

/* Stat pill */
.stat-pill {
    display: inline-block;
    padding: 0.2rem 0.6rem;
    border-radius: 4px;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.75rem;
    font-weight: 500;
}
.pill-green { background: rgba(0,208,132,0.15); color: var(--accent-green); border: 1px solid rgba(0,208,132,0.3); }
.pill-red { background: rgba(255,71,87,0.15); color: var(--accent-red); border: 1px solid rgba(255,71,87,0.3); }
.pill-yellow { background: rgba(255,211,42,0.15); color: var(--accent-yellow); border: 1px solid rgba(255,211,42,0.3); }
.pill-blue { background: rgba(52,152,219,0.15); color: var(--accent-blue); border: 1px solid rgba(52,152,219,0.3); }
.pill-gray { background: rgba(72,85,104,0.3); color: var(--text-secondary); border: 1px solid var(--border); }

/* Section headers */
.section-header {
    font-family: 'Bebas Neue', sans-serif;
    font-size: 1.8rem;
    letter-spacing: 0.1em;
    color: var(--text-primary);
    border-left: 4px solid var(--accent-green);
    padding-left: 1rem;
    margin-bottom: 1.5rem;
}

/* Data status badge */
.data-status {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.65rem;
    padding: 0.3rem 0.8rem;
    border-radius: 3px;
    display: inline-block;
}
.status-live { background: rgba(0,208,132,0.1); color: var(--accent-green); border: 1px solid rgba(0,208,132,0.3); }
.status-cached { background: rgba(255,211,42,0.1); color: var(--accent-yellow); border: 1px solid rgba(255,211,42,0.3); }
.status-error { background: rgba(255,71,87,0.1); color: var(--accent-red); border: 1px solid rgba(255,71,87,0.3); }

/* Flag badge */
.flag-badge {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.6rem;
    padding: 0.15rem 0.5rem;
    border-radius: 3px;
    background: rgba(255,211,42,0.15);
    color: var(--accent-yellow);
    border: 1px solid rgba(255,211,42,0.3);
}

/* Reliability badge */
.rel-high { color: var(--accent-green); }
.rel-med { color: var(--accent-yellow); }
.rel-low { color: var(--accent-red); }

/* Sidebar */
section[data-testid="stSidebar"] {
    background: var(--bg-secondary);
    border-right: 1px solid var(--border);
}

/* Streamlit overrides */
.stSelectbox > div > div {
    background: var(--bg-card);
    border: 1px solid var(--border);
    color: var(--text-primary);
}

.stDataFrame {
    background: var(--bg-card);
}

div[data-testid="stMetricValue"] {
    font-family: 'Bebas Neue', sans-serif;
    font-size: 2rem;
}

.stTabs [data-baseweb="tab"] {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.8rem;
    letter-spacing: 0.1em;
}

hr {
    border-color: var(--border);
}

/* Player card */
.player-card-header {
    background: linear-gradient(135deg, var(--bg-card) 0%, #0d1829 100%);
    border: 1px solid var(--border-bright);
    border-radius: 12px;
    padding: 2rem;
    margin-bottom: 1rem;
}

.player-name {
    font-family: 'Bebas Neue', sans-serif;
    font-size: 3rem;
    letter-spacing: 0.05em;
    line-height: 1;
    color: var(--text-primary);
}

.player-meta {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.75rem;
    color: var(--text-secondary);
    letter-spacing: 0.15em;
    text-transform: uppercase;
    margin-top: 0.5rem;
}

/* Warning box */
.warn-box {
    background: rgba(255,211,42,0.08);
    border: 1px solid rgba(255,211,42,0.3);
    border-radius: 6px;
    padding: 0.75rem 1rem;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.72rem;
    color: var(--accent-yellow);
    margin: 0.5rem 0;
}

.info-box {
    background: rgba(52,152,219,0.08);
    border: 1px solid rgba(52,152,219,0.3);
    border-radius: 6px;
    padding: 0.75rem 1rem;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.72rem;
    color: var(--accent-blue);
    margin: 0.5rem 0;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────
CURRENT_YEARS = [2025, 2026]
MIN_INNINGS = 300
CACHE_VERSION = 4  # Increment this to bust all cached results
MIN_RRAA_ATTEMPTS = 50
DISAGREEMENT_THRESHOLD = 8
NEIGHBOR_STD_THRESHOLD = 1.0
NEIGHBOR_CREDIT_CAP = 0.30
SHIFT_BAN_YEAR = 2023

POSITIONS = {
    'C': 'Catcher',
    '1B': 'First Base',
    '2B': 'Second Base',
    '3B': 'Third Base',
    'SS': 'Shortstop',
    'LF': 'Left Field',
    'CF': 'Center Field',
    'RF': 'Right Field',
}

# Full team name → abbreviation (handles all Savant format variants)
TEAM_NAME_TO_ABBREV = {
    'Arizona Diamondbacks': 'ARI', 'D-backs': 'ARI', 'Arizona': 'ARI',
    'Atlanta Braves': 'ATL', 'Braves': 'ATL', 'Atlanta': 'ATL',
    'Baltimore Orioles': 'BAL', 'Orioles': 'BAL', 'Baltimore': 'BAL',
    'Boston Red Sox': 'BOS', 'Red Sox': 'BOS', 'Boston': 'BOS',
    'Chicago Cubs': 'CHC', 'Cubs': 'CHC',
    'Chicago White Sox': 'CWS', 'White Sox': 'CWS',
    'Cincinnati Reds': 'CIN', 'Reds': 'CIN', 'Cincinnati': 'CIN',
    'Cleveland Guardians': 'CLE', 'Guardians': 'CLE', 'Cleveland': 'CLE',
    'Colorado Rockies': 'COL', 'Rockies': 'COL', 'Colorado': 'COL',
    'Detroit Tigers': 'DET', 'Tigers': 'DET', 'Detroit': 'DET',
    'Houston Astros': 'HOU', 'Astros': 'HOU', 'Houston': 'HOU',
    'Kansas City Royals': 'KC', 'Royals': 'KC', 'Kansas City': 'KC',
    'Los Angeles Angels': 'LAA', 'Angels': 'LAA',
    'Los Angeles Dodgers': 'LAD', 'Dodgers': 'LAD',
    'Miami Marlins': 'MIA', 'Marlins': 'MIA', 'Miami': 'MIA',
    'Milwaukee Brewers': 'MIL', 'Brewers': 'MIL', 'Milwaukee': 'MIL',
    'Minnesota Twins': 'MIN', 'Twins': 'MIN', 'Minnesota': 'MIN',
    'New York Mets': 'NYM', 'Mets': 'NYM',
    'New York Yankees': 'NYY', 'Yankees': 'NYY',
    'Oakland Athletics': 'OAK', 'Athletics': 'OAK', 'Oakland': 'OAK',
    'Sacramento River Cats': 'OAK',  # AAA affiliate fallback
    'Philadelphia Phillies': 'PHI', 'Phillies': 'PHI', 'Philadelphia': 'PHI',
    'Pittsburgh Pirates': 'PIT', 'Pirates': 'PIT', 'Pittsburgh': 'PIT',
    'San Diego Padres': 'SD', 'Padres': 'SD', 'San Diego': 'SD',
    'Seattle Mariners': 'SEA', 'Mariners': 'SEA', 'Seattle': 'SEA',
    'San Francisco Giants': 'SF', 'Giants': 'SF', 'San Francisco': 'SF',
    'St. Louis Cardinals': 'STL', 'Cardinals': 'STL', 'St. Louis': 'STL',
    'Tampa Bay Rays': 'TB', 'Rays': 'TB', 'Tampa Bay': 'TB',
    'Texas Rangers': 'TEX', 'Rangers': 'TEX', 'Texas': 'TEX',
    'Toronto Blue Jays': 'TOR', 'Blue Jays': 'TOR', 'Toronto': 'TOR',
    'Washington Nationals': 'WSH', 'Nationals': 'WSH', 'Washington': 'WSH',
}

POSITION_GROUPS = {
    'Catcher': ['C'],
    'Infield': ['1B', '2B', '3B', 'SS'],
    'Outfield': ['LF', 'CF', 'RF'],
    'All': list(POSITIONS.keys())
}

TEAMS = [
    'ARI', 'ATL', 'BAL', 'BOS', 'CHC', 'CWS', 'CIN', 'CLE',
    'COL', 'DET', 'HOU', 'KC', 'LAA', 'LAD', 'MIA', 'MIL',
    'MIN', 'NYM', 'NYY', 'OAK', 'PHI', 'PIT', 'SD', 'SEA',
    'SF', 'STL', 'TB', 'TEX', 'TOR', 'WSH'
]

# Stadium correction factors (coordinate distortion)
# Based on published research on Gameday pixel bias
STADIUM_CORRECTIONS = {
    'STL': {'x_bias': -3.2, 'y_bias': 1.1},
    'KC': {'x_bias': -2.8, 'y_bias': 0.9},
    'LAA': {'x_bias': 1.4, 'y_bias': -0.7},
    'ARI': {'x_bias': 1.1, 'y_bias': -0.5},
}

# ─────────────────────────────────────────────
# DATA FETCHING
# ─────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_savant_oaa(year: int, position: str = 'all') -> pd.DataFrame:
    """
    Pull Outs Above Average from Baseball Savant.
    Uses statcast_outs_above_average from pybaseball for each position group,
    then falls back to direct HTTP. Returns empty DataFrame with debug info on failure.
    """
    SAVANT_HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Referer': 'https://baseballsavant.mlb.com/leaderboard/outs_above_average',
    }

    # pybaseball path — statcast_outs_above_average is the correct function
    # It does not support pos='all'; pull infield + outfield separately and combine
    try:
        from pybaseball import statcast_outs_above_average
        pos_groups = ['all', 4, 5, 6, 7, 8, 9, 3]  # all, 2B, 3B, SS, LF, CF, RF, 1B
        dfs = []
        # Try 'all' first
        for pos_code in pos_groups[:1]:
            try:
                df = statcast_outs_above_average(year, pos=pos_code, min_att=1)
                if df is not None and not df.empty and 'Host not in allowlist' not in str(df.columns):
                    dfs.append(df)
                    break
            except Exception:
                pass
        # If all worked, skip position-by-position
        if not dfs:
            for pos_code in pos_groups[1:]:
                try:
                    df = statcast_outs_above_average(year, pos=pos_code, min_att=1)
                    if df is not None and not df.empty and 'Host not in allowlist' not in str(df.columns):
                        dfs.append(df)
                except Exception:
                    pass
        if dfs:
            result = pd.concat(dfs, ignore_index=True)
            # Drop duplicates (player may appear in multiple position pulls)
            if 'player_id' in result.columns:
                result = result.drop_duplicates(subset=['player_id'], keep='first')
            result['data_year'] = year
            result['data_source'] = 'savant_oaa'
            return result
    except Exception:
        pass

    # Direct HTTP fallback — try multiple URL patterns
    url_attempts = [
        f"https://baseballsavant.mlb.com/leaderboard/outs_above_average?type=Fielder&year={year}&team=&range=year&min=1&pos=all&roles=&viz=show&csv=true",
        f"https://baseballsavant.mlb.com/leaderboard/outs_above_average?type=Fielder&year={year}&team=&range=year&min=q&pos=all&roles=&viz=show&csv=true",
    ]
    for url in url_attempts:
        try:
            session = requests.Session()
            # First hit the page to get cookies
            session.get('https://baseballsavant.mlb.com', headers=SAVANT_HEADERS, timeout=10)
            r = session.get(url, headers=SAVANT_HEADERS, timeout=25)
            if r.status_code == 200 and len(r.text) > 300:
                # Check it's actually CSV not HTML
                first_line = r.text.split('\n')[0]
                if 'last_name' in first_line or 'player_id' in first_line:
                    df = pd.read_csv(io.StringIO(r.text))
                    df['data_year'] = year
                    df['data_source'] = 'savant_oaa'
                    df['_http_status'] = r.status_code
                    return df
        except Exception:
            pass

    # Return empty df with debug metadata
    debug = pd.DataFrame({'_debug_note': [f'All fetch attempts failed for year={year}']})
    return debug


@st.cache_data(ttl=86400, show_spinner=False)
def test_savant_connection() -> dict:
    """
    Test connectivity to Baseball Savant. Called on load to diagnose demo mode.
    Returns dict with status info for each endpoint.
    """
    results = {}
    test_url = "https://baseballsavant.mlb.com/leaderboard/outs_above_average?type=Fielder&year=2025&team=&range=year&min=1&pos=all&roles=&viz=show&csv=true"
    try:
        r = requests.get(test_url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }, timeout=15)
        results['savant_status'] = r.status_code
        results['savant_bytes'] = len(r.text)
        results['savant_first_50'] = r.text[:50].replace('\n', ' ')
        results['is_csv'] = 'last_name' in r.text[:200] or 'player_id' in r.text[:200]
    except Exception as e:
        results['savant_error'] = str(e)
        results['savant_status'] = 0
    return results


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_savant_frv(year: int) -> pd.DataFrame:
    """
    Pull Fielding Run Value from Baseball Savant.
    FRV is on the OAA leaderboard as 'fielding_run_value' column.
    Also contains arm_runs, reaction_runs, positioning_runs.
    """
    try:
        from pybaseball import statcast_fielding
        df = statcast_fielding(year, pos='all', min_att=1)
        if df is not None and not df.empty and 'Host not in allowlist' not in str(df.columns):
            # FRV is included in OAA endpoint as fielding_run_value
            df['data_year'] = year
            df['data_source'] = 'savant_frv'
            return df
    except Exception:
        pass

    try:
        # FRV leaderboard endpoint
        url = (
            f"https://baseballsavant.mlb.com/leaderboard/outs_above_average"
            f"?type=Fielder&year={year}&team=&range=year&min=1&pos=all&roles=&viz=show&csv=true"
        )
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://baseballsavant.mlb.com/',
        }
        r = requests.get(url, headers=headers, timeout=20)
        if r.status_code == 200 and 'last_name' in r.text:
            df = pd.read_csv(io.StringIO(r.text))
            df['data_year'] = year
            df['data_source'] = 'savant_frv'
            return df
    except Exception:
        pass

    return pd.DataFrame()


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_savant_sprint_speed(year: int) -> pd.DataFrame:
    """
    Pull sprint speed via pybaseball (statcast_sprint_speed).
    Columns: last_name, first_name, player_id, year, team, sprint_speed, hp_to_1b, bolts.
    """
    try:
        from pybaseball import statcast_sprint_speed
        df = statcast_sprint_speed(year, min_opp=5)
        if df is not None and not df.empty and 'Host not in allowlist' not in str(df.columns):
            df['data_year'] = year
            df['data_source'] = 'savant_sprint'
            return df
    except Exception:
        pass

    try:
        url = (
            f"https://baseballsavant.mlb.com/leaderboard/sprint_speed"
            f"?year={year}&position=&team=&min=5&csv=true"
        )
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://baseballsavant.mlb.com/',
        }
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code == 200 and 'sprint_speed' in r.text:
            df = pd.read_csv(io.StringIO(r.text))
            df['data_year'] = year
            df['data_source'] = 'savant_sprint'
            return df
    except Exception:
        pass

    return pd.DataFrame()


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_savant_poptime(year: int) -> pd.DataFrame:
    """
    Pull catcher pop time / arm data via pybaseball.
    Columns: last_name, first_name, pop_2b_sba, exchange_2b_3b_sba, maxeff_arm_2b_3b_sba.
    """
    try:
        from pybaseball import statcast_fielding
        # poptime is a separate leaderboard
        url = (
            f"https://baseballsavant.mlb.com/leaderboard/poptime"
            f"?year={year}&team=&min2b=5&min3b=0&csv=true"
        )
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://baseballsavant.mlb.com/',
        }
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code == 200 and 'last_name' in r.text:
            df = pd.read_csv(io.StringIO(r.text))
            df['data_year'] = year
            df['data_source'] = 'savant_arm'
            return df
    except Exception:
        pass
    return pd.DataFrame()


# Keep old name as alias for compatibility
def fetch_savant_arm(year: int) -> pd.DataFrame:
    return fetch_savant_poptime(year)


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_savant_framing(year: int) -> pd.DataFrame:
    """
    Pull catcher framing data from Savant.
    Columns: last_name, first_name, runs_extra_strikes (= framing_runs), inn.
    """
    try:
        url = (
            f"https://baseballsavant.mlb.com/catcher_framing"
            f"?year={year}&team=&min=100&sort=4,1&csv=true"
        )
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://baseballsavant.mlb.com/',
        }
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code == 200 and 'last_name' in r.text:
            df = pd.read_csv(io.StringIO(r.text))
            df['data_year'] = year
            df['data_source'] = 'savant_framing'
            return df
    except Exception:
        pass
    return pd.DataFrame()


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_br_drs(year: int) -> pd.DataFrame:
    """
    Pull DRS from Baseball Reference.
    Data courtesy of Sports Info Solutions / Baseball Reference.
    Non-commercial use, attributed per fair use standards.
    """
    url = f"https://www.baseball-reference.com/leagues/majors/{year}-standard-fielding.shtml"
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; RCDef/1.0; baseball analytics)',
            'Accept': 'text/html,application/xhtml+xml'
        }
        r = requests.get(url, headers=headers, timeout=20)
        if r.status_code == 200:
            tables = pd.read_html(io.StringIO(r.text))
            for t in tables:
                if 'DRS' in t.columns or 'Rdrs' in t.columns:
                    t['data_year'] = year
                    t['data_source'] = 'baseball_reference'
                    return t
    except Exception:
        pass
    return pd.DataFrame()


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_statcast_play_by_play(year: int) -> pd.DataFrame:
    """
    Pull raw Statcast play-by-play for RRAA and BAP calculations.
    Uses pybaseball's statcast function with date ranges.
    Large dataset - cached aggressively.
    """
    try:
        from pybaseball import statcast
        # Pull in monthly chunks to manage memory
        dfs = []
        # Regular season approximate date ranges
        date_ranges = [
            (f'{year}-03-20', f'{year}-04-30'),
            (f'{year}-05-01', f'{year}-06-30'),
            (f'{year}-07-01', f'{year}-08-31'),
            (f'{year}-09-01', f'{year}-10-05'),
        ]
        for start, end in date_ranges:
            try:
                chunk = statcast(start_dt=start, end_dt=end)
                if chunk is not None and not chunk.empty:
                    dfs.append(chunk)
                time.sleep(2)  # Rate limiting
            except Exception:
                continue
        if dfs:
            return pd.concat(dfs, ignore_index=True)
    except Exception:
        pass
    return pd.DataFrame()


# ─────────────────────────────────────────────
# DATA ORCHESTRATION
# ─────────────────────────────────────────────

def get_data_status(df: pd.DataFrame, source_name: str) -> dict:
    """Returns status info for a data source."""
    if df is None or df.empty:
        return {'status': 'error', 'rows': 0, 'source': source_name}
    return {'status': 'live', 'rows': len(df), 'source': source_name}


def normalize_dtypes(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert all non-standard dtypes to numpy float64/object.
    Handles:
    - Arrow-backed: 'double[pyarrow]', 'int64[pyarrow]' etc.
    - Pandas nullable: 'Int64', 'Float64', 'boolean' etc.
    - object columns that are actually numeric
    All are incompatible with standard pandas arithmetic in pandas 3.x.
    """
    for col in df.columns:
        try:
            dtype = df[col].dtype
            dtype_str = str(dtype)

            is_nonstandard = (
                'pyarrow' in dtype_str          # Arrow types
                or 'ArrowDtype' in dtype_str     # Arrow wrapper
                or dtype_str in ('Int8','Int16','Int32','Int64',
                                 'UInt8','UInt16','UInt32','UInt64',
                                 'Float32','Float64','boolean')  # Pandas nullable
            )

            if is_nonstandard:
                # Convert to plain numpy float64 (NaN for missing)
                df[col] = pd.to_numeric(df[col], errors='coerce').astype('float64')

            elif dtype == object:
                # Try numeric conversion for object columns
                converted = pd.to_numeric(df[col], errors='coerce')
                non_null_orig = df[col].notna().sum()
                if non_null_orig > 0 and converted.notna().sum() >= non_null_orig * 0.5:
                    df[col] = converted.astype('float64')

        except Exception:
            pass
    return df


def standardize_player_name(name: str) -> str:
    """Normalize player names for merging across sources."""
    if pd.isna(name):
        return ''
    name = str(name).strip()
    # Remove suffixes
    for suffix in [' Jr.', ' Sr.', ' II', ' III', ' IV']:
        name = name.replace(suffix, '')
    return name.lower().strip()


def combine_savant_name(df: pd.DataFrame) -> pd.DataFrame:
    """
    Handle ALL Savant CSV name formats:

    Format A (old/current): quoted combined column
      Header: "last_name, first_name"   Value: "Carroll, Corbin"
      pandas reads as single col named: 'last_name, first_name'

    Format B (some endpoints): two separate columns
      Headers: 'last_name'  ' first_name'  (note leading space)
      After strip: 'last_name' + 'first_name'

    Format C: already a 'player_name' column — do nothing.
    """
    # Always strip whitespace from column names first
    df.columns = df.columns.str.strip()

    if 'player_name' in df.columns:
        # Format C — already done
        return df

    # Format A: single combined column "last_name, first_name"
    combined = 'last_name, first_name'
    if combined in df.columns:
        def split_combined(val):
            if pd.isna(val):
                return val
            val = str(val).strip()
            if ',' in val:
                parts = val.split(',', 1)
                return f"{parts[1].strip()} {parts[0].strip()}"
            return val
        df['player_name'] = df[combined].apply(split_combined)
        df = df.drop(columns=[combined], errors='ignore')
        return df

    # Format B: separate last_name + first_name (with or without leading space already stripped)
    if 'last_name' in df.columns and 'first_name' in df.columns:
        df['player_name'] = df['first_name'].str.strip() + ' ' + df['last_name'].str.strip()
        df = df.drop(columns=['last_name', 'first_name'], errors='ignore')
        return df

    # Fallback: look for any recognizable name column
    for c in df.columns:
        if c.lower() in ['name', 'player', 'playername']:
            df['player_name'] = df[c]
            return df

    return df


def standardize_columns(df: pd.DataFrame, source: str) -> pd.DataFrame:
    """
    Standardize column names across different Savant/BR endpoints.
    Step 1: strip whitespace from all column names (Savant adds leading spaces).
    Step 2: combine last_name + first_name into player_name.
    Step 3: rename to canonical column names.
    """
    if df.empty:
        return df

    # Always strip column name whitespace first — Savant CSV quirk
    df.columns = df.columns.str.strip()

    # Combine name columns
    df = combine_savant_name(df)

    col_maps = {
        'savant_oaa': {
            'outs_above_average': 'oaa',
            'fielding_run_value': 'frv',
            'fielding_runs_prevented': 'frv',
            # Team — all known Savant column names
            'team_name_alt':     'team',
            'team_name_abbrev':  'team',
            'team_abbreviation': 'team',
            'display_team_name': 'team_long',
            'team_name':         'team_long',
            'primary_pos_formatted': 'position',
            # Innings — all known column name variants
            'inn':            'innings',
            'innings_played': 'innings',
            'total_innings':  'innings',
            # Attempts
            'attempts': 'oaa_attempts',
            'n_att':    'oaa_attempts',
        },
        'savant_frv': {
            'fielding_run_value': 'frv',
            'team_name_alt':     'team',
            'team_name_abbrev':  'team',
            'team_abbreviation': 'team',
            'display_team_name': 'team_long',
            'team_name':         'team_long',
            'primary_pos_formatted': 'position',
            'inn':            'innings',
            'innings_played': 'innings',
            'attempts':       'oaa_attempts',
        },
        'savant_sprint': {
            # sprint speed uses 'team' directly, no _alt suffix
            'sprint_speed': 'sprint_speed',
        },
        'savant_arm': {
            # poptime endpoint
            'pop_2b_sba': 'pop_time',
            'exchange_2b_3b_sba': 'exchange_time',
            'maxeff_arm_2b_3b_sba': 'arm_strength',
        },
        'savant_framing': {
            'runs_extra_strikes': 'framing_runs',
            'team_name_alt': 'team',
            'inn': 'innings',
        },
    }

    source_map = col_maps.get(source, {})
    df = df.rename(columns=source_map)

    # Drop duplicate columns that may arise from multiple aliases mapping to same canonical name
    df = df.loc[:, ~df.columns.duplicated(keep='first')]

    # Normalize team column: convert full names to abbreviations
    if 'team' in df.columns:
        df['team'] = df['team'].apply(
            lambda t: TEAM_NAME_TO_ABBREV.get(str(t).strip(), str(t).strip()) if pd.notna(t) else t
        )
    elif 'team_long' in df.columns:
        # team_long has full name — create abbreviation team column from it
        df['team'] = df['team_long'].apply(
            lambda t: TEAM_NAME_TO_ABBREV.get(str(t).strip(), str(t).strip()[:3].upper()) if pd.notna(t) else t
        )

    # Ensure innings is numeric; if missing entirely, set to 0 for now
    # (will be estimated from attempts in build_master_dataset)
    if 'innings' in df.columns:
        df['innings'] = pd.to_numeric(df['innings'], errors='coerce').fillna(0)

    return df


# ─────────────────────────────────────────────
# METRIC CALCULATIONS
# ─────────────────────────────────────────────

def calculate_stadium_correction(df: pd.DataFrame) -> pd.DataFrame:
    """Apply stadium coordinate bias correction."""
    if 'team' not in df.columns:
        df['stadium_correction'] = 0.0
        return df

    def get_correction(team):
        if team in STADIUM_CORRECTIONS:
            corr = STADIUM_CORRECTIONS[team]
            # Convert coordinate bias to approximate run impact
            # Simplified: bias in degrees * position-specific sensitivity
            return round(corr['x_bias'] * 0.12, 3)
        return 0.0

    df['stadium_correction'] = df['team'].apply(get_correction)
    return df


def calculate_attempt_range_score(df: pd.DataFrame, raw_statcast: pd.DataFrame) -> pd.DataFrame:
    """
    Attempt Range Score (ARS):
    Measures whether a fielder expands or shrinks their opportunity set
    relative to league expectation. Includes neighbor adjustment.

    When raw Statcast is unavailable, estimates from OAA attempt data.
    """
    if 'oaa_attempts' not in df.columns:
        df['attempt_range_score'] = np.nan
        df['neighbor_flag'] = False
        df['neighbor_suppression'] = False
        df['neighbor_vacuum'] = False
        return df

    # League average attempts by position (estimated from historical Statcast)
    # These get recalculated from raw data when available
    league_avg_attempts = {
        'C': 85, '1B': 120, '2B': 280, '3B': 220,
        'SS': 310, 'LF': 240, 'CF': 310, 'RF': 250
    }

    df['attempt_range_score'] = np.nan
    df['neighbor_flag'] = False
    df['neighbor_suppression'] = False
    df['neighbor_vacuum'] = False

    if 'position' not in df.columns or 'innings' not in df.columns:
        return df

    for pos in df['position'].unique():
        pos_mask = df['position'] == pos
        pos_df = df[pos_mask].copy()

        if pos_df.empty or pos not in league_avg_attempts:
            continue

        # Normalize attempts to 162-game equivalent
        avg_inn_per_game = 8.5
        games_equiv = pos_df['innings'] / avg_inn_per_game
        games_equiv = games_equiv.clip(lower=1)
        expected_attempts = league_avg_attempts[pos] * (games_equiv / 162)

        # Attempt rate vs expectation
        attempt_rate = pos_df['oaa_attempts'] / expected_attempts.clip(lower=1)
        mean_rate = attempt_rate.mean()
        std_rate = attempt_rate.std()

        if std_rate > 0:
            z_score = (attempt_rate - mean_rate) / std_rate
        else:
            z_score = pd.Series(0, index=pos_df.index)

        # Convert to run value (each attempt above average ~ 0.12 runs)
        ars = (pos_df['oaa_attempts'] - expected_attempts) * 0.12
        df.loc[pos_mask, 'attempt_range_score'] = ars.values

        # Neighbor vacuum flag: fielder's attempt rate significantly above average
        # (they may be filling space from a poor neighbor)
        vacuum_flag = z_score > NEIGHBOR_STD_THRESHOLD
        df.loc[pos_mask[pos_mask].index[vacuum_flag], 'neighbor_vacuum'] = True
        df.loc[pos_mask[pos_mask].index[vacuum_flag], 'neighbor_flag'] = True

    return df


def calculate_rraa_proxy(df: pd.DataFrame, raw_statcast: pd.DataFrame) -> pd.DataFrame:
    """
    Receiving Runs Above Average (RRAA) - First Base Only.

    When raw Statcast play-by-play is available: calculate from throw location
    and outcome data (dirt balls, wide throws, high throws, stretch plays).

    When unavailable: returns NaN for non-1B, estimate from defensive
    metrics for 1B.

    Full methodology:
    1. Classify each throw to 1B by type (dirt/low, wide, high, routine)
    2. Calculate expected catch probability for each throw type
       based on throw characteristics (velocity, deviation from target)
    3. Credit = actual_outcome - expected_probability
    4. Threshold: throws > 3 SD from mean assigned 0 fielder responsibility
    5. Convert to runs using run expectancy
    """
    df['rraa'] = np.nan
    df['rraa_attempts'] = np.nan
    df['rraa_eligible'] = False

    first_base_mask = df['position'] == '1B' if 'position' in df.columns else pd.Series(False, index=df.index)
    df.loc[first_base_mask, 'rraa_eligible'] = True

    if raw_statcast.empty:
        # Estimate RRAA from available defensive metrics for 1B
        # When OAA and FRV are both available, the difference partially reflects receiving
        if all(c in df.columns for c in ['oaa', 'frv']):
            frv_oaa_diff = df.get('frv', 0) - df.get('oaa', 0)
            # Receiving quality is partially captured in FRV but not OAA
            # FRV - OAA delta for 1B correlates with receiving ability
            estimated_rraa = frv_oaa_diff * 0.35  # Conservative partial attribution
            df.loc[first_base_mask, 'rraa'] = estimated_rraa[first_base_mask]
            df.loc[first_base_mask, 'rraa_attempts'] = 999  # Flag as estimated

        return df

    # Full RRAA calculation from raw Statcast
    try:
        # Filter to throws to first base
        throws_to_first = raw_statcast[
            raw_statcast.get('hit_location', pd.Series()).isin([3]) |
            (raw_statcast.get('events', pd.Series()) == 'field_out')
        ].copy()

        if throws_to_first.empty:
            return df

        # Classify throw difficulty
        # plate_z and plate_x give throw location for fielded balls
        if all(c in throws_to_first.columns for c in ['plate_x', 'plate_z', 'fielder_3']):
            # Calculate deviation from ideal target
            throws_to_first['throw_deviation'] = np.sqrt(
                throws_to_first['plate_x']**2 +
                (throws_to_first['plate_z'] - 3.0)**2
            )

            # Threshold: beyond 3 SD = not fielder's responsibility
            mean_dev = throws_to_first['throw_deviation'].mean()
            std_dev = throws_to_first['throw_deviation'].std()
            throws_to_first['fielder_responsibility'] = (
                throws_to_first['throw_deviation'] < (mean_dev + 3 * std_dev)
            ).astype(float)

            # Expected catch probability by deviation (sigmoid model)
            # Based on historical catch rates by throw difficulty
            max_dev = throws_to_first['throw_deviation'].quantile(0.95)
            normalized_dev = (throws_to_first['throw_deviation'] / max_dev).clip(0, 1)
            throws_to_first['exp_catch_prob'] = (
                0.98 - 0.35 * normalized_dev
            ) * throws_to_first['fielder_responsibility']

            # Actual outcome
            throws_to_first['actual_out'] = (
                throws_to_first.get('events', '') == 'field_out'
            ).astype(float)

            # Credit per play
            throws_to_first['play_credit'] = (
                throws_to_first['actual_out'] - throws_to_first['exp_catch_prob']
            ) * throws_to_first['fielder_responsibility']

            # Aggregate by first baseman
            if 'fielder_3' in throws_to_first.columns:
                rraa_by_player = throws_to_first.groupby('fielder_3').agg(
                    rraa_raw=('play_credit', 'sum'),
                    rraa_attempts=('play_credit', 'count')
                ).reset_index()

                # Convert to runs (each play worth ~0.4 runs on average)
                rraa_by_player['rraa'] = rraa_by_player['rraa_raw'] * 0.4

                # Merge back - need player ID mapping
                # This requires fielder_3 to map to player names
                # Simplified merge on available ID columns
                pass

    except Exception:
        pass

    return df


def calculate_bap(df: pd.DataFrame, raw_statcast: pd.DataFrame) -> pd.DataFrame:
    """
    Baserunner Advancement Prevention (BAP).

    Measures how well a fielder suppresses extra-base advancement
    through positioning/speed AND arm strength combined.

    Separate from Arm Runs (which measures direct throwing value).
    BAP captures the deterrence effect and positioning speed component.

    Full methodology:
    1. Identify all baserunner advancement opportunities per fielder
    2. Calculate expected advancement rate from:
       - Ball type/location
       - Runner speed
       - Runner starting base
       - Outs
       - Run state
    3. Credit = expected_advancement_rate - actual_advancement_rate
    4. Two sub-components:
       a. Positioning BAP: fielder reached ball faster than average
       b. Deterrence BAP: runner didn't attempt based on fielder reputation
    5. Convert to runs via run expectancy
    """
    df['bap'] = np.nan

    if raw_statcast.empty:
        # Estimate from OAA + arm data when full Statcast unavailable
        # BAP correlates with OAA efficiency and arm strength
        oaa = df.get('oaa', pd.Series(0, index=df.index)).fillna(0)
        arm = df.get('arm_runs', pd.Series(0, index=df.index)).fillna(0)
        # Conservative estimate: BAP = 15% of OAA value + 20% of arm value
        # Partial attribution since both metrics already capture some of this
        df['bap'] = (oaa * 0.15 + arm * 0.20).round(2)
        return df

    try:
        # Filter to plays with baserunner advancement opportunities
        advancement_plays = raw_statcast[
            raw_statcast.get('on_1b', pd.Series()).notna() |
            raw_statcast.get('on_2b', pd.Series()).notna() |
            raw_statcast.get('on_3b', pd.Series()).notna()
        ].copy()

        if advancement_plays.empty:
            return df

        # Calculate expected advancement rates
        # (simplified model - full model requires runner tracking data)
        if 'hit_distance_sc' in advancement_plays.columns:
            # Normalize by distance - deeper balls = more advancement expected
            advancement_plays['exp_advancement'] = (
                advancement_plays['hit_distance_sc'].clip(0, 450) / 450 * 0.6
            )

            # Actual advancement from delta_home_win_exp or base state change
            # This requires comparing pre/post base states
            if all(c in advancement_plays.columns for c in ['pre_runner_1b', 'pre_runner_2b', 'pre_runner_3b']):
                pass  # Full implementation with base state tracking

    except Exception:
        pass

    return df


def calculate_arm_runs(df: pd.DataFrame) -> pd.DataFrame:
    """
    Arm Runs: Direct throwing value.
    Separate from BAP which captures deterrence/positioning.

    Sources:
    - Outfielders: Savant arm value leaderboard
    - Infielders: Derived from assist/error data and throw velocity
    - Catchers: Pop time converted to run value
    """
    if 'arm_runs' not in df.columns:
        df['arm_runs'] = np.nan

    # Catchers: convert pop time to run value
    # League average pop time ~2.0 sec; each 0.1 sec below = ~0.8 runs
    if 'pop_time' in df.columns:
        catcher_mask = df.get('position', '') == 'C'
        league_avg_pop = 2.00
        pop_diff = league_avg_pop - df.loc[catcher_mask, 'pop_time'].fillna(league_avg_pop)
        df.loc[catcher_mask, 'arm_runs'] = (pop_diff * 8.0).clip(-15, 15)

    return df


def calculate_rcdef(df: pd.DataFrame) -> pd.DataFrame:
    """
    RCDef: Composite defensive metric in runs above average.

    RCDef = CR + ARS + RRAA(1B) + BAP + ARM + SC

    Where:
    CR  = Conversion Runs (from OAA/FRV)
    ARS = Attempt Range Score
    RRAA= Receiving Runs Above Average (1B only)
    BAP = Baserunner Advancement Prevention
    ARM = Arm Runs
    SC  = Stadium Correction
    """
    # Conversion Runs: average of OAA (in runs) and FRV where both available
    # OAA is in outs; convert using ~0.75 runs/out for infielders, ~0.55 for OF
    position_run_weights = {
        'C': 0.65, '1B': 0.65, '2B': 0.73, '3B': 0.72,
        'SS': 0.74, 'LF': 0.57, 'CF': 0.56, 'RF': 0.57
    }

    def get_run_weight(pos):
        return position_run_weights.get(pos, 0.65)

    if 'position' in df.columns:
        run_weights = df['position'].apply(get_run_weight)
    else:
        run_weights = pd.Series(0.65, index=df.index)

    # Conversion Runs from OAA
    oaa_col = df.get('oaa', pd.Series(np.nan, index=df.index))
    frv_col = df.get('frv', pd.Series(np.nan, index=df.index))

    # If both available, weight-average FRV (already in runs) and OAA*weight
    oaa_runs = oaa_col * run_weights
    cr_values = []
    for i in df.index:
        oaa_val = oaa_runs.get(i, np.nan) if isinstance(oaa_runs, pd.Series) else np.nan
        frv_val = frv_col.get(i, np.nan) if isinstance(frv_col, pd.Series) else np.nan
        if pd.notna(oaa_val) and pd.notna(frv_val):
            cr_values.append(round((oaa_val * 0.5 + frv_val * 0.5), 2))
        elif pd.notna(frv_val):
            cr_values.append(round(frv_val, 2))
        elif pd.notna(oaa_val):
            cr_values.append(round(oaa_val, 2))
        else:
            cr_values.append(np.nan)

    df['conversion_runs'] = cr_values

    # Sum components
    components = ['conversion_runs', 'attempt_range_score', 'bap', 'arm_runs', 'stadium_correction']
    # Add RRAA for 1B
    if 'rraa' in df.columns:
        components.append('rraa')

    # Build RCDef from available components
    rcdef_vals = pd.Series(0.0, index=df.index, dtype='float64')
    component_counts = pd.Series(0, index=df.index, dtype='int64')

    for comp in components:
        if comp in df.columns:
            # Explicit float64 cast — guards against Arrow dtype TypeError in pandas 3.x
            comp_vals = pd.to_numeric(df[comp], errors='coerce').astype('float64')
            valid = comp_vals.notna()
            rcdef_vals[valid] = rcdef_vals[valid] + comp_vals[valid]
            component_counts[valid] = component_counts[valid] + 1

    df['rcdef'] = rcdef_vals.where(component_counts > 0, np.nan).round(2)

    return df


def calculate_rcdef_plus(df: pd.DataFrame) -> pd.DataFrame:
    """
    RCDef+: Position-specific percentile (0-100).
    50 = average. 100 = best at position. 0 = worst.
    Uses method='min' so tied players share the lower rank (no ties at 100).
    Stored as float with 1 decimal so leaderboard sort is stable.
    """
    df['rcdef_plus'] = np.nan

    if 'rcdef' not in df.columns or 'position' not in df.columns:
        return df

    for pos in df['position'].unique():
        mask = df['position'] == pos
        pos_vals = pd.to_numeric(df.loc[mask, 'rcdef'], errors='coerce').dropna()
        if len(pos_vals) < 3:
            continue
        n = len(pos_vals)
        ranks = pos_vals.rank(method='first')
        pct = ((ranks - 1) / (n - 1) * 100).round(1) if n > 1 else pd.Series(50.0, index=pos_vals.index)
        df.loc[pct.index, 'rcdef_plus'] = pct.astype('float64')

    return df


def calculate_reliability(df: pd.DataFrame) -> pd.DataFrame:
    """
    Reliability indicator: Low / Medium / High
    Based on innings played and number of data sources available.
    """
    def get_reliability(row):
        innings = row.get('innings', 0) or 0
        sources = sum([
            pd.notna(row.get('oaa')),
            pd.notna(row.get('frv')),
            pd.notna(row.get('drs')),
            pd.notna(row.get('arm_runs')),
        ])

        if innings >= 900 and sources >= 3:
            return 'High'
        elif innings >= 500 and sources >= 2:
            return 'Medium'
        else:
            return 'Low'

    df['reliability'] = df.apply(get_reliability, axis=1)
    return df


def oaa_to_runs(oaa_series: pd.Series, position_series: pd.Series) -> pd.Series:
    """
    Convert OAA (outs) to runs using position-specific weights.
    OAA is measured in outs above average; DRS and FRV are in runs.
    Must convert to the same currency before comparing.
    """
    weights = {
        'C': 0.65, '1B': 0.65, '2B': 0.73, '3B': 0.72,
        'SS': 0.74, 'LF': 0.57, 'CF': 0.56, 'RF': 0.57
    }
    if position_series is not None and len(position_series) == len(oaa_series):
        w = position_series.map(weights).fillna(0.65)
    else:
        w = pd.Series(0.65, index=oaa_series.index)
    return oaa_series * w


def calculate_disagreement_flag(df: pd.DataFrame) -> pd.DataFrame:
    """
    Flag players where top two input metrics diverge > DISAGREEMENT_THRESHOLD runs.
    All metrics converted to runs before comparison:
    - OAA (outs) → runs via position-specific weight
    - FRV already in runs
    - DRS already in runs
    """
    df['disagreement_flag'] = False
    df['disagreement_detail'] = ''

    pos_series = df.get('position', None)

    # Build runs-equivalent versions of each metric
    # Cast to float64 to avoid Arrow dtype issues
    metrics_in_runs = {}
    if 'oaa' in df.columns:
        metrics_in_runs['OAA'] = oaa_to_runs(
            pd.to_numeric(df['oaa'], errors='coerce').fillna(0).astype('float64'), pos_series)
    if 'frv' in df.columns:
        metrics_in_runs['FRV'] = pd.to_numeric(df['frv'], errors='coerce').fillna(0).astype('float64')
    if 'drs' in df.columns:
        metrics_in_runs['DRS'] = pd.to_numeric(df['drs'], errors='coerce').fillna(0).astype('float64')

    # Compare every pair
    metric_names = list(metrics_in_runs.keys())
    for i in range(len(metric_names)):
        for j in range(i + 1, len(metric_names)):
            m1_name = metric_names[i]
            m2_name = metric_names[j]
            m1_vals = metrics_in_runs[m1_name]
            m2_vals = metrics_in_runs[m2_name]

            # Only compare where both metrics are actually available (non-zero/non-null in original)
            m1_orig = df.get(m1_name.lower(), pd.Series(dtype=float))
            m2_orig = df.get(m2_name.lower(), pd.Series(dtype=float))
            both_valid = m1_orig.notna() & m2_orig.notna()

            diff = (m1_vals - m2_vals).abs()
            flagged = (diff > DISAGREEMENT_THRESHOLD) & both_valid
            df.loc[flagged, 'disagreement_flag'] = True
            # Add clean detail string with the actual run difference
            for idx in df.index[flagged]:
                d = round(float(diff.loc[idx]), 1)
                df.loc[idx, 'disagreement_detail'] += f'{m1_name} vs {m2_name} ({d} run gap) | '

    return df


# ─────────────────────────────────────────────
# MASTER DATA PIPELINE
# ─────────────────────────────────────────────

@st.cache_data(ttl=1800, show_spinner=False)
def build_master_dataset(year: int, _cache_version: int = CACHE_VERSION):
    """
    Master pipeline: fetch all sources, calculate all metrics, return unified dataset.
    Returns (dataframe, status_dict). NEVER raises — always returns valid data.
    """
    status = {'mode': 'demo', 'last_updated': 'unknown'}
    try:
        result_df, result_status = _build_master_dataset_inner(year)
        # If pipeline succeeded in live mode, remove any stale demo_reason
        if result_status.get('mode') == 'live':
            result_status.pop('demo_reason', None)
            result_status.pop('traceback', None)
        return result_df, result_status
    except Exception as e:
        import traceback as tb
        status['mode'] = 'demo'
        status['demo_reason'] = f'Exception: {type(e).__name__}: {str(e)[:200]}'
        status['traceback'] = tb.format_exc()[-800:]
        status['last_updated'] = 'error'
        try:
            return build_demo_dataset(year), status
        except Exception:
            return build_demo_dataset(2025), status


def _build_master_dataset_inner(year: int):
    """Inner pipeline — called by build_master_dataset with exception wrapper."""
    status = {}
    status['cache_version'] = CACHE_VERSION

    oaa_df = fetch_savant_oaa(year)
    status['oaa'] = get_data_status(oaa_df, 'Baseball Savant OAA')

    frv_df = fetch_savant_frv(year)
    status['frv'] = get_data_status(frv_df, 'Baseball Savant FRV')

    speed_df = fetch_savant_sprint_speed(year)
    status['sprint'] = get_data_status(speed_df, 'Baseball Savant Sprint Speed')

    arm_df = fetch_savant_arm(year)
    status['arm'] = get_data_status(arm_df, 'Baseball Savant Arm')

    framing_df = fetch_savant_framing(year)
    status['framing'] = get_data_status(framing_df, 'Baseball Savant Framing')

    drs_df = fetch_br_drs(year)
    status['drs'] = get_data_status(drs_df, 'Baseball Reference / SIS DRS')

    # Standardize all dataframes — strip whitespace from columns, combine name fields
    def prep(df, source):
        if df.empty:
            return df
        return standardize_columns(df, source)

    oaa_df     = prep(oaa_df,     'savant_oaa')
    frv_df     = prep(frv_df,     'savant_frv')
    speed_df   = prep(speed_df,   'savant_sprint')
    arm_df     = prep(arm_df,     'savant_arm')
    framing_df = prep(framing_df, 'savant_framing')

    # Log column schemas for diagnostics download
    status['oaa_cols']     = list(oaa_df.columns)     if not oaa_df.empty     else []
    status['frv_cols']     = list(frv_df.columns)     if not frv_df.empty     else []
    status['speed_cols']   = list(speed_df.columns)   if not speed_df.empty   else []
    status['arm_cols']     = list(arm_df.columns)     if not arm_df.empty     else []
    status['framing_cols'] = list(framing_df.columns) if not framing_df.empty else []

    def has_players(df):
        """Check df has meaningful player data."""
        return (
            not df.empty and
            'player_name' in df.columns and
            len(df) > 3 and
            df['player_name'].notna().sum() > 3
        )

    def pick_col(df, options):
        """Return first matching column name from options list."""
        for opt in options:
            if opt in df.columns:
                return opt
        return None

    # Build base dataframe from OAA (most complete player list).
    # The Savant OAA endpoint also contains FRV, arm_runs, sprint_speed
    # in the same CSV response — extract everything in one pass.
    if has_players(oaa_df):
        base_df = oaa_df.copy()
        # Canonical column mapping — the OAA endpoint has many columns
        for canonical, options in {
            # team: use abbreviation if available, fall back to full name
            'team':         ['team', 'team_name_alt', 'team_name_abbrev', 'team_abbreviation', 'team_long', 'display_team_name', 'team_name'],
            'position':     ['position', 'primary_pos_formatted', 'pos'],
            'innings':      ['innings', 'inn'],
            'oaa':          ['oaa', 'outs_above_average'],
            'oaa_attempts': ['oaa_attempts', 'attempts', 'n_attempts', 'n_att'],
            'frv':          ['frv', 'fielding_run_value', 'fielding_runs_prevented'],
            'arm_runs':     ['arm_runs'],
            'sprint_speed': ['sprint_speed'],
        }.items():
            existing = pick_col(base_df, options)
            if existing and existing != canonical:
                base_df[canonical] = base_df[existing]
        # Keep only canonical columns that exist
        keep = ['player_name', 'data_year', 'team', 'position', 'innings',
                'oaa', 'oaa_attempts', 'frv', 'arm_runs', 'sprint_speed']
        base_df = base_df[[c for c in keep if c in base_df.columns]].copy()
        status['mode'] = 'live'
        status['base_source'] = 'Savant OAA'

    elif has_players(frv_df):
        base_df = frv_df.copy()
        for canonical, options in {
            'team':     ['team', 'team_name_alt'],
            'position': ['position', 'primary_pos_formatted', 'pos'],
            'innings':  ['innings', 'inn'],
            'frv':      ['frv', 'fielding_run_value'],
            'oaa':      ['oaa', 'outs_above_average'],
        }.items():
            existing = pick_col(base_df, options)
            if existing and existing != canonical:
                base_df[canonical] = base_df[existing]
        keep = ['player_name', 'data_year', 'team', 'position', 'innings', 'frv', 'oaa']
        base_df = base_df[[c for c in keep if c in base_df.columns]].copy()
        status['mode'] = 'live'
        status['base_source'] = 'Savant FRV'

    else:
        try:
            empty_df = build_demo_dataset(year)
        except Exception:
            empty_df = build_demo_dataset(2025)  # absolute fallback
        status['mode'] = 'demo'
        oaa_rows = status.get('oaa', {}).get('rows', 0)
        frv_rows = status.get('frv', {}).get('rows', 0)
        oaa_cols = status.get('oaa_cols', [])[:5]
        pname_oaa = 'YES' if has_players(oaa_df) else 'NO'
        pname_frv = 'YES' if has_players(frv_df) else 'NO'
        status['demo_reason'] = (
            f"OAA: {oaa_rows} rows, player_name={pname_oaa} | "
            f"FRV: {frv_rows} rows, player_name={pname_frv} | "
            f"OAA cols: {oaa_cols}"
        )
        return empty_df, status

    # Ensure required columns exist with NaN defaults
    for col in ['oaa', 'frv', 'oaa_attempts', 'arm_runs', 'sprint_speed',
                'framing_runs', 'drs']:
        if col not in base_df.columns:
            base_df[col] = np.nan

    # Merge FRV if not already in base from OAA endpoint
    if base_df['frv'].notna().sum() == 0 and has_players(frv_df):
        frv_df_std = standardize_columns(frv_df.copy(), 'savant_frv')
        if 'frv' in frv_df_std.columns and 'player_name' in frv_df_std.columns:
            frv_merge = frv_df_std[['player_name', 'frv']].drop_duplicates('player_name')
            base_df = base_df.merge(frv_merge, on='player_name', how='left', suffixes=('', '_frv2'))
            if 'frv_frv2' in base_df.columns:
                base_df['frv'] = base_df['frv_frv2'].fillna(base_df['frv'])
                base_df = base_df.drop(columns=['frv_frv2'])

    # If FRV still missing, estimate from OAA with position-specific weights
    # Labeled clearly in reliability indicator — not treated as measured data
    if base_df['frv'].notna().sum() == 0 and base_df['oaa'].notna().sum() > 0:
        pos_weights = {'C':0.65,'1B':0.65,'2B':0.73,'3B':0.72,'SS':0.74,'LF':0.57,'CF':0.56,'RF':0.57}
        if 'position' in base_df.columns:
            weights = base_df['position'].map(pos_weights).fillna(0.65)
            base_df['frv'] = (base_df['oaa'] * weights).round(2)
    status['frv_estimated'] = True

    # Merge sprint speed if not already in base
    if base_df['sprint_speed'].isna().all() and has_players(speed_df) and 'sprint_speed' in speed_df.columns:
        spd_merge = speed_df[['player_name', 'sprint_speed']].drop_duplicates('player_name')
        base_df = base_df.merge(spd_merge, on='player_name', how='left', suffixes=('', '_spd'))
        if 'sprint_speed_spd' in base_df.columns:
            base_df['sprint_speed'] = base_df['sprint_speed_spd'].fillna(base_df['sprint_speed'])
            base_df = base_df.drop(columns=['sprint_speed_spd'])

    # Merge arm data if not already in base
    if base_df['arm_runs'].isna().all() and has_players(arm_df):
        arm_keep = ['player_name'] + [c for c in ['arm_runs', 'pop_time', 'arm_strength'] if c in arm_df.columns]
        if len(arm_keep) > 1:
            arm_merge = arm_df[arm_keep].drop_duplicates('player_name')
            base_df = base_df.merge(arm_merge, on='player_name', how='left', suffixes=('', '_arm'))
            for c in ['arm_runs', 'pop_time']:
                if f'{c}_arm' in base_df.columns:
                    base_df[c] = base_df[f'{c}_arm'].fillna(base_df.get(c, np.nan))
                    base_df = base_df.drop(columns=[f'{c}_arm'], errors='ignore')

    # Merge framing (catchers)
    if has_players(framing_df) and 'framing_runs' in framing_df.columns:
        frm_merge = framing_df[['player_name', 'framing_runs']].drop_duplicates('player_name')
        base_df = base_df.merge(frm_merge, on='player_name', how='left', suffixes=('', '_frm'))
        if 'framing_runs_frm' in base_df.columns:
            base_df['framing_runs'] = base_df['framing_runs_frm'].fillna(base_df['framing_runs'])
            base_df = base_df.drop(columns=['framing_runs_frm'])

    # Merge DRS (Baseball Reference / Sports Info Solutions)
    if not drs_df.empty:
        # DRS from BR — try multiple possible column names
        drs_col = next((c for c in ['DRS', 'Rdrs', 'rdrs', 'drs'] if c in drs_df.columns), None)
        name_col = next((c for c in ['Name', 'Player', 'player_name', 'name'] if c in drs_df.columns), None)
        if not drs_col:
            # Look for any column that might contain DRS values
            for c in drs_df.columns:
                if 'drs' in c.lower() or 'run' in c.lower():
                    drs_col = c
                    break
        if drs_col and name_col:
            drs_sub = drs_df[[name_col, drs_col]].rename(
                columns={name_col: 'player_name', drs_col: 'drs'}
            ).copy()
            # Convert DRS to numeric
            drs_sub['drs'] = pd.to_numeric(drs_sub['drs'], errors='coerce')
            drs_sub = drs_sub.dropna(subset=['drs'])
            drs_sub['_key'] = drs_sub['player_name'].apply(standardize_player_name)
            base_df['_key'] = base_df['player_name'].apply(standardize_player_name)
            base_df = base_df.merge(
                drs_sub[['_key', 'drs']], on='_key', how='left', suffixes=('', '_drs')
            )
            base_df = base_df.drop(columns=['_key', 'drs_drs'], errors='ignore')
            status['drs_matched'] = int(base_df['drs'].notna().sum())

    # Innings: ensure numeric, estimate if missing
    if 'innings' not in base_df.columns:
        base_df['innings'] = 0.0
    base_df['innings'] = pd.to_numeric(base_df['innings'], errors='coerce').fillna(0)

    # If innings are all zero, estimate from attempts
    if base_df['innings'].sum() == 0 and 'oaa_attempts' in base_df.columns:
        pos_inn_rates = {'LF':4.0,'CF':4.0,'RF':4.0,'C':3.5}
        def est_inn(row):
            att = pd.to_numeric(row.get('oaa_attempts', 0), errors='coerce') or 0
            rate = pos_inn_rates.get(str(row.get('position','')), 3.0)
            return round(att * rate, 1)
        base_df['innings'] = base_df.apply(est_inn, axis=1)
    status['innings_estimated'] = True

    # Adaptive minimum: if median innings < 200, data is early-season — use 30 att as proxy
    median_inn = base_df['innings'].median() if len(base_df) > 0 else 0
    if median_inn < 100 and 'oaa_attempts' in base_df.columns:
        # Use attempts as proxy: 10+ attempts = include in main leaderboard
        att_min = 10
        main_df = base_df[
            (base_df['oaa_attempts'].fillna(0) >= att_min) | (base_df['innings'] >= 50)
        ].copy()
        limited_df = base_df[
            (base_df['oaa_attempts'].fillna(0) < att_min) & (base_df['innings'] < 50)
        ].copy()
        status['adaptive_threshold'] = f'{att_min} attempts (early season)'
    else:
        main_df = base_df[base_df['innings'] >= MIN_INNINGS].copy()
        limited_df = base_df[(base_df['innings'] > 0) & (base_df['innings'] < MIN_INNINGS)].copy()
        status['adaptive_threshold'] = f'{MIN_INNINGS} innings'

    # Normalize dtypes — convert Arrow-backed columns to numpy float64
    # Required for pandas 3.x arithmetic compatibility
    main_df = normalize_dtypes(main_df)

    # Drop any stale demo flag that may have come from a previous cached run
    main_df = main_df.drop(columns=['is_demo'], errors='ignore')

    # Apply calculations
    raw_statcast = pd.DataFrame()  # Full Statcast too large for cached session; use summary metrics

    main_df = calculate_stadium_correction(main_df)
    main_df = calculate_attempt_range_score(main_df, raw_statcast)
    main_df = calculate_rraa_proxy(main_df, raw_statcast)
    main_df = calculate_bap(main_df, raw_statcast)
    main_df = calculate_arm_runs(main_df)
    main_df = calculate_rcdef(main_df)
    main_df = calculate_rcdef_plus(main_df)
    main_df = calculate_reliability(main_df)
    main_df = calculate_disagreement_flag(main_df)

    main_df['sample_size'] = 'Full'
    if not limited_df.empty:
        limited_df = calculate_stadium_correction(limited_df)
        limited_df = calculate_attempt_range_score(limited_df, raw_statcast)
        limited_df = calculate_rraa_proxy(limited_df, raw_statcast)
        limited_df = calculate_bap(limited_df, raw_statcast)
        limited_df = calculate_arm_runs(limited_df)
        limited_df = calculate_rcdef(limited_df)
        limited_df['rcdef_plus'] = np.nan
        limited_df = calculate_reliability(limited_df)
        limited_df = calculate_disagreement_flag(limited_df)
        limited_df['sample_size'] = 'Limited'

    status['players_full'] = len(main_df)
    status['players_limited'] = len(limited_df)
    status['last_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M UTC')

    return main_df, status


def build_demo_dataset(year: int) -> pd.DataFrame:
    """
    Demo dataset when live data sources are unavailable.
    Uses realistic but synthetic values for UI development/testing.
    Clearly labeled as demo data throughout the app.
    """
    np.random.seed(42)

    # Sprint speed in ft/sec (MLB average ~27 ft/sec; elite ~30+)
    players = [
        ('Corbin Carroll', 'ARI', 'CF', 1200, 18, 15, 12, 30.1),
        ('Mookie Betts', 'LAD', 'SS', 1100, 15, 13, 11, 28.2),
        ('Matt Chapman', 'SF', '3B', 1050, 14, 12, 10, 27.5),
        ('Brice Turang', 'MIL', '2B', 980, 13, 6, 22, 28.8),
        ('Bobby Witt Jr.', 'KC', 'SS', 1150, 12, 3, 24, 30.4),
        ('Nolan Arenado', 'STL', '3B', 1000, 10, 8, 8, 27.0),
        ('Jose Trevino', 'NYY', 'C', 850, 9, 7, 5, 25.5),
        ('Christian Walker', 'ARI', '1B', 1100, 8, 7, 6, 27.2),
        ('Andres Gimenez', 'CLE', '2B', 990, 7, 9, 19, 28.1),
        ('Kevin Kiermaier', 'TOR', 'CF', 920, 11, 9, 8, 29.5),
        ('Yadier Molina', 'STL', 'C', 800, 6, 5, 4, 24.3),
        ('Paul Goldschmidt', 'STL', '1B', 1050, 5, 4, 3, 27.0),
        ('Freddie Freeman', 'LAD', '1B', 1100, 2, 1, 2, 26.8),
        ('Francisco Lindor', 'NYM', 'SS', 1150, -2, -1, -5, 28.1),
        ('Marcus Semien', 'TEX', '2B', 1000, 8, 10, 19, 27.8),
        ('Ha-Seong Kim', 'SD', 'SS', 950, 9, 8, 12, 28.0),
        ('Trea Turner', 'PHI', 'SS', 1050, -3, -2, -5, 29.3),
        ('Austin Riley', 'ATL', '3B', 1080, -5, -4, -4, 26.7),
        ('Rafael Devers', 'BOS', '3B', 1060, -4, -5, -2, 26.6),
        ('Vladimir Guerrero Jr.', 'TOR', '1B', 1100, -4, -3, -5, 27.4),
        ('Julio Rodriguez', 'SEA', 'CF', 1100, 14, 12, 10, 29.6),
        ('Michael Harris II', 'ATL', 'CF', 1050, 16, 14, 12, 30.5),
        ('Byron Buxton', 'MIN', 'CF', 800, 12, 10, 8, 30.7),
        ('Steven Kwan', 'CLE', 'LF', 980, 10, 9, 7, 27.9),
        ('Lars Nootbaar', 'STL', 'RF', 920, 8, 7, 6, 27.8),
        ('Yordan Alvarez', 'HOU', 'LF', 900, -6, -5, -4, 27.1),
        ('Adolis Garcia', 'TEX', 'RF', 980, 6, 5, 8, 28.7),
        ('Kyle Tucker', 'HOU', 'RF', 1020, 7, 6, 9, 27.9),
        ('Tommy Edman', 'LAD', '2B', 880, 8, 7, 11, 28.0),
        ('Gavin Lux', 'LAD', '2B', 750, 2, 3, -4, 26.5),
    ]

    rows = []
    for name, team, pos, inn, oaa, frv, oaa_att_mult, speed in players:
        oaa_attempts = int(oaa_att_mult * (inn / 162))
        drs = oaa + np.random.randint(-3, 4)
        arm = np.random.uniform(-2, 4) if pos in ['LF', 'CF', 'RF'] else np.random.uniform(-1, 2)
        framing = np.random.uniform(-3, 8) if pos == 'C' else np.nan
        rraa = np.random.uniform(-2, 4) if pos == '1B' else np.nan
        bap = oaa * 0.15 + arm * 0.2

        # Stadium correction
        sc = STADIUM_CORRECTIONS.get(team, {}).get('x_bias', 0) * 0.12

        # ARS — use oaa as a direct proxy for demo (realistic range)
        # Real calculation uses league attempt rate baselines
        ars = oaa * 0.18 + np.random.uniform(-1.5, 1.5)

        rows.append({
            'player_name': name,
            'team': team,
            'position': pos,
            'innings': inn,
            'oaa': oaa,
            'frv': frv,
            'drs': drs,
            'arm_runs': round(arm, 2),
            'sprint_speed': speed,
            'framing_runs': framing if pos == 'C' else np.nan,
            'rraa': rraa if pos == '1B' else np.nan,
            'rraa_attempts': 120 if pos == '1B' else np.nan,
            'rraa_eligible': pos == '1B',
            'oaa_attempts': oaa_attempts,
            'attempt_range_score': round(ars, 2),
            'bap': round(bap, 2),
            'stadium_correction': round(sc, 2),
            'conversion_runs': round((oaa * 0.65 + frv) / 2, 2),
            'data_year': year,
            'sample_size': 'Full',
            'neighbor_flag': False,
            'neighbor_suppression': False,
            'neighbor_vacuum': False,
            # is_demo column removed — use status['mode'] instead
        })

    df = pd.DataFrame(rows)

    # Calculate RCDef
    df = calculate_rcdef(df)
    df = calculate_rcdef_plus(df)
    df = calculate_reliability(df)
    df = calculate_disagreement_flag(df)

    return df


# ─────────────────────────────────────────────
# DISPLAY HELPERS
# ─────────────────────────────────────────────

def format_stat(val, decimals=1, show_plus=True):
    """Format a stat value for display."""
    if pd.isna(val) or val is None:
        return '-'
    try:
        val = float(val)
        if show_plus and val > 0:
            return f'+{val:.{decimals}f}'
        return f'{val:.{decimals}f}'
    except (ValueError, TypeError):
        return str(val)


def color_stat(val, inverse=False):
    """Return CSS color class based on value."""
    if pd.isna(val) or val is None:
        return 'pill-gray'
    try:
        val = float(val)
        if inverse:
            val = -val
        if val >= 8:
            return 'pill-green'
        elif val >= 2:
            return 'pill-blue'
        elif val >= -2:
            return 'pill-gray'
        elif val >= -8:
            return 'pill-yellow'
        else:
            return 'pill-red'
    except (ValueError, TypeError):
        return 'pill-gray'


def reliability_html(rel):
    """Return styled reliability indicator."""
    icons = {'High': '●', 'Medium': '◐', 'Low': '○'}
    classes = {'High': 'rel-high', 'Medium': 'rel-med', 'Low': 'rel-low'}
    return f'<span class="{classes.get(rel, "rel-low")}">{icons.get(rel, "○")} {rel}</span>'


def get_rcdef_context(rcdef_val):
    """Return descriptive context for an RCDef value."""
    if pd.isna(rcdef_val):
        return 'Insufficient data'
    v = float(rcdef_val)
    if v >= 20:
        return 'Elite (Top 5 in baseball)'
    elif v >= 12:
        return 'Great (Top 20%)'
    elif v >= 4:
        return 'Above Average'
    elif v >= -4:
        return 'Average'
    elif v >= -12:
        return 'Below Average'
    elif v >= -20:
        return 'Poor'
    else:
        return 'Significant defensive liability'


# ─────────────────────────────────────────────
# CHART BUILDERS
# ─────────────────────────────────────────────

def build_radar_chart(row: pd.Series, player_name: str) -> go.Figure:
    """Build component radar chart for player card."""
    categories = ['Conv. Runs', 'Att. Range', 'BAP', 'Arm Runs', 'Stadium Adj.']
    values = [
        float(row.get('conversion_runs', 0) or 0),
        float(row.get('attempt_range_score', 0) or 0),
        float(row.get('bap', 0) or 0),
        float(row.get('arm_runs', 0) or 0),
        float(row.get('stadium_correction', 0) or 0),
    ]

    # Normalize to -10/+10 scale for display
    max_abs = max(abs(v) for v in values) if any(values) else 1
    max_abs = max(max_abs, 5)

    fig = go.Figure()

    fig.add_trace(go.Scatterpolar(
        r=[abs(v) for v in values] + [abs(values[0])],
        theta=categories + [categories[0]],
        fill='toself',
        fillcolor='rgba(0, 208, 132, 0.15)',
        line=dict(color='#00d084', width=2),
        name=player_name,
    ))

    fig.update_layout(
        polar=dict(
            bgcolor='rgba(17, 24, 39, 0.8)',
            radialaxis=dict(
                visible=True,
                range=[0, max_abs * 1.2],
                tickfont=dict(color='#8892a4', size=9, family='IBM Plex Mono'),
                gridcolor='rgba(255,255,255,0.08)',
                linecolor='rgba(255,255,255,0.08)',
            ),
            angularaxis=dict(
                tickfont=dict(color='#e8eaf0', size=10, family='IBM Plex Mono'),
                gridcolor='rgba(255,255,255,0.08)',
                linecolor='rgba(255,255,255,0.1)',
            ),
        ),
        showlegend=False,
        paper_bgcolor='rgba(17, 24, 39, 0)',
        plot_bgcolor='rgba(17, 24, 39, 0)',
        margin=dict(l=40, r=40, t=40, b=40),
        height=300,
    )

    return fig


def build_percentile_bar(rcdef_plus_val: float) -> go.Figure:
    """Build horizontal percentile gauge."""
    val = float(rcdef_plus_val) if pd.notna(rcdef_plus_val) else 50

    # Color based on percentile
    if val >= 75:
        color = '#00d084'
    elif val >= 55:
        color = '#3498db'
    elif val >= 45:
        color = '#8892a4'
    elif val >= 25:
        color = '#ffd32a'
    else:
        color = '#ff4757'

    fig = go.Figure()

    # Background bar
    fig.add_trace(go.Bar(
        x=[100], y=['RCDef+'],
        orientation='h',
        marker_color='rgba(255,255,255,0.05)',
        showlegend=False,
        hoverinfo='skip',
    ))

    # Value bar
    fig.add_trace(go.Bar(
        x=[val], y=['RCDef+'],
        orientation='h',
        marker_color=color,
        showlegend=False,
        text=f'{val:.0f}th',
        textposition='outside',
        textfont=dict(color=color, size=14, family='Bebas Neue'),
        hovertemplate=f'RCDef+ Percentile: {val:.0f}<extra></extra>',
    ))

    # Average line at 50
    fig.add_vline(x=50, line_dash='dash', line_color='rgba(255,255,255,0.3)', line_width=1)

    fig.update_layout(
        barmode='overlay',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        height=80,
        margin=dict(l=0, r=60, t=10, b=10),
        xaxis=dict(
            range=[0, 110],
            visible=False,
        ),
        yaxis=dict(visible=False),
    )

    return fig


def build_leaderboard_bar_chart(df: pd.DataFrame, metric: str, title: str, n: int = 15) -> go.Figure:
    """Build horizontal bar chart for leaderboard view."""
    plot_df = df.dropna(subset=[metric]).nlargest(n, metric).sort_values(metric)

    colors = ['#00d084' if v >= 0 else '#ff4757' for v in plot_df[metric]]

    fig = go.Figure(go.Bar(
        x=plot_df[metric],
        y=plot_df['player_name'],
        orientation='h',
        marker_color=colors,
        text=[format_stat(v) for v in plot_df[metric]],
        textposition='outside',
        textfont=dict(color='#e8eaf0', size=10, family='IBM Plex Mono'),
        hovertemplate='<b>%{y}</b><br>' + title + ': %{x:.1f}<extra></extra>',
    ))

    fig.update_layout(
        paper_bgcolor='rgba(17,24,39,0)',
        plot_bgcolor='rgba(17,24,39,0)',
        height=max(400, n * 28),
        margin=dict(l=10, r=60, t=30, b=10),
        xaxis=dict(
            gridcolor='rgba(255,255,255,0.06)',
            tickfont=dict(color='#8892a4', size=9, family='IBM Plex Mono'),
            zerolinecolor='rgba(255,255,255,0.15)',
            title=dict(text=title, font=dict(color='#8892a4', size=10, family='IBM Plex Mono')),
        ),
        yaxis=dict(
            tickfont=dict(color='#e8eaf0', size=10, family='IBM Plex Mono'),
            gridcolor='rgba(0,0,0,0)',
        ),
        title=dict(
            text=title,
            font=dict(color='#e8eaf0', size=14, family='Bebas Neue'),
            x=0,
        ),
    )

    return fig


def build_scatter_comparison(df: pd.DataFrame, x_col: str, y_col: str,
                              x_label: str, y_label: str) -> go.Figure:
    """Build scatter plot comparing two metrics - useful for disagreement analysis."""
    plot_df = df.dropna(subset=[x_col, y_col]).copy()

    colors = ['#ffd32a' if row['disagreement_flag'] else '#00d084'
              for _, row in plot_df.iterrows()]

    fig = go.Figure(go.Scatter(
        x=plot_df[x_col],
        y=plot_df[y_col],
        mode='markers+text',
        marker=dict(
            color=colors,
            size=8,
            opacity=0.8,
            line=dict(color='rgba(255,255,255,0.2)', width=1),
        ),
        text=plot_df['player_name'].apply(lambda n: n.split()[-1]),
        textposition='top center',
        textfont=dict(color='#8892a4', size=8, family='IBM Plex Mono'),
        hovertemplate='<b>%{text}</b><br>' + x_label + ': %{x:.1f}<br>' + y_label + ': %{y:.1f}<extra></extra>',
        customdata=plot_df['player_name'],
    ))

    # 1:1 reference line
    vals = pd.concat([plot_df[x_col], plot_df[y_col]])
    min_v, max_v = vals.min(), vals.max()
    fig.add_trace(go.Scatter(
        x=[min_v, max_v], y=[min_v, max_v],
        mode='lines',
        line=dict(color='rgba(255,255,255,0.15)', dash='dash', width=1),
        showlegend=False,
        hoverinfo='skip',
    ))

    fig.update_layout(
        paper_bgcolor='rgba(17,24,39,0)',
        plot_bgcolor='rgba(17,24,39,0.5)',
        height=450,
        margin=dict(l=50, r=20, t=40, b=50),
        xaxis=dict(
            title=dict(text=x_label, font=dict(color='#8892a4', size=10, family='IBM Plex Mono')),
            gridcolor='rgba(255,255,255,0.06)',
            tickfont=dict(color='#8892a4', size=9, family='IBM Plex Mono'),
            zerolinecolor='rgba(255,255,255,0.15)',
        ),
        yaxis=dict(
            title=dict(text=y_label, font=dict(color='#8892a4', size=10, family='IBM Plex Mono')),
            gridcolor='rgba(255,255,255,0.06)',
            tickfont=dict(color='#8892a4', size=9, family='IBM Plex Mono'),
            zerolinecolor='rgba(255,255,255,0.15)',
        ),
        showlegend=False,
    )

    return fig


# ─────────────────────────────────────────────
# PAGE: LEADERBOARD
# ─────────────────────────────────────────────

def page_leaderboard(df: pd.DataFrame, status: dict, is_demo: bool):
    """Main leaderboard page."""

    st.markdown('<div class="section-header">Leaderboard</div>', unsafe_allow_html=True)

    if status.get('mode', 'demo') != 'live':
        demo_reason = status.get('demo_reason', 'Data sources returned no qualifying players.')
        st.markdown(f'''<div class="warn-box">
        ⚠ DEMO MODE — Live data sources returned no data. Displaying synthetic data.<br>
        <span style="opacity:0.7;font-size:0.9em;">Reason: {demo_reason}</span><br>
        <span style="opacity:0.7;font-size:0.9em;">Use the ⬇ Diagnostics CSV button in the sidebar to see exactly what each source returned.</span>
        </div>''', unsafe_allow_html=True)
        if status.get('traceback'):
            with st.expander('Pipeline error details'):
                st.code(status.get('traceback', ''), language='python')

    # Filters
    col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 2, 2])

    with col1:
        year_filter = st.selectbox('Season', CURRENT_YEARS, key='lb_year')

    with col2:
        pos_options = ['All Positions'] + list(POSITIONS.keys())
        pos_filter = st.selectbox('Position', pos_options, key='lb_pos')

    with col3:
        team_options = ['All Teams'] + sorted(df['team'].dropna().unique().tolist())
        team_filter = st.selectbox('Team', team_options, key='lb_team')

    with col4:
        sample_filter = st.selectbox('Sample', ['Full Season (300+ inn)', 'All Players'], key='lb_sample')

    with col5:
        sort_options = {
            'RCDef': 'rcdef',
            'RCDef+': 'rcdef_plus',
            'OAA': 'oaa',
            'FRV': 'frv',
            'DRS': 'drs',
            'Innings': 'innings',
        }
        sort_by_label = st.selectbox('Sort By', list(sort_options.keys()), key='lb_sort')
        sort_by = sort_options[sort_by_label]

    # Apply filters
    filtered = df.copy()

    if pos_filter != 'All Positions':
        filtered = filtered[filtered['position'] == pos_filter]

    if team_filter != 'All Teams':
        filtered = filtered[filtered['team'] == team_filter]

    if sample_filter == 'Full Season (300+ inn)':
        filtered = filtered[filtered.get('sample_size', 'Full') == 'Full']

    if sort_by in filtered.columns:
        filtered = filtered.sort_values(sort_by, ascending=False, na_position='last')

    # Summary metrics row
    st.markdown('<br>', unsafe_allow_html=True)
    m1, m2, m3, m4, m5 = st.columns(5)

    with m1:
        st.markdown(f'''<div class="metric-card">
        <div class="metric-label">Players Shown</div>
        <div class="metric-value">{len(filtered)}</div>
        </div>''', unsafe_allow_html=True)

    with m2:
        best = filtered.nlargest(1, 'rcdef')
        best_name = best['player_name'].iloc[0].split()[-1] if not best.empty else '-'
        best_val = format_stat(best['rcdef'].iloc[0]) if not best.empty else '-'
        st.markdown(f'''<div class="metric-card">
        <div class="metric-label">Top RCDef</div>
        <div class="metric-value positive">{best_val}</div>
        <div style="font-family:IBM Plex Mono;font-size:0.7rem;color:#8892a4;margin-top:0.3rem;">{best_name}</div>
        </div>''', unsafe_allow_html=True)

    with m3:
        avg_rcdef = filtered['rcdef'].mean()
        st.markdown(f'''<div class="metric-card">
        <div class="metric-label">Avg RCDef</div>
        <div class="metric-value">{format_stat(avg_rcdef)}</div>
        </div>''', unsafe_allow_html=True)

    with m4:
        flagged_count = filtered.get('disagreement_flag', pd.Series(False)).sum()
        st.markdown(f'''<div class="metric-card">
        <div class="metric-label">⚡ Metric Disagreements</div>
        <div class="metric-value" style="color:#ffd32a;">{flagged_count}</div>
        </div>''', unsafe_allow_html=True)

    with m5:
        last_updated = status.get('last_updated', 'Unknown')
        mode = status.get('mode', 'demo')
        badge_class = 'status-live' if mode == 'live' else 'status-cached'
        badge_text = 'LIVE' if mode == 'live' else 'DEMO'
        st.markdown(f'''<div class="metric-card">
        <div class="metric-label">Data Status</div>
        <div style="margin-top:0.5rem;"><span class="data-status {badge_class}">{badge_text}</span></div>
        <div style="font-family:IBM Plex Mono;font-size:0.65rem;color:#4a5568;margin-top:0.4rem;">{last_updated}</div>
        </div>''', unsafe_allow_html=True)

    st.markdown('<br>', unsafe_allow_html=True)

    # Build display dataframe
    display_cols = {
        'player_name': 'Player',
        'team': 'Team',
        'position': 'Pos',
        'innings': 'Inn',
        'rcdef': 'RCDef',
        'rcdef_plus': 'RCDef+',
        'oaa': 'OAA',
        'frv': 'FRV',
        'drs': 'DRS*',
        'conversion_runs': 'CR',
        'attempt_range_score': 'ARS',
        'rraa': 'RRAA',
        'bap': 'BAP',
        'arm_runs': 'ARM',
        'framing_runs': 'FRM',
        'stadium_correction': 'SC',
        'sprint_speed': 'Spd',
        'reliability': 'Rel',
    }

    # Only include columns that exist
    avail_cols = {k: v for k, v in display_cols.items() if k in filtered.columns}
    display_df = filtered[list(avail_cols.keys())].copy()
    display_df = display_df.rename(columns=avail_cols)

    # Format numeric columns
    numeric_format = {
        'Inn': '{:.0f}',
        'RCDef': '{:.1f}',
        'RCDef+': '{:.0f}',
        'OAA': '{:.1f}',
        'FRV': '{:.1f}',
        'DRS*': '{:.0f}',
        'CR': '{:.1f}',
        'ARS': '{:.1f}',
        'RRAA': '{:.1f}',
        'BAP': '{:.1f}',
        'ARM': '{:.1f}',
        'FRM': '{:.1f}',
        'SC': '{:.2f}',
        'Spd': '{:.1f}',
    }

    for col, fmt in numeric_format.items():
        if col in display_df.columns:
            display_df[col] = display_df[col].apply(
                lambda x: fmt.format(float(x)) if pd.notna(x) else '-'
            )

    # Add disagreement flag as FIRST column
    if 'disagreement_flag' in filtered.columns:
        display_df.insert(
            0,
            '⚡',
            filtered['disagreement_flag'].apply(lambda x: '⚡' if x else '')
        )

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        height=600,
        column_config={
            'Player': st.column_config.TextColumn('Player', width='medium'),
            'RCDef': st.column_config.TextColumn('RCDef', width='small'),
            'RCDef+': st.column_config.TextColumn('RCDef+', width='small'),
            'Rel': st.column_config.TextColumn('Reliability', width='small'),
            '⚡': st.column_config.TextColumn('', width='small'),
        }
    )

    st.markdown('''<div style="font-family:IBM Plex Mono;font-size:0.65rem;color:#4a5568;margin-top:0.5rem;">
    *DRS data courtesy of Sports Info Solutions / Baseball Reference. Non-commercial attribution.
    ⚡ = Metric disagreement flag (top metrics diverge >8 runs). Minimum 300 innings for full season display.
    </div>''', unsafe_allow_html=True)

    # ── Downloads ────────────────────────────────────────────────────────────
    dl_col1, dl_col2, dl_col3 = st.columns([2, 2, 6])

    with dl_col1:
        # Leaderboard CSV
        csv_export = filtered.copy()
        # Clean up internal columns before export
        drop_internal = ['is_demo', 'player_name_lower', 'disagreement_detail', 'sample_size']
        csv_export = csv_export.drop(columns=[c for c in drop_internal if c in csv_export.columns])
        csv_bytes = csv_export.to_csv(index=False).encode('utf-8')
        st.download_button(
            label='⬇ Download Leaderboard (.csv)',
            data=csv_bytes,
            file_name=f'rcdef_leaderboard_{year_filter}.csv',
            mime='text/csv',
            use_container_width=True,
        )

    with dl_col2:
        # Diagnostics download — all raw data columns
        diag_df = df.copy()
        diag_df['_pull_timestamp'] = status.get('last_updated', 'unknown')
        diag_df['_data_mode'] = status.get('mode', 'unknown')
        diag_df['_oaa_source_rows'] = status.get('oaa', {}).get('rows', 0)
        diag_df['_frv_source_rows'] = status.get('frv', {}).get('rows', 0)
        diag_df['_drs_source_rows'] = status.get('drs', {}).get('rows', 0)
        diag_df['_sprint_source_rows'] = status.get('sprint', {}).get('rows', 0)
        diag_df['_arm_source_rows'] = status.get('arm', {}).get('rows', 0)
        diag_df['_framing_source_rows'] = status.get('framing', {}).get('rows', 0)
        diag_bytes = diag_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label='⬇ Download Diagnostics (.csv)',
            data=diag_bytes,
            file_name=f'rcdef_diagnostics_{year_filter}.csv',
            mime='text/csv',
            use_container_width=True,
        )

    # Visualization tabs
    st.markdown('<br>', unsafe_allow_html=True)
    vtab1, vtab2, vtab3 = st.tabs(['📊 RCDef Leaders', '🔀 Metric Comparison', '📈 Component Breakdown'])

    with vtab1:
        col_l, col_r = st.columns(2)
        with col_l:
            top_n = filtered.dropna(subset=['rcdef']).nlargest(15, 'rcdef')
            if not top_n.empty:
                st.plotly_chart(
                    build_leaderboard_bar_chart(top_n, 'rcdef', 'RCDef (Runs Above Avg)', 15),
                    use_container_width=True
                )
        with col_r:
            bot_n = filtered.dropna(subset=['rcdef']).nsmallest(15, 'rcdef')
            if not bot_n.empty:
                st.plotly_chart(
                    build_leaderboard_bar_chart(bot_n, 'rcdef', 'RCDef (Worst)', 15),
                    use_container_width=True
                )

    with vtab2:
        c1, c2 = st.columns(2)
        with c1:
            x_metric = st.selectbox('X Axis', ['oaa', 'frv', 'drs', 'rcdef'], key='scatter_x')
        with c2:
            y_metric = st.selectbox('Y Axis', ['frv', 'rcdef', 'oaa', 'drs'], key='scatter_y')

        plot_filtered = filtered.dropna(subset=[x_metric, y_metric])
        if not plot_filtered.empty:
            st.plotly_chart(
                build_scatter_comparison(
                    plot_filtered, x_metric, y_metric,
                    x_metric.upper(), y_metric.upper()
                ),
                use_container_width=True
            )
            if 'disagreement_flag' in plot_filtered.columns:
                flagged = plot_filtered[plot_filtered['disagreement_flag']]
                if not flagged.empty:
                    st.markdown('<div class="warn-box">⚡ Yellow points = metric disagreement flag (divergence >8 runs)</div>',
                                unsafe_allow_html=True)
        else:
            st.info('Insufficient data for selected metrics.')

    with vtab3:
        components = ['conversion_runs', 'attempt_range_score', 'bap', 'arm_runs']
        avail_components = [c for c in components if c in filtered.columns]

        if avail_components:
            top20 = filtered.dropna(subset=['rcdef']).nlargest(20, 'rcdef')
            comp_labels = {
                'conversion_runs': 'Conv. Runs',
                'attempt_range_score': 'Att. Range',
                'bap': 'BAP',
                'arm_runs': 'Arm Runs',
            }

            fig = go.Figure()
            colors_map = {
                'conversion_runs': '#00d084',
                'attempt_range_score': '#3498db',
                'bap': '#a29bfe',
                'arm_runs': '#ffd32a',
            }

            for comp in avail_components:
                fig.add_trace(go.Bar(
                    name=comp_labels.get(comp, comp),
                    x=top20['player_name'].apply(lambda n: n.split()[-1]),
                    y=top20[comp].fillna(0),
                    marker_color=colors_map.get(comp, '#8892a4'),
                    opacity=0.85,
                ))

            fig.update_layout(
                barmode='stack',
                paper_bgcolor='rgba(17,24,39,0)',
                plot_bgcolor='rgba(17,24,39,0.5)',
                height=450,
                legend=dict(
                    font=dict(color='#8892a4', size=10, family='IBM Plex Mono'),
                    bgcolor='rgba(17,24,39,0.8)',
                ),
                xaxis=dict(
                    tickfont=dict(color='#8892a4', size=9, family='IBM Plex Mono'),
                    gridcolor='rgba(0,0,0,0)',
                ),
                yaxis=dict(
                    gridcolor='rgba(255,255,255,0.06)',
                    tickfont=dict(color='#8892a4', size=9, family='IBM Plex Mono'),
                    title=dict(text='Runs Above Average', font=dict(color='#8892a4', size=10)),
                ),
                margin=dict(l=40, r=20, t=20, b=60),
            )
            st.plotly_chart(fig, use_container_width=True)



def build_player_card_jpg(row: pd.Series, player_name: str) -> bytes | None:
    """
    Generate a JPG player card that exactly mirrors render_player_card_html.
    White background, dark header, input metrics row, component bars.
    """
    try:
        from PIL import Image, ImageDraw, ImageFont
        import io as _io

        W, H = 900, 415
        img = Image.new('RGB', (W, H), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)

        # ── Colors (match HTML) ───────────────────────────────────────────────
        C_HEADER  = (10,  14,  26)
        C_ACCENT  = (0,  208, 132)
        C_RED     = (255, 71,  87)
        C_GRAY    = (107, 114, 128)
        C_LGRAY   = (243, 244, 246)
        C_MGRAY   = (229, 231, 235)
        C_TEXT    = (55,  65,  81)
        C_SUBTEXT = (156, 163, 175)
        C_WHITE   = (255, 255, 255)

        # ── Fonts ─────────────────────────────────────────────────────────────
        font_paths = [
            '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
            '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf',
        ]
        mono_paths = [
            '/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf',
            '/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf',
        ]
        def load_font(paths, size):
            for p in paths:
                try:
                    return ImageFont.truetype(p, size)
                except Exception:
                    pass
            return ImageFont.load_default()

        fnt_logo   = load_font(font_paths, 28)
        fnt_name   = load_font(font_paths, 22)
        fnt_med    = load_font(font_paths, 16)
        fnt_sm     = load_font(font_paths, 13)
        fnt_xs     = load_font(font_paths, 11)
        fnt_mono   = load_font(mono_paths, 11)
        fnt_rcdef  = load_font(font_paths, 30)

        # ── Pull values ───────────────────────────────────────────────────────
        pos        = str(row.get('position', '?'))
        team       = str(row.get('team', '?'))
        inn        = float(row.get('innings', 0) or 0)
        year       = str(row.get('data_year', ''))
        rcdef      = row.get('rcdef', None)
        rcdef_plus = row.get('rcdef_plus', None)
        reliability= str(row.get('reliability', 'Low'))
        disagree   = bool(row.get('disagreement_flag', False))
        context    = get_rcdef_context(rcdef)
        rcdef_str  = format_stat(rcdef)
        rcdef_col  = C_ACCENT if (rcdef is not None and not (isinstance(rcdef, float) and np.isnan(rcdef)) and float(rcdef) >= 0) else C_RED
        rel_col    = {'High': C_ACCENT, 'Medium': (255, 211, 42)}.get(reliability, C_RED)
        rcp_str    = f'{float(rcdef_plus):.0f}th pct' if (rcdef_plus is not None and not (isinstance(rcdef_plus, float) and np.isnan(rcdef_plus))) else ''

        # ── HEADER (dark) ─────────────────────────────────────────────────────
        HEADER_H = 105
        draw.rectangle([(0, 0), (W, HEADER_H)], fill=C_HEADER)

        # Logo
        draw.text((22, 10), 'RCDef', font=fnt_logo, fill=C_ACCENT)
        # Player name
        draw.text((22, 42), player_name.upper(), font=fnt_name, fill=(249, 250, 251))
        # Meta
        pos_label = POSITIONS.get(pos, pos)
        draw.text((22, 68), f'{team}  ·  {pos_label}  ·  {inn:.0f} inn  ·  {year} Season', font=fnt_mono, fill=C_GRAY)
        # Context
        draw.text((22, 88), context, font=fnt_mono, fill=(156, 163, 175))

        # RCDef value (top right)
        draw.text((W - 200, 12), 'RCDef', font=fnt_xs, fill=C_GRAY)
        draw.text((W - 200, 26), rcdef_str, font=fnt_rcdef, fill=rcdef_col)
        draw.text((W - 200, 62), rcp_str, font=fnt_mono, fill=C_GRAY)

        # Reliability badge
        rel_text = reliability.upper()
        draw.rectangle([(W - 90, 10), (W - 10, 28)], fill=rel_col)
        draw.text((W - 87, 13), rel_text, font=fnt_xs, fill=C_HEADER)

        # Disagree badge
        if disagree:
            draw.rectangle([(W - 90, 34), (W - 10, 52)], fill=(255, 211, 42))
            draw.text((W - 87, 37), '⚡ FLAG', font=fnt_xs, fill=C_HEADER)

        # ── GREEN DIVIDER ─────────────────────────────────────────────────────
        draw.rectangle([(0, HEADER_H), (W, HEADER_H + 3)], fill=C_ACCENT)

        # ── INPUT METRICS ROW ─────────────────────────────────────────────────
        INP_Y = HEADER_H + 6
        input_metrics = [
            ('OAA',  row.get('oaa',          None)),
            ('FRV',  row.get('frv',          None)),
            ('DRS*', row.get('drs',          None)),
            ('Spd',  row.get('sprint_speed', None)),
            ('ARM',  row.get('arm_runs',     None)),
            ('FRM',  row.get('framing_runs', None)),
        ]
        cell_w = W // len(input_metrics)
        for idx, (lbl, val) in enumerate(input_metrics):
            x = idx * cell_w + 14
            draw.text((x, INP_Y), lbl, font=fnt_xs, fill=C_SUBTEXT)
            if val is None or (isinstance(val, float) and np.isnan(val)):
                draw.text((x, INP_Y + 14), '—', font=fnt_med, fill=C_LGRAY)
            else:
                v = float(val)
                col = C_ACCENT if v > 0 else (C_RED if v < 0 else C_GRAY)
                sign = '+' if v > 0 else ''
                draw.text((x, INP_Y + 14), f'{sign}{v:.1f}', font=fnt_med, fill=col)

        # Light separator
        SEP_Y = INP_Y + 38
        draw.rectangle([(0, SEP_Y), (W, SEP_Y + 1)], fill=C_MGRAY)

        # ── COMPONENT BARS ────────────────────────────────────────────────────
        COMP_START = SEP_Y + 10
        components = [
            ('Conv. Runs',    'conversion_runs'),
            ('Att. Range',    'attempt_range_score'),
            ('RRAA',          'rraa'),
            ('BAP',           'bap'),
            ('Arm Runs',      'arm_runs'),
            ('Framing',       'framing_runs'),
            ('Stadium Adj.',  'stadium_correction'),
        ]
        na_reasons = {
            'rraa':         '1B only' if pos != '1B' else None,
            'framing_runs': 'C only'  if pos != 'C'  else None,
        }
        comp_vals = []
        for _, col in components:
            v = row.get(col, None)
            comp_vals.append(float(v) if (v is not None and not (isinstance(v, float) and np.isnan(v))) else None)

        max_abs = max((abs(v) for v in comp_vals if v is not None), default=5)
        max_abs = max(max_abs, 5)

        LABEL_W  = 88
        BAR_X    = LABEL_W + 22
        BAR_W    = W - BAR_X - 55
        BAR_H    = 16
        ROW_GAP  = 30

        for i, ((lbl, col_key), val) in enumerate(zip(components, comp_vals)):
            y = COMP_START + i * ROW_GAP
            draw.text((14, y + 2), lbl, font=fnt_mono, fill=C_TEXT)

            na_override = na_reasons.get(col_key)
            if val is None or na_override:
                # Gray N/A bar
                draw.rectangle([(BAR_X, y), (BAR_X + BAR_W, y + BAR_H)], fill=C_LGRAY)
                reason = na_override or 'No data'
                draw.text((BAR_X + 6, y + 3), f'N/A — {reason}', font=fnt_xs, fill=C_SUBTEXT)
            else:
                bar_len = int(min(abs(val) / max_abs * BAR_W * 0.9, BAR_W))
                bar_len = max(bar_len, 3)
                bar_col = C_ACCENT if val >= 0 else C_RED
                # Track
                draw.rectangle([(BAR_X, y), (BAR_X + BAR_W, y + BAR_H)], fill=C_LGRAY)
                # Bar
                draw.rectangle([(BAR_X, y), (BAR_X + bar_len, y + BAR_H)], fill=bar_col)
                # Value
                sign = '+' if val > 0 else ''
                draw.text((BAR_X + BAR_W + 6, y + 2), f'{sign}{val:.1f}', font=fnt_mono, fill=bar_col)

        # ── FOOTER ────────────────────────────────────────────────────────────
        draw.rectangle([(0, H - 24), (W, H)], fill=C_LGRAY)
        draw.text((14, H - 16), 'RCDef Composite Defensive Analytics · rcdef.streamlit.app · *DRS © Sports Info Solutions / Baseball Reference · Non-commercial', font=fnt_xs, fill=C_SUBTEXT)

        # ── EXPORT ────────────────────────────────────────────────────────────
        buf = _io.BytesIO()
        img.save(buf, format='JPEG', quality=93, optimize=True)
        buf.seek(0)
        return buf.getvalue()

    except Exception:
        return None

def render_player_card_html(row: pd.Series, player_name: str) -> str:
    """White-background player card matching approved mockup design."""
    pos         = str(row.get('position', '?'))
    team        = str(row.get('team', '?'))
    inn         = float(row.get('innings', 0) or 0)
    year        = str(row.get('data_year', ''))
    rcdef       = row.get('rcdef', None)
    rcdef_plus  = row.get('rcdef_plus', None)
    reliability = str(row.get('reliability', 'Low'))
    disagree    = bool(row.get('disagreement_flag', False))
    disagree_detail = str(row.get('disagreement_detail', '')).rstrip('| ').strip()
    context     = get_rcdef_context(rcdef)
    rcdef_str   = format_stat(rcdef)
    speed       = row.get('sprint_speed', None)

    rcdef_col   = '#00c97a' if (rcdef is not None and not (isinstance(rcdef, float) and np.isnan(rcdef)) and float(rcdef) >= 0) else '#ef4444'
    rel_bg      = '#00c97a' if reliability == 'High' else ('#fbbf24' if reliability == 'Medium' else '#ef4444')
    rel_tc      = '#0a0e1a' if reliability in ('High', 'Medium') else '#ffffff'

    pct_val     = float(rcdef_plus) if (rcdef_plus is not None and not (isinstance(rcdef_plus, float) and np.isnan(rcdef_plus))) else 0.0
    pct_str     = f'{pct_val:.1f}th percentile' if (rcdef_plus is not None and not (isinstance(rcdef_plus, float) and np.isnan(rcdef_plus))) else '—'
    pct_col     = '#3b82f6' if pct_val >= 50 else ('#f59e0b' if pct_val >= 25 else '#ef4444')

    nb_sup = bool(row.get('neighbor_suppression', False))
    nb_vac = bool(row.get('neighbor_vacuum', False))
    if nb_sup:
        nbr_html = '<div style="font-size:11px;color:#1d4ed8;background:#eff6ff;border:0.5px solid #bfdbfe;border-radius:6px;padding:7px 10px;margin-top:10px;">&#x1F535; Neighbor suppression adjustment applied (30% cap).</div>'
    elif nb_vac:
        nbr_html = '<div style="font-size:11px;color:#92400e;background:#fef3c7;border:0.5px solid #fcd34d;border-radius:6px;padding:7px 10px;margin-top:10px;">&#x26A1; Neighbor vacuum flagged — no correction applied.</div>'
    else:
        nbr_html = '<div style="font-size:11px;color:#9ca3af;margin-top:10px;">No neighbor adjustment applied.</div>'

    speed_html = ''
    if speed is not None and not (isinstance(speed, float) and np.isnan(speed)):
        speed_html = f'<div style="background:#eff6ff;border:0.5px solid #bfdbfe;border-radius:6px;padding:7px 10px;font-size:11px;color:#1d4ed8;margin-top:12px;">&#x2139; Sprint Speed: {float(speed):.1f} ft/sec — context only</div>'

    disagree_html = ''
    if disagree and disagree_detail:
        disagree_html = f'<div style="display:inline-flex;align-items:center;gap:5px;background:rgba(234,179,8,0.15);border:0.5px solid rgba(234,179,8,0.45);border-radius:4px;padding:3px 8px;font-size:10px;color:#ca8a04;margin-top:7px;">&#x26A0; {disagree_detail}</div>'
    elif disagree:
        disagree_html = '<div style="display:inline-flex;align-items:center;gap:5px;background:rgba(234,179,8,0.15);border:0.5px solid rgba(234,179,8,0.45);border-radius:4px;padding:3px 8px;font-size:10px;color:#ca8a04;margin-top:7px;">&#x26A0; Metric disagreement detected</div>'

    def inp_cell(label, val, src):
        if val is None or (isinstance(val, float) and np.isnan(val)):
            return f'''<div style="padding:10px 8px;text-align:center;border-right:0.5px solid #e5e7eb;">
              <div style="font-size:10px;letter-spacing:0.1em;color:#6b7280;text-transform:uppercase;margin-bottom:4px;">{label}</div>
              <div style="font-size:15px;font-weight:500;color:#9ca3af;">—</div>
              <div style="font-size:10px;color:#9ca3af;margin-top:1px;">{src}</div>
            </div>'''
        v = float(val)
        col = '#059669' if v > 0 else ('#dc2626' if v < 0 else '#6b7280')
        sign = '+' if v > 0 else ''
        return f'''<div style="padding:10px 8px;text-align:center;border-right:0.5px solid #e5e7eb;">
          <div style="font-size:10px;letter-spacing:0.1em;color:#6b7280;text-transform:uppercase;margin-bottom:4px;">{label}</div>
          <div style="font-size:15px;font-weight:500;color:{col};">{sign}{v:.1f}</div>
          <div style="font-size:10px;color:#9ca3af;margin-top:1px;">{src}</div>
        </div>'''

    input_strip = (
        inp_cell('OAA',  row.get('oaa',          None), 'Statcast') +
        inp_cell('FRV',  row.get('frv',          None), 'Statcast') +
        inp_cell('DRS*', row.get('drs',          None), 'SIS / BR') +
        inp_cell('Spd',  row.get('sprint_speed', None), 'ft / sec') +
        inp_cell('ARM',  row.get('arm_runs',     None), 'Runs') +
        inp_cell('FRM',  row.get('framing_runs', None), 'C only')
    )
    # Remove border-right from last cell
    input_strip = input_strip[:input_strip.rfind('border-right:0.5px solid #e5e7eb')] +                   input_strip[input_strip.rfind('border-right:0.5px solid #e5e7eb') + len('border-right:0.5px solid #e5e7eb'):]

    na_reasons = {
        'rraa':         '1B only' if pos != '1B' else None,
        'framing_runs': 'C only'  if pos != 'C'  else None,
    }

    components = [
        ('Conversion Runs',       'conversion_runs',    'How well this fielder converts chances they attempt. Derived from OAA and FRV.'),
        ('Attempt Range Score',   'attempt_range_score','Expands or shrinks opportunity set vs. league avg. Neighbor-adjusted.'),
        ('Receiving Runs AA',     'rraa',               '(1B only) Value on throws from infielders.'),
        ('Baserunner Adv. Prev.', 'bap',                'Suppresses extra-base advancement via positioning and deterrence.'),
        ('Arm Runs',              'arm_runs',           'Direct throwing value, separate from BAP deterrence.'),
        ('Framing Runs',          'framing_runs',       '(C only) Pitch framing run value above average.'),
        ('Stadium Correction',    'stadium_correction', 'Gameday coordinate bias adjustment.'),
    ]

    comp_vals = {col: row.get(col, None) for _, col, _ in components}
    valid_vals = [abs(float(v)) for _, col, _ in components
                  for v in [comp_vals[col]]
                  if v is not None and not (isinstance(v, float) and np.isnan(v))
                  and not na_reasons.get(col)]
    max_abs = max(valid_vals) if valid_vals else 5.0
    max_abs = max(max_abs, 3.0)

    breakdown_rows = ''
    for label, col_key, desc in components:
        val = comp_vals[col_key]
        na = na_reasons.get(col_key)
        if na:
            continue  # hide N/A rows entirely
        if val is None or (isinstance(val, float) and np.isnan(val)):
            continue  # hide missing data
        # Hide stadium correction when it's zero (no adjustment needed for this team)
        if col_key == 'stadium_correction' and abs(float(val)) < 0.01:
            continue
        v = float(val)
        col = '#059669' if v > 0 else ('#dc2626' if v < 0 else '#6b7280')
        sign = '+' if v > 0 else ''
        bar_pct = min(abs(v) / max_abs * 88, 88)
        breakdown_rows += f'''
        <div style="margin-bottom:15px;">
          <div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:3px;">
            <span style="font-size:13px;font-weight:500;color:#111827;">{label}</span>
            <span style="font-size:14px;font-weight:500;color:{col};">{sign}{v:.1f}</span>
          </div>
          <div style="font-size:11px;color:#6b7280;margin-bottom:5px;line-height:1.4;">{desc}</div>
          <div style="background:#f3f4f6;border-radius:3px;height:6px;overflow:hidden;">
            <div style="width:{bar_pct:.1f}%;height:100%;background:{col};border-radius:3px;"></div>
          </div>
        </div>'''

    def inp_cmp(label, col_key, src, val):
        if val is None or (isinstance(val, float) and np.isnan(val)):
            return ''
        v = float(val)
        sign = '+' if v > 0 else ''
        bg  = '#d1fae5' if v > 0 else ('#fee2e2' if v < 0 else '#f3f4f6')
        tc  = '#065f46' if v > 0 else ('#991b1b' if v < 0 else '#374151')
        return f'''
        <div style="display:flex;justify-content:space-between;align-items:center;padding:7px 0;border-bottom:0.5px solid #f3f4f6;">
          <div>
            <div style="font-size:13px;font-weight:500;color:#111827;">{label}</div>
            <div style="font-size:11px;color:#9ca3af;">{src}</div>
          </div>
          <span style="font-size:13px;font-weight:500;padding:3px 10px;border-radius:4px;background:{bg};color:{tc};">{sign}{v:.1f}</span>
        </div>'''

    input_cmp = (
        inp_cmp('OAA',  'oaa', 'Outs Above Average · Statcast',    row.get('oaa', None)) +
        inp_cmp('FRV',  'frv', 'Fielding Run Value · Statcast',    row.get('frv', None)) +
        inp_cmp('DRS*', 'drs', 'Def. Runs Saved · SIS/BR',         row.get('drs', None))
    )

    html = f'''<div style="background:#ffffff;border:0.5px solid #e5e7eb;border-radius:12px;overflow:hidden;font-family:system-ui,sans-serif;max-width:900px;">

  <div style="background:#0a0e1a;padding:20px 24px 16px;">
    <div style="display:flex;justify-content:space-between;align-items:flex-start;">
      <div>
        <div style="font-size:11px;font-weight:500;letter-spacing:0.18em;color:#00c97a;text-transform:uppercase;margin-bottom:6px;">RCDef</div>
        <div style="font-size:26px;font-weight:500;color:#f4f5f7;letter-spacing:0.02em;line-height:1;">{player_name.upper()}</div>
        <div style="font-size:12px;color:#6b7280;margin-top:5px;letter-spacing:0.04em;">{team} &nbsp;·&nbsp; {POSITIONS.get(pos, pos)} &nbsp;·&nbsp; {inn:.0f} inn &nbsp;·&nbsp; {year} Season</div>
        {disagree_html}
      </div>
      <div style="text-align:right;flex-shrink:0;margin-left:20px;">
        <div style="font-size:10px;letter-spacing:0.15em;color:#6b7280;text-transform:uppercase;">RCDef</div>
        <div style="font-size:32px;font-weight:500;color:{rcdef_col};line-height:1;">{rcdef_str}</div>
        <div style="font-size:11px;color:#6b7280;margin-top:2px;">{context}</div>
        <div style="margin-top:6px;"><span style="display:inline-block;font-size:10px;font-weight:500;letter-spacing:0.08em;padding:3px 9px;border-radius:4px;background:{rel_bg};color:{rel_tc};">{reliability.upper()} RELIABILITY</span></div>
      </div>
    </div>
  </div>

  <div style="height:3px;background:#00c97a;"></div>

  <div style="background:#f9fafb;padding:12px 24px 10px;border-bottom:0.5px solid #e5e7eb;">
    <div style="font-size:10px;letter-spacing:0.12em;color:#6b7280;text-transform:uppercase;margin-bottom:6px;">Position percentile — RCDef+</div>
    <div style="background:#e5e7eb;border-radius:4px;height:10px;position:relative;overflow:hidden;">
      <div style="height:100%;width:{pct_val:.1f}%;background:{pct_col};border-radius:4px;"></div>
      <div style="position:absolute;top:0;left:50%;width:1px;height:100%;background:rgba(0,0,0,0.2);"></div>
    </div>
    <div style="display:flex;justify-content:space-between;font-size:10px;color:#9ca3af;margin-top:3px;">
      <span>0th</span><span style="color:{pct_col};font-weight:500;">{pct_str}</span><span>100th</span>
    </div>
  </div>

  <div style="display:grid;grid-template-columns:repeat(6,1fr);border-bottom:0.5px solid #e5e7eb;background:#ffffff;">
    {input_strip}
  </div>

  <div style="display:grid;grid-template-columns:3fr 2fr;background:#ffffff;">

    <div style="padding:18px 20px;border-right:0.5px solid #e5e7eb;">
      <div style="font-size:10px;letter-spacing:0.12em;text-transform:uppercase;color:#9ca3af;margin-bottom:14px;font-weight:500;">Component breakdown</div>
      {breakdown_rows}
    </div>

    <div style="padding:18px 18px;background:#ffffff;">
      <div style="font-size:10px;letter-spacing:0.12em;text-transform:uppercase;color:#9ca3af;margin-bottom:10px;font-weight:500;">Component radar</div>
      <svg viewBox="0 0 200 175" style="width:100%;max-width:220px;display:block;margin:0 auto 16px;">
        <defs><style>.rl{{fill:none;stroke:#e5e7eb;stroke-width:0.75}}.rt{{font-size:9px;fill:#9ca3af;text-anchor:middle;font-family:system-ui,sans-serif}}</style></defs>
        <g transform="translate(100,88)">
          <polygon points="0,-60 52,-30 52,30 0,60 -52,30 -52,-30" class="rl"/>
          <polygon points="0,-40 34.6,-20 34.6,20 0,40 -34.6,20 -34.6,-20" class="rl"/>
          <polygon points="0,-20 17.3,-10 17.3,10 0,20 -17.3,10 -17.3,-10" class="rl"/>
          <line x1="0" y1="-60" x2="0" y2="60" class="rl"/>
          <line x1="52" y1="-30" x2="-52" y2="30" class="rl"/>
          <line x1="52" y1="30" x2="-52" y2="-30" class="rl"/>
          <polygon points="{_radar_pts(row, max_abs)}" style="fill:rgba(5,150,105,0.15);stroke:#059669;stroke-width:1.5;stroke-linejoin:round"/>
          {_radar_dots(row, max_abs)}
          <text x="0" y="-67" class="rt">Conv. Runs</text>
          <text x="62" y="-33" class="rt" style="text-anchor:start">Att. Range</text>
          <text x="62" y="38" class="rt" style="text-anchor:start">BAP</text>
          <text x="0" y="74" class="rt">Arm Runs</text>
          <text x="-62" y="38" class="rt" style="text-anchor:end">Stad. Adj.</text>
          <text x="-62" y="-33" class="rt" style="text-anchor:end">FRV</text>
        </g>
      </svg>

      <div style="font-size:10px;letter-spacing:0.12em;text-transform:uppercase;color:#9ca3af;margin-bottom:8px;font-weight:500;">Input metrics</div>
      {input_cmp}
      {speed_html}
      {nbr_html}
    </div>

  </div>

  <div style="background:#f9fafb;padding:7px 24px;font-size:10px;color:#9ca3af;border-top:0.5px solid #e5e7eb;">
    RCDef Composite Defensive Analytics &nbsp;·&nbsp; rcdefplus.streamlit.app &nbsp;·&nbsp; *DRS &copy; Sports Info Solutions / Baseball Reference &nbsp;·&nbsp; Non-commercial
  </div>

</div>'''
    return html


def _radar_pts(row, max_abs):
    """Calculate radar polygon points from component values."""
    # 6 axes: Conv.Runs(top), Att.Range(top-right), BAP(bot-right), Arm(bot), Stad(bot-left), FRV(top-left)
    axes = [
        row.get('conversion_runs', 0),
        row.get('attempt_range_score', 0),
        row.get('bap', 0),
        row.get('arm_runs', 0),
        row.get('stadium_correction', 0),
        row.get('frv', 0),
    ]
    import math
    pts = []
    for i, v in enumerate(axes):
        try:
            v = float(v) if v is not None and not (isinstance(v, float) and math.isnan(v)) else 0.0
        except Exception:
            v = 0.0
        r = min(abs(v) / max(max_abs, 3) * 55, 55)
        angle = math.radians(-90 + i * 60)
        x = round(r * math.cos(angle), 1)
        y = round(r * math.sin(angle), 1)
        pts.append(f'{x},{y}')
    return ' '.join(pts)


def _radar_dots(row, max_abs):
    """Generate circle elements for radar vertices."""
    import math
    axes = [
        row.get('conversion_runs', 0),
        row.get('attempt_range_score', 0),
        row.get('bap', 0),
        row.get('arm_runs', 0),
        row.get('stadium_correction', 0),
        row.get('frv', 0),
    ]
    dots = ''
    for i, v in enumerate(axes):
        try:
            v = float(v) if v is not None and not (isinstance(v, float) and math.isnan(v)) else 0.0
        except Exception:
            v = 0.0
        r = min(abs(v) / max(max_abs, 3) * 55, 55)
        angle = math.radians(-90 + i * 60)
        x = round(r * math.cos(angle), 1)
        y = round(r * math.sin(angle), 1)
        dots += f'<circle cx="{x}" cy="{y}" r="3" fill="#059669"/>'
    return dots



def page_player_cards(df: pd.DataFrame, is_demo: bool, status: dict = None):
    """Player card page — full rich white-background layout with all charts."""
    if status is None: status = {}

    st.markdown('<div class="section-header">Player Cards</div>', unsafe_allow_html=True)

    if status.get('mode', 'demo') != 'live':
        st.markdown('<div class="warn-box">⚠ DEMO MODE — Synthetic data displayed.</div>',
                    unsafe_allow_html=True)

    player_names = sorted(df['player_name'].dropna().unique().tolist())
    selected_player = st.selectbox('Search Player', player_names, key='card_player')

    player_row = df[df['player_name'] == selected_player]
    if player_row.empty:
        st.warning('Player not found.')
        return

    row = player_row.iloc[0]

    # ── Pull key values ───────────────────────────────────────────────────────
    pos         = str(row.get('position', '?'))
    team        = str(row.get('team', '?'))
    inn         = float(row.get('innings', 0) or 0)
    year        = str(row.get('data_year', ''))
    rcdef       = row.get('rcdef', np.nan)
    rcdef_plus  = row.get('rcdef_plus', np.nan)
    reliability = str(row.get('reliability', 'Low'))
    disagree    = bool(row.get('disagreement_flag', False))
    disagree_detail = str(row.get('disagreement_detail', ''))
    context     = get_rcdef_context(rcdef)
    rcdef_str   = format_stat(rcdef)

    # ── White-background header card via components.html ─────────────────────
    import streamlit.components.v1 as components
    card_html = render_player_card_html(row, selected_player)
    full_html = f'''<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>* {{ box-sizing: border-box; }} body {{ margin:0; padding:4px 0; background:transparent; }}</style>
</head>
<body>{card_html}</body>
</html>'''
    components.html(full_html, height=660, scrolling=True)

    st.markdown('<br>', unsafe_allow_html=True)

    # ── Downloads ─────────────────────────────────────────────────────────────
    st.markdown('<br>', unsafe_allow_html=True)
    dl_c1, dl_c2 = st.columns(2)

    with dl_c1:
        jpg_bytes = build_player_card_jpg(row, selected_player)
        if jpg_bytes:
            safe_name = selected_player.replace(' ', '_').replace('.', '').replace("'", '')
            st.download_button(
                label='⬇ Download Player Card (.jpg)',
                data=jpg_bytes,
                file_name=f'rcdef_{safe_name}_{row.get("data_year","2025")}.jpg',
                mime='image/jpeg',
                use_container_width=True,
                key='dl_jpg',
            )
        else:
            st.error('JPG generation failed.')

    with dl_c2:
        player_csv = pd.DataFrame([row]).drop(
            columns=[c for c in ['is_demo', 'disagreement_detail', 'sample_size'] if c in row.index],
            errors='ignore'
        )
        st.download_button(
            label='⬇ Download Player Data (.csv)',
            data=player_csv.to_csv(index=False).encode('utf-8'),
            file_name=f'rcdef_{selected_player.replace(" ","_")}_{row.get("data_year","2025")}.csv',
            mime='text/csv',
            use_container_width=True,
            key='dl_player_csv',
        )


# ─────────────────────────────────────────────
# PAGE: TEAM DEFENSE
# ─────────────────────────────────────────────

def page_team_defense(df: pd.DataFrame, is_demo: bool, status: dict = None):
    """Team-level aggregate defensive view."""
    if status is None: status = {}

    st.markdown('<div class="section-header">Team Defense</div>', unsafe_allow_html=True)

    if status.get('mode', 'demo') != 'live':
        st.markdown('<div class="warn-box">⚠ DEMO MODE — Synthetic data displayed.</div>',
                    unsafe_allow_html=True)

    if 'team' not in df.columns or 'rcdef' not in df.columns:
        st.info('Team data unavailable.')
        return

    # Aggregate by team
    team_df = df.groupby('team').agg(
        total_rcdef=('rcdef', 'sum'),
        avg_rcdef=('rcdef', 'mean'),
        players=('player_name', 'count'),
        avg_oaa=('oaa', 'mean'),
        avg_frv=('frv', 'mean'),
        avg_drs=('drs', 'mean'),
        flagged=('disagreement_flag', 'sum'),
    ).reset_index()

    team_df = team_df.sort_values('total_rcdef', ascending=False)
    team_df['rank'] = range(1, len(team_df) + 1)

    # Team leaderboard chart
    fig = go.Figure(go.Bar(
        x=team_df['team'],
        y=team_df['total_rcdef'],
        marker_color=['#00d084' if v >= 0 else '#ff4757' for v in team_df['total_rcdef']],
        text=[format_stat(v, 1) for v in team_df['total_rcdef']],
        textposition='outside',
        textfont=dict(color='#e8eaf0', size=9, family='IBM Plex Mono'),
        hovertemplate='<b>%{x}</b><br>Total RCDef: %{y:.1f}<extra></extra>',
    ))

    fig.update_layout(
        paper_bgcolor='rgba(17,24,39,0)',
        plot_bgcolor='rgba(17,24,39,0.5)',
        height=350,
        margin=dict(l=20, r=20, t=20, b=40),
        xaxis=dict(
            tickfont=dict(color='#8892a4', size=9, family='IBM Plex Mono'),
            gridcolor='rgba(0,0,0,0)',
        ),
        yaxis=dict(
            gridcolor='rgba(255,255,255,0.06)',
            tickfont=dict(color='#8892a4', size=9, family='IBM Plex Mono'),
            title=dict(text='Total RCDef (Runs Above Avg)', font=dict(color='#8892a4', size=10)),
            zerolinecolor='rgba(255,255,255,0.2)',
        ),
    )

    st.plotly_chart(fig, use_container_width=True)

    # Team table
    display_team = team_df[['rank', 'team', 'total_rcdef', 'avg_rcdef', 'players', 'avg_oaa', 'avg_frv', 'flagged']].copy()
    display_team.columns = ['Rank', 'Team', 'Total RCDef', 'Avg RCDef', 'Players', 'Avg OAA', 'Avg FRV', '⚡ Flags']

    for col in ['Total RCDef', 'Avg RCDef', 'Avg OAA', 'Avg FRV']:
        display_team[col] = display_team[col].apply(lambda x: format_stat(x))

    st.dataframe(display_team, use_container_width=True, hide_index=True)

    # Position breakdown for selected team
    st.markdown('<br>', unsafe_allow_html=True)
    st.markdown('<div style="font-family:Bebas Neue;font-size:1.4rem;letter-spacing:0.1em;color:#e8eaf0;">TEAM DEEP DIVE</div>', unsafe_allow_html=True)

    selected_team = st.selectbox('Select Team', sorted(df['team'].dropna().unique()), key='team_select')
    team_players = df[df['team'] == selected_team].sort_values('rcdef', ascending=False)

    if team_players.empty:
        st.info('No data for selected team.')
        return

    fig2 = go.Figure(go.Bar(
        x=team_players['player_name'].apply(lambda n: n.split()[-1] + '\n' + team_players.loc[team_players['player_name'] == n, 'position'].iloc[0] if not team_players.loc[team_players['player_name'] == n, 'position'].empty else ''),
        y=team_players['rcdef'],
        marker_color=['#00d084' if v >= 0 else '#ff4757' for v in team_players['rcdef']],
        text=[format_stat(v, 1) for v in team_players['rcdef']],
        textposition='outside',
        textfont=dict(color='#e8eaf0', size=9, family='IBM Plex Mono'),
        hovertemplate='<b>%{x}</b><br>RCDef: %{y:.1f}<extra></extra>',
    ))

    fig2.update_layout(
        paper_bgcolor='rgba(17,24,39,0)',
        plot_bgcolor='rgba(17,24,39,0.5)',
        height=350,
        title=dict(text=f'{selected_team} — RCDef by Player', font=dict(color='#e8eaf0', size=14, family='Bebas Neue')),
        margin=dict(l=20, r=20, t=40, b=60),
        xaxis=dict(
            tickfont=dict(color='#8892a4', size=9, family='IBM Plex Mono'),
            gridcolor='rgba(0,0,0,0)',
        ),
        yaxis=dict(
            gridcolor='rgba(255,255,255,0.06)',
            tickfont=dict(color='#8892a4', size=9, family='IBM Plex Mono'),
            zerolinecolor='rgba(255,255,255,0.2)',
        ),
    )

    st.plotly_chart(fig2, use_container_width=True)


# ─────────────────────────────────────────────
# PAGE: METHODOLOGY
# ─────────────────────────────────────────────

def page_methodology():
    """Full methodology documentation."""

    st.markdown('<div class="section-header">Methodology</div>', unsafe_allow_html=True)

    st.markdown('''
    <div class="info-box" style="margin-bottom:2rem;">
    RCDef is an independent, non-commercial baseball defensive analytics tool.
    All methodology is published here in full. No black boxes.
    </div>
    ''', unsafe_allow_html=True)

    with st.expander('📐 What RCDef Measures', expanded=True):
        st.markdown('''
        **RCDef** measures fielder value in **runs above average**, combining multiple defensive components
        into a single number comparable to Defensive Runs Saved (DRS) and Fielding Run Value (FRV).

        **RCDef formula:**

        > RCDef = Conversion Runs + Attempt Range Score + RRAA*(1B only)* + BAP + Arm Runs + Stadium Correction

        **RCDef+** converts RCDef to a **position-specific percentile** (0–100).
        - 50 = average
        - 100 = best at position
        - 0 = worst at position

        **Scope:** Regular season only. Minimum 300 innings for full leaderboard. Multi-team seasons
        calculated separately by team and summed. Prorated by position for multi-position players.
        ''')

    with st.expander('🔄 Component: Conversion Runs (CR)'):
        st.markdown('''
        Conversion Runs measure how well a fielder converts the plays they attempt into outs,
        relative to average.

        **Source:** Weighted average of OAA (converted to runs) and FRV when both are available.
        When only one is available, that metric is used directly.

        **OAA-to-runs conversion:** Position-specific weights based on historical run expectancy:
        - Infielders (2B/SS/3B): ~0.73–0.74 runs per out above average
        - Corner infielders (1B/3B): ~0.65–0.72 runs per out above average
        - Outfielders: ~0.55–0.57 runs per out above average
        - Catchers: ~0.65 runs per out above average

        **Shift era:** Pre-2023 and post-2023 treated with separate positioning baselines,
        accounting for the shift ban implemented in 2023.
        ''')

    with st.expander('🎯 Component: Attempt Range Score (ARS)'):
        st.markdown('''
        Attempt Range Score measures whether a fielder **expands or shrinks their opportunity set**
        relative to league expectation. Conceptually derived from Baseball Prospectus's published
        Attempt Range methodology (Judge, 2023).

        **The core insight:** Infielders can control their own denominator. A fielder who only attempts
        routine plays looks better on conversion rate than one who attempts difficult plays. ARS
        credits fielders for attempting plays at the edge of their range zone.

        **Calculation:** For each ball type, bearing, and speed combination, we calculate the league
        average attempt rate at each position. Fielders who attempt plays at above-average rates
        in difficult zones receive positive ARS; those who shrink their zone receive negative ARS.

        **Neighbor Adjustment (Hybrid Model):**

        The field is divided into five directional buckets per position (hard left, soft left, straight,
        soft right, hard right), defined empirically from the Statcast population.

        Two conditions must trigger simultaneously for an adjustment:
        1. The fielder's attempt rate in a specific bucket is >1 SD below their own overall attempt rate
        2. Their positional neighbor's attempt rate in that same bucket is >1 SD above league average

        **Suppression adjustment:** When both conditions are met, a partial credit adjustment is applied,
        capped at 30% of estimated missed attempts, scaled to signal strength. Disclosed on player card.

        **Vacuum flag:** When a fielder's attempt rate appears inflated by a poor neighbor filling
        their zone less often, a warning flag is displayed. No correction is applied — transparency only.
        ''')

    with st.expander('🧤 Component: Receiving Runs Above Average (RRAA) — 1B Only'):
        st.markdown('''
        RRAA is an **original metric** addressing a documented gap in public defensive analytics:
        first base receiving quality has never been cleanly measured in a publicly available tool.

        **What RRAA measures:** The run value added or subtracted by a first baseman's ability
        to receive throws from infielders — specifically:
        - **Dirt ball / scoop plays:** Throws in the dirt requiring fielder to scoop
        - **Wide throws:** Throws pulling the fielder off the bag horizontally
        - **High throws:** Throws above the outstretched glove
        - **Stretch plays:** Close timing plays where reach maximization directly affects outcomes

        **Methodology:**
        1. Every throw to first base is classified by type and difficulty
        2. Expected catch probability calculated from throw characteristics (velocity, deviation from target)
        3. Fielder receives credit or debit: actual outcome minus expected probability
        4. **Responsibility threshold:** Throws beyond 3 standard deviations from mean throw location
           are assigned zero fielder responsibility (truly uncatchable throws)
        5. Run value conversion: each play worth approximately 0.4 runs on average

        **Minimum threshold:** 50 qualifying difficult throw attempts before RRAA displays.
        Below this threshold, RRAA shows as "—" due to sample size instability.

        **Note:** When raw Statcast play-by-play is unavailable (due to data pipeline limitations),
        RRAA is estimated from the FRV/OAA differential, which partially reflects receiving quality.
        Estimates are labeled accordingly.
        ''')

    with st.expander('🏃 Component: Baserunner Advancement Prevention (BAP)'):
        st.markdown('''
        BAP measures how well a fielder **suppresses extra-base advancement** — capturing value
        that neither OAA, FRV, nor Arm Runs fully account for.

        **Two sub-components:**
        1. **Positioning BAP:** The fielder reached the ball faster than average, compressing time
           available to the runner before they could decide to advance
        2. **Deterrence BAP:** Runners didn't attempt advancement based on the fielder's reputation
           for efficient release and accuracy (distinct from raw arm strength)

        **Methodology:**
        For each ball fielded, we calculate the expected advancement rate given:
        - Ball type and landing location
        - Runner speed
        - Runner starting base
        - Number of outs
        - Game state (score differential affects runner risk tolerance)

        The fielder is credited for suppressing advancement below expectation, or debited for
        allowing advancement above expectation.

        **Separate from Arm Runs:** ARM credits direct throws that retire runners or prevent
        advancement via throw velocity/accuracy. BAP credits the speed and efficiency component
        that happens before the throw decision is made.
        ''')

    with st.expander('💪 Component: Arm Runs (ARM)'):
        st.markdown('''
        ARM measures the direct throwing value separate from BAP deterrence effects.

        **Outfielders:** Sourced from Baseball Savant arm value leaderboard, which tracks
        outfielder assists, runs held, and throw accuracy.

        **Infielders:** Derived from assist/error data and throw velocity from Statcast.

        **Catchers:** Pop time converted to run value.
        - League average pop time: ~2.00 seconds
        - Each 0.1 second below average ≈ 0.8 additional runs
        - Values clipped at ±15 runs to prevent outlier distortion
        ''')

    with st.expander('🏟️ Stadium Correction (SC)'):
        st.markdown('''
        Applies a correction for known coordinate distortions in MLB's Gameday pixel system,
        as documented in Baseball Prospectus research (Judge, 2025).

        **Background:** MLB Gameday displays approximate ball landing locations using horizontal
        and vertical pixels estimated by stadium stringers. When converted to feet, certain
        stadiums show systematic biases — particularly the two Missouri stadiums (STL, KC)
        where lateral angles can be off by 5+ degrees.

        **Impact:** A 5-degree coordinate error can misrepresent a ground ball to the "5.5 hole"
        as a routine out for the shortstop — systematically penalizing or crediting fielders
        based on data error rather than performance.

        **Correction methodology:** Stadium-specific and position-specific correction factors
        derived from the Gameday pixel bias research. Applied before all other calculations.

        **Currently corrected stadiums:** STL, KC, LAA, ARI (others added as research identifies them)
        ''')

    with st.expander('⚡ Metric Disagreement Flag'):
        st.markdown(f'''
        When the top two input metrics (OAA, FRV, DRS) diverge by more than **{DISAGREEMENT_THRESHOLD} runs**,
        a disagreement flag is displayed.

        **Why metrics disagree:**
        - **OAA** uses actual fielder starting position from Statcast — excellent for measuring
          plays from where the fielder stood, but potentially missing fielder contribution to
          their own positioning
        - **FRV** is the run-value version of OAA with additional components
        - **DRS** uses video review and accounts for more play types including double plays,
          arm value, and good/defensive misplays — but is influenced by subjective video coding

        **What the flag means:** The flag does not indicate an error in RCDef. It signals genuine
        methodological disagreement that warrants additional context. The Brice Turang 2024 case
        is the canonical example: OAA saw him as slightly above average; DRS and updated RDA
        saw him as the best infielder in baseball. The disagreement reflects different questions
        being asked, not a measurement error.

        **Threshold:** {DISAGREEMENT_THRESHOLD} runs. Tunable based on observed distribution.
        ''')

    with st.expander('📊 Reliability Indicator'):
        st.markdown(f'''
        Each player receives a reliability rating based on sample size and data source availability:

        - **High:** 900+ innings AND 3+ input metrics available
        - **Medium:** 500+ innings AND 2+ input metrics available
        - **Low:** Below Medium thresholds

        **Why this matters:** Defensive metrics are notoriously unstable in small samples.
        A player at 300 innings (the minimum threshold) has a meaningfully wider confidence
        interval than one at 1,200 innings. The reliability indicator communicates this without
        requiring users to understand confidence intervals.

        **Minimum innings:** {MIN_INNINGS} innings for full leaderboard display.
        Players below this threshold appear in a separate limited-sample view.
        ''')

    with st.expander('📦 Data Sources & Attribution'):
        st.markdown('''
        **Primary data sources:**

        | Source | Data | License |
        |--------|------|---------|
        | MLB / Baseball Savant | OAA, FRV, Sprint Speed, Arm Data, Framing | Public / Statcast |
        | Baseball Reference | DRS display | Non-commercial attribution |
        | Sports Info Solutions | DRS (underlying) | Proprietary — displayed via BR |

        **DRS Attribution:** Defensive Runs Saved data displayed in this tool is the property of
        Sports Info Solutions (SIS) and accessed via Baseball Reference. This is a non-commercial,
        non-monetized tool displaying DRS for reference and comparison purposes only.
        All DRS values are attributed to SIS/Baseball Reference throughout.

        **Original components:** Conversion Runs, Attempt Range Score (with neighbor adjustment),
        Receiving Runs Above Average, Baserunner Advancement Prevention, and Arm Runs (catcher
        component) are calculated independently from publicly available Statcast data.

        **Methodology influences:** The Attempt Range Score methodology is conceptually derived from
        Baseball Prospectus's published Range Defense Added (RDA) research (Jonathan Judge, 2023, 2025).
        BP's specific RDA values are not used directly; the methodology is applied independently
        to public Statcast data.

        **Update frequency:** Data refreshes nightly during the regular season via GitHub Actions.
        Offseason refresh: weekly.
        ''')

    with st.expander('⚠️ Known Limitations'):
        st.markdown('''
        The following limitations are acknowledged and disclosed:

        1. **First base receiving (RRAA):** When raw Statcast play-by-play is unavailable in the
           live pipeline (due to data volume), RRAA is estimated from the FRV/OAA differential.
           Full RRAA from raw throw data requires the full Statcast download. Estimates are labeled.

        2. **RRAA responsibility threshold:** Throws beyond 3 SD from mean location are assigned
           zero fielder responsibility. This threshold is conservative and could be refined.

        3. **Catcher framing context:** Framing runs are influenced by pitcher stuff quality.
           A catcher framing elite breaking balls will register differently than one framing
           flat fastballs. Statcast's framing metric attempts to control for this but limitations remain.

        4. **Pitcher fielding:** Not included in version 1.0. Small run value but nonzero.
           Planned for future versions.

        5. **Infield pop-up coverage:** Not included in version 1.0. Who calls off whom on
           shallow pop-ups is a real skill not captured here.

        6. **Outfield communication zones:** Balls where two outfielders have a reasonable play
           are assigned to the fielder who makes the attempt. The deterrence/deference effect
           is not measured.

        7. **Neighbor vacuum adjustment:** When a fielder appears to benefit from a poor neighbor's
           vacancy, we flag but do not correct. Overcorrecting risks penalizing genuinely elite
           fielders who play next to poor teammates.

        8. **DRS unavailability:** DRS (Defensive Runs Saved) is proprietary to Sports Info Solutions.
           It is displayed where available via Baseball Reference under non-commercial attribution.
           It is not included in the RCDef composite calculation.

        9. **Pre-Statcast years:** OAA and FRV only exist from 2015 onward. Earlier seasons would
           require UZR or Total Zone as inputs, which have different methodological assumptions.
           Not supported in version 1.0.
        ''')


# ─────────────────────────────────────────────
# MAIN APP
# ─────────────────────────────────────────────

def main():

    # Header
    st.markdown('''
    <div class="rcdef-header">
        <div class="rcdef-logo">RCDef</div>
        <div class="rcdef-tagline">Composite Defensive Analytics · 2025–2026</div>
    </div>
    ''', unsafe_allow_html=True)

    # Sidebar navigation
    with st.sidebar:
        st.markdown('''
        <div style="font-family:Bebas Neue;font-size:1.5rem;letter-spacing:0.15em;color:#00d084;
        padding:1rem 0 0.5rem;border-bottom:1px solid #1e2d42;margin-bottom:1rem;">
        NAVIGATION
        </div>
        ''', unsafe_allow_html=True)

        page = st.radio(
            '',
            ['Leaderboard', 'Player Cards', 'Team Defense', 'Methodology'],
            key='nav_page',
            label_visibility='collapsed'
        )

        st.markdown('<br>', unsafe_allow_html=True)
        st.markdown('''
        <div style="font-family:Bebas Neue;font-size:1.2rem;letter-spacing:0.1em;color:#8892a4;
        padding:0.5rem 0;border-bottom:1px solid #1e2d42;margin-bottom:1rem;">
        ABOUT RCDEF
        </div>
        ''', unsafe_allow_html=True)

        st.markdown('''
        <div style="font-family:IBM Plex Mono;font-size:0.68rem;color:#4a5568;line-height:1.7;">
        RCDef combines OAA, FRV, DRS, and original components into a single runs-above-average metric.<br><br>
        <span style="color:#00d084;">RCDef</span> = Runs above average<br>
        <span style="color:#3498db;">RCDef+</span> = Position percentile<br>
        <span style="color:#a29bfe;">RRAA</span> = Receiving runs (1B)<br>
        <span style="color:#ffd32a;">BAP</span> = Baserunner prevention<br><br>
        Non-commercial. All methodology published.<br><br>
        DRS data © Sports Info Solutions / Baseball Reference
        </div>
        ''', unsafe_allow_html=True)

        st.markdown('<br>', unsafe_allow_html=True)

        # Year selector in sidebar
        year = st.selectbox('Season', CURRENT_YEARS, key='sidebar_year')

        # Refresh button
        if st.button('🔄 Refresh Data', use_container_width=True):
            # Clear ALL cached data — forces fresh fetch from all sources
            st.cache_data.clear()
            st.rerun()

        # Hard cache bust — use when app is stuck in demo mode despite live data
        if st.button('🗑️ Clear Cache & Reload', use_container_width=True, 
                     help='Use this if app is stuck showing DEMO MODE incorrectly'):
            st.cache_data.clear()
            st.session_state.clear()
            st.rerun()

    # Load data
    with st.spinner('Loading defensive data...'):
        df, status = build_master_dataset(year, _cache_version=CACHE_VERSION)

    # Determine demo mode from status only — never from df column
    # (is_demo column in df can be stale from a cached previous run)
    # Clean stale demo artifacts from status if pipeline succeeded
    _pipeline_mode = status.get('mode', 'demo')
    if _pipeline_mode == 'live':
        status.pop('demo_reason', None)
        status.pop('traceback', None)
    # is_demo is ONLY True when pipeline explicitly returned mode != 'live'
    is_demo = (_pipeline_mode != 'live')
    # Store for diagnostics
    status['_computed_is_demo'] = is_demo
    status['_pipeline_mode'] = _pipeline_mode

    if df is None or (hasattr(df, 'empty') and df.empty):
        try:
            df = build_demo_dataset(year)
            is_demo = True
            if 'demo_reason' not in status:
                status['demo_reason'] = 'Emergency fallback'
        except Exception as e:
            st.error(f'Unable to load data even in demo mode: {e}')
            return

    # Show traceback in expander if pipeline crashed
    if status.get('traceback'):
        with st.expander('⚠ Pipeline error details (for debugging)', expanded=True):
            st.code(status.get('traceback', ''), language='python')
            st.markdown('**Please share this with the developer.**')

    # Data source diagnostics in sidebar (always visible)
    with st.sidebar:
        st.markdown('''
        <div style="font-family:Bebas Neue;font-size:1.0rem;letter-spacing:0.1em;color:#4a5568;
        padding:1rem 0 0.5rem;border-top:1px solid #1e2d42;margin-top:1rem;">
        DATA SOURCES
        </div>
        ''', unsafe_allow_html=True)

        source_info = [
            ('OAA',     status.get('oaa',     {})),
            ('FRV',     status.get('frv',     {})),
            ('DRS',     status.get('drs',     {})),
            ('Sprint',  status.get('sprint',  {})),
            ('Arm',     status.get('arm',     {})),
            ('Framing', status.get('framing', {})),
        ]
        for src_name, src_status in source_info:
            rows = src_status.get('rows', 0)
            ok = rows > 3
            dot = '🟢' if ok else '🔴'
            st.markdown(
                f'''<div style="font-family:IBM Plex Mono;font-size:0.65rem;color:{'#00d084' if ok else '#ff4757'};">
                {dot} {src_name}: {rows} rows</div>''',
                unsafe_allow_html=True
            )

        mode = status.get('mode', 'demo')
        base = status.get('base_source', 'none')
        st.markdown(
            f'''<div style="font-family:IBM Plex Mono;font-size:0.6rem;color:#4a5568;margin-top:0.5rem;">
            Mode: {mode.upper()} | Base: {base}</div>''',
            unsafe_allow_html=True
        )

        st.markdown('<br>', unsafe_allow_html=True)

        # ── Diagnostics download — always available ────────────────────────
        try:
            diag_rows = []
            diag_rows.append({'key': 'mode',          'value': status.get('mode', 'unknown')})
            diag_rows.append({'key': 'base_source',   'value': status.get('base_source', 'none')})
            diag_rows.append({'key': 'last_updated',  'value': status.get('last_updated', 'unknown')})
            diag_rows.append({'key': 'demo_reason',   'value': status.get('demo_reason', '')})
            diag_rows.append({'key': 'traceback',     'value': status.get('traceback', '')})
            diag_rows.append({'key': 'frv_estimated', 'value': str(status.get('frv_estimated', False))})
            diag_rows.append({'key': 'innings_estimated', 'value': str(status.get('innings_estimated', False))})
            diag_rows.append({'key': 'adaptive_threshold', 'value': str(status.get('adaptive_threshold', ''))})
            for src_name, src_status in source_info:
                diag_rows.append({
                    'key': f'{src_name}_rows',
                    'value': str(src_status.get('rows', 0))
                })
            # Add column lists
            for col_key in ['oaa_cols', 'frv_cols', 'speed_cols', 'arm_cols', 'framing_cols']:
                diag_rows.append({
                    'key': col_key,
                    'value': str(status.get(col_key, []))
                })
            # Add full dataframe if available
            if not df.empty:
                full_diag = df.copy()
                for row in diag_rows:
                    full_diag[f'_diag_{row["key"]}'] = row['value']
            else:
                full_diag = pd.DataFrame(diag_rows)

            diag_bytes = full_diag.to_csv(index=False).encode('utf-8')
            st.download_button(
                label='⬇ Diagnostics CSV',
                data=diag_bytes,
                file_name=f'rcdef_diagnostics_{year}.csv',
                mime='text/csv',
                use_container_width=True,
                key='sidebar_diag_dl',
            )
        except Exception as diag_e:
            st.caption(f'Diagnostics error: {diag_e}')

    # Route to page
    if page == 'Leaderboard':
        page_leaderboard(df, status, is_demo)
    elif page == 'Player Cards':
        page_player_cards(df, is_demo, status)
    elif page == 'Team Defense':
        page_team_defense(df, is_demo, status)
    elif page == 'Methodology':
        page_methodology()


if __name__ == '__main__':
    main()

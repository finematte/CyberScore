"""
CyberScore - Information Security Maturity Assessment Tool
Streamlit Frontend Application with User Authentication
"""

import os
import time
import threading

# Apply Streamlit secrets to environment before any backend/config imports.
# On Streamlit Community Cloud, set Secrets (e.g. database URL, secret_key) in app dashboard.
try:
    import streamlit as st

    if hasattr(st, "secrets") and st.secrets:
        # Optional: [database] url = "sqlite:///./cyberscore.db" or MySQL URL
        db = st.secrets.get("database", {})
        if db and isinstance(db, dict):
            url = db.get("url")
            if url:
                os.environ.setdefault("DATABASE_URL", str(url))
        # Optional: [connections.mysql] style (Streamlit docs) -> DATABASE_URL
        mysql = st.secrets.get("connections", {}).get("mysql", {})
        if mysql and isinstance(mysql, dict) and not os.environ.get("DATABASE_URL"):
            from urllib.parse import quote_plus

            user = mysql.get("username", "")
            pwd = mysql.get("password", "")
            host = mysql.get("host", "localhost")
            port = mysql.get("port", 3306)
            dbname = mysql.get("database", "")
            os.environ.setdefault(
                "DATABASE_URL",
                f"mysql+pymysql://{quote_plus(user)}:{quote_plus(pwd)}@{host}:{port}/{dbname}",
            )
        # JWT secret (required for auth in production)
        sec = st.secrets.get("secrets", {})
        if sec and isinstance(sec, dict):
            sk = sec.get("secret_key")
            if sk and len(sk) >= 32:
                os.environ.setdefault("SECRET_KEY", sk)
except Exception:
    pass

import secrets as _secrets
import streamlit as st
import streamlit.components.v1 as _components
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
from datetime import datetime

# Configuration: backend runs in-process on Streamlit Cloud (see _ensure_backend)
API_BASE_URL = os.environ.get("API_BASE_URL", "http://127.0.0.1:8000")


# ---------------------------------------------------------------------------
# st.cache_resource keeps objects alive across ALL Streamlit reruns & sessions
# for the lifetime of the server process.  Module-level variables are reset on
# every rerun, so we must NOT use them for anything that needs to survive.
# ---------------------------------------------------------------------------
@st.cache_resource
def _start_backend():
    """Start FastAPI backend in a daemon thread (runs exactly once per process)."""
    base = API_BASE_URL or ""
    if "127.0.0.1" not in base and "localhost" not in base:
        return True

    def _run_uvicorn():
        import uvicorn
        uvicorn.run("backend.api:app", host="127.0.0.1", port=8000, log_level="warning")

    t = threading.Thread(target=_run_uvicorn, daemon=True)
    t.start()
    for _ in range(30):
        try:
            r = requests.get("http://127.0.0.1:8000/health", timeout=1)
            if r.status_code == 200:
                return True
        except Exception:
            time.sleep(0.2)
    return True


def _ensure_backend():
    _start_backend()


@st.cache_resource
def _get_session_store() -> dict:
    """Process-wide session store that survives Streamlit reruns."""
    return {}


# ---------------------------------------------------------------------------
# Session persistence: survive page refreshes via server-side session store
# and a short opaque session ID kept in st.query_params.
# ---------------------------------------------------------------------------
def _save_session():
    """Persist current auth state so it survives a browser refresh."""
    if not (st.session_state.get("authenticated") and st.session_state.get("user_token")):
        return
    store = _get_session_store()
    sid = st.session_state.get("_sid")
    if not sid:
        sid = _secrets.token_urlsafe(16)
        st.session_state._sid = sid
    store[sid] = {
        "token": st.session_state.user_token,
        "user_info": st.session_state.user_info,
        "lang": st.session_state.get("lang", "en"),
    }
    st.query_params["sid"] = sid


def _restore_session():
    """On fresh page load, try to restore auth from the session store."""
    try:
        store = _get_session_store()
        sid = st.query_params.get("sid")
        if sid and sid in store:
            sess = store[sid]
            st.session_state.authenticated = True
            st.session_state.user_token = sess["token"]
            st.session_state.user_info = sess["user_info"]
            st.session_state.lang = sess.get("lang", "en")
            st.session_state._sid = sid
            return True
    except Exception:
        pass
    return False


def _clear_session():
    """Remove session from store and URL on logout."""
    store = _get_session_store()
    sid = st.session_state.get("_sid")
    if sid:
        store.pop(sid, None)
    st.session_state._sid = None
    st.query_params.clear()


# ---------------------------------------------------------------------------
# Scroll helper — st.markdown strips <script> tags; components.html works.
# A unique key forces Streamlit to re-render the component (and re-run the
# script) every time instead of caching the previous iframe.
# ---------------------------------------------------------------------------
def _scroll_to_top():
    n = st.session_state.get("_scroll_n", 0) + 1
    st.session_state._scroll_n = n
    _components.html(
        f"""<script>
        // {n}
        function doScroll() {{
            const selectors = [
                'section.main',
                '[data-testid="stAppViewContainer"]',
                '[data-testid="stVerticalBlock"]',
                '.main'
            ];
            for (const sel of selectors) {{
                const el = window.parent.document.querySelector(sel);
                if (el) {{ el.scrollTop = 0; el.scrollTo({{top: 0}}); }}
            }}
            window.parent.document.documentElement.scrollTop = 0;
            window.parent.document.body.scrollTop = 0;
        }}
        doScroll();
        setTimeout(doScroll, 100);
        setTimeout(doScroll, 300);
        </script>""",
        height=0,
    )


# --- Translations (EN/PL) ---
def _load_ui_translations():
    path = os.path.join(os.path.dirname(__file__), "translations", "ui.json")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {"en": {}, "pl": {}}


def _load_content_pl():
    path = os.path.join(os.path.dirname(__file__), "translations", "content_pl.json")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {}


def _get_ui():
    if "ui_translations" not in st.session_state:
        st.session_state.ui_translations = _load_ui_translations()
    return st.session_state.ui_translations


def _get_content_pl():
    if "content_pl" not in st.session_state:
        st.session_state.content_pl = _load_content_pl()
    return st.session_state.content_pl


def t(key, **kwargs):
    """Return translated string for current language. Use {placeholder} in JSON for kwargs."""
    lang = st.session_state.get("lang", "en")
    ui = _get_ui()
    s = ui.get(lang, ui.get("en", {})).get(key, key)
    if kwargs:
        try:
            return s.format(**kwargs)
        except Exception:
            return s
    return s


def _tr_area(area):
    """Return (name, description) for area in current language."""
    lang = st.session_state.get("lang", "en")
    if lang != "pl":
        return area.get("name", ""), area.get("description", "")
    pl = _get_content_pl().get("areas", {}).get(area.get("area_id", ""), {})
    return pl.get("name", area.get("name", "")), pl.get(
        "description", area.get("description", "")
    )


def _tr_question(q):
    """Return (text, description) for question in current language."""
    lang = st.session_state.get("lang", "en")
    if lang != "pl":
        return q.get("question_text", ""), q.get("description", "")
    pl = _get_content_pl().get("questions", {}).get(q.get("question_id", ""), {})
    return pl.get("text", q.get("question_text", "")), pl.get(
        "description", q.get("description", "")
    )


def _tr_recommendation(rec):
    """Return (title, description, improvement_tips) for recommendation in current language."""
    lang = st.session_state.get("lang", "en")
    if lang != "pl":
        return (
            rec.get("title", ""),
            rec.get("description", ""),
            rec.get("improvement_tips", ""),
        )
    pl = (
        _get_content_pl().get("recommendations", {}).get(rec.get("question_id", ""), {})
    )
    return (
        pl.get("title", rec.get("title", "")),
        pl.get("description", rec.get("description", "")),
        pl.get("improvement_tips", rec.get("improvement_tips", "")),
    )


def _tr_maturity_scale():
    """Return dict of maturity scale 0-5 for current language."""
    lang = st.session_state.get("lang", "en")
    if lang != "pl":
        return None
    return _get_content_pl().get("maturity_scale", {})


def _date_fmt(dt):
    """Format date for current language."""
    lang = st.session_state.get("lang", "en")
    if lang != "pl":
        return dt.strftime("%B %d, %Y")
    months_pl = [
        "stycznia",
        "lutego",
        "marca",
        "kwietnia",
        "maja",
        "czerwca",
        "lipca",
        "sierpnia",
        "września",
        "października",
        "listopada",
        "grudnia",
    ]
    return f"{dt.day} {months_pl[dt.month - 1]} {dt.year}"


st.set_page_config(
    page_title="CyberScore",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS
st.markdown(
    """
<style>
    .main-header {
        font-size: 3rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
        font-weight: 700;
    }
    .sub-header {
        font-size: 1.5rem;
        color: #2c3e50;
        margin-top: 2rem;
        margin-bottom: 1rem;
        font-weight: 600;
    }
    .stButton > button {
        border-radius: 8px;
        font-weight: 500;
        transition: all 0.3s ease;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    .stSelectbox > div > div {
        border-radius: 8px;
    }
    .stTextInput > div > div > input {
        border-radius: 8px;
    }
    .stSlider > div > div > div {
        border-radius: 8px;
    }
    .home-card {
        display: flex;
        flex-direction: column;
        height: 100%;
    }
    .home-card-content {
        flex-grow: 1;
    }
    .home-card h3 {
        margin-bottom: 0.25rem;
    }
    .home-card p {
        margin-bottom: 0.5rem;
    }
    .score-card {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
        margin: 1rem 0;
    }
    .report-header {
        background: linear-gradient(135deg, #1a2332 0%, #2c3e50 100%);
        color: #ffffff;
        padding: 2rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
    }
    .report-header h2 { color: #ffffff !important; margin: 0 0 0.25rem 0; font-size: 1.6rem; }
    .report-header p { color: #a8b8c8; margin: 0; font-size: 0.9rem; }
    .score-ring {
        width: 160px; height: 160px;
        border-radius: 50%;
        display: flex; flex-direction: column;
        align-items: center; justify-content: center;
        margin: 0 auto;
    }
    .score-ring .score-value { font-size: 2.5rem; font-weight: 700; line-height: 1; }
    .score-ring .score-label { font-size: 0.85rem; margin-top: 4px; font-weight: 500; }
    .exec-summary {
        font-size: 0.95rem;
        line-height: 1.6;
        color: #c8d6e0;
    }
    .stat-card {
        text-align: center;
        padding: 1rem 0.5rem;
        background: rgba(255,255,255,0.05);
        border-radius: 8px;
        border: 1px solid rgba(255,255,255,0.1);
    }
    .stat-card .stat-value { font-size: 1.6rem; font-weight: 700; color: #ffffff; }
    .stat-card .stat-label { font-size: 0.75rem; color: #a8b8c8; text-transform: uppercase; letter-spacing: 0.5px; }
    .area-card {
        padding: 1rem 1.2rem;
        border-radius: 8px;
        border-left: 5px solid;
        margin-bottom: 0.6rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .area-card-light { background: #f8f9fa; }
    .area-card .area-name { font-weight: 600; font-size: 0.95rem; }
    .area-card .area-score { font-weight: 700; font-size: 1.1rem; }
    .area-card .area-level { font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.5px; opacity: 0.8; }
    .progress-bar-bg {
        height: 8px; background: #e9ecef; border-radius: 4px;
        flex: 1; margin: 0 1rem; min-width: 100px;
    }
    .progress-bar-fill { height: 100%; border-radius: 4px; transition: width 0.5s ease; }
    .recommendation-card {
        padding: 1.2rem;
        border-radius: 8px;
        border-left: 4px solid #ffc107;
        margin: 0.5rem 0;
        color: #212529 !important;
    }
    .recommendation-card h4 { color: #212529 !important; margin-top: 0; }
    .recommendation-card p, .recommendation-card ul, .recommendation-card li { color: #212529 !important; }
    .recommendation-card .ref-list { font-size: 0.85rem; }
    .recommendation-card .ref-list li { margin-bottom: 2px; }
    .high-priority {
        border-left-color: #dc3545 !important;
        background-color: #f8d7da !important;
        color: #721c24 !important;
    }
    .high-priority h4, .high-priority p, .high-priority ul, .high-priority li { color: #721c24 !important; }
    .medium-priority {
        border-left-color: #ffc107 !important;
        background-color: #fff3cd !important;
        color: #856404 !important;
    }
    .medium-priority h4, .medium-priority p, .medium-priority ul, .medium-priority li { color: #856404 !important; }
    .low-priority {
        border-left-color: #28a745 !important;
        background-color: #d4edda !important;
        color: #155724 !important;
    }
    .low-priority h4, .low-priority p, .low-priority ul, .low-priority li { color: #155724 !important; }
    .priority-tag {
        display: inline-block; padding: 2px 10px; border-radius: 12px;
        font-size: 0.7rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;
        margin-left: 8px; vertical-align: middle;
    }
    .tag-high { background: #dc3545; color: #fff; }
    .tag-medium { background: #ffc107; color: #212529; }
    .tag-low { background: #28a745; color: #fff; }
    .top-action-card {
        background: linear-gradient(135deg, #1a2332 0%, #2c3e50 100%);
        color: #ffffff; padding: 1.2rem; border-radius: 10px;
        border-left: 5px solid; height: 100%;
    }
    .top-action-card h4 { color: #ffffff !important; margin: 0 0 0.5rem 0; font-size: 0.95rem; }
    .top-action-card p { color: #c8d6e0 !important; font-size: 0.85rem; margin: 0; }
    .top-action-card .action-num {
        font-size: 2rem; font-weight: 800; opacity: 0.3; position: absolute; top: 8px; right: 16px;
    }
    /* Dark mode */
    @media (prefers-color-scheme: dark) {
        [data-testid="stApp"] .score-card { background-color: #1e1e1e !important; border-left-color: #4a9eff !important; }
        [data-testid="stApp"] .area-card-light { background: #1e1e1e !important; }
        [data-testid="stApp"] .recommendation-card { background-color: #332d1a !important; color: #fafafa !important; }
        [data-testid="stApp"] .recommendation-card h4, [data-testid="stApp"] .recommendation-card p,
        [data-testid="stApp"] .recommendation-card ul, [data-testid="stApp"] .recommendation-card li { color: #fafafa !important; }
        [data-testid="stApp"] .high-priority { background-color: #3d1a1a !important; }
        [data-testid="stApp"] .high-priority h4, [data-testid="stApp"] .high-priority p,
        [data-testid="stApp"] .high-priority ul, [data-testid="stApp"] .high-priority li { color: #f5c6cb !important; }
        [data-testid="stApp"] .medium-priority { background-color: #332d1a !important; }
        [data-testid="stApp"] .medium-priority h4, [data-testid="stApp"] .medium-priority p,
        [data-testid="stApp"] .medium-priority ul, [data-testid="stApp"] .medium-priority li { color: #ffeeba !important; }
        [data-testid="stApp"] .low-priority { background-color: #1a2e1a !important; }
        [data-testid="stApp"] .low-priority h4, [data-testid="stApp"] .low-priority p,
        [data-testid="stApp"] .low-priority ul, [data-testid="stApp"] .low-priority li { color: #c3e6cb !important; }
        [data-testid="stApp"] .progress-bar-bg { background: #333 !important; }
    }
    [data-testid="stApp"][data-theme="dark"] .score-card, [data-theme="dark"] .score-card {
        background-color: #1e1e1e !important; border-left-color: #4a9eff !important;
    }
    [data-testid="stApp"][data-theme="dark"] .area-card-light, [data-theme="dark"] .area-card-light {
        background: #1e1e1e !important;
    }
    [data-testid="stApp"][data-theme="dark"] .recommendation-card, [data-theme="dark"] .recommendation-card {
        background-color: #332d1a !important; color: #fafafa !important;
    }
    [data-testid="stApp"][data-theme="dark"] .recommendation-card h4,
    [data-testid="stApp"][data-theme="dark"] .recommendation-card p,
    [data-testid="stApp"][data-theme="dark"] .recommendation-card ul,
    [data-testid="stApp"][data-theme="dark"] .recommendation-card li,
    [data-theme="dark"] .recommendation-card h4, [data-theme="dark"] .recommendation-card p,
    [data-theme="dark"] .recommendation-card ul, [data-theme="dark"] .recommendation-card li {
        color: #fafafa !important;
    }
    [data-testid="stApp"][data-theme="dark"] .high-priority, [data-theme="dark"] .high-priority {
        background-color: #3d1a1a !important;
    }
    [data-testid="stApp"][data-theme="dark"] .high-priority h4, [data-testid="stApp"][data-theme="dark"] .high-priority p,
    [data-testid="stApp"][data-theme="dark"] .high-priority ul, [data-testid="stApp"][data-theme="dark"] .high-priority li,
    [data-theme="dark"] .high-priority h4, [data-theme="dark"] .high-priority p,
    [data-theme="dark"] .high-priority ul, [data-theme="dark"] .high-priority li {
        color: #f5c6cb !important;
    }
    [data-testid="stApp"][data-theme="dark"] .medium-priority, [data-theme="dark"] .medium-priority {
        background-color: #332d1a !important;
    }
    [data-testid="stApp"][data-theme="dark"] .medium-priority h4, [data-testid="stApp"][data-theme="dark"] .medium-priority p,
    [data-testid="stApp"][data-theme="dark"] .medium-priority ul, [data-testid="stApp"][data-theme="dark"] .medium-priority li,
    [data-theme="dark"] .medium-priority h4, [data-theme="dark"] .medium-priority p,
    [data-theme="dark"] .medium-priority ul, [data-theme="dark"] .medium-priority li {
        color: #ffeeba !important;
    }
    [data-testid="stApp"][data-theme="dark"] .low-priority, [data-theme="dark"] .low-priority {
        background-color: #1a2e1a !important;
    }
    [data-testid="stApp"][data-theme="dark"] .low-priority h4, [data-testid="stApp"][data-theme="dark"] .low-priority p,
    [data-testid="stApp"][data-theme="dark"] .low-priority ul, [data-testid="stApp"][data-theme="dark"] .low-priority li,
    [data-theme="dark"] .low-priority h4, [data-theme="dark"] .low-priority p,
    [data-theme="dark"] .low-priority ul, [data-theme="dark"] .low-priority li {
        color: #c3e6cb !important;
    }
    [data-testid="stApp"][data-theme="dark"] .progress-bar-bg, [data-theme="dark"] .progress-bar-bg {
        background: #333 !important;
    }
    .auth-container {
        max-width: 400px;
        margin: 0 auto;
        padding: 2rem;
        background-color: #f8f9fa;
        border-radius: 0.5rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .user-info {
        background-color: #216ca3;
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    /* Ensure buttons align at consistent distance from text */
    /* Make columns flex containers so buttons can sit at the bottom */
    [data-testid="column"] {
        display: flex;
        flex-direction: column;
    }

    /* Make sure normal Streamlit blocks don't stretch weirdly */
    [data-testid="column"] > div {
        flex: 0 0 auto;
    }

    /* Push the last button in each column to the bottom */
    [data-testid="column"] .stButton {
        margin-top: auto;
    }
    .maturity-scale {
        background-color: #f8f9fa;
        border: 1px solid #dee2e6;
        border-radius: 8px;
        padding: 1rem;
        margin: 0.5rem 0;
        font-size: 0.9rem;
        color: #262730;
    }
    /* Dark mode support - Streamlit uses [data-testid="stApp"] with dark theme */
    [data-testid="stApp"][data-theme="dark"] .maturity-scale,
    .stApp[data-theme="dark"] .maturity-scale,
    [data-theme="dark"] .maturity-scale {
        background-color: #0e1117 !important;
        border-color: #404040 !important;
        color: #fafafa !important;
    }
    /* Also support system dark mode preference */
    @media (prefers-color-scheme: dark) {
        [data-testid="stApp"] .maturity-scale {
            background-color: #0e1117 !important;
            border-color: #404040 !important;
            color: #fafafa !important;
        }
    }
    .maturity-scale-item {
        padding: 0.25rem 0;
        border-bottom: 1px solid #e9ecef;
        color: inherit;
    }
    [data-testid="stApp"][data-theme="dark"] .maturity-scale-item,
    .stApp[data-theme="dark"] .maturity-scale-item,
    [data-theme="dark"] .maturity-scale-item {
        border-bottom-color: #404040 !important;
        color: #fafafa !important;
    }
    /* Also support system dark mode preference for items */
    @media (prefers-color-scheme: dark) {
        [data-testid="stApp"] .maturity-scale-item {
            border-bottom-color: #404040 !important;
            color: #fafafa !important;
        }
    }
    .maturity-scale-item:last-child {
        border-bottom: none;
    }
    .maturity-scale-label {
        font-weight: 600;
        color: #1f77b4;
        display: inline-block;
        min-width: 20px;
    }
    /* Dark mode label color - brighter blue for visibility */
    [data-testid="stApp"][data-theme="dark"] .maturity-scale-label,
    .stApp[data-theme="dark"] .maturity-scale-label,
    [data-theme="dark"] .maturity-scale-label {
        color: #4a9eff !important;
    }
    /* Also support system dark mode preference for labels */
    @media (prefers-color-scheme: dark) {
        [data-testid="stApp"] .maturity-scale-label {
            color: #4a9eff !important;
        }
    }
</style>
""",
    unsafe_allow_html=True,
)


def make_api_request(endpoint, method="GET", data=None, token=None):
    """Make API request with error handling and authentication"""
    try:
        url = f"{API_BASE_URL}{endpoint}"
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"

        if method == "GET":
            response = requests.get(url, headers=headers, timeout=10)
        elif method == "POST":
            response = requests.post(url, json=data, headers=headers, timeout=10)
        elif method == "PUT":
            response = requests.put(url, json=data, headers=headers, timeout=10)
        elif method == "DELETE":
            response = requests.delete(url, headers=headers, timeout=10)
        else:
            return None

        if response.status_code == 200:
            return response.json()
        elif response.status_code == 401:
            st.error("Authentication failed. Please login again.")
            _clear_session()
            st.session_state.authenticated = False
            st.session_state.user_token = None
            st.session_state.user_info = None
            return None
        elif response.status_code == 403:
            st.error("Access denied. You don't have permission to perform this action.")
            return None
        elif response.status_code == 404:
            st.error("Resource not found. Please try again.")
            return None
        elif response.status_code >= 500:
            st.error("Server error. Please try again later.")
            return None
        else:
            st.error(f"API Error: {response.status_code} - {response.text}")
            return None

    except requests.exceptions.ConnectionError:
        st.error(
            "Cannot connect to the API server. Please make sure the backend is running."
        )
        return None
    except requests.exceptions.Timeout:
        st.error("Request timed out. Please try again.")
        return None
    except Exception as e:
        st.error(f"Error: {str(e)}")
        return None


@st.cache_data(show_spinner=False)
def fetch_assessment_with_questions(assessment_id: int, token: str):
    """Cache assessment + areas/questions to avoid refetch on every rerun"""
    return make_api_request(
        f"/assessments/{assessment_id}/questions",
        token=token,
    )


def clear_assessment_cache():
    """Clear cached assessment data (useful when starting new assessment)"""
    fetch_assessment_with_questions.clear()


SHORT_AREA_NAMES = {
    "Governance & Risk Oversight": "Governance",
    "Identify – Assets, Risk & Business Context": "Identify",
    "Protect – Access Control, Awareness & Data Protection": "Protect",
    "Detect – Monitoring, Logging & Anomaly Detection": "Detect",
    "Respond – Incident Response & Reporting": "Respond",
    "Recover – Business Continuity & Resilience": "Recover",
}


def _short_name(full_name: str) -> str:
    return SHORT_AREA_NAMES.get(
        full_name, full_name.split(" – ")[0] if " – " in full_name else full_name
    )


def _extract_area_data(area_scores):
    areas, scores = [], []
    for s in area_scores:
        if isinstance(s, dict):
            areas.append(s.get("area_name", "Unknown"))
            scores.append(float(s.get("score", 0)))
        else:
            areas.append(getattr(s.area, "name", "Unknown"))
            scores.append(float(getattr(s, "score", 0)))
    return areas, scores


def _score_color(score: float) -> str:
    if score < 40:
        return "#dc3545"
    elif score < 70:
        return "#ffc107"
    else:
        return "#28a745"


def _maturity_label(score: float) -> str:
    if score < 40:
        return "Low"
    elif score < 70:
        return "Medium"
    else:
        return "High"


def create_radar_chart(area_scores):
    if not area_scores:
        return None
    areas, scores = _extract_area_data(area_scores)
    short = [_short_name(a) for a in areas]

    short_closed = short + [short[0]]
    scores_closed = scores + [scores[0]]

    fig = go.Figure()
    fig.add_trace(
        go.Scatterpolar(
            r=scores_closed,
            theta=short_closed,
            fill="toself",
            name="Your Score",
            line=dict(color="#3b82f6", width=3),
            fillcolor="rgba(59,130,246,0.15)",
        )
    )
    fig.add_trace(
        go.Scatterpolar(
            r=[70] * len(short_closed),
            theta=short_closed,
            fill="none",
            name="Target (70%)",
            line=dict(color="#ef4444", dash="dash", width=2),
        )
    )
    fig.add_trace(
        go.Scatterpolar(
            r=[40] * len(short_closed),
            theta=short_closed,
            fill="none",
            name="Minimum (40%)",
            line=dict(color="#f59e0b", dash="dot", width=2),
        )
    )
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                tickmode="linear",
                tick0=0,
                dtick=20,
                tickfont=dict(size=10),
                gridcolor="rgba(128,128,128,0.2)",
            ),
            angularaxis=dict(tickfont=dict(size=13)),
            bgcolor="rgba(0,0,0,0)",
        ),
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.15,
            xanchor="center",
            x=0.5,
            font=dict(size=11),
        ),
        height=420,
        margin=dict(t=30, b=60, l=60, r=60),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def create_bar_chart(area_scores):
    if not area_scores:
        return None
    areas, scores = _extract_area_data(area_scores)

    paired = sorted(zip(areas, scores), key=lambda x: x[1])
    areas_sorted = [p[0] for p in paired]
    scores_sorted = [p[1] for p in paired]
    short_sorted = [_short_name(a) for a in areas_sorted]
    colors = [_score_color(s) for s in scores_sorted]

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            y=short_sorted,
            x=scores_sorted,
            orientation="h",
            marker=dict(color=colors, line=dict(width=0)),
            text=[f"  {s:.0f}%" for s in scores_sorted],
            textposition="outside",
            textfont=dict(size=13),
            hovertemplate="<b>%{y}</b><br>Score: %{x:.1f}%<extra></extra>",
        )
    )
    fig.add_vline(
        x=70,
        line_dash="dash",
        line_color="#ef4444",
        line_width=2,
        annotation=dict(text="Target 70%", font=dict(size=11, color="#ef4444")),
    )
    fig.add_vline(
        x=40,
        line_dash="dot",
        line_color="#f59e0b",
        line_width=2,
        annotation=dict(text="Min 40%", font=dict(size=11, color="#f59e0b")),
    )

    fig.update_layout(
        xaxis=dict(
            title="Score (%)",
            range=[0, 110],
            tickmode="linear",
            tick0=0,
            dtick=20,
            gridcolor="rgba(128,128,128,0.15)",
        ),
        yaxis=dict(tickfont=dict(size=13)),
        height=350,
        margin=dict(t=20, b=50, l=10, r=40),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        bargap=0.35,
    )
    return fig


def main():
    # Initialize session state
    fresh = "authenticated" not in st.session_state
    if fresh:
        st.session_state.authenticated = False
    if "user_token" not in st.session_state:
        st.session_state.user_token = None
    if "user_info" not in st.session_state:
        st.session_state.user_info = None
    if "current_page" not in st.session_state:
        st.session_state.current_page = "Home"
    if "show_auth_modal" not in st.session_state:
        st.session_state.show_auth_modal = False
    if "lang" not in st.session_state:
        st.session_state.lang = "en"

    # Restore login session after a page refresh
    if fresh and not st.session_state.authenticated:
        _restore_session()

    # Header
    st.markdown('<h1 class="main-header">🛡️ CyberScore</h1>', unsafe_allow_html=True)
    st.markdown(
        f'<p style="text-align: center; font-size: 1.2rem; color: #666;">{t("app_subtitle")}</p>',
        unsafe_allow_html=True,
    )

    # Show main app with authentication overlay if needed
    show_main_app()


def show_auth_modal():
    """Show authentication modal"""
    # Create a clean authentication section
    st.markdown("---")

    # Header with close button
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("✕", key="close_auth", help=t("close")):
            st.session_state.show_auth_modal = False
            st.rerun()

    # Determine which tab to show
    auth_mode = st.session_state.get("auth_mode", "login")

    if auth_mode == "login":
        show_login_form()
    else:
        show_register_form()


def show_login_form():
    """Show login form"""
    # Create a nice container for the form
    with st.container():
        st.markdown(f"### {t('login_title')}")

        with st.form("login_form_modal"):
            email_or_username = st.text_input(
                t("email_or_username"), placeholder=t("email_or_username_placeholder")
            )
            password = st.text_input(
                t("password"), type="password", placeholder=t("password_placeholder")
            )
            login_submitted = st.form_submit_button(
                t("login_submit"), type="primary", use_container_width=True
            )

            if login_submitted:
                if email_or_username and password:
                    login_data = {
                        "email_or_username": email_or_username,
                        "password": password,
                    }

                    result = make_api_request("/login", "POST", login_data)
                    if result:
                        st.session_state.authenticated = True
                        st.session_state.user_token = result["access_token"]
                        st.session_state.user_info = result["user"]
                        st.session_state.show_auth_modal = False
                        _save_session()
                        st.success(t("login_success"))
                        st.rerun()
                    else:
                        st.error(t("login_failed"))
                else:
                    st.error(t("fill_all_fields"))

    # Switch to register
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button(
            t("no_account"),
            key="switch_to_register",
            use_container_width=True,
        ):
            st.session_state.auth_mode = "register"
            st.rerun()


def show_register_form():
    """Show register form"""
    # Create a nice container for the form
    with st.container():
        st.markdown(f"### {t('register_title')}")

        with st.form("register_form_modal"):
            username = st.text_input(
                t("username"), placeholder=t("username_placeholder")
            )
            email = st.text_input(t("email"), placeholder=t("email_placeholder"))
            password = st.text_input(
                t("password"), type="password", placeholder=t("password_create")
            )
            confirm_password = st.text_input(
                t("confirm_password"),
                type="password",
                placeholder=t("confirm_password_placeholder"),
            )
            register_submitted = st.form_submit_button(
                t("register_submit"), type="primary", use_container_width=True
            )

            if register_submitted:
                if username and email and password and confirm_password:
                    if password == confirm_password:
                        register_data = {
                            "username": username,
                            "email": email,
                            "password": password,
                        }

                        result = make_api_request("/register", "POST", register_data)
                        if result:
                            st.success(t("register_success"))
                            st.session_state.auth_mode = "login"
                            st.rerun()
                        else:
                            st.error(t("register_failed"))
                    else:
                        st.error(t("passwords_no_match"))
                else:
                    st.error(t("fill_all_fields"))

    # Switch to login
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button(
            t("have_account"),
            key="switch_to_login",
            use_container_width=True,
        ):
            st.session_state.auth_mode = "login"
            st.rerun()


def show_unauthorized_page(page_key):
    """Show unauthorized access page. page_key: e.g. page_assessment, page_my_assessments, page_results."""
    page_name = t(page_key)
    st.markdown(
        f"""
    ## 🔒 {t("auth_required_title")}
    
    {t("auth_required_message", page_name=page_name)}
    
    {t("auth_required_instruction")}
    """
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button(
            t("login"),
            type="primary",
            use_container_width=True,
            key="unauthorized_login",
        ):
            st.session_state.show_auth_modal = True
            st.session_state.auth_mode = "login"
            st.session_state.scroll_to_top = True
            st.rerun()
    with col2:
        if st.button(
            t("register"), use_container_width=True, key="unauthorized_register"
        ):
            st.session_state.show_auth_modal = True
            st.session_state.auth_mode = "register"
            st.session_state.scroll_to_top = True
            st.rerun()


def show_main_app():
    """Show main application"""
    _ensure_backend()
    # Sidebar
    st.sidebar.title(t("nav_title"))

    # Language switcher
    lang_col1, lang_col2 = st.sidebar.columns(2)
    with lang_col1:
        if st.sidebar.button(
            "EN",
            key="lang_en",
            use_container_width=True,
            type="primary" if st.session_state.get("lang") == "en" else "secondary",
        ):
            st.session_state.lang = "en"
            _save_session()
            st.rerun()
    with lang_col2:
        if st.sidebar.button(
            "PL",
            key="lang_pl",
            use_container_width=True,
            type="primary" if st.session_state.get("lang") == "pl" else "secondary",
        ):
            st.session_state.lang = "pl"
            _save_session()
            st.rerun()

    # Authentication status and controls
    if st.session_state.authenticated and st.session_state.user_info:
        st.sidebar.markdown(
            f"""
        <div class="user-info">
            <strong>{t('welcome', username=st.session_state.user_info['username'])}</strong>
        </div>
        """,
            unsafe_allow_html=True,
        )

        # Logout button
        if st.sidebar.button(f"🚪 {t('logout')}", use_container_width=True):
            _clear_session()
            st.session_state.authenticated = False
            st.session_state.user_token = None
            st.session_state.user_info = None
            st.session_state.current_page = "Home"
            st.rerun()
    else:
        # Login/Register buttons for unauthenticated users
        st.sidebar.markdown(f"### {t('account')}")
        col1, col2 = st.sidebar.columns(2)
        with col1:
            if st.button(t("login"), use_container_width=True):
                st.session_state.show_auth_modal = True
                st.session_state.auth_mode = "login"
                st.session_state.scroll_to_top = True
                st.rerun()
        with col2:
            if st.button(t("register"), use_container_width=True):
                st.session_state.show_auth_modal = True
                st.session_state.auth_mode = "register"
                st.session_state.scroll_to_top = True
                st.rerun()

    # Navigation
    _page_options = [
        "Home",
        "Take Assessment",
        "My Assessments",
        "View Results",
        "About",
    ]
    _page_labels = [
        t("page_home"),
        t("page_assessment"),
        t("page_my_assessments"),
        t("page_results"),
        t("page_about"),
    ]
    page = st.sidebar.selectbox(
        t("choose_page"),
        _page_options,
        index=(
            _page_options.index(st.session_state.current_page)
            if st.session_state.current_page in _page_options
            else 0
        ),
        format_func=lambda x: _page_labels[_page_options.index(x)],
    )

    # Update session state when page changes
    if page != st.session_state.current_page:
        st.session_state.current_page = page
        st.rerun()

    # Show authentication modal if needed
    if st.session_state.show_auth_modal:
        show_auth_modal()

    # Display the selected page
    if st.session_state.current_page == "Home":
        show_home_page()
    elif st.session_state.current_page == "Take Assessment":
        if st.session_state.authenticated:
            show_assessment_page()
        else:
            show_unauthorized_page("page_assessment")
    elif st.session_state.current_page == "My Assessments":
        if st.session_state.authenticated:
            show_my_assessments_page()
        else:
            show_unauthorized_page("page_my_assessments")
    elif st.session_state.current_page == "View Results":
        if st.session_state.authenticated:
            show_results_page()
        else:
            show_unauthorized_page("page_results")
    elif st.session_state.current_page == "About":
        show_about_page()

    # Catch-all: scroll after ALL page content is rendered
    if st.session_state.get("scroll_to_top", False):
        _scroll_to_top()
        st.session_state.scroll_to_top = False


def show_home_page():
    """Display home page"""
    lang = st.session_state.get("lang", "en")

    # Welcome message based on authentication status
    if st.session_state.authenticated and st.session_state.user_info:
        username = st.session_state.user_info.get("username", "")
        st.markdown(f"## {t('home_welcome_back', username=username)}")
        st.markdown(t("home_welcome_back_intro"))
    else:
        st.markdown(f"## {t('home_welcome_guest')}")
        st.markdown(t("home_intro_guest"))

    if lang == "pl":
        home_body = _get_content_pl().get("home_body", "")
        if home_body:
            st.markdown(home_body)
    else:
        st.markdown(
            """
        It's a lightweight cybersecurity posture assessment tool that helps you understand where your organisation stands in terms of cybersecurity maturity. 
        
        It is built around international frameworks and regulations, including:
        
        - **ISO/IEC 27001** – information security management systems  
        - **NIST Cybersecurity Framework** – identify, protect, detect, respond, recover  
        - **CIS Controls v8** – practical technical and organisational safeguards  
        - **NIS2 Directive** – EU requirements for risk management and incident reporting
        
        ### What you do
        
        1. **Answer the questionnaire** – 36 questions across six key areas of cybersecurity  
        2. **Get a score** – weighted maturity scores calculated per area and overall  
        3. **Review the results** – clear breakdown of strengths and gaps  
        4. **Act on recommendations** – concrete next steps mapped to ISO, NIST, CIS and NIS2 references
        
        ### Security areas covered
        
        - **Governance & Risk Oversight** – roles, responsibilities and decision-making  
        - **Asset & Risk Management** – business context, critical assets and risk handling  
        - **Access & Data Protection** – access control, data protection and user awareness  
        - **Monitoring & Threat Detection** – logging, monitoring and anomaly detection  
        - **Incident Response & Communication** – handling incidents and required notifications  
        - **Business Continuity & Recovery** – continuity planning, backups and restoration
        
        ### Your final report combines these into area scores and an overall CyberScore, together with tailored improvement actions.
        ---
        """
        )

    # Action buttons based on authentication status
    # Action buttons based on authentication status
    if st.session_state.authenticated:
        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown(
                f"""
                <div class="home-card">
                  <div class="home-card-content">
                    <h3>{t("page_assessment")}</h3>
                    <p>{t("home_card_assessment_desc")}</p>
                  </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button(
                t("start_new"),
                type="primary",
                use_container_width=True,
                key="start_assessment_btn",
            ):
                st.session_state.current_page = "Take Assessment"
                st.session_state.scroll_to_top = True
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        with col2:
            st.markdown(
                f"""
                <div class="home-card">
                  <div class="home-card-content">
                    <h3>{t("page_my_assessments")}</h3>
                    <p>{t("home_card_my_desc")}</p>
                  </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button(
                t("page_my_assessments"),
                use_container_width=True,
                key="my_assessments_btn",
            ):
                st.session_state.current_page = "My Assessments"
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        with col3:
            st.markdown(
                f"""
                <div class="home-card">
                  <div class="home-card-content">
                    <h3>{t("home_card_about_title")}</h3>
                    <p>{t("home_card_about_desc")}</p>
                  </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button(
                t("home_card_about_btn"),
                use_container_width=True,
                key="about_btn",
            ):
                st.session_state.current_page = "About"
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
    else:
        # For unauthenticated users
        st.markdown(f"### {t('get_started')}")
        col1, col2 = st.columns(2)

        with col1:
            st.markdown(
                f"""
                **{t("home_guest_cta_title")}**
                
                {t("home_guest_cta_desc")}
                """
            )
            if st.button(t("login_to_start"), type="primary", use_container_width=True):
                st.session_state.show_auth_modal = True
                st.session_state.auth_mode = "login"
                st.session_state.scroll_to_top = True
                st.rerun()

        with col2:
            st.markdown(
                """
                **New to CyberScore?**
                
                Learn more about our assessment methodology and the international standards we follow.
                """
            )
            if st.button(t("learn_more"), use_container_width=True):
                st.session_state.current_page = "About"
                st.rerun()


def show_my_assessments_page():
    """Display user's assessments"""
    st.markdown(
        f'<h2 class="sub-header">{t("my_assessments")}</h2>', unsafe_allow_html=True
    )

    # Get user's assessments
    assessments = make_api_request("/my-assessments", token=st.session_state.user_token)

    if not assessments:
        st.info(t("no_assessments"))
        return

    st.info(t("found_assessments", n=len(assessments)))

    # Display assessments in a table
    assessment_data = []
    for assessment in assessments:
        # Handle score formatting safely
        try:
            if (
                assessment["total_score"] is not None
                and str(assessment["total_score"]).strip() != ""
            ):
                score_display = f"{float(assessment['total_score']):.1f}%"
            else:
                score_display = "Not scored"
        except (ValueError, TypeError):
            score_display = "Not scored"

        assessment_data.append(
            {
                "ID": assessment["id"],
                "Title": assessment["title"],
                "Status": assessment["status"],
                "Score": score_display,
                "Maturity": (
                    assessment["maturity_level"]
                    if assessment["maturity_level"]
                    else "N/A"
                ),
                "Created": (
                    assessment["created_at"][:10] if assessment["created_at"] else "N/A"
                ),
            }
        )

    df = pd.DataFrame(assessment_data)
    st.dataframe(df, use_container_width=True)

    # Select assessment to view results
    st.markdown(f"### {t('view_assessment_results')}")
    selected_id = st.selectbox(
        t("select_assessment_prompt"),
        [a["id"] for a in assessments],
        format_func=lambda x: f"Assessment {x} - {next(a['title'] for a in assessments if a['id'] == x)}",
    )

    if st.button(t("view_results"), type="primary"):
        st.session_state.selected_assessment_id = selected_id
        st.session_state.current_page = "View Results"
        st.rerun()


def show_assessment_page():
    """Display assessment page - SIMPLE VERSION"""
    st.markdown(
        f'<h2 class="sub-header">{t("assessment_page_title")}</h2>',
        unsafe_allow_html=True,
    )

    # Initialize session state
    if "assessment_id" not in st.session_state:
        st.session_state.assessment_id = None
    if "current_area" not in st.session_state:
        st.session_state.current_area = 0
    if "answers" not in st.session_state:
        st.session_state.answers = {}
    if "completed_assessment_id" not in st.session_state:
        st.session_state.completed_assessment_id = None

    # Create new assessment
    if st.session_state.assessment_id is None:
        starting_assesment_info = st.info(t("starting_assessment"))

        # Check if user info is available
        if not st.session_state.user_info or "id" not in st.session_state.user_info:
            st.error("User information not available. Please login again.")
            st.session_state.authenticated = False
            st.rerun()

        # Create assessment
        assessment_data = {
            "user_id": st.session_state.user_info["id"],
            "title": f"Assessment - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        }

        result = make_api_request(
            "/assessments", "POST", assessment_data, st.session_state.user_token
        )
        if result:
            st.session_state.assessment_id = result["id"]
            # Clear cache for new assessment to ensure fresh data
            clear_assessment_cache()
            st.session_state.scroll_to_top = True
            assesment_created_info = st.success(
                t("assessment_created", id=st.session_state.assessment_id)
            )
        else:
            st.error(t("create_failed"))
            return

        if starting_assesment_info:
            starting_assesment_info.empty()
        if assesment_created_info:
            assesment_created_info.empty()

    # Get assessment data (cached to avoid duplicate requests)
    assessment_data = fetch_assessment_with_questions(
        st.session_state.assessment_id,
        st.session_state.user_token,
    )
    if not assessment_data:
        st.error("Failed to load assessment data")
        return

    areas = assessment_data["areas"]

    # Validate areas exist
    if not areas or len(areas) == 0:
        st.error(t("no_areas_found"))
        return

    # Validate and clamp current_area to valid range
    if st.session_state.current_area < 0:
        st.session_state.current_area = 0
    elif st.session_state.current_area >= len(areas):
        st.session_state.current_area = len(areas) - 1

    # Progress bar
    total_questions = sum(len(area["questions"]) for area in areas)
    answered_questions = len(st.session_state.answers)
    progress = answered_questions / total_questions if total_questions > 0 else 0

    st.progress(progress)
    st.write(
        t("progress_questions", answered=answered_questions, total=total_questions)
    )

    # Display questions for current area (no selectbox to avoid conflicts)
    area = areas[st.session_state.current_area]

    # Validate area has questions
    if not area.get("questions") or len(area["questions"]) == 0:
        st.warning(f"Area '{area['name']}' has no questions. Skipping to next area...")
        if st.session_state.current_area < len(areas) - 1:
            st.session_state.current_area += 1
            st.rerun()
        return

    area_name, area_desc = _tr_area(area)
    # Show current area info with navigation
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        st.markdown(
            f"**{t('area_of', current=st.session_state.current_area + 1, total=len(areas))}**"
        )
    with col2:
        st.markdown(f"### {area_name}")
    with col3:
        if st.session_state.current_area < len(areas) - 1:
            next_name, _ = _tr_area(areas[st.session_state.current_area + 1])
            st.markdown(f"**{t('next_area', name=next_name)}**")
        else:
            st.markdown(f"**{t('final_area')}**")

    st.markdown(f"*{area_desc}*")

    # Show progress for current area
    current_area_questions = [q["id"] for q in area["questions"]]
    answered_in_area = sum(
        1 for qid in current_area_questions if qid in st.session_state.answers
    )
    area_progress = (
        answered_in_area / len(current_area_questions) if current_area_questions else 0
    )

    # Questions - FORM-BASED APPROACH (no immediate processing)
    with st.form(f"area_{st.session_state.current_area}_form"):
        for i, question in enumerate(area["questions"]):
            question_id = question["id"]

            # Get current answer
            current_answer = st.session_state.answers.get(question_id, {})
            if isinstance(current_answer, dict):
                current_score = current_answer.get("score", 0)
            else:
                current_score = current_answer if isinstance(current_answer, int) else 0

            # Ensure current_score is an integer
            current_score = int(current_score) if current_score is not None else 0

            # Question container with better styling
            with st.container():
                # Check if question is answered
                is_answered = question_id in st.session_state.answers
                # status_icon = "✅" if is_answered else "⭕"

                q_text, q_desc = _tr_question(question)
                # Display question text
                st.markdown(f"**{q_text}**")
                if q_desc:
                    st.markdown(f"*{q_desc}*")

                # Maturity scale reference (collapsible)
                scale_pl = _tr_maturity_scale()
                scale_lines = ""
                if scale_pl:
                    for k in ["0", "1", "2", "3", "4", "5"]:
                        scale_lines += f'<div class="maturity-scale-item"><span class="maturity-scale-label">{k}:</span> {scale_pl.get(k, "")}</div>'
                else:
                    scale_lines = """
                        <div class="maturity-scale-item"><span class="maturity-scale-label">0:</span> Not implemented – no formal practices or processes in place.</div>
                        <div class="maturity-scale-item"><span class="maturity-scale-label">1:</span> Ad hoc – practices are reactive, informal, and not consistently applied.</div>
                        <div class="maturity-scale-item"><span class="maturity-scale-label">2:</span> Partially defined – some processes are documented but applied inconsistently.</div>
                        <div class="maturity-scale-item"><span class="maturity-scale-label">3:</span> Defined and implemented – processes are documented, communicated, and generally followed across the organization.</div>
                        <div class="maturity-scale-item"><span class="maturity-scale-label">4:</span> Measured and monitored – processes are regularly reviewed, measured, and improved based on performance metrics.</div>
                        <div class="maturity-scale-item"><span class="maturity-scale-label">5:</span> Optimized – processes are proactive, continuously improved, and fully aligned with business and risk management objectives.</div>
                    """
                with st.expander(t("maturity_scale_ref"), expanded=False):
                    st.markdown(
                        f'<div class="maturity-scale">{scale_lines}</div>',
                        unsafe_allow_html=True,
                    )

                # Score slider - NO IMMEDIATE PROCESSING
                score = st.slider(
                    t("score_0_5"),
                    min_value=0,
                    max_value=5,
                    value=current_score,
                    key=f"question_{question_id}",
                    help=t("score_help"),
                )

                # Store answer in session state (no immediate processing)
                st.session_state.answers[question_id] = {"score": score}

                # Add spacing between questions
                if i < len(area["questions"]) - 1:
                    st.markdown("---")

        # Form submit button
        col1, col2 = st.columns(2)

        with col1:
            if st.session_state.current_area > 0:
                if st.form_submit_button(
                    f"← {t('previous_area')}", use_container_width=True
                ):
                    st.session_state.current_area = st.session_state.current_area - 1
                    st.session_state.scroll_to_top = True
                    st.rerun()

        with col2:
            if st.session_state.current_area < len(areas) - 1:
                if st.form_submit_button(
                    f"{t('next_area_btn')} →", use_container_width=True
                ):
                    st.session_state.current_area = st.session_state.current_area + 1
                    st.session_state.scroll_to_top = True
                    st.rerun()
            else:
                if st.form_submit_button(
                    t("submit_finish"), type="primary", use_container_width=True
                ):
                    # Use a single status container to manage all messages
                    status_container = st.empty()

                    try:
                        # Step 1: Processing message
                        with status_container.container():
                            st.info(t("processing"))

                        # Save final answers
                        answers_data = []
                        for (
                            question_id,
                            answer_data,
                        ) in st.session_state.answers.items():
                            answers_data.append(
                                {
                                    "assessment_id": st.session_state.assessment_id,
                                    "question_id": question_id,
                                    "score": answer_data["score"],
                                }
                            )

                        # Step 2: Save answers
                        save_result = make_api_request(
                            "/answers/bulk",
                            "POST",
                            {
                                "assessment_id": st.session_state.assessment_id,
                                "answers": answers_data,
                            },
                            st.session_state.user_token,
                        )

                        if save_result:
                            # Clear and show save success
                            with status_container.container():
                                st.success(t("answers_saved"))

                            # Step 3: Calculate score
                            score_result = make_api_request(
                                "/score",
                                "POST",
                                {"assessment_id": st.session_state.assessment_id},
                                st.session_state.user_token,
                            )

                            if score_result:
                                # Clear and show final success
                                with status_container.container():
                                    st.success(t("completed_redirect"))

                                # Update session state
                                st.session_state.completed_assessment_id = (
                                    st.session_state.assessment_id
                                )
                                st.session_state.assessment_id = None
                                st.session_state.answers = {}
                                st.session_state.current_area = 0
                                st.session_state.current_page = "View Results"
                                st.session_state.scroll_to_top = True

                                # Brief pause then redirect
                                time.sleep(1)
                                st.rerun()
                            else:
                                with status_container.container():
                                    st.error(t("save_failed"))
                        else:
                            with status_container.container():
                                st.error(t("save_failed"))

                    except Exception as e:
                        with status_container.container():
                            st.error(t("error_occurred", err=str(e)))

    # Scroll after all content is rendered so the DOM is ready
    if st.session_state.get("scroll_to_top", False):
        _scroll_to_top()
        st.session_state.scroll_to_top = False


def show_results_page():
    """Display assessment results report"""
    assessment_id = st.session_state.get(
        "completed_assessment_id"
    ) or st.session_state.get("selected_assessment_id")
    if not assessment_id:
        st.info(t("no_assessment_selected"))
        return

    results = make_api_request(
        f"/results/{assessment_id}", token=st.session_state.user_token
    )
    if not results:
        st.error(t("load_results_failed"))
        return

    assessment = results["assessment"]
    area_scores = results["area_scores"]
    recommendations = results["recommendations"]

    total_score = float(assessment["total_score"])
    maturity_level = assessment["maturity_level"]
    score_color = _score_color(total_score)

    areas_full, scores_list = _extract_area_data(area_scores)
    if (
        st.session_state.get("lang") == "pl"
        and area_scores
        and isinstance(area_scores[0], dict)
    ):
        pl_areas = _get_content_pl().get("areas", {})
        areas_full = [
            pl_areas.get(s.get("area_id_str", ""), {}).get("name", areas_full[i])
            for i, s in enumerate(area_scores)
        ]
    highest_score = max(scores_list) if scores_list else 0
    lowest_score = min(scores_list) if scores_list else 0
    strongest_area = ""
    weakest_area = ""
    for name, val in zip(areas_full, scores_list):
        if val == highest_score:
            strongest_area = name
        if val == lowest_score:
            weakest_area = name

    n_high = sum(1 for r in recommendations if r.get("priority") == "high")
    n_med = sum(1 for r in recommendations if r.get("priority") == "medium")

    # --- SECTION 1: Executive Summary Header ---
    maturity_desc = (
        t("maturity_low_desc")
        if maturity_level == "Low"
        else (
            t("maturity_medium_desc")
            if maturity_level == "Medium"
            else t("maturity_high_desc")
        )
    )

    stat_cards = (
        f'<div style="display:flex;gap:12px;margin-top:1.2rem;">'
        f'<div class="stat-card" style="flex:1;"><div class="stat-value">{len(areas_full)}</div><div class="stat-label">{t("stat_areas")}</div></div>'
        f'<div class="stat-card" style="flex:1;"><div class="stat-value">36</div><div class="stat-label">{t("stat_questions")}</div></div>'
        f'<div class="stat-card" style="flex:1;"><div class="stat-value">{len(recommendations)}</div><div class="stat-label">{t("stat_recommendations")}</div></div>'
        f'<div class="stat-card" style="flex:1;"><div class="stat-value">{n_high}</div><div class="stat-label">{t("stat_high_priority")}</div></div>'
        f"</div>"
    )

    recs_lead = t("report_recs_singular") if n_high == 1 else t("report_recs_plural")
    ring_border = f"border: 6px solid {score_color}"
    st.markdown(
        f'<div class="report-header">'
        f'<div style="display:flex;align-items:center;gap:2rem;flex-wrap:wrap;">'
        f'<div style="flex-shrink:0;">'
        f'<div class="score-ring" style="{ring_border};">'
        f'<span class="score-value" style="color:{score_color};">{total_score:.0f}%</span>'
        f'<span class="score-label" style="color:{score_color};">{maturity_level} Maturity</span>'
        f"</div></div>"
        f'<div style="flex:1;min-width:250px;">'
        f'<h2>{t("report_title")}</h2>'
        f"<p>{_date_fmt(datetime.now())}</p>"
        f'<div class="exec-summary" style="margin-top:1rem;">'
        f'{t("report_intro_1")} <strong style="color:{score_color};">{total_score:.1f}%</strong> {t("report_intro_2")} '
        f'<strong style="color:{score_color};">{maturity_level}</strong> {t("report_intro_3")} {maturity_desc}. '
        f'{t("report_strongest")} <strong>{_short_name(strongest_area)}</strong> ({highest_score:.0f}%) '
        f'{t("report_weakest")} <strong>{_short_name(weakest_area)}</strong> ({lowest_score:.0f}%). '
        f'{recs_lead} <strong>{n_high}</strong> {t("report_recs_tail")} <strong>{n_med}</strong> {t("report_recs_tail2")}'
        f"</div>"
        f"{stat_cards}"
        f"</div></div></div>",
        unsafe_allow_html=True,
    )

    # --- SECTION 2: Area Performance Overview ---
    st.markdown(
        f'<h3 class="sub-header">{t("area_performance")}</h3>', unsafe_allow_html=True
    )

    chart_scores = [
        {
            "area_name": areas_full[i],
            "score": scores_list[i],
            "weighted_score": scores_list[i],
        }
        for i in range(len(areas_full))
    ]
    bar_fig = create_bar_chart(chart_scores)
    if bar_fig:
        st.plotly_chart(bar_fig, use_container_width=True)

    recs_by_area = {}
    for r in recommendations:
        aname = r.get("area_name", "Unknown")
        recs_by_area.setdefault(aname, []).append(r)

    area_score_lookup = dict(zip(areas_full, scores_list))
    area_display_name = {}
    area_name_to_score = {}
    if area_scores and isinstance(area_scores[0], dict):
        for i, s in enumerate(area_scores):
            en_name = s.get("area_name", "")
            area_display_name[en_name] = areas_full[i]
            area_name_to_score[en_name] = scores_list[i]

    # --- SECTION 3: Radar Chart ---
    st.markdown(
        f'<h3 class="sub-header">{t("maturity_profile")}</h3>', unsafe_allow_html=True
    )
    radar_fig = create_radar_chart(chart_scores)
    if radar_fig:
        col_r1, col_r2, col_r3 = st.columns([1, 3, 1])
        with col_r2:
            st.plotly_chart(radar_fig, use_container_width=True)

    # --- SECTION 4: Top Priority Actions ---
    if recommendations:
        st.markdown(
            f'<h3 class="sub-header">{t("top_priority_actions")}</h3>',
            unsafe_allow_html=True,
        )

        sorted_recs = sorted(
            recommendations,
            key=lambda r: (
                (
                    0
                    if r.get("priority") == "high"
                    else 1 if r.get("priority") == "medium" else 2
                ),
                r.get("question_score", 5),
                area_score_lookup.get(r.get("area_name", ""), 50),
            ),
        )
        top_3 = sorted_recs[:3]
        cols = st.columns(len(top_3))
        action_colors = ["#ef4444", "#f59e0b", "#3b82f6"]
        for i, (col, rec) in enumerate(zip(cols, top_3)):
            with col:
                border_color = action_colors[i] if i < len(action_colors) else "#6b7280"
                st.markdown(
                    f'<div class="top-action-card" style="border-left-color:{border_color};position:relative;">'
                    f'<div class="action-num">{i + 1}</div>'
                    f"<h4>{_tr_recommendation(rec)[0]}</h4>"
                    f'<p>{_short_name(rec.get("area_name", ""))} &middot; {t("question_score")}: {rec.get("question_score", 0)}/5</p>'
                    f"</div>",
                    unsafe_allow_html=True,
                )

    # --- SECTION 5: Detailed Recommendations by Area ---
    if recommendations:
        st.markdown(
            f'<h3 class="sub-header">{t("detailed_recommendations")}</h3>',
            unsafe_allow_html=True,
        )

        area_order = sorted(
            recs_by_area.keys(),
            key=lambda a: (
                area_name_to_score.get(a, 50)
                if area_name_to_score
                else next((s for n, s in zip(areas_full, scores_list) if n == a), 50)
            ),
        )

        for area_name in area_order:
            area_recs = recs_by_area[area_name]
            display_name = (
                area_display_name.get(area_name, area_name)
                if area_display_name
                else area_name
            )
            area_score_val = (
                area_name_to_score.get(area_name, 0)
                if area_name_to_score
                else next(
                    (s for n, s in zip(areas_full, scores_list) if n == area_name), 0
                )
            )
            n_high_area = sum(1 for r in area_recs if r.get("priority") == "high")
            badge = f" ({n_high_area} {t('high_priority')})" if n_high_area > 0 else ""

            with st.expander(
                f"{_short_name(display_name)} — {area_score_val:.0f}% — {len(area_recs)} {t('recommendations') if len(area_recs) != 1 else t('recommendation')}{badge}",
                expanded=(area_score_val < 50),
            ):
                for rec in sorted(
                    area_recs,
                    key=lambda r: (
                        0
                        if r.get("priority") == "high"
                        else 1 if r.get("priority") == "medium" else 2
                    ),
                ):
                    priority = rec.get("priority", "medium")
                    css_class = {
                        "high": "high-priority",
                        "medium": "medium-priority",
                        "low": "low-priority",
                    }.get(priority, "medium-priority")
                    tag_class = {
                        "high": "tag-high",
                        "medium": "tag-medium",
                        "low": "tag-low",
                    }.get(priority, "tag-medium")

                    rec_title, rec_desc, rec_tips = _tr_recommendation(rec)
                    ref_items = ""
                    for key, label in [
                        ("iso_reference", "ISO"),
                        ("nist_reference", "NIST"),
                        ("cis_reference", "CIS"),
                        ("nis2_reference", "NIS2"),
                    ]:
                        val = rec.get(key, "")
                        if val:
                            ref_items += f"<li>{label}: {val}</li>"

                    tips_html = (
                        f'<p><strong>{t("improvement_tips")}:</strong> {rec_tips}</p>'
                        if rec_tips
                        else ""
                    )

                    st.markdown(
                        f'<div class="recommendation-card {css_class}">'
                        f'<h4>{rec_title}<span class="priority-tag {tag_class}">{t(priority)}</span></h4>'
                        f"<p>{rec_desc}</p>"
                        f'<p><strong>{t("question_score")}:</strong> {rec.get("question_score", 0)}/5</p>'
                        f"{tips_html}"
                        f'<p><strong>{t("references")}:</strong></p>'
                        f'<ul class="ref-list">{ref_items}</ul>'
                        f"</div>",
                        unsafe_allow_html=True,
                    )
    else:
        st.success(t("no_recommendations"))

    # --- SECTION 6: Export ---
    st.markdown(
        f'<h3 class="sub-header">{t("export_results")}</h3>', unsafe_allow_html=True
    )

    export_data = {
        "assessment_id": assessment_id,
        "total_score": total_score,
        "maturity_level": maturity_level,
        "generated_at": datetime.now().isoformat(),
        "area_scores": [
            {"area": name, "score": round(sc, 1), "maturity": _maturity_label(sc)}
            for name, sc in zip(areas_full, scores_list)
        ],
        "recommendations": [
            {
                "area": rec.get("area_name", ""),
                "title": rec.get("title", ""),
                "priority": rec.get("priority", ""),
                "question_score": rec.get("question_score", 0),
                "description": rec.get("description", ""),
                "improvement_tips": rec.get("improvement_tips", ""),
                "iso_reference": rec.get("iso_reference", ""),
                "nist_reference": rec.get("nist_reference", ""),
                "cis_reference": rec.get("cis_reference", ""),
                "nis2_reference": rec.get("nis2_reference", ""),
            }
            for rec in sorted(
                recommendations,
                key=lambda r: (
                    0
                    if r.get("priority") == "high"
                    else 1 if r.get("priority") == "medium" else 2
                ),
            )
        ],
    }

    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            label=t("download_json"),
            data=json.dumps(export_data, indent=2),
            file_name=f"cyberscore_report_{assessment_id}.json",
            mime="application/json",
        )
    with col2:
        csv_rows = []
        for name, sc in zip(areas_full, scores_list):
            csv_rows.append(
                {
                    "Area": name,
                    "Score (%)": round(sc, 1),
                    "Maturity Level": _maturity_label(sc),
                }
            )
        df_scores = pd.DataFrame(csv_rows)
        st.download_button(
            label=t("download_csv"),
            data=df_scores.to_csv(index=False),
            file_name=f"cyberscore_scores_{assessment_id}.csv",
            mime="text/csv",
        )

    # Scroll after all content is rendered
    if st.session_state.get("scroll_to_top", False):
        _scroll_to_top()
        st.session_state.scroll_to_top = False


def show_about_page():
    """Display about page"""
    st.markdown(
        f'<h2 class="sub-header">{t("about_title")}</h2>', unsafe_allow_html=True
    )

    lang = st.session_state.get("lang", "en")
    if lang == "pl":
        about_md = _get_content_pl().get("about", "")
        if about_md:
            st.markdown(about_md)
            return
    st.markdown(
        """
    ## Overview
    
    CyberScore is a comprehensive information security maturity assessment tool designed for organizations seeking to evaluate and improve their cybersecurity posture. The tool is based on internationally recognized standards and frameworks.
    
    ## Standards & Frameworks
    
    ### ISO/IEC 27001:2022
    - **Information Security Management Systems**
    - Provides requirements for establishing, implementing, maintaining, and continually improving an information security management system
    - Focuses on risk management and continuous improvement
    
    ### NIST Cybersecurity Framework (CSF 2.0)
    - **Framework for Improving Critical Infrastructure Cybersecurity**
    - Provides a common language for understanding, managing, and expressing cybersecurity risk
    - Six core functions: Govern, Identify, Protect, Detect, Respond, Recover
    
    ### CIS Controls v8
    - **Critical Security Controls**
    - A prioritized set of actions that collectively form a defense-in-depth set of best practices
    - Focuses on the most important security controls for effective cyber defense
    
    ### NIS2 Directive
    - **EU Network and Information Security Directive**
    - Establishes cybersecurity risk management and incident reporting obligations for essential and important entities across the EU
    
    ## Methodology
    
    ### Scoring System
    - **Question Level**: Each question is scored on a 0-5 maturity scale
    - **Area Level**: Weighted average of questions within each area (0-100%)
    - **Overall Level**: Weighted average of all area scores
    - **Maturity Levels**: Low (<40%), Medium (40-70%), High (>70%)
    
    ### Weighting
    - Questions and areas are weighted based on their importance to overall security
    - Weights are derived from industry best practices and expert consensus
    
    ## Features
    
    - **Comprehensive Assessment**: 36 questions across 6 security areas
    - **Automated Scoring**: Weighted scoring algorithm at question, area, and overall levels
    - **Visual Analytics**: Radar charts and bar charts for easy interpretation
    - **Actionable Recommendations**: Specific improvement suggestions mapped to ISO 27001, NIST CSF, CIS Controls, and NIS2
    - **Export Capabilities**: JSON and CSV export for further analysis
    - **User Management**: Secure user accounts with personal assessment history
    
    ## Security Areas
    
    1. **Governance & Risk Oversight** - roles, responsibilities, policies, and strategic oversight
    2. **Asset & Risk Management** - business context, critical assets, and risk handling
    3. **Access & Data Protection** - access control, data protection, and user awareness
    4. **Monitoring & Threat Detection** - logging, monitoring, and anomaly detection
    5. **Incident Response & Communication** - handling incidents and required notifications
    6. **Business Continuity & Recovery** - continuity planning, backups, and restoration
    
    ## Use Cases
    
    - **Self-Assessment**: Organizations evaluating their own cybersecurity maturity
    - **Compliance**: Meeting regulatory requirements and standards
    - **Improvement Planning**: Identifying areas for security enhancement
    - **Benchmarking**: Comparing against industry standards
    - **Research**: Academic and industry research on security maturity
    
    ## Contact & Support
    
    This tool was developed as part of a master's thesis project on cybersecurity posture measurement. For questions or support, please refer to the project documentation.
    
    ---
    
    **Version**: 2.0.0  
    **License**: Academic Use
    """
    )


if __name__ == "__main__":
    main()

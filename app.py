import io
from datetime import datetime, date, timezone
import pandas as pd
import requests
import streamlit as st
import time

def _now_ts() -> float:
    return time.time()

def _timeout_seconds() -> int:
    # Legge da secrets, default 30 minuti
    try:
        minutes = int(st.secrets.get("AUTH", {}).get("SESSION_TIMEOUT_MINUTES", 30))
    except Exception:
        minutes = 30
    return minutes * 60

def require_login():
    # Stato iniziale
    if "auth_ok" not in st.session_state:
        st.session_state.auth_ok = False
    if "auth_user" not in st.session_state:
        st.session_state.auth_user = None
    if "auth_last_seen" not in st.session_state:
        st.session_state.auth_last_seen = 0.0

    # Se già loggato, verifica timeout
    if st.session_state.auth_ok:
        if _now_ts() - float(st.session_state.auth_last_seen) > _timeout_seconds():
            # timeout → logout automatico
            st.session_state.auth_ok = False
            st.session_state.auth_user = None
            st.session_state.auth_last_seen = 0.0
            st.warning("Session expired. Please log in again.")
            st.rerun()
        else:
            # aggiorna last_seen e lascia passare
            st.session_state.auth_last_seen = _now_ts()
            return

    # UI Login
    st.title("🔐 Login")
    st.caption("Enter your credentials to access the app.")

    username = st.text_input("Username", key="login_user")
    password = st.text_input("Password", type="password", key="login_pass")

    if st.button("Login", use_container_width=True, key="login_btn"):
        users = st.secrets.get("AUTH_USERS", {})
        expected_pw = users.get(username)
        if expected_pw and password == expected_pw:
            st.session_state.auth_ok = True
            st.session_state.auth_user = username
            st.session_state.auth_last_seen = _now_ts()
            st.rerun()
        else:
            st.error("Wrong username or password.")

    st.stop()

def render_auth_header():
    """Header con username + logout"""
    if st.session_state.get("auth_ok"):
        with st.container():
            col1, col2 = st.columns([0.75, 0.25])
            col1.markdown(f"**Logged in as:** `{st.session_state.get('auth_user')}`")
            if col2.button("Logout", use_container_width=True, key="logout_btn"):
                st.session_state.auth_ok = False
                st.session_state.auth_user = None
                st.session_state.auth_last_seen = 0.0
                st.rerun()
        st.divider()

try:
    from google_play_scraper import reviews, Sort
    GP_OK = True
except Exception:
    GP_OK = False

st.set_page_config(page_title="Reviews Exporter", page_icon="📥", layout="centered")
require_login()
render_auth_header()
st.title("📥 Reviews Exporter")
st.caption("Extract reviews from Google Play & Apple App Store → Excel (.xlsx)")

TAB_GOOGLE, TAB_APPLE = st.tabs(["Google Play", "Apple App Store"])


# ---------------------------
# Helpers
# ---------------------------
def sanitize_filename(s: str) -> str:
    return "".join(c if c.isalnum() or c in ("-", "_", ".") else "_" for c in s)


def to_excel_download(df: pd.DataFrame, filename: str, key: str):
    buffer = io.BytesIO()
    df.to_excel(buffer, index=False)
    st.download_button(
        label="⬇️ Download Excel",
        data=buffer.getvalue(),
        file_name=filename,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
        key=key,
    )


# ---------------------------
# TAB: Google Play
# ---------------------------
with TAB_GOOGLE:
    st.subheader("Google Play")
    if not GP_OK:
        st.info("⚠️ Missing dependency: google-play-scraper (check requirements.txt)")

    col1, col2 = st.columns(2)
    app_id_g = col1.text_input(
        "APP_ID (e.g. it.enelmobile, com.whatsapp)",
        value="",
        placeholder="com.example.app",
        key="gp_app_id",
    )
    lang_g = col2.text_input("Language (lang)", value="it", key="gp_lang")

    col3, col4 = st.columns(2)
    country_g = col3.text_input("Country (store)", value="it", key="gp_country")
    since_g = col4.date_input("SINCE_DATE (included)", value=date(2024, 8, 1), key="gp_since")
    until_g = st.date_input("UNTIL_DATE (excluded)", value=date(2025, 9, 1), key="gp_until")

    run_g = st.button("Extract & Generate Excel (Google Play)", use_container_width=True, key="gp_run")

    if run_g:
        if not app_id_g.strip():
            st.error("APP_ID is required (e.g. it.enelmobile).")
        elif not GP_OK:
            st.error("Module google-play-scraper not installed.")
        else:
            try:
                SINCE_DATE = datetime.combine(since_g, datetime.min.time()).replace(tzinfo=timezone.utc)
                UNTIL_DATE = datetime.combine(until_g, datetime.min.time()).replace(tzinfo=timezone.utc)
                if UNTIL_DATE <= SINCE_DATE:
                    st.error("UNTIL_DATE must be after SINCE_DATE.")
                else:
                    all_rows, token = [], None
                    while True:
                        chunk, token = reviews(
                            app_id_g.strip(),
                            lang=lang_g.strip() or "it",
                            country=country_g.strip() or "it",
                            sort=Sort.NEWEST,
                            count=200,
                            continuation_token=token,
                        )
                        if not chunk:
                            break

                        stop = False
                        for r in chunk:
                            d = r.get("at")
                            if d is None:
                                continue
                            if d.tzinfo is None:
                                d = d.replace(tzinfo=timezone.utc)
                            else:
                                d = d.astimezone(timezone.utc)

                            if d >= UNTIL_DATE:
                                continue
                            if d < SINCE_DATE:
                                stop = True
                                break

                            all_rows.append({
                                "Date": d.date().isoformat(),
                                "Text": (r.get("content") or "").strip(),
                                "Rating": r.get("score"),
                            })

                        if stop or token is None:
                            break

                    df = pd.DataFrame(all_rows, columns=["Date", "Text", "Rating"]) \
                        .sort_values("Date", ascending=False).reset_index(drop=True)
                    st.success(f"Reviews collected: {len(df)}")
                    st.dataframe(df.head(10), use_container_width=True, key="gp_table")
                    fname = f"google_play_{sanitize_filename(app_id_g)}_{SINCE_DATE.date()}_{UNTIL_DATE.date()}.xlsx"
                    to_excel_download(df, fname, key="gp_download")
            except Exception as e:
                st.exception(e)


# ---------------------------
# TAB: Apple App Store
# ---------------------------
with TAB_APPLE:
    st.subheader("Apple App Store")

    col1, col2 = st.columns(2)
    app_id_a = col1.text_input("APP_ID numeric (e.g. 310633997)", value="", placeholder="digits only", key="ap_app_id")
    country_a = col2.text_input("Country (store)", value="it", key="ap_country")

    col3, col4 = st.columns(2)
    since_a = col3.date_input("SINCE_DATE (included)", value=date(2024, 8, 1), key="ap_since")
    until_a = col4.date_input("UNTIL_DATE (excluded)", value=date(2025, 9, 1), key="ap_until")

    run_a = st.button("Extract & Generate Excel (Apple)", use_container_width=True, key="ap_run")

    def parse_apple_date(value):
        if isinstance(value, datetime):
            d = value
        else:
            s = str(value).strip()
            if s.endswith("Z"):
                s = s[:-1] + "+00:00"
            try:
                d = datetime.fromisoformat(s)
            except Exception:
                try:
                    d = datetime.strptime(s.split("T")[0], "%Y-%m-%d")
                except Exception:
                    return None
        if d.tzinfo is not None:
            d = d.astimezone(timezone.utc).replace(tzinfo=None)
        return d

    if run_a:
        if not app_id_a.strip().isdigit():
            st.error("APP_ID must be numeric (e.g. 310633997).")
        else:
            try:
                SINCE_DATE = datetime.combine(since_a, datetime.min.time())
                UNTIL_DATE = datetime.combine(until_a, datetime.min.time())
                if UNTIL_DATE <= SINCE_DATE:
                    st.error("UNTIL_DATE must be after SINCE_DATE.")
                else:
                    all_rows, page = [], 1
                    while True:
                        url = f"https://itunes.apple.com/{country_a.strip().lower()}/rss/customerreviews/page={page}/id={app_id_a.strip()}/sortBy=mostRecent/json"
                        resp = requests.get(url, timeout=20)
                        if resp.status_code != 200:
                            break
                        data = resp.json()
                        entries = data.get("feed", {}).get("entry", [])
                        if len(entries) <= 1:
                            break

                        stop = False
                        for e in entries[1:]:
                            d = parse_apple_date(e.get("updated", {}).get("label"))
                            if not d:
                                continue
                            if d < SINCE_DATE:
                                stop = True
                                break
                            if d >= UNTIL_DATE:
                                continue

                            try:
                                rating = int(e.get("im:rating", {}).get("label", 0))
                            except Exception:
                                rating = None

                            all_rows.append({
                                "Date": d.date().isoformat(),
                                "Title": (e.get("title", {}).get("label") or "").strip(),
                                "Text": (e.get("content", {}).get("label") or "").strip(),
                                "Rating": rating,
                            })

                        if stop:
                            break

                        last_d = parse_apple_date(entries[-1].get("updated", {}).get("label"))
                        if last_d and last_d < SINCE_DATE:
                            break

                        page += 1

                    df = pd.DataFrame(all_rows, columns=["Date", "Title", "Text", "Rating"]) \
                        .sort_values("Date", ascending=False).reset_index(drop=True)
                    st.success(f"Reviews collected: {len(df)}")
                    st.dataframe(df.head(10), use_container_width=True, key="ap_table")
                    fname = f"apple_store_{sanitize_filename(app_id_a)}_{SINCE_DATE.date()}_{UNTIL_DATE.date()}.xlsx"
                    to_excel_download(df, fname, key="ap_download")
            except Exception as e:
                st.exception(e)

st.divider()
st.caption("Use realistic date ranges and correct App IDs (Android: package name, Apple: numeric ID).")

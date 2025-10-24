import io
from datetime import datetime, date, timezone

import pandas as pd
import requests
import streamlit as st

# --- opzionale: solo quando usi il tab Google Play ---
try:
    from google_play_scraper import reviews, Sort
    GP_OK = True
except Exception:
    GP_OK = False

st.set_page_config(page_title="Reviews Exporter • Google Play & Apple", page_icon="📥", layout="centered")
st.title("📥 Reviews Exporter")
st.caption("Google Play Store & Apple App Store → Excel (.xlsx) — solo inserimento parametri, nessuna modifica al codice")

TAB_GOOGLE, TAB_APPLE = st.tabs(["Google Play", "Apple App Store"])


# ---------------------------
# Helper comuni
# ---------------------------
def sanitize_filename(s: str) -> str:
    return "".join(c if c.isalnum() or c in ("-", "_", ".") else "_" for c in s)

def to_excel_download(df: pd.DataFrame, filename: str) -> None:
    buffer = io.BytesIO()
    df.to_excel(buffer, index=False)
    st.download_button(
        label="⬇️ Scarica Excel",
        data=buffer.getvalue(),
        file_name=filename,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )

def daterange_to_strings(since: date, until: date):
    return since.isoformat(), until.isoformat()


# ---------------------------
# TAB: Google Play
# ---------------------------
with TAB_GOOGLE:
    st.subheader("Google Play")
    if not GP_OK:
        st.info("Installa la dipendenza `google-play-scraper` su Streamlit Cloud tramite `requirements.txt`.")
    col1, col2 = st.columns(2)
    app_id_g = col1.text_input("APP_ID (es. it.enelmobile, com.whatsapp)", value="", placeholder="com.example.app")
    lang_g = col2.text_input("Lingua (lang)", value="it")

    col3, col4 = st.columns(2)
    country_g = col3.text_input("Country (store)", value="it")
    since_g = col4.date_input("SINCE_DATE (inclusa)", value=date(2024, 8, 1))
    until_g = st.date_input("UNTIL_DATE (esclusa)", value=date(2025, 9, 1))

    run_g = st.button("Estrai e genera Excel (Google Play)", use_container_width=True)

    if run_g:
        if not app_id_g.strip():
            st.error("APP_ID è obbligatorio (es. it.enelmobile).")
        elif not GP_OK:
            st.error("Modulo `google-play-scraper` non disponibile. Controlla `requirements.txt`.")
        else:
            since_str, until_str = daterange_to_strings(since_g, until_g)
            try:
                SINCE_DATE = datetime.fromisoformat(since_str).replace(tzinfo=timezone.utc)
                UNTIL_DATE = datetime.fromisoformat(until_str).replace(tzinfo=timezone.utc)
                if UNTIL_DATE <= SINCE_DATE:
                    st.error("UNTIL_DATE deve essere successiva a SINCE_DATE.")
                else:
                    # Pagina le recensioni ordinate dalle più recenti
                    all_rows, token = [], None
                    BATCH = 200
                    while True:
                        chunk, token = reviews(
                            app_id_g.strip(),
                            lang=lang_g.strip() or "it",
                            country=country_g.strip() or "it",
                            sort=Sort.NEWEST,
                            count=BATCH,
                            continuation_token=token,
                        )
                        if not chunk:
                            break

                        stop = False
                        for r in chunk:
                            d = r.get("at")
                            if d is None:
                                continue
                            # normalizza a UTC-aware
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

                    df = pd.DataFrame(all_rows, columns=["Date", "Text", "Rating"]).sort_values("Date", ascending=False).reset_index(drop=True)
                    st.success(f"Recensioni trovate: {len(df)}")
                    st.dataframe(df.head(10), use_container_width=True)
                    fname = f"google_play_{sanitize_filename(app_id_g)}_{SINCE_DATE.date()}_{UNTIL_DATE.date()}.xlsx"
                    to_excel_download(df, fname)
            except Exception as e:
                st.exception(e)


# ---------------------------
# TAB: Apple App Store
# ---------------------------
with TAB_APPLE:
    st.subheader("Apple App Store")
    col1, col2 = st.columns(2)
    app_id_a = col1.text_input("APP_ID numerico (es. 310633997)", value="", placeholder="solo cifre")
    country_a = col2.text_input("Country (store)", value="it")

    col3, col4 = st.columns(2)
    since_a = col3.date_input("SINCE_DATE (inclusa)", value=date(2024, 8, 1), key="apple_since")
    until_a = col4.date_input("UNTIL_DATE (esclusa)", value=date(2025, 9, 1), key="apple_until")

    run_a = st.button("Estrai e genera Excel (Apple)", use_container_width=True)

    def parse_apple_date(value):
        """Restituisce datetime naive UTC a partire dal campo 'updated.label' del feed."""
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
            st.error("APP_ID deve essere numerico (es. 310633997).")
        else:
            since_str, until_str = daterange_to_strings(since_a, until_a)
            try:
                SINCE_DATE = datetime.fromisoformat(since_str)
                UNTIL_DATE = datetime.fromisoformat(until_str)
                if UNTIL_DATE <= SINCE_DATE:
                    st.error("UNTIL_DATE deve essere successiva a SINCE_DATE.")
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

                    df = pd.DataFrame(all_rows, columns=["Date", "Title", "Text", "Rating"]).sort_values("Date", ascending=False).reset_index(drop=True)
                    st.success(f"Recensioni trovate: {len(df)}")
                    st.dataframe(df.head(10), use_container_width=True)
                    fname = f"apple_store_{sanitize_filename(app_id_a)}_{SINCE_DATE.date()}_{UNTIL_DATE.date()}.xlsx"
                    to_excel_download(df, fname)
            except Exception as e:
                st.exception(e)

st.divider()
st.caption("Suggerimenti: usa intervalli realistici e l'APP_ID corretto (Android: packageName; Apple: ID numerico in URL).")

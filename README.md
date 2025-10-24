📥 Reviews Exporter

Google Play & Apple App Store → Excel (.xlsx)

This web app lets you automatically extract app reviews from the Google Play Store or Apple App Store and export them to Excel (.xlsx) — just by filling out a few input fields.
End users can only interact with the interface — they can’t edit or see the code.

🚀 How It Works

Google Play → uses the open-source library google-play-scraper

Apple App Store → fetches data from Apple’s public RSS JSON endpoint itunes.apple.com/rss/customerreviews/...

Each tab exports reviews to Excel with the following columns:

Google: Date | Text | Rating

Apple: Date | Title | Text | Rating

🧩 Deploying on Streamlit Cloud
1️⃣ Create a GitHub Repository

Create a new public repo, e.g. reviews-exporter, containing:

app.py
requirements.txt
README.md

2️⃣ requirements.txt
streamlit>=1.37
pandas>=2.2
openpyxl>=3.1
requests>=2.32
google-play-scraper>=1.2.6


If you only need Apple App Store reviews, you can remove google-play-scraper.

3️⃣ Deploy to Streamlit Cloud

Go to 👉 https://streamlit.io/cloud

Sign in with your GitHub account.

Click “New app”.

Choose your repo → set the main file path to app.py.

Click Deploy 🚀

After a short setup, your public URL will look like:

https://reviews-exporter.streamlit.app


You can share this link — users only see the UI, not the code.

🌐 How to Use

Open your Streamlit app URL

Choose a tab:

Google Play

Apple App Store

Fill in the fields:

Google Play:

APP_ID (e.g. it.enelmobile, com.whatsapp)

lang, country, SINCE_DATE, UNTIL_DATE

Apple App Store:

APP_ID numeric (e.g. 310633997)

country, SINCE_DATE, UNTIL_DATE

Click “Extract & Generate Excel”

Wait a few seconds — you’ll see a Download Excel button appear

📂 Example Output
Google Play
Date	Text	Rating
2025-02-01	Great app, very intuitive...	5
2025-01-25	Crashes frequently...	2
Apple App Store
Date	Title	Text	Rating
2025-02-03	Perfect!	Stable and fast app.	5
2024-09-12	Needs improvement	No dark mode...	3
⚙️ Configuration Notes

The date range is inclusive for SINCE_DATE and exclusive for UNTIL_DATE

You can change default values in the code, but end users will only interact with the interface

If you want to include Author, App Version, or other fields, add them in the dictionary inside all_rows.append() in app.py

🛡️ Limitations
Source	Limitations
Google Play	May cap the number of reviews (usually up to 10–20k)
Apple App Store	RSS feed returns up to ~10 pages (~500 most recent reviews)
Streamlit Free Plan	Public apps only, max 3 active, auto-sleeps after 1 hour of inactivity
🧭 Useful Tips

Use realistic date ranges (e.g., 1 year max for best performance)

Verify you’re using the correct App ID:

Android → the package name (com.example.app)

Apple → numeric ID found in the App Store URL (id123456789)

You can add your own logo or emoji in the app header by editing:

st.set_page_config(page_title="Reviews Exporter", page_icon="📥", layout="centered")

👤 Author

Created for analytical and educational purposes.
Feel free to fork, reuse, or adapt it with attribution.

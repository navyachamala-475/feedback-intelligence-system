import os

APP_NAME = "Feedback Intelligence System"
APP_VERSION = "1.0.0"

TARGET_APPS = {
    "google_play": {
        "app_id": "com.spotify.music",
        "app_name": "Spotify",
        "country": "us",
        "lang": "en",
        "count": 200,
    },
    "app_store": {
        "app_id": "324684580",
        "app_name": "Spotify",
        "country": "us",
        "count": 200,
    },
}

SENTIMENT_THRESHOLDS = {
    "positive": 0.05,
    "negative": -0.05,
}

CRITICAL_ISSUE_MIN_COUNT = 5
CRITICAL_NEGATIVE_RATIO = 0.6
TREND_WINDOW_DAYS = 7

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")
SAMPLE_CSV_PATH = os.path.join(DATA_DIR, "sample_survey.csv")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)

REPORT_TITLE = "Weekly Feedback Intelligence Report"
COMPANY_NAME = "ProductTeam Analytics"
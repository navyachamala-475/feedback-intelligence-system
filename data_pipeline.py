# data_pipeline.py
import logging
import os
import json
from datetime import datetime
import pandas as pd

from config import DATA_DIR, TARGET_APPS, SAMPLE_CSV_PATH
from fetchers import (
    fetch_google_play_reviews,
    fetch_app_store_reviews,
    load_csv_reviews,
    generate_sample_csv,
)
from analysis import SentimentAnalyzer, IssueDetector, TrendAnalyzer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CACHE_PATH = os.path.join(DATA_DIR, "reviews_cache.csv")
META_PATH  = os.path.join(DATA_DIR, "fetch_meta.json")


class DataPipeline:

    def __init__(self):
        self.sentiment = SentimentAnalyzer()
        self.issue_detector = IssueDetector()
        self.trend_analyzer = TrendAnalyzer()

    def load_data(self, use_cache=True, csv_path=None, force_sample=False):
        if use_cache and self._cache_valid() and not force_sample:
            logger.info("Loading from cache...")
            df = pd.read_csv(CACHE_PATH)
            df["date"] = pd.to_datetime(df["date"])
            return df

        frames = []

        try:
            cfg = TARGET_APPS["google_play"]
            gp_df = fetch_google_play_reviews(
                app_id=cfg["app_id"],
                app_name=cfg["app_name"],
                count=cfg["count"],
                lang=cfg["lang"],
                country=cfg["country"],
            )
            if not gp_df.empty:
                frames.append(gp_df)
        except Exception as e:
            logger.warning(f"Google Play fetch skipped: {e}")

        try:
            cfg = TARGET_APPS["app_store"]
            as_df = fetch_app_store_reviews(
                app_id=cfg["app_id"],
                app_name=cfg["app_name"],
                country=cfg["country"],
                count=cfg["count"],
            )
            if not as_df.empty:
                frames.append(as_df)
        except Exception as e:
            logger.warning(f"App Store fetch skipped: {e}")

        effective_csv = csv_path or SAMPLE_CSV_PATH
        if force_sample or not os.path.exists(effective_csv):
            generate_sample_csv(SAMPLE_CSV_PATH)
            effective_csv = SAMPLE_CSV_PATH
        try:
            csv_df = load_csv_reviews(effective_csv, app_name="Survey Data", source_label="CSV Survey")
            if not csv_df.empty:
                frames.append(csv_df)
        except Exception as e:
            logger.warning(f"CSV load skipped: {e}")

        if not frames:
            logger.warning("All real sources failed. Using demo data.")
            frames.append(self._generate_demo_data())

        df = pd.concat(frames, ignore_index=True)
        df = self._clean(df)
        df = self.sentiment.analyze_dataframe(df)
        df = self.issue_detector.detect_issues(df)

        df.to_csv(CACHE_PATH, index=False)
        self._write_meta()

        return df

    def get_summary_stats(self, df):
        if df.empty:
            return {}
        return {
            "total_reviews":  len(df),
            "sources":        df["source"].unique().tolist(),
            "avg_rating":     round(df["rating"].mean(), 2),
            "avg_sentiment":  round(df["compound"].mean(), 4),
            "positive_pct":   round((df["sentiment_label"] == "Positive").sum() / len(df) * 100, 1),
            "negative_pct":   round((df["sentiment_label"] == "Negative").sum() / len(df) * 100, 1),
            "neutral_pct":    round((df["sentiment_label"] == "Neutral").sum() / len(df) * 100, 1),
        }

    @staticmethod
    def _clean(df):
        df = df.drop_duplicates(subset=["review_id"], keep="first")
        df["body"]   = df["body"].fillna("").astype(str)
        df["title"]  = df["title"].fillna("").astype(str)
        df["rating"] = pd.to_numeric(df["rating"], errors="coerce").fillna(0)
        df["date"]   = pd.to_datetime(df["date"], errors="coerce")
        df = df.dropna(subset=["date"])
        df = df[df["body"].str.len() > 5]
        return df.reset_index(drop=True)

    @staticmethod
    def _cache_valid():
        if not os.path.exists(CACHE_PATH) or not os.path.exists(META_PATH):
            return False
        try:
            with open(META_PATH) as f:
                meta = json.load(f)
            fetched = datetime.fromisoformat(meta.get("fetched_at", "2000-01-01"))
            hours_old = (datetime.now() - fetched).total_seconds() / 3600
            return hours_old < 6
        except Exception:
            return False

    @staticmethod
    def _write_meta():
        with open(META_PATH, "w") as f:
            json.dump({"fetched_at": datetime.now().isoformat()}, f)

    @staticmethod
    def _generate_demo_data():
        import random
        from datetime import timedelta
        random.seed(2024)

        templates = [
            ("App crashes on startup every time", 1),
            ("Amazing app, love the new features!", 5),
            ("Subscription too expensive", 2),
            ("Offline mode is broken after update", 1),
            ("Search doesn't work properly", 2),
            ("Battery drain is terrible now", 2),
            ("Love the redesign, much cleaner UI", 5),
            ("Please add dark mode", 3),
            ("Keeps logging me out randomly", 1),
            ("Best app in its category", 5),
            ("Recommendations have gotten much better", 4),
            ("Download feature is unreliable", 2),
            ("Support team was incredibly helpful", 4),
            ("Need better audio quality settings", 3),
            ("App freezes on my phone after update", 1),
            ("Great value for the price", 5),
            ("Login via social keeps failing", 2),
            ("The UI update broke my workflow", 2),
            ("Playlist management is top notch", 4),
            ("Notifications are very spammy", 2),
        ]

        sources = ["Google Play", "App Store", "CSV Survey"]
        rows = []
        base = datetime.now()

        for i in range(300):
            tmpl = random.choice(templates)
            src  = random.choice(sources)
            days_ago = random.randint(0, 30)
            rows.append({
                "review_id": f"demo_{i}",
                "source":    src,
                "app_name":  "Demo App",
                "author":    f"User_{i}",
                "rating":    float(tmpl[1]),
                "title":     tmpl[0][:40],
                "body":      tmpl[0] + ". " + random.choice([
                    "Really hope this gets fixed soon.",
                    "Would recommend to others.",
                    "This is a recurring problem.",
                    "Overall still good though.",
                    "Please address this in next update.",
                ]),
                "date":      (base - timedelta(days=days_ago)).strftime("%Y-%m-%d"),
                "thumbs_up": random.randint(0, 50),
                "version":   f"v{random.randint(1,5)}.{random.randint(0,9)}",
            })

        return pd.DataFrame(rows)

import logging
import time
from datetime import datetime
import pandas as pd

logger = logging.getLogger(__name__)

def fetch_google_play_reviews(app_id, app_name="App", count=200, lang="en", country="us"):
    try:
        from google_play_scraper import reviews, Sort
        logger.info(f"Fetching {count} Google Play reviews for {app_id}...")
        result, _ = reviews(app_id, lang=lang, country=country, sort=Sort.NEWEST, count=count)
        if not result:
            return pd.DataFrame()
        rows = []
        for r in result:
            rows.append({
                "review_id": str(r.get("reviewId", "")),
                "source":    "Google Play",
                "app_name":  app_name,
                "author":    r.get("userName", "Anonymous"),
                "rating":    float(r.get("score", 0)),
                "title":     r.get("reviewCreatedVersion", ""),
                "body":      r.get("content", ""),
                "date":      _parse_date(r.get("at")),
                "thumbs_up": r.get("thumbsUpCount", 0),
                "version":   r.get("reviewCreatedVersion", ""),
            })
        df = pd.DataFrame(rows)
        df["date"] = pd.to_datetime(df["date"])
        logger.info(f"Fetched {len(df)} Google Play reviews.")
        return df
    except ImportError:
        logger.error("google-play-scraper not installed.")
        return _empty_df()
    except Exception as e:
        logger.error(f"Google Play fetch failed: {e}")
        return _empty_df()

def _parse_date(val):
    if val is None:
        return datetime.now().strftime("%Y-%m-%d")
    if isinstance(val, datetime):
        return val.strftime("%Y-%m-%d")
    try:
        return pd.to_datetime(val).strftime("%Y-%m-%d")
    except Exception:
        return datetime.now().strftime("%Y-%m-%d")

def _empty_df():
    return pd.DataFrame(columns=["review_id","source","app_name","author",
                                  "rating","title","body","date","thumbs_up","version"])
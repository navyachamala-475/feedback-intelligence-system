
import logging
import time
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
import pandas as pd

logger = logging.getLogger(__name__)

def fetch_app_store_reviews(app_id, app_name="App", country="us", count=200):
    df = _fetch_via_scraper(app_id, app_name, country, count)
    if df.empty:
        logger.info("Falling back to RSS feed...")
        df = _fetch_via_rss(app_id, app_name, country)
    return df

def _fetch_via_scraper(app_id, app_name, country, count):
    try:
        from app_store_scraper import AppStore
        app = AppStore(country=country, app_name=app_name, app_id=app_id)
        app.review(how_many=count)
        if not app.reviews:
            return pd.DataFrame()
        rows = []
        for r in app.reviews:
            rows.append({
                "review_id": str(r.get("reviewId", "")),
                "source":    "App Store",
                "app_name":  app_name,
                "author":    r.get("userName", "Anonymous"),
                "rating":    float(r.get("rating", 0)),
                "title":     r.get("title", ""),
                "body":      r.get("review", ""),
                "date":      _parse_date(r.get("date")),
                "thumbs_up": 0,
                "version":   "",
            })
        df = pd.DataFrame(rows)
        df["date"] = pd.to_datetime(df["date"])
        logger.info(f"Fetched {len(df)} App Store reviews.")
        return df
    except Exception as e:
        logger.warning(f"app-store-scraper failed: {e}")
        return pd.DataFrame()

def _fetch_via_rss(app_id, app_name, country):
    rows = []
    ns = {
        "atom": "http://www.w3.org/2005/Atom",
        "im":   "http://itunes.apple.com/rss",
    }
    for page in range(1, 11):
        url = f"https://itunes.apple.com/{country}/rss/customerreviews/page={page}/id={app_id}/sortby=mostrecent/xml"
        try:
            resp = requests.get(url, timeout=15)
            if resp.status_code != 200:
                break
            root    = ET.fromstring(resp.content)
            entries = root.findall("atom:entry", ns)
            if not entries:
                break
            for entry in entries:
                rows.append({
                    "review_id": _text(entry, "atom:id", ns),
                    "source":    "App Store",
                    "app_name":  app_name,
                    "author":    _text(entry, "atom:author/atom:name", ns) or "Anonymous",
                    "rating":    float(_text(entry, "im:rating", ns) or 0),
                    "title":     _text(entry, "atom:title", ns) or "",
                    "body":      _text(entry, "atom:content", ns) or "",
                    "date":      _parse_date(_text(entry, "atom:updated", ns)),
                    "thumbs_up": 0,
                    "version":   "",
                })
            time.sleep(0.5)
        except Exception as e:
            logger.warning(f"RSS page {page} error: {e}")
            break

    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    logger.info(f"Fetched {len(df)} App Store reviews via RSS.")
    return df

def _text(element, path, ns):
    el = element.find(path, ns)
    return el.text if el is not None else ""

def _parse_date(val):
    if not val:
        return datetime.now().strftime("%Y-%m-%d")
    try:
        return pd.to_datetime(val).strftime("%Y-%m-%d")
    except Exception:
        return datetime.now().strftime("%Y-%m-%d")
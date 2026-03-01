
import logging
import pandas as pd
from datetime import datetime
import os

logger = logging.getLogger(__name__)

COLUMN_ALIASES = {
    "body":   ["review","feedback","comment","response","text","message","body"],
    "rating": ["rating","score","stars","satisfaction","nps","rate"],
    "date":   ["date","timestamp","created_at","submitted_at","time","datetime"],
    "author": ["name","user","email","respondent","author","username"],
    "title":  ["title","subject","headline","summary"],
}

def load_csv_reviews(filepath, app_name="Survey", source_label="CSV Survey"):
    try:
        df_raw = pd.read_csv(filepath, encoding="utf-8-sig")
        logger.info(f"Loaded CSV with {len(df_raw)} rows")
    except UnicodeDecodeError:
        df_raw = pd.read_csv(filepath, encoding="latin-1")
    except FileNotFoundError:
        logger.error(f"CSV file not found: {filepath}")
        return _empty_df()
    except Exception as e:
        logger.error(f"CSV load error: {e}")
        return _empty_df()

    col_map = _detect_columns(df_raw.columns.tolist())
    rows = []

    for idx, row in df_raw.iterrows():
        body   = str(row.get(col_map.get("body", ""), "")).strip()
        rating = _parse_rating(row.get(col_map.get("rating", ""), None))
        date   = _parse_date(row.get(col_map.get("date", ""), None))
        author = str(row.get(col_map.get("author", ""), "Anonymous")).strip()
        title  = str(row.get(col_map.get("title", ""), "")).strip()

        if not body or body.lower() in ("nan", "none", ""):
            continue

        rows.append({
            "review_id": f"csv_{idx}",
            "source":    source_label,
            "app_name":  app_name,
            "author":    author if author not in ("nan","None","") else "Anonymous",
            "rating":    rating,
            "title":     title if title not in ("nan","None") else "",
            "body":      body,
            "date":      date,
            "thumbs_up": 0,
            "version":   "",
        })

    if not rows:
        logger.warning("No valid rows found in CSV.")
        return _empty_df()

    result = pd.DataFrame(rows)
    result["date"] = pd.to_datetime(result["date"])
    logger.info(f"Loaded {len(result)} valid CSV reviews.")
    return result

def _detect_columns(columns):
    col_lower = {c.lower(): c for c in columns}
    mapping = {}
    for field, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in col_lower:
                mapping[field] = col_lower[alias]
                break
    return mapping

def _parse_rating(val):
    if val is None or str(val).strip() in ("","nan","None"):
        return 0.0
    try:
        r = float(str(val).strip())
        if r > 5:
            r = (r / 10) * 5
        return round(min(max(r, 0), 5), 1)
    except Exception:
        return 0.0

def _parse_date(val):
    if val is None or str(val).strip() in ("","nan","None"):
        return datetime.now().strftime("%Y-%m-%d")
    try:
        return pd.to_datetime(val).strftime("%Y-%m-%d")
    except Exception:
        return datetime.now().strftime("%Y-%m-%d")

def _empty_df():
    return pd.DataFrame(columns=["review_id","source","app_name","author",
                                  "rating","title","body","date","thumbs_up","version"])

def generate_sample_csv(output_path):
    import random
    from datetime import timedelta
    random.seed(42)

    comments = [
        ("The app crashes every time I open it", 1),
        ("Love the new UI update, very clean!", 5),
        ("Subscription price is too high", 2),
        ("Offline mode doesn't work after update", 1),
        ("Search feature is broken", 2),
        ("Battery drain has gotten worse", 2),
        ("The social features are amazing", 5),
        ("Please add dark mode support", 3),
        ("Keeps logging me out randomly", 1),
        ("Best music app I've ever used", 5),
        ("Recommendations are getting better", 4),
        ("App is slow on my older device", 2),
        ("Downloaded songs disappear", 1),
        ("Customer support was very helpful", 4),
        ("Need more audio quality options", 3),
    ]

    rows = []
    base_date = datetime.now()
    for i in range(150):
        comment, base_rating = random.choice(comments)
        rating = max(1, min(5, base_rating + random.randint(-1, 1)))
        date   = base_date - timedelta(days=random.randint(0, 30))
        rows.append({
            "timestamp": date.strftime("%Y-%m-%d %H:%M:%S"),
            "name":      f"User_{i+1}",
            "rating":    rating,
            "feedback":  comment,
            "title":     comment[:30] + "...",
        })

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    pd.DataFrame(rows).to_csv(output_path, index=False)
    logger.info(f"Sample CSV created at {output_path}")
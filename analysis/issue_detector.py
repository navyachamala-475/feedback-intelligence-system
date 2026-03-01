
import logging
import re
from collections import Counter
from datetime import datetime
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

ISSUE_PATTERNS = {
    "App Crashes / Freezing": [
        "crash","crashes","crashing","freeze","frozen","stuck","hang","force close","not responding","black screen",
    ],
    "Login / Authentication": [
        "login","log in","log out","logout","sign in","sign out","password","account","authentication","logged out",
    ],
    "Performance / Speed": [
        "slow","lag","lagging","laggy","performance","loading","load time","battery","ram","memory","drain",
    ],
    "Audio / Playback Issues": [
        "playback","play","audio","sound","music","skips","skipping","buffering","stream","quality","offline","download",
    ],
    "UI / Design": [
        "ui","interface","design","layout","button","navigation","dark mode","theme","font","screen","display",
    ],
    "Subscription / Pricing": [
        "price","pricing","subscription","payment","charge","billing","expensive","cost","refund","free","premium",
    ],
    "Search Functionality": [
        "search","find","discover","recommend","suggestion","algorithm","playlist","library","browse",
    ],
    "Notifications": [
        "notification","notify","alert","push","email","spam","annoying",
    ],
    "Customer Support": [
        "support","help","service","response","contact","reply","customer","staff","team",
    ],
    "Feature Requests": [
        "feature","add","wish","want","need","request","missing","would be great","please add","should have",
    ],
}

class IssueDetector:

    def __init__(self, min_count=5, critical_neg_ratio=0.6):
        self.min_count          = min_count
        self.critical_neg_ratio = critical_neg_ratio

    def detect_issues(self, df):
        if df.empty:
            return df
        df = df.copy()
        df["issue_categories"] = df.apply(self._classify_review, axis=1)
        return df

    def get_issue_summary(self, df):
        if df.empty or "issue_categories" not in df.columns:
            return pd.DataFrame()
        issue_records = []
        for _, row in df.iterrows():
            cats = str(row.get("issue_categories","")).split(",")
            for cat in cats:
                cat = cat.strip()
                if cat:
                    issue_records.append({
                        "category": cat,
                        "compound": row.get("compound", 0),
                        "label":    row.get("sentiment_label","Neutral"),
                    })
        if not issue_records:
            return pd.DataFrame()
        issues_df = pd.DataFrame(issue_records)
        summary   = issues_df.groupby("category").agg(
            mention_count=("compound","count"),
            avg_sentiment=("compound","mean"),
            neg_count=("label", lambda x: (x=="Negative").sum()),
        ).reset_index()
        summary["neg_ratio"]      = summary["neg_count"] / summary["mention_count"]
        summary["is_critical"]    = (
            (summary["mention_count"] >= self.min_count) &
            (summary["neg_ratio"]     >= self.critical_neg_ratio)
        )
        summary["priority_score"] = (
            summary["mention_count"] * summary["neg_ratio"] * -summary["avg_sentiment"]
        ).round(3)
        return summary.sort_values("priority_score", ascending=False).reset_index(drop=True)

    def _classify_review(self, row):
        text    = f"{row.get('title','')} {row.get('body','')}".lower()
        matched = [cat for cat, kws in ISSUE_PATTERNS.items() if any(kw in text for kw in kws)]
        return ", ".join(matched) if matched else "General Feedback"


class TrendAnalyzer:

    def get_daily_sentiment(self, df):
        if df.empty or "date" not in df.columns:
            return pd.DataFrame()
        df         = df.copy()
        df["date"] = pd.to_datetime(df["date"]).dt.date
        agg        = df.groupby(["date","source"]).agg(
            avg_sentiment=("compound",  "mean"),
            avg_rating=   ("rating",    "mean"),
            review_count= ("review_id", "count"),
            positive_pct= ("sentiment_label", lambda x: (x=="Positive").sum()/len(x)*100),
            negative_pct= ("sentiment_label", lambda x: (x=="Negative").sum()/len(x)*100),
        ).reset_index()
        agg["date"] = pd.to_datetime(agg["date"])
        return agg.sort_values("date")

    def get_trend_direction(self, df):
        daily = self.get_daily_sentiment(df)
        if daily.empty:
            return {}
        results = {}
        for source in daily["source"].unique():
            src_data   = daily[daily["source"]==source].sort_values("date")
            if len(src_data) < 3:
                results[source] = "stable"
                continue
            sentiments = src_data["avg_sentiment"].values
            x          = np.arange(len(sentiments))
            slope      = np.polyfit(x, sentiments, 1)[0]
            if slope > 0.002:
                results[source] = "improving"
            elif slope < -0.002:
                results[source] = "declining"
            else:
                results[source] = "stable"
        return results

    def get_rating_distribution(self, df):
        if df.empty:
            return pd.DataFrame()
        df           = df.copy()
        df["rating"] = df["rating"].round().clip(1,5).astype(int)
        return df.groupby(["source","rating"]).size().reset_index(name="count")

    def get_top_words(self, df, sentiment=None, top_n=30):
        STOPWORDS = {
            "the","a","an","and","or","but","in","on","at","to","for","of","with",
            "this","that","is","it","i","my","me","we","you","your","they","them",
            "was","are","be","have","had","has","do","did","will","can","not","no",
            "app","so","very","just","get","got","would","could","please","also",
            "even","still","been","when","what",
        }
        filtered = df.copy()
        if sentiment:
            filtered = filtered[filtered["sentiment_label"]==sentiment]
        if filtered.empty:
            return []
        all_text  = " ".join(filtered["body"].fillna("").astype(str).tolist()).lower()
        words     = re.findall(r'\b[a-z]{3,}\b', all_text)
        word_freq = Counter(w for w in words if w not in STOPWORDS)
        return word_freq.most_common(top_n)

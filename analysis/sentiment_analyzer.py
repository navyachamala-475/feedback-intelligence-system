
import logging
import re
import pandas as pd

logger = logging.getLogger(__name__)

class SentimentAnalyzer:

    def __init__(self):
        self._vader = None
        self._load_vader()

    def _load_vader(self):
        try:
            from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
            self._vader = SentimentIntensityAnalyzer()
            logger.info("VADER sentiment model loaded.")
        except ImportError:
            logger.warning("VADER not available. Install vaderSentiment.")

    def analyze_text(self, text):
        if not text or not str(text).strip():
            return self._empty_result()
        clean = self._clean_text(str(text))
        if self._vader:
            scores   = self._vader.polarity_scores(clean)
            compound = scores["compound"]
            pos, neu, neg = scores["pos"], scores["neu"], scores["neg"]
        else:
            compound, pos, neu, neg = self._textblob_fallback(clean)
        label, confidence = self._label_from_compound(compound)
        return {
            "compound":        round(compound, 4),
            "sentiment_pos":   round(pos, 4),
            "sentiment_neu":   round(neu, 4),
            "sentiment_neg":   round(neg, 4),
            "sentiment_label": label,
            "confidence":      round(confidence, 4),
        }

    def analyze_dataframe(self, df):
        if df.empty:
            return df
        logger.info(f"Analyzing sentiment for {len(df)} reviews...")
        combined_text = (
            df.get("title", pd.Series([""] * len(df))).fillna("").astype(str)
            + " "
            + df.get("body", pd.Series([""] * len(df))).fillna("").astype(str)
        ).str.strip()
        results      = combined_text.apply(self.analyze_text)
        sentiment_df = pd.DataFrame(results.tolist())
        for col in sentiment_df.columns:
            df[col] = sentiment_df[col].values
        logger.info("Sentiment analysis complete.")
        return df

    @staticmethod
    def _clean_text(text):
        text = re.sub(r"http\S+|www\.\S+", "", text)
        text = re.sub(r"[^\w\s\!\?\.\,\'\"-]", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:5000]

    @staticmethod
    def _label_from_compound(compound):
        if compound >= 0.05:
            label      = "Positive"
            confidence = min(1.0, (compound + 1) / 2)
        elif compound <= -0.05:
            label      = "Negative"
            confidence = min(1.0, (-compound + 1) / 2)
        else:
            label      = "Neutral"
            confidence = 1.0 - abs(compound) * 10
        return label, round(max(0.5, confidence), 4)

    @staticmethod
    def _textblob_fallback(text):
        try:
            from textblob import TextBlob
            blob     = TextBlob(text)
            polarity = blob.sentiment.polarity
            if polarity > 0:
                return polarity * 0.9, polarity, 1 - polarity, 0
            elif polarity < 0:
                return polarity * 0.9, 0, 1 + polarity, -polarity
            return 0, 0, 1, 0
        except Exception:
            return 0, 0, 1, 0

    @staticmethod
    def _empty_result():
        return {
            "compound": 0.0, "sentiment_pos": 0.0,
            "sentiment_neu": 1.0, "sentiment_neg": 0.0,
            "sentiment_label": "Neutral", "confidence": 0.5,
        }
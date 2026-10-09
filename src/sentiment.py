"""
sentiment.py
Rule-based financial sentiment using VADER plus a small finance lexicon.
No model training, no heavy dependencies.

Output scale: 1 (very negative) .. 5.5 (neutral) .. 10 (very positive)
"""

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# VADER is built for social media, so we add finance-specific words.
# Values range roughly -4 (very negative) to +4 (very positive).
FINANCE_LEXICON = {
    # negative
    "crash": -3.0, "plunge": -3.0, "slump": -2.5, "default": -3.0, "defaults": -3.0,
    "downgrade": -2.5, "downgrades": -2.5, "downgraded": -2.5, "recession": -3.0,
    "crisis": -3.0, "bankruptcy": -3.5, "fraud": -3.5, "manipulation": -3.0,
    "investigation": -2.0, "probe": -2.0, "penalties": -2.0, "penalty": -2.0,
    "ban": -2.5, "bans": -2.5, "banned": -2.5, "sanctions": -2.5, "conflict": -2.5,
    "shortage": -2.0, "shutdown": -2.5, "halts": -2.0, "strike": -1.5,
    "disruption": -2.0, "inflation": -1.5, "spike": -1.5, "bad": -2.0,
    "falls": -1.8, "drop": -1.8, "slashes": -2.0, "layoffs": -2.5,
    "escalates": -2.0, "contracts": -1.5, "fears": -2.0, "breach": -2.5,
    # positive
    "record": 2.0, "profit": 2.0, "jumps": 2.2, "surges": 1.0, "wins": 2.5,
    "growth": 2.0, "improved": 2.0, "strong": 2.2, "launches": 1.5,
    "completes": 1.5, "acquire": 1.0, "expands": 1.8, "upgrade": 2.5,
    "upgraded": 2.5, "rally": 2.5, "beats": 2.0, "steady": 0.8,
}

_analyzer = SentimentIntensityAnalyzer()
_analyzer.lexicon.update(FINANCE_LEXICON)


def compound_to_score(compound):
    """Map VADER compound (-1..1) to the 1..10 scale used by the engine."""
    return round(1 + (compound + 1) / 2 * 9, 1)


def get_label(compound):
    if compound >= 0.15:
        return "Positive"
    if compound <= -0.15:
        return "Negative"
    return "Neutral"


def analyze_sentiment(text):
    """
    Returns dict:
      compound        float -1..1 (raw VADER)
      sentiment_score float 1..10 (1 = very negative, 10 = very positive)
      label           'Positive' | 'Neutral' | 'Negative'
    """
    text = (text or "").strip()
    compound = _analyzer.polarity_scores(text)["compound"] if text else 0.0
    return {
        "compound": round(compound, 3),
        "sentiment_score": compound_to_score(compound),
        "label": get_label(compound),
    }


if __name__ == "__main__":
    import pandas as pd
    from pathlib import Path

    csv = Path(__file__).resolve().parent.parent / "data" / "financial_news.csv"
    df = pd.read_csv(csv)
    for _, row in df.iterrows():
        r = analyze_sentiment(row["headline"])
        print(f"{r['sentiment_score']:>4} {r['label']:<9} {row['headline'][:70]}")
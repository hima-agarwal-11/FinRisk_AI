"""
Loads financial headlines from NewsAPI, with automatic fallback to a local CSV.
"""

import os
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
CSV_PATH = BASE_DIR / "data" / "financial_news.csv"

load_dotenv(BASE_DIR / ".env")

NEWSAPI_URL = "https://newsapi.org/v2/everything"
DEFAULT_QUERY = (
    "(bank OR RBI OR SEBI OR inflation OR earnings OR merger OR sanctions) "
    "AND (India OR market)"
)
COLUMNS = ["id", "source", "company", "headline"]


def load_csv_headlines(path=CSV_PATH):
    """Load local headlines as a reliable fallback."""
    df = pd.read_csv(path)
    df["source"] = df["source"].fillna("synthetic")
    return df[COLUMNS]


def fetch_newsapi_headlines(query=DEFAULT_QUERY, page_size=20, timeout=8):
    """Fetch news articles, returning None if the API is unavailable."""
    api_key = os.getenv("NEWSAPI_KEY", "").strip()

    if not api_key or api_key == "your_key_here":
        return None

    params = {
        "q": query,
        "language": "en",
        "sortBy": "publishedAt",
        "pageSize": page_size,
        "apiKey": api_key,
    }

    try:
        response = requests.get(NEWSAPI_URL, params=params, timeout=timeout)
        response.raise_for_status()
        articles = response.json().get("articles", [])
    except Exception as exc:
        print(f"[ingestion] NewsAPI failed ({exc}); using CSV fallback.")
        return None

    rows = []

    for i, article in enumerate(articles, start=1):
        title = (article.get("title") or "").strip()

        if not title or title == "[Removed]":
            continue

        source_name = (article.get("source") or {}).get("name") or "NewsAPI"

        rows.append({
            "id": i,
            "source": f"NewsAPI:{source_name}",
            "company": "Market News",
            "headline": title,
        })

    if not rows:
        print("[ingestion] No usable NewsAPI articles; using CSV fallback.")
        return None

    return pd.DataFrame(rows, columns=COLUMNS)


def get_headlines(use_api=True):
    """Return a DataFrame and the source label."""
    if use_api:
        df = fetch_newsapi_headlines()
        if df is not None and not df.empty:
            return df, "NewsAPI (live)"

    return load_csv_headlines(), "CSV (local fallback)"


if __name__ == "__main__":
    data, label = get_headlines()
    print(f"Source used: {label}")
    print(f"Headlines loaded: {len(data)}")
    print(data.head(3).to_string(index=False))
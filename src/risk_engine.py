"""
risk_engine.py
Combines sentiment + event classification into one structured, explainable
risk signal per headline.

impact_score (1-10) = 0.40 * event_weight
                    + 0.35 * sentiment_extremity
                    + 0.25 * keyword_severity
Every component is on a 0-10 scale, and all three are returned so the score
can be explained to a judge.
"""

import json
import re
from pathlib import Path

import pandas as pd

from sentiment import analyze_sentiment
from event_classifier import classify_event

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

IMPACT_THRESHOLD = 7  # impact_score > 7 triggers the stress test

# How market-moving each event type usually is (prototype ASSUMPTION, 0-10)
EVENT_WEIGHTS = {
    "Geopolitical": 9,
    "Macroeconomic": 8,
    "Regulatory": 8,
    "Merger/Acquisition": 6,
    "Supply Chain": 6,
    "Financial Performance": 5,
    "Product Launch": 3,
    "Other": 2,
}

# Severe words. Each hit adds to keyword_severity (capped at 10).
SEVERITY_KEYWORDS = {
    "crash": 4, "plunge": 4, "collapse": 4, "default": 4, "defaults": 4,
    "bankruptcy": 5, "fraud": 5, "manipulation": 4, "crisis": 4, "recession": 4,
    "war": 4, "military": 3, "conflict": 3, "sanctions": 4, "sanction": 4,
    "ban": 3, "bans": 3, "banned": 3, "downgrade": 3, "downgrades": 3,
    "investigation": 3, "penalties": 3, "shutdown": 3, "halts": 3,
    "escalates": 3, "slump": 3, "surges": 2, "spike": 2, "disruption": 3,
    "shortage": 2, "strike": 2, "breach": 3, "layoffs": 3, "contracts": 2,
}

# Positive news is less of a downside risk, so its extremity counts for less.
POSITIVE_DAMPING = 0.5


def keyword_severity(text):
    """Return (severity 0-10, list of matched severe words)."""
    words = re.findall(r"[a-z]+", (text or "").lower())
    hits = [w for w in words if w in SEVERITY_KEYWORDS]
    score = min(10, sum(SEVERITY_KEYWORDS[w] for w in hits))
    return score, sorted(set(hits))


def compute_impact(compound, event_type, severity):
    """Returns (impact_score 1-10, breakdown dict)."""
    event_weight = EVENT_WEIGHTS.get(event_type, 2)
    extremity = abs(compound) * 10
    if compound > 0:
        extremity *= POSITIVE_DAMPING

    raw = 0.40 * event_weight + 0.35 * extremity + 0.25 * severity
    impact = round(max(1, min(10, raw)), 1)
    breakdown = {
        "event_weight": event_weight,
        "sentiment_extremity": round(extremity, 1),
        "keyword_severity": severity,
    }
    return impact, breakdown


def analyze_headline(headline, company="Unknown"):
    """Full NLP pipeline for one headline -> structured risk signal (dict)."""
    sent = analyze_sentiment(headline)
    event = classify_event(headline)
    severity, hits = keyword_severity(headline)
    impact, breakdown = compute_impact(sent["compound"], event["event_type"], severity)

    return {
        # --- required fields ---
        "company": company,
        "headline": headline,
        "sentiment_score": sent["sentiment_score"],
        "event_type": event["event_type"],
        "impact_score": impact,
        # --- extra fields for the dashboard / explainability ---
        "sentiment_label": sent["label"],
        "stress_test_triggered": impact > IMPACT_THRESHOLD,
        "severity_keywords": hits,
        "impact_breakdown": breakdown,
    }


def analyze_dataframe(df):
    """Run the engine on a DataFrame with 'company' and 'headline' columns."""
    return [analyze_headline(r["headline"], r.get("company", "Unknown"))
            for _, r in df.iterrows()]


def save_signals(signals, folder=DATA_DIR):
    """Save signals to data/risk_signals.json and data/risk_signals.csv."""
    folder = Path(folder)
    folder.mkdir(exist_ok=True)
    with open(folder / "risk_signals.json", "w", encoding="utf-8") as f:
        json.dump(signals, f, indent=2, ensure_ascii=False)
    flat = pd.DataFrame(signals)
    flat["severity_keywords"] = flat["severity_keywords"].apply(", ".join)
    flat["impact_breakdown"] = flat["impact_breakdown"].apply(json.dumps)
    flat.to_csv(folder / "risk_signals.csv", index=False)


if __name__ == "__main__":
    df = pd.read_csv(DATA_DIR / "financial_news.csv")
    signals = analyze_dataframe(df)
    save_signals(signals)

    print(f"{'Company':<20} {'Event':<22} {'Sent':>4} {'Impact':>6}  Stress?")
    for s in signals:
        flag = "YES" if s["stress_test_triggered"] else "-"
        print(f"{s['company'][:19]:<20} {s['event_type']:<22} "
              f"{s['sentiment_score']:>4} {s['impact_score']:>6}  {flag}")
    triggered = sum(s["stress_test_triggered"] for s in signals)
    print(f"\n{len(signals)} signals saved to data/risk_signals.json and .csv")
    print(f"Stress test triggered for {triggered} headline(s)")
    print("\nSample signal (JSON):")
    sample = {k: signals[6][k] for k in
              ["company", "headline", "sentiment_score", "event_type", "impact_score"]}
    print(json.dumps(sample, indent=2))
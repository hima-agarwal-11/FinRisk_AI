"""
nlp_engine.py
Unified pipeline that connects every module:

  ingestion -> sentiment + event classification -> risk signal
            -> (if impact_score > 7) stress test -> result

The Streamlit dashboard only needs the two functions below.
"""

from data_ingestion import get_headlines
from risk_engine import analyze_dataframe, analyze_headline, save_signals
from stress_test import run_stress_test


def process_headline(headline, company="Custom Input"):
    """
    Analyze ONE headline (picked from the list or typed by the user).
    Returns dict: {"signal": {...}, "stress": {...} or None}
    The stress test only runs when the signal's impact_score > 7.
    """
    signal = analyze_headline(headline, company)
    stress = run_stress_test(signal["event_type"]) if signal["stress_test_triggered"] else None
    return {"signal": signal, "stress": stress}


def run_pipeline(use_api=True, save=True):
    """
    Ingest headlines (API with CSV fallback) and analyze all of them.
    Returns (signals list, source label).
    """
    df, source_label = get_headlines(use_api=use_api)
    signals = analyze_dataframe(df)
    if save:
        save_signals(signals)
    return signals, source_label


if __name__ == "__main__":
    signals, source = run_pipeline()
    triggered = [s for s in signals if s["stress_test_triggered"]]
    print(f"Source: {source}")
    print(f"Signals generated: {len(signals)}")
    print(f"Stress test triggered: {len(triggered)}")

    # End-to-end demo on the highest-impact headline
    top = max(signals, key=lambda s: s["impact_score"])
    result = process_headline(top["headline"], top["company"])
    sig, st = result["signal"], result["stress"]
    print("\n--- End-to-end example (highest impact) ---")
    print(f"Headline : {sig['headline']}")
    print(f"Event    : {sig['event_type']} | Sentiment {sig['sentiment_score']} | Impact {sig['impact_score']}")
    if st:
        print(f"Stress   : TRIGGERED -> {st['value_before']:,.0f} -> {st['value_after']:,.0f} "
              f"({st['total_change_pct']}%)")

    # Custom text that should NOT trigger
    calm = process_headline("Zomato launches new app feature for restaurants", "Zomato")
    print(f"\nCustom calm headline -> impact {calm['signal']['impact_score']}, "
          f"stress triggered: {calm['stress'] is not None}")
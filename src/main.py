"""
main.py  -  FinRisk AI Streamlit dashboard
Run:  streamlit run src/main.py
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from nlp_engine import process_headline, run_pipeline
from risk_engine import IMPACT_THRESHOLD
from stress_test import format_inr, run_stress_test

ASSUMPTION_NOTE = (
    "All shock percentages, event weights and severity points in this prototype "
    "are ASSUMPTIONS for demonstration. They are not real market predictions "
    "and this is not financial advice."
)

st.set_page_config(page_title="FinRisk AI", page_icon="📉", layout="wide")


@st.cache_data(show_spinner="Loading and analyzing headlines...")
def load_signals(use_api):
    return run_pipeline(use_api=use_api)


# ------------------------------------------------------------------ header
st.title("📉 FinRisk AI")
st.caption("AI-Powered Financial Risk Intelligence & Event-Driven Stress Testing")
st.warning(ASSUMPTION_NOTE, icon="⚠️")

# ----------------------------------------------------------------- sidebar
with st.sidebar:
    st.header("Controls")
    use_api = st.checkbox("Try NewsAPI (falls back to CSV)", value=True)
    mode = st.radio("Input mode", ["Pick a headline", "Enter custom text"])
    force_stress = st.checkbox("Force stress test (demo)", value=False,
                               help="Run the stress test even if impact score is not above the threshold.")
    st.markdown(f"**Stress test trigger:** impact score > {IMPACT_THRESHOLD}")

signals, source_label = load_signals(use_api)
st.sidebar.success(f"Data source: {source_label}")

# ------------------------------------------------------------ input select
if mode == "Pick a headline":
    labels = [f"{s['company']}: {s['headline']}" for s in signals]
    choice = st.selectbox("Select a headline", range(len(labels)), format_func=lambda i: labels[i])
    company, headline = signals[choice]["company"], signals[choice]["headline"]
else:
    headline = st.text_area("Enter a headline or short news text",
                            "SEBI launches fraud investigation into major bank as shares crash and defaults rise")
    company = st.text_input("Company (optional)", "Custom Input")

if not headline.strip():
    st.info("Enter some text to analyze.")
    st.stop()

result = process_headline(headline, company or "Custom Input")
signal = result["signal"]
stress = result["stress"]
if stress is None and force_stress:
    stress = run_stress_test(signal["event_type"])

# ------------------------------------------------------------ risk signal
st.subheader("1. Risk Signal")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Event type", signal["event_type"])
c2.metric("Sentiment (1-10)", signal["sentiment_score"], signal["sentiment_label"], delta_color="off")
c3.metric("Impact score (1-10)", signal["impact_score"])
c4.metric("Stress test", "TRIGGERED" if signal["stress_test_triggered"] else "Not triggered")

with st.expander("Why this impact score? (explainability)"):
    b = signal["impact_breakdown"]
    st.write(
        f"**Impact = 0.40 × event weight + 0.35 × sentiment extremity + 0.25 × keyword severity**\n\n"
        f"- Event weight ({signal['event_type']}): **{b['event_weight']}**\n"
        f"- Sentiment extremity: **{b['sentiment_extremity']}**\n"
        f"- Keyword severity: **{b['keyword_severity']}** "
        f"(matched: {', '.join(signal['severity_keywords']) or 'none'})"
    )
    st.json({k: signal[k] for k in ["company", "headline", "sentiment_score", "event_type", "impact_score"]})

# ------------------------------------------------------------ stress test
st.subheader("2. Portfolio Stress Test (Module B)")
if stress is None:
    st.info(f"Impact score {signal['impact_score']} is not above {IMPACT_THRESHOLD}, "
            "so no stress test was triggered. Tick 'Force stress test' in the sidebar to see one anyway.")
else:
    if not signal["stress_test_triggered"]:
        st.caption("Stress test forced manually (demo mode).")
    m1, m2, m3 = st.columns(3)
    m1.metric("Portfolio value before", format_inr(stress["value_before"]))
    m2.metric("Portfolio value after", format_inr(stress["value_after"]))
    m3.metric("Total loss / gain", format_inr(stress["total_change"]),
              f"{stress['total_change_pct']}%")

    df = stress["asset_impact"]
    left, right = st.columns(2)

    fig1 = go.Figure()
    fig1.add_bar(name="Before", x=df["asset_class"], y=df["value_before"], marker_color="#4C78A8")
    fig1.add_bar(name="After", x=df["asset_class"], y=df["value_after"], marker_color="#F58518")
    fig1.update_layout(barmode="group", title="Portfolio value before vs after (INR)",
                       yaxis_title="Value (INR)", legend_orientation="h", margin=dict(t=50, b=10))
    left.plotly_chart(fig1, width="stretch")

    colors = ["#2CA02C" if v >= 0 else "#D62728" for v in df["change_inr"]]
    fig2 = go.Figure(go.Bar(x=df["asset_class"], y=df["change_inr"], marker_color=colors,
                            text=[f"{p:+.0f}%" for p in df["shock_pct"]], textposition="outside"))
    fig2.update_layout(title=f"Asset-wise impact: {stress['event_type']} event (INR)",
                       yaxis_title="Gain / loss (INR)", margin=dict(t=50, b=10))
    right.plotly_chart(fig2, width="stretch")

    table = pd.DataFrame({
        "Asset class": df["asset_class"],
        "Shock (assumed)": df["shock_pct"].map(lambda p: f"{p:+.0f}%"),
        "Value before": df["value_before"].map(format_inr),
        "Value after": df["value_after"].map(format_inr),
        "Change": df["change_inr"].map(format_inr),
    })
    st.dataframe(table, hide_index=True, width="stretch")

# ------------------------------------------------------------ all signals
with st.expander("All risk signals from the engine"):
    all_df = pd.DataFrame(signals)[["company", "headline", "sentiment_score", "event_type",
                                    "impact_score", "stress_test_triggered"]]
    st.dataframe(all_df, hide_index=True, width="stretch")

st.caption(ASSUMPTION_NOTE)
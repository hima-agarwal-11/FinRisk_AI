"""
stress_test.py  (Module B: event-driven portfolio stress test)

Applies an event-specific shock table to a synthetic Rs 1 crore portfolio and
reports value before, value after, total loss/gain and asset-wise impact.

IMPORTANT: every shock percentage below is a prototype ASSUMPTION chosen for
demonstration. They are NOT real market predictions.
"""

from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
PORTFOLIO_PATH = BASE_DIR / "data" / "portfolio.csv"

# Percentage change applied to each asset class when an event type is detected
SHOCK_TABLES = {
    "Regulatory": {"Govt Bonds": 2, "Corporate Bonds": -5, "Loans": -3, "Equity": -10, "Derivatives": -15},
    "Geopolitical": {"Govt Bonds": 3, "Corporate Bonds": -6, "Loans": -4, "Equity": -12, "Derivatives": -20},
    "Macroeconomic": {"Govt Bonds": -2, "Corporate Bonds": -4, "Loans": -4, "Equity": -9, "Derivatives": -12},
    "Financial Performance": {"Govt Bonds": 1, "Corporate Bonds": -7, "Loans": -8, "Equity": -8, "Derivatives": -10},
    "Supply Chain": {"Govt Bonds": 0, "Corporate Bonds": -3, "Loans": -4, "Equity": -6, "Derivatives": -8},
    "Merger/Acquisition": {"Govt Bonds": 0, "Corporate Bonds": -1, "Loans": -1, "Equity": -3, "Derivatives": -4},
    "Product Launch": {"Govt Bonds": 0, "Corporate Bonds": 0, "Loans": 0, "Equity": 1, "Derivatives": 1},
    "Other": {"Govt Bonds": 0, "Corporate Bonds": 0, "Loans": 0, "Equity": -1, "Derivatives": -1},
}


def load_portfolio(path=PORTFOLIO_PATH):
    return pd.read_csv(path)


def run_stress_test(event_type, portfolio=None):
    """
    Returns dict:
      event_type, value_before, value_after, total_change, total_change_pct,
      asset_impact (DataFrame: asset_class, value_before, shock_pct,
                    value_after, change_inr)
    """
    if portfolio is None:
        portfolio = load_portfolio()
    shocks = SHOCK_TABLES.get(event_type, SHOCK_TABLES["Other"])

    df = portfolio.rename(columns={"value_inr": "value_before"}).copy()
    df["shock_pct"] = df["asset_class"].map(shocks).fillna(0)
    df["value_after"] = (df["value_before"] * (1 + df["shock_pct"] / 100)).round(0)
    df["change_inr"] = df["value_after"] - df["value_before"]

    before = float(df["value_before"].sum())
    after = float(df["value_after"].sum())
    return {
        "event_type": event_type if event_type in SHOCK_TABLES else "Other",
        "value_before": before,
        "value_after": after,
        "total_change": after - before,
        "total_change_pct": round((after - before) / before * 100, 2),
        "asset_impact": df,
    }


def format_inr(amount):
    """Indian digit grouping, e.g. 10000000 -> Rs 1,00,00,000."""
    sign = "-" if amount < 0 else ""
    s = str(int(round(abs(amount))))
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        s = ",".join(parts + [tail])
    return f"{sign}Rs {s}"


if __name__ == "__main__":
    for event in ["Regulatory", "Geopolitical", "Product Launch"]:
        r = run_stress_test(event)
        print(f"=== {event} ===")
        print(f"Before: {format_inr(r['value_before'])}")
        print(f"After : {format_inr(r['value_after'])}")
        print(f"Change: {format_inr(r['total_change'])} ({r['total_change_pct']}%)")
        for _, row in r["asset_impact"].iterrows():
            print(f"  {row['asset_class']:<16} {row['shock_pct']:>+5.0f}%  {format_inr(row['change_inr'])}")
        print()
    print("NOTE: shock percentages are prototype assumptions, not real predictions.")
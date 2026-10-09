"""
event_classifier.py
Rule-based event classification using weighted keyword patterns.
No model training. Each event type has a list of regex patterns; the type with
the most matches wins. Ties are broken by PRIORITY order.
"""

import re

EVENT_TYPES = [
    "Geopolitical", "Macroeconomic", "Regulatory", "Merger/Acquisition",
    "Product Launch", "Financial Performance", "Supply Chain", "Other",
]

# Patterns are matched on whole words. "\w*" lets a stem match its variants
# (e.g. "acquir\w*" matches acquire, acquires, acquisition).
EVENT_KEYWORDS = {
    "Geopolitical": [
        r"war", r"military", r"conflict", r"sanctions?", r"missile", r"invasion",
        r"troops", r"tensions?", r"border", r"terror\w*", r"embargo", r"geopolitic\w*",
        r"middle east", r"ceasefire", r"nuclear",
    ],
    "Macroeconomic": [
        r"repo rate", r"interest rates?", r"rate (hike|cut)", r"inflation", r"gdp",
        r"recession", r"unemployment", r"fiscal", r"monetary", r"oil prices?",
        r"currency", r"rupee", r"basis points", r"central bank", r"fed",
    ],
    "Regulatory": [
        r"rbi imposes", r"sebi", r"regulat\w*", r"compliance", r"penalt\w*",
        r"norms", r"ban(s|ned)?", r"investigation", r"probe", r"gst",
        r"fine[sd]?", r"licen[cs]e", r"audit", r"lawsuit", r"antitrust", r"tax rules?",
    ],
    "Merger/Acquisition": [
        r"merger", r"merges?", r"merged", r"acquir\w*", r"acquisition", r"takeover",
        r"buyout", r"stake sale", r"demerger", r"all-cash deal",
    ],
    "Product Launch": [
        r"launch\w*", r"unveil\w*", r"introduces?", r"rolls? out", r"new (model|service|product|app|suv)",
        r"debut\w*",
    ],
    "Financial Performance": [
        r"profit", r"revenue", r"earnings", r"quarterly", r"results", r"loan growth",
        r"bad loans", r"defaults?", r"downgrade[sd]?", r"upgrade[sd]?", r"liquidity",
        r"dividend", r"margins?", r"contract", r"asset quality", r"shares slump",
        r"net loss", r"guidance",
    ],
    "Supply Chain": [
        r"supply chain", r"shortage", r"shutdown", r"halts?",
        r"port strike", r"strike", r"logistics", r"semiconductor", r"raw material",
        r"disrupt\w*", r"shipment", r"factory", r"plants?",
    ],
}

# Strong signals count double (a sanction or a SEBI action is the real driver
# of a headline even when other words also match).
STRONG = {"sanctions?", "military", "conflict", "invasion", "missile", "war",
          "sebi", "rbi imposes", "merger", "acquir\\w*", "takeover"}

# Tie-break order (first = highest priority)
PRIORITY = [
    "Geopolitical", "Regulatory", "Merger/Acquisition", "Macroeconomic",
    "Supply Chain", "Financial Performance", "Product Launch",
]

_COMPILED = {
    etype: [(re.compile(rf"\b{p}\b", re.IGNORECASE), 2 if p in STRONG else 1)
            for p in patterns]
    for etype, patterns in EVENT_KEYWORDS.items()
}


def classify_event(text):
    """
    Returns dict:
      event_type  one of EVENT_TYPES
      matches     keyword score for the winning type
    """
    text = text or ""
    scores = {
        etype: sum(w for rx, w in regexes if rx.search(text))
        for etype, regexes in _COMPILED.items()
    }
    best = max(scores.values())
    if best == 0:
        return {"event_type": "Other", "matches": 0}

    tied = [e for e, s in scores.items() if s == best]
    winner = min(tied, key=PRIORITY.index)
    return {"event_type": winner, "matches": best}


if __name__ == "__main__":
    import pandas as pd
    from pathlib import Path

    csv = Path(__file__).resolve().parent.parent / "data" / "financial_news.csv"
    df = pd.read_csv(csv)
    for _, row in df.iterrows():
        r = classify_event(row["headline"])
        print(f"{r['event_type']:<22} ({r['matches']}) {row['headline'][:60]}")
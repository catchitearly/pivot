"""
Builds a single self-contained interactive HTML dashboard from the backtest
outputs: results/nifty_indicators.csv, results/trade_log.csv, results/summary.json

Usage:
    python generate_dashboard.py

Output:
    results/dashboard.html
"""

import json
import os

import numpy as np
import pandas as pd

import config

TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), "dashboard_template.html")


def _segment_by_direction(df: pd.DataFrame):
    """Split supertrend into a green (bullish) series and a red (bearish) series,
    each with None where the other direction is active, so Plotly renders two
    distinctly colored lines over the same x-axis (small 1-bar gap at each
    direction flip, which is a reasonable/accurate visual signal itself)."""
    bull_x = df["timestamp"].tolist()
    bull_y = [v if d == 1 else None for v, d in zip(df["supertrend"], df["supertrend_dir"])]
    bear_x = df["timestamp"].tolist()
    bear_y = [v if d == -1 else None for v, d in zip(df["supertrend"], df["supertrend_dir"])]
    return bull_x, bull_y, bear_x, bear_y


def build():
    nifty = pd.read_csv(f"{config.OUTPUT_DIR}/nifty_indicators.csv", parse_dates=["timestamp"])
    trades_path = f"{config.OUTPUT_DIR}/trade_log.csv"
    trades = pd.read_csv(trades_path, parse_dates=["entry_time", "exit_time"]) if os.path.exists(trades_path) and os.path.getsize(trades_path) > 0 else pd.DataFrame()

    with open(f"{config.OUTPUT_DIR}/summary.json") as f:
        summary = json.load(f)

    bull_x, bull_y, bear_x, bear_y = _segment_by_direction(nifty)

    price_data = {
        "x": nifty["timestamp"].dt.strftime("%Y-%m-%d %H:%M").tolist(),
        "close": nifty["close"].round(2).tolist(),
        "r1": nifty["r1"].round(2).tolist(),
        "s1": nifty["s1"].round(2).tolist(),
        "pivot": nifty["pivot"].round(2).tolist(),
        "st_bull_x": [pd.Timestamp(t).strftime("%Y-%m-%d %H:%M") for t in bull_x],
        "st_bull_y": [None if v is None or (isinstance(v, float) and np.isnan(v)) else round(v, 2) for v in bull_y],
        "st_bear_x": [pd.Timestamp(t).strftime("%Y-%m-%d %H:%M") for t in bear_x],
        "st_bear_y": [None if v is None or (isinstance(v, float) and np.isnan(v)) else round(v, 2) for v in bear_y],
    }

    if not trades.empty:
        trades = trades.sort_values("entry_time").reset_index(drop=True)
        trades["cum_pnl"] = trades["pnl_rupees"].cumsum()
        entries_pe = trades[trades["option_type"] == "PE"]
        entries_ce = trades[trades["option_type"] == "CE"]

        markers = {
            "pe_entry_x": entries_pe["entry_time"].dt.strftime("%Y-%m-%d %H:%M").tolist(),
            "pe_entry_y": entries_pe["entry_spot"].round(2).tolist(),
            "ce_entry_x": entries_ce["entry_time"].dt.strftime("%Y-%m-%d %H:%M").tolist(),
            "ce_entry_y": entries_ce["entry_spot"].round(2).tolist(),
            "exit_x": trades["exit_time"].dt.strftime("%Y-%m-%d %H:%M").tolist(),
            "exit_y": trades["exit_spot"].round(2).tolist(),
        }

        pnl_data = {
            "x": trades["exit_time"].dt.strftime("%Y-%m-%d %H:%M").tolist(),
            "cum_pnl": trades["cum_pnl"].round(2).tolist(),
            "trade_pnl": trades["pnl_rupees"].round(2).tolist(),
        }

        table_cols = ["entry_time", "exit_time", "option_type", "strike", "expiry",
                      "entry_pivot", "entry_r1", "entry_s1",
                      "entry_price", "exit_price", "pnl_points", "pnl_rupees",
                      "entry_reason", "exit_reason"]
        table_cols = [c for c in table_cols if c in trades.columns]
        table_df = trades[table_cols].copy()
        for c in ["entry_time", "exit_time"]:
            if c in table_df.columns:
                table_df[c] = table_df[c].dt.strftime("%Y-%m-%d %H:%M")
        for c in ["entry_pivot", "entry_r1", "entry_s1", "entry_price", "exit_price", "pnl_points", "pnl_rupees"]:
            if c in table_df.columns:
                table_df[c] = table_df[c].round(2)
        table_rows = table_df.to_dict(orient="records")
    else:
        markers = {"pe_entry_x": [], "pe_entry_y": [], "ce_entry_x": [], "ce_entry_y": [], "exit_x": [], "exit_y": []}
        pnl_data = {"x": [], "cum_pnl": [], "trade_pnl": []}
        table_rows = []

    with open(TEMPLATE_PATH) as f:
        template = f.read()

    html = template
    html = html.replace("__PRICE_DATA__", json.dumps(price_data))
    html = html.replace("__MARKERS__", json.dumps(markers))
    html = html.replace("__PNL_DATA__", json.dumps(pnl_data))
    html = html.replace("__TABLE_ROWS__", json.dumps(table_rows))
    html = html.replace("__SUMMARY__", json.dumps(summary))

    out_path = f"{config.OUTPUT_DIR}/dashboard.html"
    with open(out_path, "w") as f:
        f.write(html)
    print(f"Dashboard written to {out_path}")


if __name__ == "__main__":
    build()

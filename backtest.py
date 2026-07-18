"""
Main backtest runner.

Pipeline:
1. Fetch Nifty index 5-min candles for the configured date range.
2. Compute daily pivots (R1/S1) + Supertrend(7,3).
3. Generate ENTRY/EXIT events per strategy rules.
4. For each ENTRY, resolve ATM strike + weekly expiry -> option symbol,
   fetch that option's 5-min data, and pull the price at entry/exit timestamps.
5. Pair up entries/exits into trades, compute P&L (short option: profit = entry - exit),
   write trade_log.csv and summary.json.
"""

import json
import os
from datetime import date, timedelta

import pandas as pd

import config
import fyers_client
import indicators
import strategy
import symbols


def resolve_option_price(fyers, option_symbol: str, ts: pd.Timestamp, cache: dict) -> float:
    """Fetch (with caching) the option's 5-min series and return the close price
    at or immediately after `ts`."""
    if option_symbol not in cache:
        day = ts.date()
        df = fyers_client.fetch_history(
            fyers, option_symbol, str(config.TIMEFRAME_MINUTES), day, day
        )
        cache[option_symbol] = df

    df = cache[option_symbol]
    if df.empty:
        raise ValueError(f"No option data returned for {option_symbol} on {ts.date()}")

    candidates = df[df["timestamp"] >= ts]
    row = candidates.iloc[0] if not candidates.empty else df.iloc[-1]
    return float(row["close"])


def run():
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    fyers = fyers_client.get_fyers_session()

    print(f"Fetching Nifty 5-min data {config.START_DATE} -> {config.END_DATE} "
          f"(+{config.PIVOT_LOOKBACK_CALENDAR_DAYS}d lookback for pivot calc) ...")
    fetch_start = config.START_DATE - timedelta(days=config.PIVOT_LOOKBACK_CALENDAR_DAYS)
    nifty_df = fyers_client.fetch_history(
        fyers, config.INDEX_SYMBOL, str(config.TIMEFRAME_MINUTES),
        fetch_start, config.END_DATE,
    )
    if nifty_df.empty:
        raise RuntimeError("No Nifty data returned — check symbol/date range/token.")

    nifty_df = indicators.add_daily_pivots(nifty_df)
    nifty_df = indicators.add_supertrend(
        nifty_df, period=config.SUPERTREND_PERIOD, multiplier=config.SUPERTREND_MULTIPLIER
    )

    # trim the lookback buffer back off now that pivots/supertrend are computed
    nifty_df = nifty_df[nifty_df["timestamp"].dt.date >= config.START_DATE].reset_index(drop=True)
    if nifty_df.empty:
        raise RuntimeError(
            "No candles remain after trimming to START_DATE — this usually means "
            "START_DATE has no prior trading day within PIVOT_LOOKBACK_CALENDAR_DAYS. "
            "Increase PIVOT_LOOKBACK_CALENDAR_DAYS in config.py."
        )

    events = strategy.generate_events(nifty_df)
    print(f"Generated {len(events)} raw entry/exit events.")

    # persist full indicator series for the dashboard (price, R1/S1, supertrend)
    nifty_df.to_csv(f"{config.OUTPUT_DIR}/nifty_indicators.csv", index=False)

    option_cache: dict = {}
    trades = []
    open_trade = None

    for ev in events:
        expiry = symbols.get_weekly_expiry(ev.timestamp.date())
        strike = symbols.get_atm_strike(ev.spot)
        option_symbol = symbols.build_option_symbol(expiry, strike, ev.option_type)

        try:
            price = resolve_option_price(fyers, option_symbol, ev.timestamp, option_cache)
        except Exception as e:  # noqa: BLE001
            print(f"[WARN] skipping event {ev} due to price fetch error: {e}")
            continue

        if ev.kind == "ENTRY":
            open_trade = {
                "entry_time": ev.timestamp,
                "option_type": ev.option_type,
                "expiry": expiry,
                "strike": strike,
                "symbol": option_symbol,
                "entry_price": price,
                "entry_spot": ev.spot,
                "entry_reason": ev.reason,
                "entry_pivot": ev.pivot,
                "entry_r1": ev.r1,
                "entry_s1": ev.s1,
            }
        elif ev.kind == "EXIT" and open_trade is not None:
            open_trade.update({
                "exit_time": ev.timestamp,
                "exit_price": price,
                "exit_spot": ev.spot,
                "exit_reason": ev.reason,
                "exit_pivot": ev.pivot,
                "exit_r1": ev.r1,
                "exit_s1": ev.s1,
            })
            # short option: profit when price falls
            open_trade["pnl_points"] = open_trade["entry_price"] - open_trade["exit_price"]
            open_trade["pnl_rupees"] = open_trade["pnl_points"] * config.LOT_SIZE
            trades.append(open_trade)
            open_trade = None

    TRADE_COLUMNS = [
        "entry_time", "option_type", "expiry", "strike", "symbol",
        "entry_price", "entry_spot", "entry_reason", "entry_pivot", "entry_r1", "entry_s1",
        "exit_time", "exit_price", "exit_spot", "exit_reason", "exit_pivot", "exit_r1", "exit_s1",
        "pnl_points", "pnl_rupees",
    ]
    trade_df = pd.DataFrame(trades, columns=TRADE_COLUMNS)
    trade_df.to_csv(config.TRADE_LOG_CSV, index=False)

    summary = {
        "total_trades": len(trade_df),
        "total_pnl_rupees": float(trade_df["pnl_rupees"].sum()) if not trade_df.empty else 0.0,
        "win_rate_pct": float((trade_df["pnl_rupees"] > 0).mean() * 100) if not trade_df.empty else 0.0,
        "avg_pnl_rupees": float(trade_df["pnl_rupees"].mean()) if not trade_df.empty else 0.0,
        "max_win_rupees": float(trade_df["pnl_rupees"].max()) if not trade_df.empty else 0.0,
        "max_loss_rupees": float(trade_df["pnl_rupees"].min()) if not trade_df.empty else 0.0,
        "open_trade_at_end": open_trade is not None,
    }
    with open(config.SUMMARY_JSON, "w") as f:
        json.dump(summary, f, indent=2, default=str)

    print("=== Backtest complete ===")
    print(json.dumps(summary, indent=2, default=str))
    print(f"Trade log: {config.TRADE_LOG_CSV}")
    print(f"Summary:   {config.SUMMARY_JSON}")

    import generate_dashboard
    generate_dashboard.build()


if __name__ == "__main__":
    run()

"""
Central config for the backtest.
Dates / expiries are HARDCODED here on purpose (per requirement) — edit before each run.
Credentials are pulled from environment variables (set as GitHub Actions secrets, or a local .env).
"""

import os
from datetime import date

# ---------------------------------------------------------------------------
# Fyers credentials (never hardcode these directly — use env vars / GH secrets)
# ---------------------------------------------------------------------------
FYERS_CLIENT_ID = os.environ["FYERS_CLIENT_ID"]      # e.g. "ABC123-100"
FYERS_ACCESS_TOKEN = os.environ["FYERS_ACCESS_TOKEN"]  # generated token (valid ~1 day, refresh before each run)

# ---------------------------------------------------------------------------
# Backtest date range (HARDCODED — edit for each run)
# ---------------------------------------------------------------------------
START_DATE = date(2025, 6, 1)
END_DATE = date(2025, 6, 30)

# ---------------------------------------------------------------------------
# Weekly expiry handling (HARDCODED — edit as needed)
# Nifty weekly expiry weekday has changed historically (was Thursday, moved to
# Tuesday from Jan 2025 onward on NSE). Set the correct weekday for your date
# range below. 0=Mon, 1=Tue, 2=Wed, 3=Thu, 4=Fri
# ---------------------------------------------------------------------------
EXPIRY_WEEKDAY = 1  # Tuesday (change to 3 for Thursday if backtesting pre-2025 dates)

# Manually override/patch specific dates whose expiry was shifted due to
# exchange holidays (NSE moves expiry to the previous trading day on holidays).
# Format: {trading_date: expiry_date}
EXPIRY_OVERRIDES = {
    # date(2025, 8, 15): date(2025, 8, 14),  # example: Independence Day holiday
}

# ---------------------------------------------------------------------------
# Pivot lookback buffer: R1/S1 for a given day are derived from the PREVIOUS
# day's OHLC, so we need at least 1 extra prior trading day of data. We fetch
# extra *calendar* days (not trading days) to safely cover weekends/holidays,
# then trim the output back down to [START_DATE, END_DATE] after computing
# indicators. 7 covers any single-weekend/holiday gap; increase if your
# START_DATE follows a long holiday break.
# ---------------------------------------------------------------------------
PIVOT_LOOKBACK_CALENDAR_DAYS = 7

# ---------------------------------------------------------------------------
# Instrument / strategy params
# ---------------------------------------------------------------------------
INDEX_SYMBOL = "NSE:NIFTY50-INDEX"
UNDERLYING_NAME = "NIFTY"      # used in option symbol construction
STRIKE_STEP = 50               # Nifty strike interval
LOT_SIZE = 75                  # update to current NSE lot size for your backtest period

TIMEFRAME_MINUTES = 5
SUPERTREND_PERIOD = 7
SUPERTREND_MULTIPLIER = 3

# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------
OUTPUT_DIR = "results"
TRADE_LOG_CSV = f"{OUTPUT_DIR}/trade_log.csv"
SUMMARY_JSON = f"{OUTPUT_DIR}/summary.json"

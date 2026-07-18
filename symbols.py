"""
Weekly expiry date resolution + Fyers option symbol construction.

IMPORTANT — VERIFY BEFORE A FULL RUN:
Fyers' weekly-option symbol format (as documented) is:
    NSE:{UNDERLYING}{YY}{MonthCode}{DD}{STRIKE}{CE|PE}
where MonthCode is a single character: 1-9 for Jan-Sep, O for Oct, N for Nov, D for Dec.
Example: NIFTY expiring 2025-07-08, strike 24000, CE -> NSE:NIFTY25708CE... i.e.
    "NIFTY" + "25" + "7" + "08" + "24000" + "CE"  =>  NSE:NIFTY2570824000CE

Since Fyers doesn't publish a *historical* symbol master (expired contracts drop
off the current master file), this constructs the symbol deterministically from
the naming convention rather than looking it up. Before trusting backtest
results, run `python symbols.py --selftest` (see bottom of file) against a
KNOWN recent expiry and confirm the constructed symbol matches what Fyers'
options chain / symbol master shows for that contract.
"""

import argparse
from datetime import date, timedelta

import config

_MONTH_CODES = {1: "1", 2: "2", 3: "3", 4: "4", 5: "5", 6: "6",
                7: "7", 8: "8", 9: "9", 10: "O", 11: "N", 12: "D"}


def get_weekly_expiry(trading_date: date) -> date:
    """Return the weekly expiry date applicable to `trading_date`."""
    if trading_date in config.EXPIRY_OVERRIDES:
        return config.EXPIRY_OVERRIDES[trading_date]

    days_ahead = (config.EXPIRY_WEEKDAY - trading_date.weekday()) % 7
    expiry = trading_date + timedelta(days=days_ahead)
    return expiry


def get_atm_strike(spot: float, step: int = None) -> int:
    step = step or config.STRIKE_STEP
    return int(round(spot / step) * step)


def build_option_symbol(expiry: date, strike: int, option_type: str) -> str:
    """
    option_type: "CE" or "PE"
    """
    assert option_type in ("CE", "PE")
    yy = expiry.strftime("%y")
    month_code = _MONTH_CODES[expiry.month]
    dd = expiry.strftime("%d")
    return f"NSE:{config.UNDERLYING_NAME}{yy}{month_code}{dd}{strike}{option_type}"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Verify option symbol construction against Fyers.")
    parser.add_argument("--expiry", required=True, help="YYYY-MM-DD")
    parser.add_argument("--strike", type=int, required=True)
    parser.add_argument("--type", choices=["CE", "PE"], required=True)
    args = parser.parse_args()

    y, m, d = map(int, args.expiry.split("-"))
    sym = build_option_symbol(date(y, m, d), args.strike, args.type)
    print(f"Constructed symbol: {sym}")
    print("Now check this against the Fyers options chain / symbol master before trusting the backtest.")

"""
Thin wrapper around fyers_apiv3 for historical candle data.
Fyers limits intraday history requests to ~100 days per call, so we chunk.
"""

import time
from datetime import date, timedelta
import pandas as pd
from fyers_apiv3 import fyersModel

import config

MAX_CHUNK_DAYS = 90  # keep comfortably under Fyers' ~100 day intraday limit


def get_fyers_session() -> fyersModel.FyersModel:
    return fyersModel.FyersModel(
        client_id=config.FYERS_CLIENT_ID,
        token=config.FYERS_ACCESS_TOKEN,
        is_async=False,
        log_path="",
    )


def _daterange_chunks(start: date, end: date, chunk_days: int = MAX_CHUNK_DAYS):
    cur = start
    while cur <= end:
        chunk_end = min(cur + timedelta(days=chunk_days - 1), end)
        yield cur, chunk_end
        cur = chunk_end + timedelta(days=1)


def fetch_history(fyers: fyersModel.FyersModel, symbol: str, resolution: str,
                   start: date, end: date, retries: int = 3) -> pd.DataFrame:
    """
    Fetch historical candles for `symbol` between start and end (inclusive).
    resolution: "5" for 5-min, "D" for daily, etc.
    Returns a DataFrame with columns: timestamp, open, high, low, close, volume
    (timestamp is UTC epoch converted to IST-naive datetime).
    """
    frames = []
    for chunk_start, chunk_end in _daterange_chunks(start, end):
        payload = {
            "symbol": symbol,
            "resolution": resolution,
            "date_format": "1",
            "range_from": chunk_start.strftime("%Y-%m-%d"),
            "range_to": chunk_end.strftime("%Y-%m-%d"),
            "cont_flag": "1",
        }

        last_err = None
        for attempt in range(retries):
            try:
                resp = fyers.history(payload)
                if resp.get("s") != "ok":
                    last_err = resp
                    time.sleep(1 + attempt)
                    continue
                candles = resp.get("candles", [])
                if candles:
                    df = pd.DataFrame(candles, columns=["timestamp", "open", "high", "low", "close", "volume"])
                    frames.append(df)
                last_err = None
                break
            except Exception as e:  # noqa: BLE001
                last_err = e
                time.sleep(1 + attempt)

        if last_err is not None:
            print(f"[WARN] failed to fetch {symbol} {chunk_start}..{chunk_end}: {last_err}")

        time.sleep(0.3)  # be polite to the API / avoid rate limits

    if not frames:
        return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])

    out = pd.concat(frames, ignore_index=True)
    out["timestamp"] = pd.to_datetime(out["timestamp"], unit="s", utc=True).dt.tz_convert("Asia/Kolkata").dt.tz_localize(None)
    out = out.drop_duplicates(subset="timestamp").sort_values("timestamp").reset_index(drop=True)
    return out

"""
Indicator calculations: classic daily Pivot (R1/S1) and Supertrend(7,3).
"""

import numpy as np
import pandas as pd


def add_daily_pivots(df_5min: pd.DataFrame) -> pd.DataFrame:
    """
    Given 5-min OHLC data (with a 'timestamp' column, datetime, IST-naive),
    compute the classic pivot, R1, S1 for each trading day using the
    PREVIOUS day's daily OHLC, and broadcast it onto every 5-min candle
    of the current day.
    """
    df = df_5min.copy()
    df["date"] = df["timestamp"].dt.date

    daily = df.groupby("date").agg(
        day_high=("high", "max"),
        day_low=("low", "min"),
        day_close=("close", "last"),
    ).reset_index()

    daily["pivot"] = (daily["day_high"] + daily["day_low"] + daily["day_close"]) / 3
    daily["r1"] = 2 * daily["pivot"] - daily["day_low"]
    daily["s1"] = 2 * daily["pivot"] - daily["day_high"]

    # shift by 1 so today's levels are derived from YESTERDAY's daily OHLC
    daily["pivot"] = daily["pivot"].shift(1)
    daily["r1"] = daily["r1"].shift(1)
    daily["s1"] = daily["s1"].shift(1)

    daily = daily[["date", "pivot", "r1", "s1"]]
    df = df.merge(daily, on="date", how="left")
    df = df.dropna(subset=["r1", "s1"]).reset_index(drop=True)  # drop first day (no prior day)
    return df


def add_supertrend(df: pd.DataFrame, period: int = 7, multiplier: float = 3.0) -> pd.DataFrame:
    """
    Standard Supertrend calculation.
    Adds columns: 'atr', 'supertrend', 'supertrend_dir'
    supertrend_dir: 1 = bullish (green), -1 = bearish (red)
    """
    df = df.copy()
    high, low, close = df["high"], df["low"], df["close"]

    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)

    # Wilder's smoothing for ATR
    atr = tr.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    df["atr"] = atr

    hl2 = (high + low) / 2
    basic_ub = hl2 + multiplier * atr
    basic_lb = hl2 - multiplier * atr

    final_ub = basic_ub.copy()
    final_lb = basic_lb.copy()

    for i in range(1, len(df)):
        if pd.isna(basic_ub.iloc[i - 1]) or close.iloc[i - 1] > final_ub.iloc[i - 1]:
            final_ub.iloc[i] = basic_ub.iloc[i]
        else:
            final_ub.iloc[i] = min(basic_ub.iloc[i], final_ub.iloc[i - 1])

        if pd.isna(basic_lb.iloc[i - 1]) or close.iloc[i - 1] < final_lb.iloc[i - 1]:
            final_lb.iloc[i] = basic_lb.iloc[i]
        else:
            final_lb.iloc[i] = max(basic_lb.iloc[i], final_lb.iloc[i - 1])

    supertrend = pd.Series(index=df.index, dtype=float)
    direction = pd.Series(index=df.index, dtype=int)

    for i in range(len(df)):
        if i == 0 or pd.isna(final_ub.iloc[i - 1]):
            supertrend.iloc[i] = final_ub.iloc[i]
            direction.iloc[i] = -1
            continue

        if supertrend.iloc[i - 1] == final_ub.iloc[i - 1]:
            if close.iloc[i] <= final_ub.iloc[i]:
                supertrend.iloc[i] = final_ub.iloc[i]
                direction.iloc[i] = -1
            else:
                supertrend.iloc[i] = final_lb.iloc[i]
                direction.iloc[i] = 1
        else:
            if close.iloc[i] >= final_lb.iloc[i]:
                supertrend.iloc[i] = final_lb.iloc[i]
                direction.iloc[i] = 1
            else:
                supertrend.iloc[i] = final_ub.iloc[i]
                direction.iloc[i] = -1

    df["supertrend"] = supertrend
    df["supertrend_dir"] = direction  # 1 = bullish/green, -1 = bearish/red
    return df

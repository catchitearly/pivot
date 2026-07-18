"""
Signal generation: given the Nifty 5-min df (with pivot + supertrend columns),
produce a list of entry/exit events.

Rules:
- Bullish: close > R1 AND supertrend_dir == 1 (green)  -> SELL ATM PE
    exit when supertrend_dir flips to -1
- Bearish: close < S1 AND supertrend_dir == -1 (red)    -> SELL ATM CE
    exit when supertrend_dir flips to 1
- Only one position open at a time.
- Entry condition is checked on EVERY qualifying candle while flat
  (not just the first candle of the state change).
"""

from dataclasses import dataclass
from typing import Optional, List
import pandas as pd


@dataclass
class TradeEvent:
    kind: str          # "ENTRY" or "EXIT"
    timestamp: pd.Timestamp
    option_type: str   # "CE" or "PE"
    spot: float
    reason: str
    pivot: float
    r1: float
    s1: float


def generate_events(df: pd.DataFrame) -> List[TradeEvent]:
    events: List[TradeEvent] = []
    position: Optional[str] = None  # None, "PE" (short PE = bullish view), "CE" (short CE = bearish view)

    for _, row in df.iterrows():
        ts = row["timestamp"]
        close = row["close"]
        pivot = row["pivot"]
        r1 = row["r1"]
        s1 = row["s1"]
        st_dir = row["supertrend_dir"]

        # --- check exit first ---
        if position == "PE" and st_dir == -1:
            events.append(TradeEvent("EXIT", ts, "PE", close, "supertrend flipped bearish", pivot, r1, s1))
            position = None

        elif position == "CE" and st_dir == 1:
            events.append(TradeEvent("EXIT", ts, "CE", close, "supertrend flipped bullish", pivot, r1, s1))
            position = None

        # --- check entry (only if flat) ---
        if position is None:
            if close > r1 and st_dir == 1:
                events.append(TradeEvent("ENTRY", ts, "PE", close, "close>R1 & supertrend bullish", pivot, r1, s1))
                position = "PE"
            elif close < s1 and st_dir == -1:
                events.append(TradeEvent("ENTRY", ts, "CE", close, "close<S1 & supertrend bearish", pivot, r1, s1))
                position = "CE"

    return events

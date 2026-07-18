# Nifty Pivot + Supertrend Option-Selling Backtest

Strategy:
- **Bullish**: 5-min close > daily R1 **and** Supertrend(7,3) is green → sell ATM PE, exit on Supertrend flip to red.
- **Bearish**: 5-min close < daily S1 **and** Supertrend(7,3) is red → sell ATM CE, exit on Supertrend flip to green.
- One position at a time. ATM strike = nearest weekly expiry, strike nearest to spot.

## Files
- `config.py` — **hardcoded** backtest date range, expiry weekday, lot size, strike step. Edit before every run.
- `fyers_client.py` — Fyers historical data fetch wrapper (chunked, retried).
- `indicators.py` — Pivot (R1/S1) and Supertrend(7,3) calculations.
- `symbols.py` — Weekly expiry date resolution + Fyers option symbol construction.
- `strategy.py` — Entry/exit signal generation.
- `backtest.py` — Orchestrates the full run, writes `results/trade_log.csv` and `results/summary.json`.

## ⚠️ Before your first real run
Fyers does not publish a historical symbol master (expired option contracts drop
off), so option symbols are **constructed** from Fyers' documented naming
convention rather than looked up. Verify this is correct for your broker/account
before trusting results:

```bash
python symbols.py --expiry 2025-07-08 --strike 24000 --type CE
```

Compare the printed symbol against what Fyers' option chain shows for that
contract. If it doesn't match, fix `build_option_symbol()` in `symbols.py`.

Also double check:
- `EXPIRY_WEEKDAY` in `config.py` (Nifty weekly expiry weekday has changed over time on NSE).
- `LOT_SIZE` in `config.py` for your backtest period (lot size has changed over time).
- `EXPIRY_OVERRIDES` for any holiday-shifted expiries in your date range.

## Local setup

```bash
pip install -r requirements.txt

export FYERS_CLIENT_ID="your-app-id"
export FYERS_ACCESS_TOKEN="your-access-token"

python backtest.py
```

## GitHub Actions setup
1. Push this repo to GitHub.
2. Add repo secrets: `FYERS_CLIENT_ID`, `FYERS_ACCESS_TOKEN` (Settings → Secrets and variables → Actions).
   Note: Fyers access tokens expire daily — you'll need to refresh this secret each day you run the workflow,
   or add a token-refresh step using your Fyers refresh token if your app supports it.
3. Run manually from the Actions tab (`workflow_dispatch`), or uncomment the `schedule` cron in
   `.github/workflows/backtest.yml`.
4. Results are uploaded as a workflow artifact (`results/trade_log.csv`, `results/summary.json`).

## Known limitations
- Fyers historical intraday data retention for options is limited (not multi-year) — your `START_DATE` /
  `END_DATE` range must fall within what Fyers actually retains for the constructed option symbols.
- Entry/exit option price is taken from that option's candle at/after the signal timestamp — no slippage,
  spread, or brokerage modeled. Add this in `backtest.py` if you want a more realistic P&L.
- No stop-loss/target — exits are pure Supertrend-flip as specified.

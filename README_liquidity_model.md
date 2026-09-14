# Liquidity + AI Risk Model — Chat-Style Codex / Streamlit Pack

This version is designed to reproduce the market-model layout from ChatGPT in Codex and Streamlit: **actual numbers + stoplights + commentary + sources/timestamps**.

## What now appears near the top
1. AI Credit Risk
2. Precious Metals / Fiscal Credibility
3. Earnings Durability / Expectation Gap
4. 10Y/30Y/real yields
5. Yen/Japan carry risk
6. Volatility compression/breakout
7. Short-term drawdown score
8. 2–8 week rally sustainability
9. Trade stance

## Run
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export FRED_API_KEY="YOUR_KEY"
python liquidity_model.py --fast --json-out latest_model_run.json
streamlit run streamlit_app.py
```

## Critical workflow
The Python app pulls FRED/Yahoo automatically, but **news-derived data cannot be trusted to remain current without a refresh**. Before each serious run, have Codex follow `CODEX_PROMPT.md` and refresh:
- `market_context.json` — AI credit, Fed probabilities/comments, yen/Japan, oil and current headlines.
- `earnings_watchlist.json` — latest-quarter earnings durability and expectation/valuation data.

The Streamlit app then displays those current figures alongside FRED/Yahoo data.

## Manual overrides
For a more current verified quote, environment variables override free feeds:
`DGS10`, `DGS30`, `DFII10`, `USDJPY`, `JGB10Y`, `JGB30Y`, `OIL_BRENT`, `OIL_WTI`, `VIX`, `VVIX`.

Example:
```bash
export DGS10=4.80
export USDJPY=155.32
streamlit run streamlit_app.py
```

## Data-integrity behavior
- Every key row displays source/as-of.
- Missing/stale tiles remain visible and become neutral/unscored.
- FRED is authoritative but often daily/weekly.
- Yahoo/yfinance may be delayed or fail.
- Current news-derived metrics should be refreshed by Codex and written into the JSON context files.
- No index futures are scored.

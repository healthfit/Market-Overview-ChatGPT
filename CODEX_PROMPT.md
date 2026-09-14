# Codex task — refresh and run the Liquidity + AI Risk dashboard

The user wants the Codex / Streamlit output to look like the ChatGPT market-model runs: **actual numbers + stoplights + commentary + source/as-of timestamps**, not just scores.

## Non-negotiable layout
At the top show, in this order:
1. **AI CREDIT RISK** — dot + actual spread / issuance / order-book / concession numbers + one-line commentary.
2. **PRECIOUS METALS / FISCAL CREDIBILITY** — GLD/GDX/SLV/SIL actual prices/returns + commentary.
3. **EARNINGS DURABILITY / EXPECTATION GAP** — ranked stock table with actual earnings and valuation numbers.
4. **10Y / 30Y / real yields**.
5. **USD/JPY / JGB carry risk**.
6. **VOL COMPRESSION / BREAKOUT** — VIX, VIX9D, VIX3M, VVIX.
7. **Short-term drawdown score** and **2–8 week rally score**.
8. **Trade stance + tripwires**.

No index futures in the scored model.

## Every run: refresh current data before rendering

### 1. Run free data ingestion
Install requirements and set the FRED key if available:
```bash
pip install -r requirements.txt
export FRED_API_KEY="..."
```
The Python model pulls FRED + Yahoo/yfinance automatically. FRED is official but may be daily/weekly; Yahoo is used for approximate live tape/rates where available.

### 2. Refresh `market_context.json` from current web/news sources
Do not leave this as generic prose. Populate the exact current numbers and timestamps:
- `ai_credit_spread_bps`
- `broad_ig_spread_bps`
- `ai_issuance_ytd_bn`
- `ai_book_coverage_x`
- `ai_new_issue_concession_bps`
- `ai_lower_quality_score` (-1/0/+1)
- `ai_credit_commentary`
- September Fed probabilities: `sept_hold_odds_pct`, `sept_hike_odds_pct`, `sept_cut_odds_pct`
- `fed_commentary` — summarize the **latest Fed speaker comments today** (e.g. Waller/Warsh) and what the market did afterward
- Japan/yen context and source/as-of
- Brent/WTI context and source/as-of
- `market_commentary`: 2–5 sentences explaining today’s cross-asset setup
- `headlines`: only materially relevant current headlines, each with impact + source
- `sources`: source list / timestamps

If a current figure cannot be verified, set it `null` and say it is unavailable. Never invent or average conflicting quotes silently.

### 3. Refresh `earnings_watchlist.json`
For the tracked AI / high-growth book and the best new candidates, update the latest quarter and actual market price/valuation where possible.

Always include at least:
- NVDA, MU, SNDK, LITE, AAOI, MRVL
- GEV, DELL, VRT, ANET, CEG, APP when data are available

Populate raw fields:
- `revenue_growth_yoy_pct`
- `eps_or_opinc_growth_yoy_pct`
- `fcf_growth_yoy_pct`
- `backlog_growth_yoy_pct` (or ARR/RPO/orders where applicable)
- `pe`
- `daily_return_pct`
- `status`, `commentary`, `as_of`, `source`

Populate the 0–100 component scores using evidence from the quarter:
- `organic_revenue_score` 25%
- `earnings_quality_score` 20%
- `guidance_revision_score` 20%
- `fcf_score` 15%
- `backlog_score` 10%
- `balance_sheet_score` 10%
- `expectation_gate_score` separately (valuation, rate sensitivity, post-earnings reaction, beat magnitude, financing/customer quality)

Do not rank a stock highly merely because backward-looking EPS growth is large. Prefer **durable forward revisions minus valuation, financing and expectation risk**.

### 4. Run and render
CLI:
```bash
python liquidity_model.py --fast --json-out latest_model_run.json
```
Dashboard:
```bash
streamlit run streamlit_app.py
```

Use demo mode only for validation:
```bash
python liquidity_model.py --fast --mock
```

## Integrity rule
Every important row must show:
- actual number(s)
- dot
- commentary
- source / as-of

Stale/missing data stay visible and become neutral/unscored. Never silently delete a tile or make up a current number.

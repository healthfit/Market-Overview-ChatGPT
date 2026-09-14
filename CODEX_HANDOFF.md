# Codex Handoff

You are maintaining a two-horizon market risk model for an AI-heavy portfolio.

## Non-negotiable rules
- No index futures in the score.
- Keep pinned tiles visible even when data is unavailable.
- Missing/stale data becomes neutral/unscored.
- Do not remove model rows or change weights without first proposing the change and why.
- Use real pricing whenever possible.
- AI Credit Risk must appear at the top of the dashboard.
- Precious Metals must appear immediately after AI Credit.
- Earnings Durability + Expectation Gap must be included in every run.

## Run locally
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# add FRED_API_KEY to .env
python run_model.py
streamlit run app.py
```

## Priority improvements
1. Add a reliable professional Treasury intraday source or cross-check.
2. Add direct CME/market-implied Fed-probability ingestion.
3. Automate hyperscaler bond-spread and new-issue/order-book ingestion.
4. Add analyst revision data if a licensed source is available.
5. Improve NYSE advance/decline breadth sourcing.
6. Log every run to a snapshot database and create a flip history.
7. Backtest model-state transitions against forward 1d/5d/20d QQQ and SOX returns.

Do not optimize for explaining the present. Optimize for better forward decisions.

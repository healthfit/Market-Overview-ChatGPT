# Review: What is still missing?

The v2 package now contains all model layers used in the chat, but these items remain the biggest opportunities to improve reliability and predictive power.

## 1. Professional intraday rates
FRED is authoritative but daily. For intraday decision-making, connect a licensed or institutional source for:
- UST 2Y / 5Y / 10Y / 30Y
- real yields
- JGB 10Y / 30Y

Until then, use dashboard overrides.

## 2. Automated AI-credit feed
The model has the scoring framework, but free sources do not reliably expose:
- hyperscaler option-adjusted spreads
- CDS
- new-issue concessions
- order-book coverage
- AI project-finance/private-credit terms

A Bloomberg/ICE/TRACE/FactSet/Capital IQ-style feed would materially improve this layer.

## 3. Fed probability / commentary parser
The package accepts a `FED_REPRICING_SCORE`, but it does not scrape CME FedWatch or parse Waller/Warsh/FOMC comments automatically.
Best upgrade: ingest probabilities plus NLP-classified policy commentary.

## 4. Analyst revisions
The earnings layer ships with editable seed grades. A licensed consensus source should automate:
- next-quarter EPS revisions
- FY1/FY2 revenue and EPS revisions
- target changes
- estimate dispersion

## 5. Breadth / ZBT
The model supports breadth inputs, but a robust NYSE advances/declines feed should replace fragile free scraping.

## 6. Snapshot history and backtesting
Next major engineering improvement:
- save every run to SQLite/Postgres
- calculate 1d / 5d / 20d forward QQQ, SOX and SPY returns
- evaluate false positives and false negatives
- tune thresholds only after out-of-sample validation

## 7. Portfolio-aware risk
The next version should ingest actual portfolio weights and calculate:
- AI-factor concentration
- rates duration
- beta to QQQ/SOX
- yen/carry sensitivity
- hedge sizing for PSQ/QID/SOXS/TBT/TMV
- precious-metals hedge contribution

This is probably the single most useful next step for turning the dashboard into a portfolio decision engine.

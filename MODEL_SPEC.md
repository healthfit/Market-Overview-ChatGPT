# Market Risk Model v2 — Model Specification

## Top-line layout
Every requested run should show, in this order:

1. **AI CREDIT RISK**
2. **PRECIOUS METALS / FISCAL CREDIBILITY**
3. **EARNINGS DURABILITY + EXPECTATION GAP**
4. **VOL COMPRESSION / BREAKOUT STATUS**
5. **10Y / REAL-YIELD REGIME**
6. **JAPAN / YEN CARRY RISK**
7. **SHORT-TERM DRAWDOWN RISK (1–10 trading days)**
8. **2–8 WEEK RALLY SUSTAINABILITY**
9. **TRADE STANCE**

Index futures are context only and are not scored.

---

## Short-term model
Designed to answer: **Should we press risk now?**

Core components:
- Vol regime
- Rates / real yields / curve
- Funding
- Broad HY/IG credit
- AI-specific credit
- Breadth / ZBT
- Japan / yen carry
- Precious-metals cross-asset warning
- Stock-level earnings durability

## Medium-term model
Designed to answer: **Can the rally survive for 2–8 weeks?**

Core components:
- Net liquidity
- Fed balance-sheet regime
- Broad credit
- AI credit
- Inflation expectations and real yields
- Earnings durability/revision momentum
- Breadth
- Fed repricing
- Japan carry
- Precious-metals fiscal-credibility signal

---

# AI Credit Risk
This is deliberately separate from broad IG/HY spreads.

Track:
- Hyperscaler spread level and 5-day spread momentum
- New-issue concessions
- Order-book coverage
- YTD AI/hyperscaler issuance
- Lower-quality AI infrastructure borrowers
- Rating/outlook changes
- Lease-adjusted leverage / project finance dependence

Interpretation:
- Strong ratings + strong order books + wider spreads = supply pressure, not solvency stress.
- Wider spreads + weak books + larger concessions + rating deterioration = genuine AI-credit warning.
- Sector-specific red override: hyperscaler spreads widen another ~20–25 bp while broad HY remains <3.5%.

---

# Precious Metals / Fiscal Credibility
Track:
- Gold vs 10Y real yields and USD
- GDX vs GLD
- Silver vs gold
- SIL/SILJ confirmation
- Miner margins / AISC / FCF
- Oil-driven miner cost pressure

Interpret two ways:
1. Investment signal for metals/miners
2. Broader-market fiscal/credibility warning

Gold rising while policymakers attempt to suppress long yields can be bullish for gold and simultaneously bearish for long-duration equities.

---

# Earnings Durability + Expectation Gap
Do not rank stocks by backward-looking EPS growth alone.

Base score:
- Organic revenue growth — 25%
- Operating income/EPS growth excluding one-offs — 20%
- Guidance / analyst revision momentum — 20%
- FCF growth and conversion — 15%
- Backlog / RPO / ARR / order growth — 10%
- Balance-sheet + customer-credit durability — 10%

Expectation/Valuation gate:
- Valuation relative to forward growth
- Sensitivity to 10Y and real yields
- Post-earnings price reaction
- Beat size vs prior quarters
- Margin/guidance acceleration
- Dependence on debt, leases or weaker counterparties
- One-off accounting or commodity-price distortions

Preferred names are those where **durable forward revisions outrun multiple compression**.

Tracked AI exposure:
- Memory/storage: SNDK, MU
- Optics/interconnect: LITE, AAOI
- Custom silicon/networking: MRVL
- Core AI / infrastructure: NVDA, GEV, VRT, ANET, DELL
- Power: CEG, VST
- Additional quality/earnings names: MSFT, APP, CRWD, CAT

---

# Vol Compression / Breakout
Compression warning:
- VIX <15 with macro risk elevated = yellow, not green.
- First release: VIX >16.5–17 after sub-15 compression.
- Confirmation: VIX >18.
- Strong red: VIX >20 + VVIX >100.
- Hard red: VIX >22 + backwardation.
- Dangerous combo: 10Y >4.75%, USDJPY rapidly toward/below 157, VVIX >100, VIX >17.

Healthy term structure:
VIX9D < VIX < VIX3M.

---

# Japan / Yen Carry
Focus on both level and speed.
- Weak yen can support carry trades, but intervention risk grows near 160–162.
- Rapid move 160 -> 157 -> 155 is a carry-unwind warning.
- Japan 10Y/30Y stress can reduce Japan's role as a marginal buyer of foreign bonds.
- JGB 30Y >3.7% = red; >4.0% = hard red.

---

# Historical-regime lens
Use analogs as probabilistic templates, not forecasts:
- 1994: bond massacre / equity chop
- 2013: rising yields / equities kept climbing
- 2021: yields up / rotation away from long-duration growth
- Aug–Oct 2023: 10Y near 5%, tech correction, then violent rebound when yields rolled over
- Aug 2024: yen carry unwind / fast vol shock

Inflation composition matters:
- Good yield rise: growth + earnings + tight credit
- Bad yield rise: oil + sticky core inflation + real yields + Treasury/AI supply

---

# Data-integrity rule
If a data feed is missing, stale or inconsistent:
- Keep the tile visible
- Mark it ⚪ / unavailable
- Do not silently average conflicting feeds
- Do not fabricate

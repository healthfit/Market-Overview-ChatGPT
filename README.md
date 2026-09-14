# Market Risk Model v2

A two-horizon market-risk dashboard designed for an AI-heavy portfolio.

It combines:
- Treasury rates / real yields / curve
- Fed liquidity and funding
- Broad credit
- **AI-specific credit**
- **Precious metals / fiscal credibility**
- **Earnings durability + expectation gap**
- Volatility compression and breakout risk
- Japan / yen carry risk
- Breadth / ZBT
- AI sub-buckets: memory, optics, custom silicon/networking, power and infrastructure

## 1) Local installation

### macOS / Linux
```bash
git clone <YOUR_REPO_URL>
cd market_risk_model_v2

python3 -m venv .venv
source .venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt

cp .env.example .env
```

Edit `.env` and add:
```text
FRED_API_KEY=YOUR_KEY
```

Get a free FRED API key:
https://fred.stlouisfed.org/docs/api/api_key.html

Run the CLI:
```bash
python run_model.py
```

Run the dashboard:
```bash
streamlit run app.py
```

Open:
```text
http://localhost:8501
```

### Windows PowerShell
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
streamlit run app.py
```

---

## 2) Mock/demo mode
No API keys needed:
```bash
python run_model.py --mock
streamlit run app.py
```
Then enable **Mock mode** in the sidebar.

---

## 3) Manual overrides
Free feeds can be delayed. Use `.env` or the dashboard sidebar for overrides:
- JGB10Y
- JGB30Y
- BRENT
- WTI
- USDJPY
- AI credit inputs

Manual overrides are displayed as overrides; they are not silently mixed.

---

## 4) Create a cloud version — easiest: Streamlit Community Cloud

1. Create a GitHub repository.
2. Upload this project.
3. Commit and push.
4. Go to Streamlit Community Cloud.
5. Create app from your GitHub repository.
6. Set main file to:
   `app.py`
7. In app settings -> Secrets, paste:
```toml
FRED_API_KEY = "YOUR_FRED_KEY"
```
8. Deploy.

For optional overrides:
```toml
JGB10Y = "3.00"
JGB30Y = "4.10"
```

Never commit `.env` or `secrets.toml`.

See `DEPLOY_CLOUD.md` for Render/Docker instructions.

---

## 5) Recommended workflow
Morning / intraday:
```bash
python run_model.py
```

Use the dashboard to review:
1. AI Credit Risk
2. Precious Metals
3. Earnings Durability
4. Vol compression
5. 10Y/30Y + real yields
6. Yen/Japan
7. Short-term score
8. 2–8 week score

---

## 6) Data limitations
This project intentionally uses free/public sources where possible.

Reliable automated:
- FRED: liquidity, Treasury daily closes, real yields, breakevens, SOFR/EFFR, HY/IG OAS
- yfinance: market prices and volatility proxies

More fragile / best as manual or licensed feeds:
- Live Treasury intraday yields
- JGB 30Y
- CME FedWatch probabilities
- Hyperscaler single-name bond spreads
- New-issue concessions/order books
- Analyst earnings revisions
- Breadth/ZBT source

If a feed is missing, the model leaves the tile visible and unscored rather than guessing.

---

## 7) Social sentiment
The included Reddit/X report is reference context only. It is not a scored timing input.

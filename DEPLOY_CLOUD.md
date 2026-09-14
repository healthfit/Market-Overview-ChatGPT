# Cloud Deployment

## Option A — Streamlit Community Cloud (easiest)
Best for a personal dashboard.

1. Push this folder to GitHub.
2. Sign in to Streamlit Community Cloud with GitHub.
3. Choose **New app**.
4. Select repo / branch.
5. Main file path: `app.py`
6. Add secrets:
```toml
FRED_API_KEY = "YOUR_FRED_API_KEY"
```
7. Deploy.

The app will receive a hosted URL.

### Updating
Push commits to GitHub. Streamlit redeploys automatically.

---

## Option B — Render
Included: `render.yaml`.

1. Push the repo to GitHub.
2. In Render choose **New -> Blueprint**.
3. Connect the repository.
4. Render reads `render.yaml`.
5. Set secret environment variable:
   - `FRED_API_KEY`
6. Deploy.

Start command:
```bash
streamlit run app.py --server.address 0.0.0.0 --server.port $PORT
```

---

## Option C — Docker
Build:
```bash
docker build -t market-risk-v2 .
```

Run:
```bash
docker run --rm -p 8501:8501 --env-file .env market-risk-v2
```

Open:
```text
http://localhost:8501
```

Deploy the same image to:
- AWS ECS / App Runner
- Google Cloud Run
- Azure Container Apps
- Fly.io
- Railway

---

## Option D — Google Cloud Run
After installing the gcloud CLI:

```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID

gcloud run deploy market-risk-v2 \
  --source . \
  --region us-west1 \
  --allow-unauthenticated \
  --set-env-vars FRED_API_KEY=YOUR_FRED_KEY
```

For a private app, omit `--allow-unauthenticated`.

---

## Production hardening
For anything beyond personal use:
- Put secrets in the hosting platform's secret manager.
- Add authentication in front of the app.
- Pin dependency versions.
- Add error monitoring.
- Persist snapshots to SQLite/Postgres.
- Cache public data pulls for 1–5 minutes.
- Add a paid/authoritative live rates feed if decisions depend on intraday Treasury levels.

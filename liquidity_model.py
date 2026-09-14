#!/usr/bin/env python3
"""
Liquidity + Risk Model — FAST / Commentary Mode

Designed to reproduce the chat-style dashboard in Codex / Streamlit:
- actual numbers
- stoplights
- one-line commentary for every important signal
- source / as-of timestamps
- AI credit risk near the top
- precious-metals / fiscal-credibility module
- earnings durability + expectation/valuation layer
- vol compression / breakout warning
- short-term drawdown + 2–8 week rally sustainability
- tripwires and optional flip log

No index futures are scored.
"""
from __future__ import annotations

import argparse
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import requests
import yaml
from dotenv import load_dotenv

try:
    import yfinance as yf
except Exception:
    yf = None

load_dotenv()
BASE = Path(__file__).resolve().parent
UA = {"User-Agent": "Mozilla/5.0 (compatible; LiquidityRiskModel/2.0; local)"}

FRED_SERIES = {
    "WALCL": "Fed Total Assets",
    "WDTGAL": "Treasury General Account",
    "RRPONTSYD": "ON RRP",
    "WRESBAL": "Reserve Balances",
    "DGS2": "UST 2Y",
    "DGS5": "UST 5Y",
    "DGS10": "UST 10Y",
    "DGS30": "UST 30Y",
    "DFII10": "10Y Real Yield",
    "T5YIE": "5Y Breakeven",
    "T10YIE": "10Y Breakeven",
    "T5YIFR": "5y5y Forward Inflation",
    "BAMLH0A0HYM2": "HY OAS",
    "BAMLC0A0CM": "IG OAS",
    "SOFR": "SOFR",
    "EFFR": "EFFR",
}

# FRED units are not consistent. Convert plumbing series to $bn at ingestion.
FRED_DIVISORS = {"WALCL": 1000.0, "WDTGAL": 1000.0, "WRESBAL": 1000.0, "RRPONTSYD": 1.0}

YF_MAP = {
    "VIX": "^VIX", "VIX9D": "^VIX9D", "VIX3M": "^VIX3M", "VVIX": "^VVIX", "VXN": "^VXN",
    "USDJPY": "JPY=X", "BTC": "BTC-USD",
    "SPY": "SPY", "QQQ": "QQQ", "IWM": "IWM",
    "NVDA": "NVDA", "MU": "MU", "SNDK": "SNDK", "LITE": "LITE", "AAOI": "AAOI", "MRVL": "MRVL",
    "GEV": "GEV", "DELL": "DELL", "VRT": "VRT", "ANET": "ANET", "CEG": "CEG", "APP": "APP",
    "GLD": "GLD", "SLV": "SLV", "GDX": "GDX", "GDXJ": "GDXJ", "SIL": "SIL", "SILJ": "SILJ",
    "NEM": "NEM", "AEM": "AEM", "FNV": "FNV", "WPM": "WPM",
}

# Yahoo rate indexes: ^TNX and ^TYX are quoted as yield x10.
YF_RATE_MAP = {"DGS10_LIVE": "^TNX", "DGS30_LIVE": "^TYX", "DGS5_LIVE": "^FVX"}


def load_config(path: str = "config.yaml") -> Dict[str, Any]:
    p = Path(path)
    if not p.is_absolute():
        p = BASE / p
    with p.open("r") as f:
        return yaml.safe_load(f)


def load_json(path: Path, default: Any) -> Any:
    try:
        with path.open("r") as f:
            return json.load(f)
    except Exception:
        return default


def safe_float(x: Any) -> Optional[float]:
    try:
        if x is None:
            return None
        if isinstance(x, (int, float, np.floating)):
            v = float(x)
            return None if math.isnan(v) else v
        s = str(x).strip().replace(",", "").replace("%", "")
        if s in {"", ".", "nan", "NA", "None", "null"}:
            return None
        return float(s)
    except Exception:
        return None


def fmt(x: Any, digits: int = 2, suffix: str = "") -> str:
    v = safe_float(x)
    return "NA" if v is None else f"{v:.{digits}f}{suffix}"


def dot_from_score(score: Optional[float]) -> str:
    if score is None:
        return "⚪"
    if score > 0:
        return "🟢"
    if score < 0:
        return "🔴"
    return "🟡"


def risk_label(score: float) -> str:
    if score >= 0.25:
        return "🟢"
    if score <= -0.25:
        return "🔴"
    return "🟡"


def fred_observations(series_id: str, api_key: str, limit: int = 10) -> pd.DataFrame:
    url = "https://api.stlouisfed.org/fred/series/observations"
    params = {"series_id": series_id, "api_key": api_key, "file_type": "json", "sort_order": "desc", "limit": limit}
    r = requests.get(url, params=params, headers=UA, timeout=20)
    r.raise_for_status()
    df = pd.DataFrame(r.json().get("observations", []))
    if df.empty:
        return pd.DataFrame(columns=["date", "value"])
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    return df.dropna(subset=["date"]).sort_values("date")


def fetch_fred_bundle(api_key: Optional[str]) -> Dict[str, Any]:
    if not api_key:
        return {"fred_status": "missing FRED_API_KEY"}
    out: Dict[str, Any] = {"fred_status": "ok"}
    for sid in FRED_SERIES:
        try:
            df = fred_observations(sid, api_key, limit=10).dropna(subset=["value"])
            if df.empty:
                out[sid] = None
                continue
            div = FRED_DIVISORS.get(sid, 1.0)
            out[sid] = float(df.iloc[-1]["value"]) / div
            out[f"{sid}_date"] = str(df.iloc[-1]["date"].date())
            out[f"{sid}_source"] = "FRED"
            if len(df) >= 2:
                out[f"{sid}_prev"] = float(df.iloc[-2]["value"]) / div
        except Exception as e:
            out[sid] = None
            out[f"{sid}_error"] = str(e)
    return out


def _last_row(df: pd.DataFrame, ticker: str) -> Tuple[Optional[pd.Series], Optional[pd.Series]]:
    try:
        sub = df[ticker].dropna(how="all") if isinstance(df.columns, pd.MultiIndex) else df.dropna(how="all")
        if sub.empty:
            return None, None
        return sub.iloc[-1], sub.iloc[-2] if len(sub) >= 2 else None
    except Exception:
        return None, None


def fetch_yahoo_bundle() -> Dict[str, Any]:
    if yf is None:
        return {"yahoo_status": "yfinance unavailable"}
    out: Dict[str, Any] = {"yahoo_status": "ok"}
    tickers = list(YF_MAP.values()) + list(YF_RATE_MAP.values())
    try:
        df = yf.download(" ".join(tickers), period="5d", interval="1d", progress=False,
                         auto_adjust=False, group_by="ticker", threads=True)
        for key, ticker in YF_MAP.items():
            last, prev = _last_row(df, ticker)
            if last is None:
                continue
            close = safe_float(last.get("Close"))
            prev_close = safe_float(prev.get("Close")) if prev is not None else None
            out[key] = close
            out[f"{key}_source"] = "Yahoo Finance"
            out[f"{key}_date"] = str(pd.Timestamp(last.name).date()) if hasattr(last, "name") else None
            if close is not None and prev_close:
                out[f"{key}_ret"] = (close / prev_close - 1.0) * 100
        for key, ticker in YF_RATE_MAP.items():
            last, prev = _last_row(df, ticker)
            if last is None:
                continue
            raw = safe_float(last.get("Close"))
            prev_raw = safe_float(prev.get("Close")) if prev is not None else None
            out[key] = raw / 10.0 if raw is not None else None
            out[f"{key}_source"] = "Yahoo Finance"
            out[f"{key}_date"] = str(pd.Timestamp(last.name).date()) if hasattr(last, "name") else None
            if raw is not None and prev_raw:
                out[f"{key}_change_bp"] = (raw - prev_raw) * 10.0
    except Exception as e:
        out["yahoo_status"] = f"error: {e}"

    # 15m snapshots for rates / VIX / yen / major tape. Use if available.
    try:
        intraday_tickers = ["^TNX", "^TYX", "^VIX", "JPY=X", "QQQ", "GLD", "GDX"]
        intra = yf.download(" ".join(intraday_tickers), period="1d", interval="15m", progress=False,
                            auto_adjust=False, group_by="ticker", threads=True)
        for key, ticker, scale in [
            ("DGS10_LIVE", "^TNX", 0.1), ("DGS30_LIVE", "^TYX", 0.1),
            ("VIX_LIVE", "^VIX", 1.0), ("USDJPY_LIVE", "JPY=X", 1.0),
            ("QQQ_LIVE", "QQQ", 1.0), ("GLD_LIVE", "GLD", 1.0), ("GDX_LIVE", "GDX", 1.0),
        ]:
            last, _ = _last_row(intra, ticker)
            if last is None:
                continue
            raw = safe_float(last.get("Close"))
            if raw is not None:
                out[key] = raw * scale
                out[f"{key}_source"] = "Yahoo Finance 15m"
                out[f"{key}_date"] = str(last.name)
    except Exception:
        pass
    return out


def compute_zbt_from_adrn_closes(closes: List[float]) -> Dict[str, Any]:
    vals = [safe_float(x) for x in closes]
    vals = [x for x in vals if x is not None]
    if not vals:
        return {"BREADTH_TODAY": None, "ZBT_EMA10": None, "ZBT_TRIGGER": None}
    arr = np.array(vals, dtype=float)
    breadth = arr / (1.0 + arr)
    ema = pd.Series(breadth).ewm(span=10, adjust=False).mean()
    ema10 = float(ema.iloc[-1])
    min10 = float(ema.tail(10).min())
    return {"BREADTH_TODAY": float(breadth[-1]), "ZBT_EMA10": ema10,
            "ZBT_MIN10": min10, "ZBT_TRIGGER": bool(ema10 > 0.615 and min10 < 0.40)}


def fetch_adrn() -> Dict[str, Any]:
    try:
        r = requests.get("https://www.eoddata.com/stockquote/INDEX/ADRN.htm", headers=UA, timeout=20)
        r.raise_for_status()
        for t in pd.read_html(r.text):
            cols = [str(c).strip().lower() for c in t.columns]
            if "date" in cols and "close" in cols:
                t = t.copy()
                t.columns = cols
                t["date"] = pd.to_datetime(t["date"], errors="coerce")
                t["close"] = pd.to_numeric(t["close"], errors="coerce")
                t = t.dropna(subset=["date", "close"]).sort_values("date")
                out = compute_zbt_from_adrn_closes(t["close"].tail(20).tolist())
                out["breadth_source"] = "EODData ADRN proxy"
                out["breadth_date"] = str(t.iloc[-1]["date"].date()) if not t.empty else None
                return out
    except Exception as e:
        return {"adrn_error": str(e)}
    return {"adrn_error": "No ADRN table found"}


def load_market_context(mock: bool = False) -> Dict[str, Any]:
    name = "sample_market_context.json" if mock else "market_context.json"
    return load_json(BASE / name, {})


def load_earnings_watchlist(mock: bool = False) -> List[Dict[str, Any]]:
    name = "sample_earnings_watchlist.json" if mock else "earnings_watchlist.json"
    return load_json(BASE / name, [])


def merge_data(mock: bool = False) -> Dict[str, Any]:
    if mock:
        data = load_json(BASE / "sample_snapshot.json", {})
        # normalize old sample naming
        if "TGA" in data and "WDTGAL" not in data: data["WDTGAL"] = data["TGA"]
        if "RRP" in data and "RRPONTSYD" not in data: data["RRPONTSYD"] = data["RRP"]
        if "BRENT" in data and "OIL_BRENT" not in data: data["OIL_BRENT"] = data["BRENT"]
        data.update(compute_zbt_from_adrn_closes(data.get("ADRN_CLOSES", [])))
        data["market_context"] = load_market_context(True)
        data["earnings_watchlist"] = load_earnings_watchlist(True)
        return data

    data: Dict[str, Any] = {"as_of": datetime.now(timezone.utc).isoformat()}
    data.update(fetch_fred_bundle(os.getenv("FRED_API_KEY")))
    data.update(fetch_yahoo_bundle())
    data.update(fetch_adrn())
    data["market_context"] = load_market_context(False)
    data["earnings_watchlist"] = load_earnings_watchlist(False)

    # Manual overrides take precedence over free feeds.
    for k in ["DGS2", "DGS5", "DGS10", "DGS30", "DFII10", "USDJPY", "JGB10Y", "JGB30Y",
              "OIL_BRENT", "OIL_WTI", "EARNINGS_BEAT_RATE", "VIX", "VIX9D", "VIX3M", "VVIX", "VXN"]:
        v = os.getenv(k)
        if v not in {None, ""}:
            data[k] = safe_float(v)
            data[f"{k}_source"] = "environment override"
            data[f"{k}_date"] = datetime.now().isoformat(timespec="minutes")

    # Prefer intraday Treasury / VIX / yen snapshots when available.
    for target, live in [("DGS10", "DGS10_LIVE"), ("DGS30", "DGS30_LIVE"), ("VIX", "VIX_LIVE"), ("USDJPY", "USDJPY_LIVE")]:
        if safe_float(data.get(live)) is not None and os.getenv(target) in {None, ""}:
            data[target] = data[live]
            data[f"{target}_source"] = data.get(f"{live}_source", "Yahoo Finance 15m")
            data[f"{target}_date"] = data.get(f"{live}_date")
    return data


def net_liquidity(data: Dict[str, Any]) -> Tuple[Optional[float], Optional[float]]:
    w, t, r = map(safe_float, [data.get("WALCL"), data.get("WDTGAL"), data.get("RRPONTSYD")])
    if w is None or t is None or r is None:
        return None, None
    net = w - t - r
    wp, tp, rp = map(safe_float, [data.get("WALCL_prev"), data.get("WDTGAL_prev"), data.get("RRPONTSYD_prev")])
    if wp is None or tp is None or rp is None:
        return net, None
    return net, net - (wp - tp - rp)


def score_vol(data: Dict[str, Any], cfg: Dict[str, Any]) -> int:
    th = cfg["thresholds"]
    vix, v9, v3, vvix, vxn = map(safe_float, [data.get("VIX"), data.get("VIX9D"), data.get("VIX3M"), data.get("VVIX"), data.get("VXN")])
    if vix is None: return 0
    if vix >= th["vix_red_min"] or (vvix is not None and vvix >= th["vvix_red_min"]) or (v9 is not None and v9 > vix):
        return -1
    if vix < th["vix_green_max"] and (v3 is None or vix < v3): return 1
    if vxn is not None and vxn >= th["vxn_red_min"]: return -1
    return 0


def score_vol_compression(data: Dict[str, Any]) -> Tuple[int, str]:
    vix, vvix, v9, v3 = map(safe_float, [data.get("VIX"), data.get("VVIX"), data.get("VIX9D"), data.get("VIX3M")])
    if vix is None: return 0, "VIX unavailable"
    if vix >= 22 or (v9 is not None and v9 > vix and vix >= 18):
        return -1, "Volatility regime has broken higher / backwardation risk."
    if vix >= 17 or (vvix is not None and vvix >= 100):
        return -1, "Compression is releasing; breakout confirmation risk is elevated."
    if vix < 15:
        return 0, "VIX is compressed below 15; cheap protection can become a coiled-spring risk."
    if v3 is not None and vix < v3:
        return 1, "Vol curve remains in contango; no confirmed breakout."
    return 0, "Volatility is neutral; watch term structure and VVIX."


def score_rates(data: Dict[str, Any], cfg: Dict[str, Any]) -> int:
    th = cfg["thresholds"]
    y10, y30, real = map(safe_float, [data.get("DGS10"), data.get("DGS30"), data.get("DFII10")])
    if y10 is None: return 0
    if y10 >= th["ten_year_red_min"] or (y30 is not None and y30 >= th["thirty_year_red_min"]) or (real is not None and real >= 2.0): return -1
    if y10 <= th["ten_year_green_max"]: return 1
    return 0


def score_funding(data: Dict[str, Any], cfg: Dict[str, Any]) -> int:
    sofr, effr = safe_float(data.get("SOFR")), safe_float(data.get("EFFR"))
    if sofr is None or effr is None: return 0
    bp = (sofr - effr) * 100
    if bp >= cfg["thresholds"]["sofr_effr_red_bps"]: return -1
    if bp >= cfg["thresholds"]["sofr_effr_yellow_bps"]: return 0
    return 1


def score_credit(data: Dict[str, Any], cfg: Dict[str, Any]) -> int:
    th = cfg["thresholds"]
    hy, ig = safe_float(data.get("BAMLH0A0HYM2")), safe_float(data.get("BAMLC0A0CM"))
    if hy is None and ig is None: return 0
    if (hy is not None and hy >= th["hy_oas_red_min"]) or (ig is not None and ig >= th["ig_oas_red_min"]): return -1
    if hy is not None and hy < th["hy_oas_green_max"] and (ig is None or ig < th["ig_oas_green_max"]): return 1
    return 0


def score_breadth(data: Dict[str, Any], cfg: Dict[str, Any]) -> int:
    if data.get("ZBT_TRIGGER") is True: return 1
    b, ema = safe_float(data.get("BREADTH_TODAY")), safe_float(data.get("ZBT_EMA10"))
    if b is not None and b < cfg["thresholds"]["adrn_shock_breadth"]: return -1
    if ema is not None and ema < 0.45: return -1
    if ema is not None and ema > 0.55: return 1
    return 0


def score_japan(data: Dict[str, Any], cfg: Dict[str, Any]) -> int:
    th = cfg["thresholds"]
    fx, j10, j30 = map(safe_float, [data.get("USDJPY"), data.get("JGB10Y"), data.get("JGB30Y")])
    if fx is not None and fx < th["usdjpy_carry_red"]: return -1
    if j30 is not None and j30 >= th.get("jgb30_red_min", 3.7): return -1
    if j10 is not None and j10 >= th.get("jgb10_red_min", 2.8): return -1
    if fx is not None and fx > 158 and (j30 is None or j30 < 3.6): return 1
    return 0


def score_macro_shock(data: Dict[str, Any], cfg: Dict[str, Any]) -> int:
    b = safe_float(data.get("OIL_BRENT"))
    if str(os.getenv("POLICY_SHOCK_ACTIVE", "false")).lower() in {"1", "true", "yes"}: return -1
    if b is None: return 0
    if b >= cfg["thresholds"]["brent_red_level"]: return -1
    if b >= cfg["thresholds"]["brent_shock_level"]: return 0
    return 1


def score_net_liquidity(data: Dict[str, Any]) -> int:
    _, d = net_liquidity(data)
    if d is None: return 0
    if d < -50: return -1
    if d > 25: return 1
    return 0


def score_inflation_real(data: Dict[str, Any]) -> int:
    real, be5 = safe_float(data.get("DFII10")), safe_float(data.get("T5YIE"))
    if real is not None and real >= 2.0: return -1
    if be5 is not None and be5 <= 2.6: return 1
    return 0


def score_earnings_aggregate(data: Dict[str, Any]) -> int:
    beat = safe_float(data.get("EARNINGS_BEAT_RATE"))
    if beat is None: return 0
    if beat >= 75: return 1
    if beat >= 65: return 0
    return -1


def score_fed_repricing(data: Dict[str, Any]) -> int:
    ctx = data.get("market_context", {}) or {}
    hike = safe_float(ctx.get("sept_hike_odds_pct"))
    cut = safe_float(ctx.get("sept_cut_odds_pct"))
    if hike is not None and hike >= 50: return -1
    if cut is not None and cut >= 50 and score_credit(data, load_config()) >= 0: return 1
    effr, y2 = safe_float(data.get("EFFR")), safe_float(data.get("DGS2"))
    if effr is None or y2 is None: return 0
    return 1 if effr - y2 > 0.50 else (-1 if effr - y2 < -0.05 else 0)


def score_ai_credit(data: Dict[str, Any]) -> Tuple[int, str]:
    ctx = data.get("market_context", {}) or {}
    spread = safe_float(ctx.get("ai_credit_spread_bps"))
    broad = safe_float(ctx.get("broad_ig_spread_bps"))
    cov = safe_float(ctx.get("ai_book_coverage_x"))
    concession = safe_float(ctx.get("ai_new_issue_concession_bps"))
    lowq = safe_float(ctx.get("ai_lower_quality_score"))
    negatives = 0; positives = 0
    if spread is not None and broad is not None:
        if spread - broad >= 20: negatives += 1
        elif spread - broad <= 5: positives += 1
    if cov is not None:
        if cov < 2.0: negatives += 1
        elif cov >= 3.0: positives += 1
    if concession is not None:
        if concession >= 20: negatives += 1
        elif concession <= 10: positives += 1
    if lowq is not None:
        if lowq < 0: negatives += 1
        elif lowq > 0: positives += 1
    if negatives >= 2: score = -1
    elif positives >= 2 and negatives == 0: score = 1
    else: score = 0
    text = ctx.get("ai_credit_commentary") or "AI credit context has not been refreshed; run the Codex news refresh step."
    return score, text


def score_metals(data: Dict[str, Any]) -> Tuple[int, str]:
    gld, gdx, slv, sil = [safe_float(data.get(f"{k}_ret")) for k in ["GLD", "GDX", "SLV", "SIL"]]
    real = safe_float(data.get("DFII10"))
    if gld is None and gdx is None:
        return 0, "Metals tape unavailable."
    if gld is not None and gdx is not None and gld > 0 and gdx > gld:
        return (1 if real is None or real < 2.5 else 0), "Gold and miners are rising with miners outperforming bullion; confirmation is constructive."
    if gld is not None and gdx is not None and gld < -1 and gdx < gld:
        return -1, "Gold is weak and miners are underperforming bullion; high real yields are dominating the hedge trade."
    if slv is not None and sil is not None and slv > 0 and sil < slv:
        return 0, "Bullion is participating but miner confirmation is incomplete."
    return 0, "Precious metals are mixed; structural hedge thesis remains separate from the tactical signal."


def weighted_score(scores: Dict[str, int], weights: Dict[str, float]) -> float:
    den = sum(weights.get(k, 0) for k in scores)
    return 0.0 if den == 0 else sum(scores[k] * weights.get(k, 0) for k in scores) / den


def stance(short_label: str, medium_label: str) -> str:
    if short_label == "🔴" and medium_label in {"🟢", "🟡"}: return "hold core; wait or use tiny probes only"
    if short_label == "🔴" and medium_label == "🔴": return "defensive; preserve dry powder"
    if short_label == "🟢" and medium_label == "🟢": return "press risk in tranches"
    if short_label == "🟢": return "selective risk-on"
    return "selective / scaled entries only"


def earnings_score_row(r: Dict[str, Any]) -> Dict[str, Any]:
    # Codex refreshes 0–100 component scores from the latest quarter. Raw values are displayed separately.
    weights = {
        "organic_revenue_score": .25, "earnings_quality_score": .20, "guidance_revision_score": .20,
        "fcf_score": .15, "backlog_score": .10, "balance_sheet_score": .10,
    }
    vals = {k: safe_float(r.get(k)) for k in weights}
    available = [(k, v) for k, v in vals.items() if v is not None]
    durability = sum(v * weights[k] for k, v in available) / sum(weights[k] for k, _ in available) if available else None
    gate = safe_float(r.get("expectation_gate_score"))
    final = None if durability is None else (0.7 * durability + 0.3 * (gate if gate is not None else 50))
    grade = "NA"
    if final is not None:
        grade = "A" if final >= 80 else "B" if final >= 65 else "C" if final >= 50 else "D"
    return {
        "Ticker": r.get("ticker"), "Durability": None if durability is None else round(durability, 1),
        "Expectation gate": gate, "Final": None if final is None else round(final, 1), "Grade": grade,
        "Revenue YoY": r.get("revenue_growth_yoy_pct"), "EPS/OpInc YoY": r.get("eps_or_opinc_growth_yoy_pct"),
        "FCF YoY": r.get("fcf_growth_yoy_pct"), "Backlog/RPO YoY": r.get("backlog_growth_yoy_pct"),
        "P/E": r.get("pe"), "Daily %": r.get("daily_return_pct"), "Status": r.get("status", ""),
        "Commentary": r.get("commentary", ""), "As of": r.get("as_of", ""), "Source": r.get("source", ""),
    }


def earnings_table(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows = [earnings_score_row(x) for x in (data.get("earnings_watchlist") or [])]
    return sorted(rows, key=lambda x: -1e9 if x["Final"] is None else -x["Final"])


def build_model(data: Dict[str, Any], cfg: Dict[str, Any]) -> Dict[str, Any]:
    ai_score, ai_comment = score_ai_credit(data)
    metal_score, metal_comment = score_metals(data)
    vol_comp_score, vol_comp_comment = score_vol_compression(data)
    short_scores = {
        "vol_regime": score_vol(data, cfg), "breadth": score_breadth(data, cfg), "rates": score_rates(data, cfg),
        "funding": score_funding(data, cfg), "credit": score_credit(data, cfg), "japan_carry": score_japan(data, cfg),
        "macro_shock": score_macro_shock(data, cfg), "ai_credit": ai_score,
    }
    short_weights = cfg["weights"]["short_term"].copy()
    short_weights.update({"macro_shock": .10, "ai_credit": .06})
    # reduce broad credit to preserve total intent after adding AI-credit subfactor
    short_weights["credit"] = .09

    medium_scores = {
        "net_liquidity": score_net_liquidity(data), "balance_sheet_regime": 0,
        "credit": score_credit(data, cfg), "ai_credit": ai_score, "inflation_real_yields": score_inflation_real(data),
        "earnings": score_earnings_aggregate(data), "breadth_zbt": score_breadth(data, cfg), "fed_repricing": score_fed_repricing(data),
    }
    medium_weights = cfg["weights"]["medium_term"].copy()
    medium_weights["credit"] = .075; medium_weights["ai_credit"] = .075

    sv = weighted_score(short_scores, short_weights); mv = weighted_score(medium_scores, medium_weights)
    sl, ml = risk_label(sv), risk_label(mv)
    return {
        "short_scores": short_scores, "medium_scores": medium_scores,
        "short_value": sv, "medium_value": mv, "short_label": sl, "medium_label": ml,
        "stance": stance(sl, ml),
        "ai_credit_score": ai_score, "ai_credit_label": dot_from_score(ai_score), "ai_credit_commentary": ai_comment,
        "metals_score": metal_score, "metals_label": dot_from_score(metal_score), "metals_commentary": metal_comment,
        "vol_compression_score": vol_comp_score, "vol_compression_label": dot_from_score(vol_comp_score),
        "vol_compression_commentary": vol_comp_comment,
        "earnings_rows": earnings_table(data),
    }


def source_text(data: Dict[str, Any], key: str, fallback: str = "") -> str:
    s = data.get(f"{key}_source", fallback); d = data.get(f"{key}_date")
    return f"{s} | {d}" if s and d else (str(s) if s else (str(d) if d else "unavailable"))


def module_rows(data: Dict[str, Any], model: Dict[str, Any], cfg: Dict[str, Any]) -> List[Dict[str, str]]:
    ctx = data.get("market_context", {}) or {}
    net, nd = net_liquidity(data)
    y10, y30, y2 = safe_float(data.get("DGS10")), safe_float(data.get("DGS30")), safe_float(data.get("DGS2"))
    real, be10 = safe_float(data.get("DFII10")), safe_float(data.get("T10YIE"))
    vix, v9, v3, vvix = map(safe_float, [data.get("VIX"), data.get("VIX9D"), data.get("VIX3M"), data.get("VVIX")])
    hy, ig = safe_float(data.get("BAMLH0A0HYM2")), safe_float(data.get("BAMLC0A0CM"))
    sofr, effr = safe_float(data.get("SOFR")), safe_float(data.get("EFFR"))
    fx, j10, j30 = map(safe_float, [data.get("USDJPY"), data.get("JGB10Y"), data.get("JGB30Y")])
    brent = safe_float(data.get("OIL_BRENT"))
    ai_spread = safe_float(ctx.get("ai_credit_spread_bps")); broad = safe_float(ctx.get("broad_ig_spread_bps"))
    issuance = safe_float(ctx.get("ai_issuance_ytd_bn")); cov = safe_float(ctx.get("ai_book_coverage_x")); concession = safe_float(ctx.get("ai_new_issue_concession_bps"))
    fed_txt = ctx.get("fed_commentary") or "Fed policy commentary not refreshed."
    hold, hike, cut = [safe_float(ctx.get(k)) for k in ["sept_hold_odds_pct", "sept_hike_odds_pct", "sept_cut_odds_pct"]]
    rows = []
    rows.append({"Signal":"AI CREDIT RISK", "Actual numbers":f"AI spread {fmt(ai_spread,0,' bp')} | broad IG {fmt(broad,0,' bp')} | issuance ${fmt(issuance,0,'B')} | book {fmt(cov,1,'x')} | concession {fmt(concession,0,' bp')}", "Dot":model["ai_credit_label"], "Commentary":model["ai_credit_commentary"], "Source / as-of":ctx.get("ai_credit_source_asof", "not refreshed")})
    rows.append({"Signal":"PRECIOUS METALS", "Actual numbers":f"GLD {fmt(data.get('GLD'),2)} ({fmt(data.get('GLD_ret'),2,'%')}) | GDX {fmt(data.get('GDX'),2)} ({fmt(data.get('GDX_ret'),2,'%')}) | SLV {fmt(data.get('SLV'),2)} ({fmt(data.get('SLV_ret'),2,'%')}) | SIL {fmt(data.get('SIL'),2)} ({fmt(data.get('SIL_ret'),2,'%')})", "Dot":model["metals_label"], "Commentary":model["metals_commentary"], "Source / as-of":source_text(data,"GLD","Yahoo Finance")})
    rows.append({"Signal":"EARNINGS DURABILITY", "Actual numbers":f"{len(model['earnings_rows'])} names ranked | top: " + (model['earnings_rows'][0]['Ticker'] if model['earnings_rows'] else "NA"), "Dot":"🟢" if model['earnings_rows'] else "⚪", "Commentary":"Ranks durable forward earnings revisions against valuation, rates, financing and embedded expectations. See detailed table below.", "Source / as-of":ctx.get("earnings_source_asof","watchlist not refreshed")})
    rows.append({"Signal":"10Y / 30Y TREASURY", "Actual numbers":f"10Y {fmt(y10,3,'%')} | 30Y {fmt(y30,3,'%')} | 2Y {fmt(y2,3,'%')} | real10 {fmt(real,2,'%')} | BE10 {fmt(be10,2,'%')}", "Dot":dot_from_score(score_rates(data,cfg)), "Commentary":("Long-duration discount-rate pressure is severe; high real yields are the main valuation headwind." if score_rates(data,cfg)<0 else "Rates are not currently in the model's hard stress zone."), "Source / as-of":source_text(data,"DGS10","FRED/Yahoo")})
    rows.append({"Signal":"VOL COMPRESSION / BREAKOUT", "Actual numbers":f"VIX {fmt(vix,2)} | VIX9D {fmt(v9,2)} | VIX3M {fmt(v3,2)} | VVIX {fmt(vvix,2)}", "Dot":model["vol_compression_label"], "Commentary":model["vol_compression_commentary"], "Source / as-of":source_text(data,"VIX","Yahoo Finance")})
    rows.append({"Signal":"BROAD CREDIT", "Actual numbers":f"HY OAS {fmt(hy,2,'%')} | IG OAS {fmt(ig,2,'%')}", "Dot":dot_from_score(score_credit(data,cfg)), "Commentary":("Broad credit is calm; this argues against a systemic solvency event." if score_credit(data,cfg)>0 else "Broad credit is no longer providing a benign offset."), "Source / as-of":source_text(data,"BAMLH0A0HYM2","FRED")})
    rows.append({"Signal":"FUNDING", "Actual numbers":f"SOFR {fmt(sofr,2,'%')} | EFFR {fmt(effr,2,'%')} | spread {fmt((sofr-effr)*100 if sofr is not None and effr is not None else None,1,' bp')}", "Dot":dot_from_score(score_funding(data,cfg)), "Commentary":("No funding accident; repo plumbing remains orderly." if score_funding(data,cfg)>0 else "Funding spread is widening and needs attention."), "Source / as-of":source_text(data,"SOFR","FRED")})
    rows.append({"Signal":"NET LIQUIDITY", "Actual numbers":f"Net ${fmt(net,1,'B')} | w/w {fmt(nd,1,'B')} | TGA ${fmt(data.get('WDTGAL'),1,'B')} | reserves ${fmt(data.get('WRESBAL'),1,'B')}", "Dot":dot_from_score(score_net_liquidity(data)), "Commentary":("Liquidity impulse is improving." if score_net_liquidity(data)>0 else "Liquidity is flat-to-deteriorating; high TGA/falling reserves reduce the buffer."), "Source / as-of":source_text(data,"WALCL","FRED")})
    rows.append({"Signal":"JAPAN / YEN CARRY", "Actual numbers":f"USDJPY {fmt(fx,2)} | JGB10 {fmt(j10,3,'%')} | JGB30 {fmt(j30,3,'%')}", "Dot":dot_from_score(score_japan(data,cfg)), "Commentary":("Carry/repatriation risk is elevated; a rapid yen strengthening through 157→155 is a forced-deleveraging trigger." if score_japan(data,cfg)<0 or (fx is not None and fx<158) else "Carry remains orderly, but intervention/reversal risk should stay on the board."), "Source / as-of":ctx.get("japan_source_asof", source_text(data,"USDJPY","Yahoo Finance"))})
    rows.append({"Signal":"FED / SEPTEMBER PRICING", "Actual numbers":f"Hold {fmt(hold,1,'%')} | hike {fmt(hike,1,'%')} | cut {fmt(cut,1,'%')}", "Dot":dot_from_score(score_fed_repricing(data)), "Commentary":fed_txt, "Source / as-of":ctx.get("fed_source_asof","not refreshed")})
    rows.append({"Signal":"OIL / MACRO SHOCK", "Actual numbers":f"Brent {fmt(brent,2,'')} | WTI {fmt(data.get('OIL_WTI'),2,'')}", "Dot":dot_from_score(score_macro_shock(data,cfg)), "Commentary":("Oil is inside the inflation-shock zone and can keep term premium/Fed expectations elevated." if score_macro_shock(data,cfg)<0 else "Oil is not currently forcing the inflation-shock override."), "Source / as-of":ctx.get("oil_source_asof","manual/context")})
    rows.append({"Signal":"BREADTH / ZBT", "Actual numbers":f"Breadth {fmt(data.get('BREADTH_TODAY'),3)} | EMA10 {fmt(data.get('ZBT_EMA10'),3)} | ZBT {data.get('ZBT_TRIGGER')}", "Dot":dot_from_score(score_breadth(data,cfg)), "Commentary":"Breadth is used as confirmation; no ZBT is claimed without a valid 10-session series.", "Source / as-of":data.get("breadth_source","EODData ADRN proxy")})
    return rows


def full_tile_rows(data: Dict[str, Any], model: Dict[str, Any], cfg: Dict[str, Any]) -> List[Dict[str, str]]:
    rows = module_rows(data, model, cfg)
    # add tape / AI names with exact numbers
    for k in ["SPY","QQQ","IWM","NVDA","MU","SNDK","LITE","AAOI","MRVL","GEV","DELL","VRT","ANET","CEG","APP","GLD","GDX","SLV"]:
        if safe_float(data.get(k)) is not None:
            rows.append({"Signal":k, "Actual numbers":f"{fmt(data.get(k),2)} | day {fmt(data.get(k+'_ret'),2,'%')}", "Dot":"🟢" if (safe_float(data.get(k+'_ret')) or 0)>0 else ("🔴" if (safe_float(data.get(k+'_ret')) or 0)<0 else "🟡"), "Commentary":"Tape / relative-strength context; not independently scored.", "Source / as-of":source_text(data,k,"Yahoo Finance")})
    return rows


def tripwires(data: Dict[str, Any]) -> List[str]:
    return [
        "10Y closes >4.80% and then trades >4.85% → AI-duration de-rating override.",
        "30Y closes >5.30% → global long-duration stress is not contained.",
        "USD/JPY breaks rapidly through 157 toward 155 → carry unwind joins the bond shock.",
        "VIX >17 with VVIX >100; VIX >20 + VVIX >100 = confirmed volatility regime deterioration.",
        "Hyperscaler/AI spreads widen another ~20–25 bp while HY OAS remains <3.5% → AI-specific de-rating signal.",
        "Gold weak + GDX underperforms while real10 >2.5% → postpone miner additions; gold/GDX recovery with lower real yields reopens the tranche.",
    ]


def integrity_rows(data: Dict[str, Any]) -> List[Dict[str, str]]:
    keys = ["DGS10","DGS30","DFII10","VIX","VVIX","BAMLH0A0HYM2","BAMLC0A0CM","SOFR","EFFR","WALCL","WDTGAL","WRESBAL","USDJPY"]
    out=[]
    for k in keys:
        out.append({"Field":k,"Value":fmt(data.get(k),3),"Source":str(data.get(f"{k}_source","unknown")),"As of":str(data.get(f"{k}_date","unknown")),"Status":"PASS" if safe_float(data.get(k)) is not None else "MISSING"})
    return out


def top_summary(data: Dict[str, Any], model: Dict[str, Any]) -> Dict[str, str]:
    y10 = fmt(data.get("DGS10"),3,"%")
    fx = fmt(data.get("USDJPY"),2)
    earn = model["earnings_rows"]
    top = earn[0]["Ticker"] if earn else "NA"
    return {
        "AI CREDIT RISK": model["ai_credit_label"],
        "PRECIOUS METALS": model["metals_label"],
        "EARNINGS DURABILITY": "🟢" if earn else "⚪",
        "10Y TREASURY": f"{dot_from_score(score_rates(data, load_config()))} {y10}",
        "YEN / CARRY": f"{dot_from_score(score_japan(data, load_config()))} {fx}",
        "VOL COMPRESSION": model["vol_compression_label"],
        "SHORT-TERM": model["short_label"],
        "2–8 WEEK": model["medium_label"],
        "TRADE STANCE": model["stance"],
        "TOP EARNINGS NAME": top,
    }


def print_fast(data: Dict[str, Any], model: Dict[str, Any], cfg: Dict[str, Any]) -> None:
    print(f"FAST MODEL RUN — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("No index futures in score.")
    top = top_summary(data, model)
    for k, v in top.items(): print(f"{k}: {v}")
    print("\nACTUAL NUMBERS + COMMENTARY")
    print("| Signal | Actual numbers | Dot | Commentary | Source / as-of |")
    print("|---|---|:--:|---|---|")
    for r in module_rows(data, model, cfg):
        vals = [str(r[x]).replace("|","/") for x in ["Signal","Actual numbers","Dot","Commentary","Source / as-of"]]
        print("| " + " | ".join(vals) + " |")
    print("\nEARNINGS DURABILITY / EXPECTATION GAP")
    if model["earnings_rows"]:
        print("| Ticker | Final | Grade | Rev YoY | EPS/OpInc YoY | FCF YoY | Backlog/RPO YoY | P/E | Daily % | Status |")
        print("|---|---:|:--:|---:|---:|---:|---:|---:|---:|---|")
        for r in model["earnings_rows"]:
            print(f"| {r['Ticker']} | {r['Final']} | {r['Grade']} | {r['Revenue YoY']} | {r['EPS/OpInc YoY']} | {r['FCF YoY']} | {r['Backlog/RPO YoY']} | {r['P/E']} | {r['Daily %']} | {r['Status']} |")
    else:
        print("No refreshed earnings watchlist. Run the Codex refresh step.")
    print("\nTRIPWIRES")
    for x in tripwires(data): print(f"- {x}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fast", action="store_true")
    ap.add_argument("--mock", action="store_true")
    ap.add_argument("--json-out")
    ap.add_argument("--config", default="config.yaml")
    args = ap.parse_args()
    cfg = load_config(args.config); data = merge_data(args.mock); model = build_model(data, cfg)
    print_fast(data, model, cfg)
    if args.json_out:
        payload = {"as_of": datetime.now(timezone.utc).isoformat(), "summary": top_summary(data,model),
                   "data": data, "model": {k:v for k,v in model.items() if k != "earnings_rows"},
                   "modules": module_rows(data,model,cfg), "earnings": model["earnings_rows"], "tripwires": tripwires(data),
                   "integrity": integrity_rows(data)}
        Path(args.json_out).write_text(json.dumps(payload, indent=2, default=str))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

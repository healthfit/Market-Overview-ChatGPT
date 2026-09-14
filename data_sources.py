\
from __future__ import annotations
import os, json, math
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
import pandas as pd
import numpy as np
import requests
try:
    import yfinance as yf
except Exception:
    yf = None
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

FRED_SERIES = [
    "WALCL","WDTGAL","RRPONTSYD","WRESBAL",
    "DGS2","DGS5","DGS10","DGS30","DFII10",
    "T5YIE","T10YIE","T5YIFR",
    "BAMLH0A0HYM2","BAMLC0A0CM","SOFR","EFFR"
]

YF_MAP = {
    "VIX":"^VIX","VIX9D":"^VIX9D","VIX3M":"^VIX3M","VVIX":"^VVIX","VXN":"^VXN",
    "USDJPY":"JPY=X",
    "GLD":"GLD","GDX":"GDX","SLV":"SLV","SIL":"SIL","SILJ":"SILJ",
    "SPY":"SPY","QQQ":"QQQ","IWM":"IWM",
    "NVDA":"NVDA","MU":"MU","SNDK":"SNDK","LITE":"LITE","AAOI":"AAOI","MRVL":"MRVL",
    "GEV":"GEV","VRT":"VRT","ANET":"ANET","DELL":"DELL","CEG":"CEG","VST":"VST",
    "MSFT":"MSFT","APP":"APP","CRWD":"CRWD","CAT":"CAT"
}

def _float(x: Any) -> Optional[float]:
    try:
        if x is None: return None
        v=float(x)
        if math.isnan(v): return None
        return v
    except Exception:
        return None

def fred_obs(series_id: str, api_key: str, limit: int = 8) -> pd.DataFrame:
    r=requests.get(
        "https://api.stlouisfed.org/fred/series/observations",
        params={"series_id":series_id,"api_key":api_key,"file_type":"json","sort_order":"desc","limit":limit},
        timeout=20
    )
    r.raise_for_status()
    df=pd.DataFrame(r.json().get("observations",[]))
    if df.empty: return pd.DataFrame(columns=["date","value"])
    df["date"]=pd.to_datetime(df["date"],errors="coerce")
    df["value"]=pd.to_numeric(df["value"],errors="coerce")
    return df.dropna(subset=["date"]).sort_values("date")

def fetch_fred() -> Dict[str,Any]:
    key=os.getenv("FRED_API_KEY")
    if not key: return {"fred_error":"FRED_API_KEY missing"}
    out={}
    for sid in FRED_SERIES:
        try:
            df=fred_obs(sid,key,10).dropna(subset=["value"])
            if df.empty:
                out[sid]=None
                continue
            out[sid]=float(df.iloc[-1]["value"])
            out[f"{sid}_date"]=str(df.iloc[-1]["date"].date())
            if len(df)>=2:
                out[f"{sid}_prev"]=float(df.iloc[-2]["value"])
        except Exception as e:
            out[sid]=None
            out[f"{sid}_error"]=str(e)
    return out

def fetch_yahoo() -> Dict[str,Any]:
    out={}
    if yf is None:
        return {"yahoo_error":"yfinance not installed"}
    tickers=list(YF_MAP.values())
    try:
        df=yf.download(" ".join(tickers),period="5d",interval="1d",progress=False,auto_adjust=False,group_by="ticker",threads=True)
        for key,t in YF_MAP.items():
            try:
                sub=df[t].dropna() if isinstance(df.columns,pd.MultiIndex) else df.dropna()
                if sub.empty: continue
                close=float(sub["Close"].iloc[-1])
                prev=float(sub["Close"].iloc[-2]) if len(sub)>1 else None
                out[key]=close
                out[f"{key}_ret"]=((close/prev)-1)*100 if prev else None
                out[f"{key}_date"]=str(sub.index[-1].date())
            except Exception:
                pass
    except Exception as e:
        out["yahoo_error"]=str(e)
    return out

def apply_env_overrides(data: Dict[str,Any]) -> Dict[str,Any]:
    mapping={
        "UST2Y":"DGS2","UST5Y":"DGS5","UST10Y":"DGS10","UST30Y":"DGS30","REAL10Y":"DFII10",
        "JGB10Y":"JGB10Y","JGB30Y":"JGB30Y","BRENT":"BRENT","WTI":"WTI","USDJPY":"USDJPY",
        "FED_REPRICING_SCORE":"FED_REPRICING_SCORE","MACRO_SHOCK_SCORE":"MACRO_SHOCK_SCORE",
        "AI_HYPERSCALER_SPREAD_BP":"AI_HYPERSCALER_SPREAD_BP",
        "AI_HYPERSCALER_SPREAD_CHANGE_5D_BP":"AI_HYPERSCALER_SPREAD_CHANGE_5D_BP",
        "AI_ORDERBOOK_COVERAGE_X":"AI_ORDERBOOK_COVERAGE_X",
        "AI_ISSUANCE_YTD_B":"AI_ISSUANCE_YTD_B",
        "AI_LOWER_QUALITY_STRESS_SCORE":"AI_LOWER_QUALITY_STRESS_SCORE",
    }
    for env_key,data_key in mapping.items():
        raw=os.getenv(env_key)
        if raw not in (None,""):
            val=_float(raw)
            if val is not None:
                data[data_key]=val
                data[f"{data_key}_override"]=True
    return data

def load_snapshot(mock=False) -> Dict[str,Any]:
    if mock:
        return json.loads(Path("sample_snapshot.json").read_text())
    data={"as_of":datetime.now().isoformat(timespec="seconds")}
    data.update(fetch_fred())
    data.update(fetch_yahoo())
    return apply_env_overrides(data)

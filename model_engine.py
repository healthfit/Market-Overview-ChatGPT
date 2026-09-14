\
from __future__ import annotations
from typing import Dict, Any, Optional, List
import pandas as pd
import numpy as np
import yaml

def val(d,k,default=None):
    x=d.get(k,default)
    try:
        return float(x) if x is not None else default
    except Exception:
        return default

def dot(score: Optional[float]) -> str:
    if score is None: return "⚪"
    if score >= 0.35: return "🟢"
    if score <= -0.35: return "🔴"
    return "🟡"

def band(value, green_max, red_min):
    if value is None: return 0
    if value < green_max: return 1
    if value > red_min: return -1
    return 0

def net_liquidity(d):
    w,t,r=val(d,"WALCL"),val(d,"WDTGAL"),val(d,"RRPONTSYD")
    if None in (w,t,r): return None
    return w-t-r

def net_liquidity_change(d):
    keys=["WALCL","WDTGAL","RRPONTSYD"]
    if any(val(d,k) is None or val(d,f"{k}_prev") is None for k in keys):
        return None
    now=val(d,"WALCL")-val(d,"WDTGAL")-val(d,"RRPONTSYD")
    prev=val(d,"WALCL_prev")-val(d,"WDTGAL_prev")-val(d,"RRPONTSYD_prev")
    return now-prev

def score_vol(d):
    vix,v9,v3,vv=val(d,"VIX"),val(d,"VIX9D"),val(d,"VIX3M"),val(d,"VVIX")
    if vix is None: return 0
    if vix>22 or (vv is not None and vv>120) or (v9 is not None and v9>vix): return -1
    if vix<18 and v9 is not None and v3 is not None and v9<vix<v3: return 1
    return 0

def vol_compression_label(d):
    vix,vv,v9,v3=val(d,"VIX"),val(d,"VVIX"),val(d,"VIX9D"),val(d,"VIX3M")
    if vix is None: return ("⚪","Unavailable")
    if vix>22 and v9 is not None and v9>vix:
        return ("🔴","Hard breakout / backwardation")
    if vix>20 and vv is not None and vv>100:
        return ("🔴","Breakout with convexity demand")
    if vix>18:
        return ("🔴","Confirmed breakout")
    if vix>=16.5:
        return ("🟡","Compression release / watch closely")
    if vix<15:
        return ("🟡","Compressed / coiled, not triggered")
    return ("🟢","Calm, term structure not stressed")

def score_rates(d):
    ten,thirty,real=val(d,"DGS10"),val(d,"DGS30"),val(d,"DFII10")
    if ten is None: return 0
    if ten>=4.80 or (thirty is not None and thirty>=5.25): return -1
    if ten>4.35 or (real is not None and real>2.0): return -0.7
    if ten<4.10 and (real is None or real<1.75): return 1
    return 0

def score_funding(d):
    s,e=val(d,"SOFR"),val(d,"EFFR")
    if s is None or e is None: return 0
    bps=(s-e)*100
    if bps>15: return -1
    if bps<5: return 1
    return 0

def score_credit(d):
    hy,ig=val(d,"BAMLH0A0HYM2"),val(d,"BAMLC0A0CM")
    if hy is None or ig is None: return 0
    if hy>5 or ig>1.5: return -1
    if hy<3.5 and ig<1.0: return 1
    return 0

def score_ai_credit(d):
    spread=val(d,"AI_HYPERSCALER_SPREAD_BP")
    change=val(d,"AI_HYPERSCALER_SPREAD_CHANGE_5D_BP")
    books=val(d,"AI_ORDERBOOK_COVERAGE_X")
    issuance=val(d,"AI_ISSUANCE_YTD_B")
    lower=val(d,"AI_LOWER_QUALITY_STRESS_SCORE")
    parts=[]
    if change is not None:
        parts.append(-1 if change>=20 else (-0.5 if change>=10 else (0.5 if change<=0 else 0)))
    if books is not None:
        parts.append(-1 if books<2 else (0.5 if books>=3 else 0))
    if issuance is not None:
        parts.append(-0.5 if issuance>=200 else 0)
    if lower is not None:
        parts.append(max(-1,min(1,lower)))
    if spread is not None:
        parts.append(-0.5 if spread>=100 else (0.25 if spread<75 else 0))
    return float(np.mean(parts)) if parts else 0

def score_japan(d):
    fx,j30=val(d,"USDJPY"),val(d,"JGB30Y")
    score=0
    if j30 is not None:
        if j30>=4.0: score-=0.7
        elif j30>=3.7: score-=0.4
    if fx is not None:
        if fx<=155: score-=0.8
        elif fx<=157: score-=0.4
        elif fx>=160: score-=0.2  # intervention risk despite carry support
        else: score+=0.1
    return max(-1,min(1,score))

def score_metals(d):
    gld,gdx,slv,sil=val(d,"GLD_ret"),val(d,"GDX_ret"),val(d,"SLV_ret"),val(d,"SIL_ret")
    real=val(d,"DFII10")
    parts=[]
    if gld is not None: parts.append(0.5 if gld>0 else -0.3)
    if gdx is not None and gld is not None: parts.append(0.5 if gdx>gld else -0.3)
    if sil is not None and slv is not None: parts.append(0.4 if sil>slv else -0.2)
    if real is not None and real>2.5: parts.append(-0.5)
    return float(np.mean(parts)) if parts else 0

def earnings_table(path="earnings_watchlist.csv"):
    df=pd.read_csv(path)
    base_cols=["organic_rev_growth","op_eps_growth","guidance_revision","fcf_growth","backlog_growth","balance_sheet_quality"]
    weights=np.array([.25,.20,.20,.15,.10,.10])
    base=(df[base_cols].values*weights).sum(axis=1)
    gate=(0.40*df["valuation_gate"] + 0.25*df["rate_sensitivity"] + 0.35*df["expectation_gap"])
    df["durability_score"]=base
    df["adjusted_score"]=base + gate
    return df.sort_values("adjusted_score",ascending=False)

def score_earnings(path="earnings_watchlist.csv"):
    df=earnings_table(path)
    top=df.head(8)["adjusted_score"].mean()
    return float(max(-1,min(1,top)))

def score_breadth(d):
    b=val(d,"BREADTH_FRACTION")
    z=val(d,"ZBT_EMA10")
    if b is not None and b<0.35: return -1
    if z is not None and z>0.615: return 1
    if z is not None and z<0.45: return -0.5
    return 0

def score_netliq(d):
    ch=net_liquidity_change(d)
    if ch is None: return 0
    # FRED balance sheet/TGA are millions; 50,000 = $50B
    if ch>50000: return 1
    if ch<-50000: return -1
    return 0

def score_balance_sheet_regime(d):
    now,prev=val(d,"WALCL"),val(d,"WALCL_prev")
    if now is None or prev is None: return 0
    delta=now-prev
    if delta>15000: return 0.5
    if delta<-15000: return -0.5
    return 0

def score_fed_repricing(d):
    x=val(d,"FED_REPRICING_SCORE")
    if x is None: return 0
    return max(-1,min(1,x))

def weighted(parts, weights):
    return sum(parts.get(k,0)*w for k,w in weights.items()) / max(sum(weights.values()),1e-9)

def build_model(d, cfg, earnings_path="earnings_watchlist.csv"):
    short_parts={
        "vol_regime":score_vol(d),
        "rates":score_rates(d),
        "funding":score_funding(d),
        "broad_credit":score_credit(d),
        "ai_credit":score_ai_credit(d),
        "breadth":score_breadth(d),
        "japan_carry":score_japan(d),
        "precious_metals_cross_asset":score_metals(d),
        "earnings_durability":score_earnings(earnings_path),
    }
    med_parts={
        "net_liquidity":score_netliq(d),
        "balance_sheet_regime":score_balance_sheet_regime(d),
        "broad_credit":score_credit(d),
        "ai_credit":score_ai_credit(d),
        "inflation_real_yields":score_rates(d),
        "earnings_durability":score_earnings(earnings_path),
        "breadth_zbt":score_breadth(d),
        "fed_repricing":score_fed_repricing(d),
        "japan_carry":score_japan(d),
        "precious_metals_cross_asset":score_metals(d),
    }
    short=weighted(short_parts,cfg["weights"]["short_term"])
    medium=weighted(med_parts,cfg["weights"]["medium_term"])

    # Approved macro-shock overlay: oil/war/tariff shocks can cap or worsen risk
    shock=val(d,"MACRO_SHOCK_SCORE")
    if shock is not None:
        shock=max(-1,min(1,shock))
        short += 0.15*shock
        medium += 0.08*shock

    short=max(-1,min(1,short))
    medium=max(-1,min(1,medium))

    ai=score_ai_credit(d)
    pm=score_metals(d)
    earn=score_earnings(earnings_path)
    vc_dot,vc_text=vol_compression_label(d)

    if short<=-.35: stance="Defensive / tiny probes only"
    elif short>=.35 and medium>=0: stance="Buy dips in tranches"
    else: stance="Selective / no chase"

    return {
        "short_value":short,"short_dot":dot(short),
        "medium_value":medium,"medium_dot":dot(medium),
        "ai_credit_value":ai,"ai_credit_dot":dot(ai),
        "metals_value":pm,"metals_dot":dot(pm),
        "earnings_value":earn,"earnings_dot":dot(earn),
        "vol_dot":vc_dot,"vol_text":vc_text,
        "rates_dot":dot(score_rates(d)),
        "japan_dot":dot(score_japan(d)),
        "stance":stance,
        "short_parts":short_parts,"medium_parts":med_parts,
    }

def headline_rows(d,m):
    ten=val(d,"DGS10")
    fx=val(d,"USDJPY")
    return [
        ["AI CREDIT RISK",m["ai_credit_dot"],f'{m["ai_credit_value"]:+.2f}'],
        ["PRECIOUS METALS",m["metals_dot"],f'{m["metals_value"]:+.2f}'],
        ["EARNINGS DURABILITY",m["earnings_dot"],f'{m["earnings_value"]:+.2f}'],
        ["VOL COMPRESSION",m["vol_dot"],m["vol_text"]],
        ["10Y / REAL YIELD",m["rates_dot"],f'10Y {ten:.2f}%' if ten is not None else "NA"],
        ["JAPAN / YEN CARRY",m["japan_dot"],f'USDJPY {fx:.2f}' if fx is not None else "NA"],
        ["SHORT-TERM DRAWDOWN",m["short_dot"],f'{m["short_value"]:+.2f}'],
        ["2–8 WEEK RALLY",m["medium_dot"],f'{m["medium_value"]:+.2f}'],
    ]

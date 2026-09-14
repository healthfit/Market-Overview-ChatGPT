\
import os
import yaml
import pandas as pd
import streamlit as st

from data_sources import load_snapshot
from model_engine import build_model, headline_rows, earnings_table, net_liquidity, net_liquidity_change

st.set_page_config(page_title="Market Risk Model v2", layout="wide")
st.title("Market Risk Model v2")
st.caption("AI-heavy portfolio risk dashboard — two-horizon model")

# Load Streamlit secrets into environment without exposing them
try:
    for k,v in st.secrets.items():
        if isinstance(v,(str,int,float)):
            os.environ.setdefault(k,str(v))
except Exception:
    pass

with st.sidebar:
    st.header("Controls")
    mock=st.toggle("Mock mode",value=False)
    st.caption("Live FRED requires FRED_API_KEY.")
    st.write("FRED key:", "SET" if os.getenv("FRED_API_KEY") else "MISSING")
    st.divider()
    st.subheader("Manual overrides")
    st.caption("Use these only when a free live feed is stale.")
    manual_ust10=st.text_input("UST 10Y live override",value=os.getenv("UST10Y",""))
    manual_ust30=st.text_input("UST 30Y live override",value=os.getenv("UST30Y",""))
    manual_usdjpy=st.text_input("USDJPY override",value=os.getenv("USDJPY",""))
    manual_jgb10=st.text_input("Japan 10Y override",value=os.getenv("JGB10Y",""))
    manual_jgb30=st.text_input("Japan 30Y override",value=os.getenv("JGB30Y",""))
    manual_brent=st.text_input("Brent override",value=os.getenv("BRENT",""))
    st.subheader("AI credit overrides")
    ai_spread=st.text_input("Hyperscaler spread (bp)",value=os.getenv("AI_HYPERSCALER_SPREAD_BP",""))
    ai_change=st.text_input("5d spread change (bp)",value=os.getenv("AI_HYPERSCALER_SPREAD_CHANGE_5D_BP",""))
    ai_books=st.text_input("New-issue book coverage (x)",value=os.getenv("AI_ORDERBOOK_COVERAGE_X",""))
    ai_issuance=st.text_input("AI issuance YTD ($B)",value=os.getenv("AI_ISSUANCE_YTD_B",""))
    if manual_ust10: os.environ["UST10Y"]=manual_ust10
    if manual_ust30: os.environ["UST30Y"]=manual_ust30
    if manual_usdjpy: os.environ["USDJPY"]=manual_usdjpy
    if manual_jgb10: os.environ["JGB10Y"]=manual_jgb10
    if manual_jgb30: os.environ["JGB30Y"]=manual_jgb30
    if manual_brent: os.environ["BRENT"]=manual_brent
    if ai_spread: os.environ["AI_HYPERSCALER_SPREAD_BP"]=ai_spread
    if ai_change: os.environ["AI_HYPERSCALER_SPREAD_CHANGE_5D_BP"]=ai_change
    if ai_books: os.environ["AI_ORDERBOOK_COVERAGE_X"]=ai_books
    if ai_issuance: os.environ["AI_ISSUANCE_YTD_B"]=ai_issuance

cfg=yaml.safe_load(open("config.yaml"))
data=load_snapshot(mock=mock)
model=build_model(data,cfg)

# Top line — deliberately prominent
rows=headline_rows(data,model)
cols=st.columns(4)
for i,row in enumerate(rows[:4]):
    cols[i].metric(row[0],row[1],row[2])
cols2=st.columns(4)
for i,row in enumerate(rows[4:]):
    cols2[i].metric(row[0],row[1],row[2])

st.info(f"Trade stance: **{model['stance']}**")

st.subheader("Core market data")
core_keys=[
    "DGS2","DGS5","DGS10","DGS30","DFII10","T5YIE","T10YIE",
    "VIX","VIX9D","VIX3M","VVIX","VXN",
    "BAMLH0A0HYM2","BAMLC0A0CM","SOFR","EFFR",
    "USDJPY","JGB10Y","JGB30Y","BRENT",
    "WALCL","WDTGAL","RRPONTSYD","WRESBAL"
]
st.dataframe(pd.DataFrame([{"metric":k,"value":data.get(k)} for k in core_keys]),use_container_width=True,hide_index=True)

c1,c2=st.columns(2)
with c1:
    nl=net_liquidity(data)
    ch=net_liquidity_change(data)
    st.subheader("Liquidity")
    st.metric("Net liquidity proxy",f"{nl/1_000_000:.3f}T" if nl is not None else "NA")
    st.metric("Weekly change",f"{ch/1000:+.1f}B" if ch is not None else "NA")
with c2:
    st.subheader("Model component scores")
    st.json({"short":model["short_parts"],"medium":model["medium_parts"]})

st.subheader("Earnings Durability + Expectation Gap")
earn=earnings_table()
show=earn[["ticker","bucket","durability_score","adjusted_score","valuation_gate","rate_sensitivity","expectation_gap","notes"]]
st.dataframe(show,use_container_width=True,hide_index=True)

st.subheader("AI book tape")
tickers=["NVDA","MU","SNDK","LITE","AAOI","MRVL","GEV","VRT","ANET","DELL","CEG","VST","MSFT","APP","CRWD","CAT"]
tape=[]
for t in tickers:
    tape.append({"ticker":t,"price":data.get(t),"daily_return_pct":data.get(f"{t}_ret")})
st.dataframe(pd.DataFrame(tape),use_container_width=True,hide_index=True)

st.subheader("Tripwires")
st.markdown("""
- **10Y closes >4.80% / trades >4.85%** → AI-duration de-rating warning.
- **30Y >5.25–5.30%** → global long-duration stress.
- **USDJPY rapid move through 157 toward 155** → carry-unwind risk.
- **VIX >17 after compression; VIX >20 + VVIX >100** → volatility breakout.
- **Hyperscaler spreads +20–25 bp while HY OAS <3.5%** → AI-sector de-rating override.
- **10Y <4.60% + AI spreads tightening + strong earnings breadth** → aggressive-risk unlock.
""")

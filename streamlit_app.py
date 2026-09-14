import json
import os
from pathlib import Path

import pandas as pd
import streamlit as st

from liquidity_model import (
    load_config, merge_data, build_model, module_rows, full_tile_rows,
    top_summary, tripwires, integrity_rows,
)

BASE = Path(__file__).resolve().parent
st.set_page_config(page_title="Liquidity + AI Risk Model", layout="wide")
st.title("Liquidity + AI Risk Model — FAST Dashboard")
st.caption("Chat-style layout: actual numbers + stoplights + commentary + sources. No index futures are scored.")

with st.sidebar:
    st.header("Run controls")
    mock = st.toggle("Mock/demo mode", value=False)
    st.caption("Live mode uses FRED + Yahoo/yfinance, then overlays Codex-refreshed market_context.json and earnings_watchlist.json.")
    st.write("FRED API:", "✅ set" if os.getenv("FRED_API_KEY") else "⚠️ missing")
    st.divider()
    st.subheader("Manual live overrides")
    st.caption("Optional. These beat free feeds when you have a more current number.")
    for env_name in ["DGS10","DGS30","DFII10","USDJPY","JGB10Y","JGB30Y","OIL_BRENT","VIX","VVIX"]:
        st.text_input(env_name, value=os.getenv(env_name, ""), key=f"show_{env_name}", disabled=True)
    st.divider()
    st.caption("To refresh news/Fed/AI-credit/earnings commentary, have Codex update market_context.json and earnings_watchlist.json before launching the app.")

cfg = load_config("config.yaml")
data = merge_data(mock=mock)
model = build_model(data, cfg)
summary = top_summary(data, model)

# Prominent lines exactly like the chat layout.
st.markdown(f"### AI CREDIT RISK: {model['ai_credit_label']} — {model['ai_credit_commentary']}")
st.markdown(f"### PRECIOUS METALS / FISCAL CREDIBILITY: {model['metals_label']} — {model['metals_commentary']}")
st.markdown("### EARNINGS DURABILITY / EXPECTATION GAP: " + ("🟢 ranked below" if model["earnings_rows"] else "⚪ not refreshed"))

cols = st.columns(5)
cols[0].metric("10Y Treasury", summary["10Y TREASURY"])
cols[1].metric("USD/JPY", summary["YEN / CARRY"])
cols[2].metric("Vol compression", summary["VOL COMPRESSION"])
cols[3].metric("Short-term drawdown", summary["SHORT-TERM"], f"{model['short_value']:+.2f}")
cols[4].metric("2–8 week rally", summary["2–8 WEEK"], f"{model['medium_value']:+.2f}")
st.info(f"**Trade stance:** {model['stance']}")

# News/context banner
ctx = data.get("market_context", {}) or {}
if ctx.get("market_commentary"):
    st.markdown("#### Today’s market read")
    st.write(ctx["market_commentary"])
else:
    st.warning("News commentary has not been refreshed. Run the Codex refresh step so Waller/Warsh/Bessent/Fed-pricing and other current headlines appear here.")

st.markdown("## Actual numbers + commentary")
st.dataframe(pd.DataFrame(module_rows(data, model, cfg)), use_container_width=True, hide_index=True)

# Headline cards if present
if ctx.get("headlines"):
    st.markdown("## Headlines driving the model")
    for h in ctx["headlines"]:
        title = h.get("title", "Headline") if isinstance(h, dict) else str(h)
        note = h.get("impact", "") if isinstance(h, dict) else ""
        source = h.get("source", "") if isinstance(h, dict) else ""
        st.markdown(f"- **{title}** — {note} {('('+source+')') if source else ''}")

# Detailed tabs
ov, ai, metals, earnings, tape, integrity = st.tabs([
    "Overview", "AI credit", "Metals", "Earnings durability", "Tape / full board", "Integrity / sources"
])

with ov:
    st.subheader("Model interpretation")
    y10 = data.get("DGS10")
    vix = data.get("VIX")
    fx = data.get("USDJPY")
    st.write(f"**10Y:** {y10 if y10 is not None else 'NA'}%  |  **VIX:** {vix if vix is not None else 'NA'}  |  **USD/JPY:** {fx if fx is not None else 'NA'}")
    st.write("The model distinguishes a systemic credit/funding problem from a sector-specific AI financing / valuation problem. High-quality AI can remain fundamentally strong while high real yields compress multiples.")
    st.subheader("Tripwires")
    for x in tripwires(data): st.write("• " + x)

with ai:
    st.subheader("AI credit — actual numbers")
    ai_fields = {
        "AI credit spread (bp)": ctx.get("ai_credit_spread_bps"),
        "Broad IG spread (bp)": ctx.get("broad_ig_spread_bps"),
        "AI issuance YTD ($bn)": ctx.get("ai_issuance_ytd_bn"),
        "Typical order-book coverage (x)": ctx.get("ai_book_coverage_x"),
        "New-issue concession (bp)": ctx.get("ai_new_issue_concession_bps"),
        "Lower-quality AI score (-1/0/+1)": ctx.get("ai_lower_quality_score"),
    }
    st.dataframe(pd.DataFrame([{"Metric":k,"Value":v} for k,v in ai_fields.items()]), use_container_width=True, hide_index=True)
    st.write(model["ai_credit_commentary"])
    if ctx.get("ai_credit_names"):
        st.dataframe(pd.DataFrame(ctx["ai_credit_names"]), use_container_width=True, hide_index=True)

with metals:
    st.subheader("Gold / silver / miners")
    mrows=[]
    for k in ["GLD","GDX","GDXJ","SLV","SIL","SILJ","NEM","AEM","FNV","WPM"]:
        if data.get(k) is not None:
            mrows.append({"Ticker":k,"Price":data.get(k),"Daily %":data.get(k+"_ret"),"Source":data.get(k+"_source","Yahoo Finance"),"As of":data.get(k+"_date","")})
    st.dataframe(pd.DataFrame(mrows), use_container_width=True, hide_index=True)
    st.write(model["metals_commentary"])

with earnings:
    st.subheader("Earnings durability + expectation/valuation gate")
    st.caption("This is the stock-selection layer: durable forward earnings revisions minus valuation, rates, financing and embedded expectations.")
    if model["earnings_rows"]:
        st.dataframe(pd.DataFrame(model["earnings_rows"]), use_container_width=True, hide_index=True)
    else:
        st.warning("earnings_watchlist.json is empty or stale. Have Codex refresh it from the latest quarter before using this ranking.")

with tape:
    st.subheader("Full board")
    st.dataframe(pd.DataFrame(full_tile_rows(data, model, cfg)), use_container_width=True, hide_index=True)

with integrity:
    st.subheader("Data integrity / timestamp gate")
    st.dataframe(pd.DataFrame(integrity_rows(data)), use_container_width=True, hide_index=True)
    st.json({"fred_status":data.get("fred_status"),"yahoo_status":data.get("yahoo_status"),"context_as_of":ctx.get("as_of"),"context_sources":ctx.get("sources",[])})

st.caption("Model is decision support only. Free feeds may be delayed; manual overrides and Codex-refreshed context should be used when a faster source is available.")

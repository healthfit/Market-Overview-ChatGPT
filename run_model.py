\
#!/usr/bin/env python3
import argparse, json
import yaml
from tabulate import tabulate
from data_sources import load_snapshot
from model_engine import build_model, headline_rows, earnings_table, net_liquidity, net_liquidity_change

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--mock",action="store_true")
    ap.add_argument("--json",action="store_true")
    args=ap.parse_args()

    cfg=yaml.safe_load(open("config.yaml"))
    data=load_snapshot(mock=args.mock)
    model=build_model(data,cfg)

    if args.json:
        print(json.dumps({"data":data,"model":model},indent=2,default=str))
        return

    print(f'FAST MODEL RUN — {data.get("as_of","")}')
    print(tabulate(headline_rows(data,model),headers=["Module","Signal","Read"],tablefmt="github"))
    print()
    nl=net_liquidity(data)
    ch=net_liquidity_change(data)
    if nl is not None:
        print(f"Net liquidity proxy: {nl/1_000_000:.3f}T")
    if ch is not None:
        print(f"Net liquidity change: {ch/1000:+.1f}B")
    print(f"Trade stance: {model['stance']}")
    print()
    e=earnings_table().head(12)[["ticker","bucket","durability_score","adjusted_score"]]
    print("Top earnings-durability names")
    print(tabulate(e,headers="keys",tablefmt="github",showindex=False,floatfmt=".2f"))

if __name__=="__main__":
    main()

import yaml
from data_sources import load_snapshot
from model_engine import build_model, earnings_table

def test_mock_model_runs():
    cfg=yaml.safe_load(open("config.yaml"))
    d=load_snapshot(mock=True)
    m=build_model(d,cfg)
    assert "short_value" in m
    assert "medium_value" in m
    assert len(earnings_table()) >= 10

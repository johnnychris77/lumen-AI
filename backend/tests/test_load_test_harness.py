"""PERF-07 — unit coverage for the load-test harness's pure logic.

These tests exercise the deterministic pieces (percentiles, plan expansion,
summarization, scenario loading) without a live server, so the harness itself
is regression-covered in CI. The networked run is exercised manually against a
booted instance (see docs/production-readiness/perf-07-load-test/).
"""
import json
import types

import pytest

from scripts import load_test as lt


def test_percentile_empty_and_single():
    assert lt._percentile([], 95) == 0.0
    assert lt._percentile([42.0], 99) == 42.0


def test_percentile_interpolates_within_range():
    values = [float(i) for i in range(1, 101)]  # 1..100 sorted
    # p50 of 1..100 (nearest-rank interpolation) lands mid-range.
    assert 50.0 <= lt._percentile(values, 50) <= 51.0
    assert lt._percentile(values, 100) == 100.0
    assert lt._percentile(values, 0) == 1.0


def test_build_plan_expands_by_weight():
    scenario = [
        {"name": "a", "path": "/a", "weight": 1},
        {"name": "b", "path": "/b", "weight": 3},
    ]
    plan = lt._build_plan(scenario)
    assert len(plan) == 4
    assert sum(1 for e in plan if e["name"] == "b") == 3


def test_build_plan_rejects_empty():
    with pytest.raises(ValueError):
        lt._build_plan([])


def test_summarize_computes_rates_and_distribution():
    samples = [
        lt.Sample("health", 200, 10.0, True),
        lt.Sample("health", 200, 20.0, True),
        lt.Sample("health", 500, 30.0, False),
        lt.Sample("ready", 0, 40.0, False),  # transport failure
    ]
    args = types.SimpleNamespace(
        base_url="http://x", concurrency=4, duration=1.0, warmup=0.0
    )
    report = lt._summarize(args, [{"name": "health"}], samples, wall_elapsed=1.0)
    agg = report["aggregate"]
    assert agg["requests"] == 4
    assert agg["errors"] == 2
    assert agg["error_rate"] == 0.5
    assert agg["throughput_rps"] == 4.0
    # Per-endpoint breakdown separates the two names.
    assert report["endpoints"]["health"]["errors"] == 1
    assert report["endpoints"]["health"]["ok"] == 2
    assert report["endpoints"]["ready"]["error_rate"] == 1.0
    # Status 0 (transport failure) is retained in the status breakdown.
    assert report["endpoints"]["ready"]["status_counts"] == {"0": 1}


def test_load_scenario_default_when_none():
    assert lt._load_scenario(None) == lt.DEFAULT_SCENARIO


def test_load_scenario_reads_wrapped_list(tmp_path):
    f = tmp_path / "s.json"
    f.write_text(json.dumps({"scenario": [{"path": "/health"}]}))
    scenario = lt._load_scenario(str(f))
    assert scenario[0]["path"] == "/health"
    assert scenario[0]["name"] == "/health"  # name defaulted from path


def test_load_scenario_rejects_missing_path(tmp_path):
    f = tmp_path / "bad.json"
    f.write_text(json.dumps([{"weight": 2}]))
    with pytest.raises(ValueError):
        lt._load_scenario(str(f))

#!/usr/bin/env python3
"""PERF-07 — representative HTTP load-test harness for the LumenAI API.

This is the load tool the Phase-4 performance review recorded as *missing*
("no production-representative environment or load tool (locust/k6/wrk/ab)
available"). It is dependency-light — standard library plus ``httpx``, which
the backend already depends on — so it runs anywhere the app runs, including a
managed/production-representative environment when one is available.

What it does
------------
Drives concurrent HTTP traffic at a fixed concurrency against a running server,
for a fixed duration, following a weighted *scenario* (a list of requests). It
records per-request wall-clock latency and status, then reports throughput
(requests/second), error rate, and the latency distribution (mean, p50, p90,
p95, p99, max) both per-endpoint and in aggregate.

Honesty notes
-------------
- This harness measures whatever server you point ``--base-url`` at. Numbers
  from a local single-process SQLite dev instance are NOT production figures:
  they characterize framework + connection-pool + DB-round-trip overhead on
  this box, not a multi-replica deployment on managed Postgres. Always record
  the target environment alongside the numbers (this tool stamps it into the
  JSON output).
- The default scenario uses only ``/health`` (liveness; pure ASGI + app
  overhead) and ``/ready`` (readiness; includes a real ``SELECT 1`` DB
  round-trip). Both return 200 on any booted instance with no seeded data, so
  the default run is reproducible everywhere. Authenticated, data-dependent
  endpoints belong in a scenario file pointed at a seeded environment (see
  ``--scenario`` and ``scripts/load_scenarios/``).

Usage
-----
    # Default scenario against a locally running server:
    python scripts/load_test.py --base-url http://127.0.0.1:8000 \
        --concurrency 32 --duration 20

    # Custom weighted scenario (JSON) with a bearer token for auth routes:
    python scripts/load_test.py --base-url https://staging.example \
        --scenario scripts/load_scenarios/read_mixed.json \
        --auth-token "$DEV_AUTH_TOKEN" --concurrency 64 --duration 60 \
        --out results.json

Exit code is 0 on success, or 1 if the observed error rate exceeds
``--max-error-rate`` (default 0.01) — so it can gate CI or a release check.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import sys
import time
from dataclasses import dataclass, field

import httpx

# The default scenario: reproducible on any booted instance, no seed data.
# Weights are relative; here readiness (DB round-trip) is exercised as often as
# liveness so the default run touches the connection pool, not just the ASGI
# layer.
DEFAULT_SCENARIO: list[dict] = [
    {"name": "health", "method": "GET", "path": "/health", "weight": 1, "auth": False},
    {"name": "ready", "method": "GET", "path": "/ready", "weight": 1, "auth": False},
]


@dataclass
class Sample:
    name: str
    status: int
    latency_ms: float
    ok: bool


@dataclass
class EndpointStats:
    name: str
    latencies: list[float] = field(default_factory=list)
    ok: int = 0
    errors: int = 0
    status_counts: dict[int, int] = field(default_factory=dict)


def _percentile(sorted_values: list[float], pct: float) -> float:
    """Nearest-rank percentile on an already-sorted, non-empty list."""
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return sorted_values[0]
    rank = pct / 100.0 * (len(sorted_values) - 1)
    lo = int(rank)
    hi = min(lo + 1, len(sorted_values) - 1)
    frac = rank - lo
    return sorted_values[lo] + (sorted_values[hi] - sorted_values[lo]) * frac


def _build_plan(scenario: list[dict]) -> list[dict]:
    """Expand a weighted scenario into a flat round-robin request plan."""
    plan: list[dict] = []
    for entry in scenario:
        weight = max(1, int(entry.get("weight", 1)))
        for _ in range(weight):
            plan.append(entry)
    if not plan:
        raise ValueError("Scenario is empty — nothing to request.")
    return plan


async def _worker(
    client: httpx.AsyncClient,
    plan: list[dict],
    deadline: float,
    auth_header: dict[str, str],
    samples: list[Sample],
    counter: list[int],
) -> None:
    """One concurrent virtual user: fire requests until the deadline."""
    plan_len = len(plan)
    while time.monotonic() < deadline:
        idx = counter[0] % plan_len
        counter[0] += 1
        entry = plan[idx]
        headers = auth_header if entry.get("auth") else None
        method = entry.get("method", "GET").upper()
        path = entry["path"]
        body = entry.get("json")
        start = time.perf_counter()
        try:
            resp = await client.request(method, path, headers=headers, json=body)
            latency_ms = (time.perf_counter() - start) * 1000.0
            ok = 200 <= resp.status_code < 400
            samples.append(Sample(entry["name"], resp.status_code, latency_ms, ok))
        except Exception:
            latency_ms = (time.perf_counter() - start) * 1000.0
            # Status 0 == transport/connection failure (timeout, refused, reset).
            samples.append(Sample(entry["name"], 0, latency_ms, False))


async def _run(args: argparse.Namespace, scenario: list[dict]) -> dict:
    plan = _build_plan(scenario)
    auth_header = {"Authorization": f"Bearer {args.auth_token}"} if args.auth_token else {}
    samples: list[Sample] = []
    counter = [0]

    limits = httpx.Limits(
        max_connections=args.concurrency,
        max_keepalive_connections=args.concurrency,
    )
    timeout = httpx.Timeout(args.timeout)
    async with httpx.AsyncClient(
        base_url=args.base_url, limits=limits, timeout=timeout
    ) as client:
        # Warmup — connect, JIT any lazy imports, fill the pool. Discarded.
        if args.warmup > 0:
            warm_deadline = time.monotonic() + args.warmup
            warm: list[Sample] = []
            await asyncio.gather(*[
                _worker(client, plan, warm_deadline, auth_header, warm, [0])
                for _ in range(args.concurrency)
            ])

        wall_start = time.perf_counter()
        deadline = time.monotonic() + args.duration
        await asyncio.gather(*[
            _worker(client, plan, deadline, auth_header, samples, counter)
            for _ in range(args.concurrency)
        ])
        wall_elapsed = time.perf_counter() - wall_start

    return _summarize(args, scenario, samples, wall_elapsed)


def _summarize(
    args: argparse.Namespace,
    scenario: list[dict],
    samples: list[Sample],
    wall_elapsed: float,
) -> dict:
    per_endpoint: dict[str, EndpointStats] = {}
    for s in samples:
        st = per_endpoint.setdefault(s.name, EndpointStats(name=s.name))
        st.latencies.append(s.latency_ms)
        st.status_counts[s.status] = st.status_counts.get(s.status, 0) + 1
        if s.ok:
            st.ok += 1
        else:
            st.errors += 1

    def _dist(latencies: list[float]) -> dict:
        s = sorted(latencies)
        return {
            "count": len(s),
            "mean_ms": round(statistics.fmean(s), 2) if s else 0.0,
            "p50_ms": round(_percentile(s, 50), 2),
            "p90_ms": round(_percentile(s, 90), 2),
            "p95_ms": round(_percentile(s, 95), 2),
            "p99_ms": round(_percentile(s, 99), 2),
            "max_ms": round(s[-1], 2) if s else 0.0,
        }

    total = len(samples)
    total_errors = sum(st.errors for st in per_endpoint.values())
    error_rate = (total_errors / total) if total else 1.0

    endpoints = {}
    for name, st in per_endpoint.items():
        d = _dist(st.latencies)
        d["ok"] = st.ok
        d["errors"] = st.errors
        d["error_rate"] = round(st.errors / len(st.latencies), 4) if st.latencies else 1.0
        d["status_counts"] = {str(k): v for k, v in sorted(st.status_counts.items())}
        endpoints[name] = d

    return {
        "target": {
            "base_url": args.base_url,
            "concurrency": args.concurrency,
            "duration_s": args.duration,
            "warmup_s": args.warmup,
        },
        "note": (
            "Numbers reflect the pointed-at server only. A local single-process "
            "SQLite instance is NOT production-representative."
        ),
        "aggregate": {
            "requests": total,
            "wall_seconds": round(wall_elapsed, 3),
            "throughput_rps": round(total / wall_elapsed, 2) if wall_elapsed else 0.0,
            "errors": total_errors,
            "error_rate": round(error_rate, 4),
            **_dist([s.latency_ms for s in samples]),
        },
        "endpoints": endpoints,
        "scenario": scenario,
    }


def _print_report(report: dict) -> None:
    agg = report["aggregate"]
    tgt = report["target"]
    print()
    print("=" * 72)
    print("LumenAI load test — PERF-07 harness")
    print("=" * 72)
    print(f"Target       : {tgt['base_url']}")
    print(f"Concurrency  : {tgt['concurrency']}   Duration: {tgt['duration_s']}s"
          f"   Warmup: {tgt['warmup_s']}s")
    print(f"Requests     : {agg['requests']}   Wall: {agg['wall_seconds']}s"
          f"   Throughput: {agg['throughput_rps']} req/s")
    print(f"Errors       : {agg['errors']}   Error rate: {agg['error_rate']*100:.2f}%")
    print("-" * 72)
    print("Aggregate latency (ms):")
    print(f"  mean={agg['mean_ms']}  p50={agg['p50_ms']}  p90={agg['p90_ms']}"
          f"  p95={agg['p95_ms']}  p99={agg['p99_ms']}  max={agg['max_ms']}")
    print("-" * 72)
    print(f"{'endpoint':<18}{'reqs':>7}{'err':>6}{'p50':>9}{'p95':>9}{'p99':>9}{'max':>9}")
    for name, d in report["endpoints"].items():
        print(f"{name:<18}{d['count']:>7}{d['errors']:>6}"
              f"{d['p50_ms']:>9}{d['p95_ms']:>9}{d['p99_ms']:>9}{d['max_ms']:>9}")
    print("=" * 72)
    print(f"NOTE: {report['note']}")
    print()


def _load_scenario(path: str | None) -> list[dict]:
    if not path:
        return DEFAULT_SCENARIO
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    scenario = data["scenario"] if isinstance(data, dict) and "scenario" in data else data
    if not isinstance(scenario, list) or not scenario:
        raise ValueError(f"Scenario file {path} must contain a non-empty list of requests.")
    for entry in scenario:
        entry.setdefault("name", entry.get("path", "req"))
        if "path" not in entry:
            raise ValueError(f"Scenario entry missing 'path': {entry}")
    return scenario


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="LumenAI HTTP load-test harness (PERF-07)")
    p.add_argument("--base-url", default="http://127.0.0.1:8000",
                   help="Server under test (default: http://127.0.0.1:8000)")
    p.add_argument("--concurrency", type=int, default=16, help="Concurrent virtual users")
    p.add_argument("--duration", type=float, default=15.0, help="Measurement seconds")
    p.add_argument("--warmup", type=float, default=2.0, help="Warmup seconds (discarded)")
    p.add_argument("--timeout", type=float, default=30.0, help="Per-request timeout seconds")
    p.add_argument("--scenario", help="Path to a JSON scenario file (default: built-in)")
    p.add_argument("--auth-token", default="", help="Bearer token for auth-flagged requests")
    p.add_argument("--out", help="Write the full JSON report to this path")
    p.add_argument("--max-error-rate", type=float, default=0.01,
                   help="Exit non-zero if error rate exceeds this (default 0.01)")
    args = p.parse_args(argv)

    scenario = _load_scenario(args.scenario)
    report = asyncio.run(_run(args, scenario))
    _print_report(report)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        print(f"Wrote JSON report to {args.out}")

    error_rate = report["aggregate"]["error_rate"]
    if error_rate > args.max_error_rate:
        print(f"FAIL: error rate {error_rate*100:.2f}% exceeds "
              f"threshold {args.max_error_rate*100:.2f}%", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

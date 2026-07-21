# Load-test scenarios

Scenario files for `scripts/load_test.py` (PERF-07 harness). A scenario is a
weighted list of HTTP requests the harness drives concurrently.

## Format

A JSON file that is either a bare list of request entries, or an object with a
`"scenario"` key wrapping that list. Each entry:

| Field | Required | Default | Meaning |
| --- | --- | --- | --- |
| `path` | yes | — | Request path, appended to `--base-url`. |
| `name` | no | `path` | Label used in the per-endpoint report. |
| `method` | no | `GET` | HTTP method. |
| `weight` | no | `1` | Relative frequency (integer ≥ 1). |
| `auth` | no | `false` | If true, send `Authorization: Bearer <--auth-token>`. |
| `json` | no | — | Request body for POST/PUT/PATCH. |

## Files

- `read_mixed.json` — read-mostly template mixing the two unauthenticated
  probes with two authenticated list endpoints. The authenticated entries
  require a **seeded** environment and a valid `--auth-token`; point it at
  staging, not a bare local instance.

## Example

```bash
python scripts/load_test.py \
  --base-url https://staging.example \
  --scenario scripts/load_scenarios/read_mixed.json \
  --auth-token "$DEV_AUTH_TOKEN" \
  --concurrency 64 --duration 60 --out results.json
```

See `docs/production-readiness/perf-07-load-test/LOAD_TEST_REPORT.md` for the
full harness description, measured baseline, and the honest scope of what the
numbers do and do not represent.

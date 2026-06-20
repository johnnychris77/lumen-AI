# LumenAI Inspection Ranking Engine — Architecture

**Version:** 1.0  
**Milestone:** P3 — AI-Powered Inspection Ranking Engine  
**Status:** Production-Ready

---

## Overview

The Inspection Ranking Engine scores each surgical instrument inspection finding on a 0–100 scale using a deterministic, explainable algorithm. It produces a risk tier (Low / Medium / High / Critical), a baseline match percentage, a structured findings list, and a tamper-evident audit record.

---

## Detection Categories

| # | Category | Max Deduction |
|---|---|---|
| 1 | Blood / Retained Blood Residue | 30 |
| 2 | Bone / Bone Fragment | 28 |
| 3 | Tissue / Retained Tissue | 26 |
| 4 | Insulation Damage | 25 |
| 5 | Missing Component | 20 |
| 6 | Baseline Mismatch | 20 |
| 7 | Crack / Hairline Fracture | 22 |
| 8 | Corrosion / Surface Rust | 18 |
| 9 | Pitting | 15 |
| 10 | Debris / Retained Debris | 12 |

---

## Scoring Algorithm

```
base_score = 100
category_deduction = CATEGORY_WEIGHT × SEVERITY_MULTIPLIER
confidence_penalty  = 0–15  (based on AI confidence score)
identifier_bonus    = 0–5   (barcode / QR / KeyDot present)
baseline_bonus      = 0–10  (approved baseline found and matched)

final_score = clamp(base_score − category_deduction − confidence_penalty
                    + identifier_bonus + baseline_bonus, 0, 100)
```

### Severity Multipliers

| Severity | Multiplier |
|---|---|
| Critical | 1.5× |
| High | 1.2× |
| Medium | 1.0× |
| Low | 0.6× |

### Risk Tiers

| Score Range | Risk Level |
|---|---|
| 80–100 | Low |
| 60–79 | Medium |
| 40–59 | High |
| 0–39 | Critical |

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/enterprise/ranking/score` | Compute score for a finding |
| `GET` | `/api/enterprise/ranking/history/{finding_id}` | Re-score stored finding |
| `GET` | `/api/enterprise/ranking/kpi-summary` | Dashboard KPI aggregation |

### POST /api/enterprise/ranking/score

**Request** (`RankingRequest`):
```json
{
  "finding_category": "blood / retained blood residue",
  "severity": "critical",
  "confidence_score": 0.85,
  "barcode_value": "STRYKER-FRAZ-8FR-001",
  "baseline_status": "approved_baseline_found",
  "instrument_match_status": "matched"
}
```

**Response** (`RankingResult`):
```json
{
  "inspection_score": 37,
  "risk_level": "Critical",
  "baseline_match_pct": 85.0,
  "findings": [{"category": "blood / retained blood residue", "severity": "critical", "score_deduction": 45, "rationale": "..."}],
  "recommended_action": "Immediate quarantine, notify infection control, initiate CAPA",
  "ranking_mode": "Baseline-confirmed ranking",
  "final_ranking_allowed": true,
  "audit_evidence": {
    "ranking_mode": "Baseline-confirmed ranking",
    "baseline_review_required": false,
    "final_ranking_allowed": true,
    "baseline_review_reason": "Approved baseline matched.",
    "identifier_match": {"barcode": "matched"},
    "scoring_breakdown": {"base_score": 100, "category_deduction": 45, "confidence_penalty": 0, "identifier_bonus": 2, "baseline_bonus": 10, "final_score": 67}
  }
}
```

---

## Baseline Contract Integration

The engine delegates baseline classification to `app/core/baseline_ranking_contract.py`, which resolves one of four ranking modes:

| Mode | Condition |
|---|---|
| Baseline-confirmed ranking | `approved_baseline_found` + instrument `matched` |
| Provisional ranking | `pending_baseline_review` |
| Manual review required | `no_approved_baseline` or `baseline_not_available` |
| Pending baseline check | Any other status |

---

## Audit Evidence

Every `RankingResult` includes a full `audit_evidence` block:

- `ranking_mode` — which of the four contract modes applied
- `baseline_review_required` — whether human review is needed before finalization
- `final_ranking_allowed` — whether the score can be used for disposition
- `identifier_match` — which of barcode / QR / KeyDot were present
- `scoring_breakdown` — full numeric decomposition for explainability

---

## File Locations

| File | Purpose |
|---|---|
| `backend/app/schemas/ranking.py` | Pydantic I/O schemas |
| `backend/app/services/ranking_engine.py` | Core scoring logic |
| `backend/app/routes/ranking.py` | FastAPI router (3 endpoints) |
| `backend/tests/test_ranking_engine.py` | 41 unit + integration tests |

---

## Test Coverage

```
41 tests / 41 passed
- Unit: category deduction, severity multiplier, confidence penalty, identifier bonus, risk level mapping
- Integration: score_inspection() function, all edge cases (min/max score, boundary tiers)
- API: all 3 endpoints, validation (422 on bad input), 404 on missing finding
```

---

## Recommended Action Rules

| Risk Level | Finding Type | Recommended Action |
|---|---|---|
| Critical | Blood / Bone / Tissue | Immediate quarantine, notify infection control, initiate CAPA |
| Critical | Insulation / Crack | Remove from service immediately, return to manufacturer |
| Critical | Other | Immediate quarantine, escalate to SPD supervisor and quality team |
| High | Any | Quarantine, reclean with enhanced protocol, second inspection required |
| Medium | Any | Flag for additional inspection, document findings, monitor trend |
| Low | Any | Document and monitor; re-inspect at next scheduled maintenance |

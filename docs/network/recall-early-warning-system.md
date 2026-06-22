# LumenAI Recall Early Warning System

> **Audience:** SPD leadership, quality, and patient safety teams. Defines how LumenAI surfaces aggregated anomaly signals that may precede formal recall announcements — as candidate indicators requiring human review, not causation findings. No FDA/regulatory claims.

---

## 1. Purpose

Detect recurring defect, contamination, or failure patterns across the network before a formal FDA/manufacturer recall is announced — giving facilities early visibility to investigate and act. All signals are **candidate indicators** that must be human-reviewed by a network steward before any escalation or external notification.

---

## 2. Signal Detection Architecture

```
facility inspection data (anonymized, aggregated)
        ↓
anomaly detection scan (scheduled / manual)
        ↓
signal surfaced if n_facilities >= 3 (internal floor)
        ↓
human review required (network steward)
        ↓
decision: escalate / monitor / close / suppress
        ↓
(if escalated) → steward notifies appropriate parties
```

The automated system **only surfaces and categorizes signals**. It never autonomously notifies external parties, triggers recalls, or contacts manufacturers.

---

## 3. Signal Structure

| Field | Description |
|-------|-------------|
| `signal_ref` | Internal reference (e.g., REW-2026-A3F7B2) |
| `instrument_category` | Category level (never specific model in published data) |
| `manufacturer_pseudonym` | Anonymized — internal mapping is governance-controlled |
| `finding_type` | contamination / defect / failure / corrosion |
| `anomaly_score` | 0.0–1.0; higher = stronger signal |
| `n_facilities_reporting` | Must be ≥ 3 to surface internally |
| `warning_level` | watch / advisory / alert |
| `trend` | increasing / stable / decreasing |
| `human_review_required` | Always `true` on creation |

---

## 4. Warning Levels

| Level | Meaning | Action |
|-------|---------|--------|
| `watch` | Early pattern; low anomaly score | Monitor; re-scan next cycle |
| `advisory` | Consistent pattern; moderate score | Steward review; consider facility notification |
| `alert` | Strong, growing signal; high anomaly score | Priority steward review; escalation eligible |

---

## 5. Human Review Decisions

| Decision | Outcome |
|----------|---------|
| `monitor` | Status → `under_review`; signal tracked in next anomaly run |
| `escalate` | Status → `escalated`; steward decision recorded; steward notifies appropriate parties outside the system |
| `close` | Status → `closed`; signal resolved / pattern explained |
| `suppress` | Status → `suppressed`; signal was a false pattern |

---

## 6. Manufacturer Intelligence Profiles

Aggregated at the manufacturer-category level (pseudonymized, k-floor of 5). Profiles include:

- Network defect rate, pass rate, repair rate
- Open early warnings count
- Formal recall count
- Intelligence grade (A–F) based on aggregated performance

---

## 7. Endpoints

| Endpoint | Purpose |
|----------|---------|
| `POST /api/network-intelligence/recall-early-warning` | Surface a new warning signal |
| `GET /api/network-intelligence/recall-early-warning` | List active signals |
| `POST /api/network-intelligence/recall-early-warning/{id}/review` | Human review decision |
| `POST /api/network-intelligence/anomaly-detection/run` | Log a detection scan |
| `GET /api/network-intelligence/anomaly-detection/runs` | Detection run history |
| `POST /api/network-intelligence/manufacturer-intelligence` | Publish manufacturer profile (k-floor enforced) |
| `GET /api/network-intelligence/manufacturer-intelligence` | List profiles |

---

## 8. Governance & Claims Discipline

| Principle | Enforcement |
|-----------|-------------|
| Candidate signals only | No automated external notification; steward decision required |
| No causation | Signals are "potential association" / "investigation candidate" — never causation |
| Anonymization | Manufacturer and facility pseudonyms; k-anonymity floor |
| Human review | `human_review_required: true` on all new signals |
| Audit trail | Every signal creation, review, and escalation is compliance-flagged |
| No FDA claims | LumenAI does not submit to or act on behalf of FDA |
| Steward accountability | Escalated signals carry `reviewed_by` and `reviewed_at` |

---

*LumenAI does not claim FDA clearance or regulatory approval. All recall early warning signals are candidate indicators requiring human review. LumenAI does not submit adverse event reports to FDA — that determination rests with qualified medical device professionals at the facility.*

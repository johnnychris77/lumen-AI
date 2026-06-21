# Quality Intelligence Governance Framework
## P21 — Human Oversight, Escalation, and Auditability

**Effective:** 2026-06-21  
**Applies to:** All P21 intelligence outputs including signals, investigations, recommendations, and executive summaries  
**Principle:** Association is not causation. Human review is always required.

---

## 1. Human Oversight Requirements

All intelligence outputs from the P21 system are advisory. The system does not make,
confirm, or execute any clinical or operational decision autonomously.

**Mandatory human oversight applies to:**

- Every EmergingRiskSignal (human_review_required: True, hardcoded)
- Every QualityInvestigationP21 (human_review_required: True, hardcoded)
- Every PreventiveActionRecommendation (status: pending_review until human acts)
- Every executive summary and dashboard KPI

**No signal, recommendation, or investigation may be acted upon without human review.**

The `human_review_required` field is enforced at the model layer (non-nullable, default=True)
and validated in all API responses.

---

## 2. Escalation Process

### Tier Definitions

| Confidence Score | Tier   | Escalation Path                                     |
|-----------------|--------|-----------------------------------------------------|
| < 0.4           | Low    | Quality analyst review; 5-business-day SLA          |
| 0.4 – 0.7       | Medium | Quality director notification; 48-hour SLA          |
| > 0.7           | High   | Quality director + CNO notification; 24-hour SLA    |

**All tiers require human review.** High confidence does not mean confirmed risk.
Confidence scores are statistical estimates with associated disclaimer on every response.

### Escalation Steps

1. Signal detected → status: open → audit log entry created
2. Quality analyst assigned → investigation opened (status: open)
3. Investigation updated to in_progress → quality director notified
4. Evidence gathered → evidence_notes populated
5. Human determination made → investigation resolved/closed + resolution_notes required
6. If escalated: CNO/executive review via executive-summary endpoint
7. All escalation steps produce audit log entries

---

## 3. Recommendation Review Workflow

```
Recommendation Created (status: pending_review)
         │
         ▼
Quality Director Reviews
         │
    ┌────┴────┐
    │         │
    ▼         ▼
Accepted   Rejected
    │         │
    ▼         ▼
status:    status:
accepted   rejected
    │
    ▼
Implementation (human-led)
    │
    ▼
effectiveness_score populated (post-implementation)
status: implemented
```

**All status transitions require:**
- reviewed_by field populated (human actor identity)
- reviewed_at timestamp recorded
- Audit log entry created

**API:** `POST /api/intelligence/recommendations/{id}/review`  
Body: `{ "action": "accepted" | "rejected", "reviewed_by": "<human actor>" }`

---

## 4. Confidence Thresholds

| Range     | Label  | Meaning                                                        |
|-----------|--------|----------------------------------------------------------------|
| 0.0 – 0.39 | Low   | Weak statistical pattern; review recommended as precaution    |
| 0.4 – 0.70 | Medium| Moderate pattern strength; quality review required            |
| 0.71 – 1.0 | High  | Stronger pattern signal; expedited human review required      |

**Disclaimer applied to all scores:**
> "Confidence scores are statistical estimates and do not confirm or establish causation.
> Human review is required before any clinical or operational decision."

This disclaimer appears on every API response containing confidence_score values.

---

## 5. Auditability

Every signal detection, investigation action, and recommendation review creates an audit
log entry via `log_audit_event()`. The audit log captures:

- tenant_id and tenant_name
- actor_email (authenticated human user)
- action_type (e.g., intelligence.signals.list, intelligence.investigations.create)
- resource_type and resource_id
- Timestamp (server-side)
- Details payload (signal counts, priority, action taken)

**Audit log entries are immutable.** They are append-only and cannot be modified via API.

Covered action types:
- `intelligence.signals.list`
- `intelligence.emerging_risks.list`
- `intelligence.investigations.list`
- `intelligence.investigations.create`
- `intelligence.investigations.update`
- `intelligence.recommendations.list`
- `intelligence.recommendations.accepted`
- `intelligence.recommendations.rejected`
- `intelligence.executive_summary.view`
- `intelligence.analysis.run`
- `intelligence.risk_graph.view`
- `intelligence.dashboard.view`

---

## 6. Explainability

Every EmergingRiskSignal must include a non-null `association_reason` field. This field:

- Explains the statistical basis for the signal in plain language
- Uses association-not-causation language explicitly
- References the signal_type and quality pattern observed
- States that human review is required before any determination

**Example:**
> "Elevated frequency of contamination review candidates observed across multiple inspection
> cycles; flagged as an emerging signal for quality review. Association is not causation —
> human review required."

The `association_reason` field is tested at the API response level and enforced in all
service functions that generate or return signals.

---

## 7. Appeal and Override Mechanism

### Dismissing Signals

Signals may be dismissed by a human quality reviewer via status update:
- `EmergingRiskSignal.status` may be set to `dismissed` by an authorized human actor
- Dismissal requires a reason captured in the linked investigation's resolution_notes
- Audit log entry is created for the dismissal action

### Rejecting Recommendations

Recommendations may be rejected by a human quality director:
- `POST /api/intelligence/recommendations/{id}/review` with `action: rejected`
- reviewed_by and reviewed_at are recorded
- Rejected recommendations do not auto-regenerate; a new analysis run is required

### Overriding Investigation Priority

Investigation priority may be updated at any time by an authorized human actor via:
- `PATCH /api/intelligence/investigations/{id}` with `priority` field
- Audit log records the actor and timestamp of every priority change

### Governance Safeguards

- No API endpoint allows setting `human_review_required` to False
- No API endpoint allows marking a signal as "confirmed causation"
- The system never generates reports or communications autonomously
- All outputs include disclaimer language enforced at the service layer

---

## 8. Prohibited Language

The following terms are prohibited in all intelligence outputs:

| Prohibited          | Use Instead                            |
|--------------------|----------------------------------------|
| caused              | potential association                  |
| led to              | emerging signal                        |
| resulted in         | review recommended                     |
| responsible for     | investigation candidate                |
| confirmed risk      | elevated risk (requires human review)  |
| proven correlation  | statistical pattern observed           |

Automated tests in `test_p21_quality_intelligence.py` enforce this policy on every
API response.

# Project Sage — Adaptive Learning Plans

LumenAI AI Specialist, Section 5, and Educator/Supervisor Workspace
(Section 12).

## Approval gate

A `SageLearningPlan` is created with `approved_by = ""`. It is not visible
to its learner via `/api/sage/my-learning` until an authorized educator,
supervisor, or manager calls `POST /api/sage/learning-plans/{id}/approve` --
mirrors Vulcan's `recommended_disposition`/`final_disposition` split:
Sage's own recommendation never becomes an assigned plan on its own.

## Override reason required for high-confidence recommendations

`sage_learning_plan_service.reject_or_edit_learning_plan` raises
`OverrideReasonRequiredError` if the plan's own `confidence == "high"` and no
`override_reason` is supplied — enforced in the service layer, not just
documented in the brief.

## Plan fields (Section 5)

learner or group, identified need, supporting evidence, learning objective,
instrument family, anatomy zone, finding category, education content,
practice activity, return demonstration, evaluator, due date, completion
status, effectiveness review — every field the brief names is a real column
on `SageLearningPlan`.

## API

```
POST /api/sage/learning-plans
POST /api/sage/learning-plans/{id}/approve
POST /api/sage/learning-plans/{id}/reject-or-edit
POST /api/sage/learning-plans/{id}/complete
GET  /api/sage/learning-plans
GET  /api/sage/learning-plans/{id}
```

All leadership-only. A technician's own approved plans are only reachable
via `GET /api/sage/my-learning`, which resolves the learner from the
authenticated identity.

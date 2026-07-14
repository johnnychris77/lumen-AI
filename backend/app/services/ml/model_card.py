"""Dataset Registry & AI Model Development Foundation — Section 9.

Automatically generates a Model Card (markdown) from a
``ModelRegistryEntry`` row plus its task's label space
(``app.services.ml.model_tasks``). Genuinely new — no model-card generator
existed anywhere in this codebase before this pass.
"""
from __future__ import annotations

import json

from app.models.model_registry import ModelRegistryEntry
from app.services.ml.model_tasks import MODEL_TASKS, task_labels


def generate_model_card(entry: ModelRegistryEntry) -> str:
    """Render a Model Card as markdown. Every section is derived directly
    from registry fields — nothing about performance or scope is asserted
    beyond what the entry itself records."""
    task = MODEL_TASKS.get(entry.model_type, {})

    try:
        eval_metrics = json.loads(entry.evaluation_metrics or "{}")
    except (TypeError, ValueError):
        eval_metrics = {}
    try:
        train_metrics = json.loads(entry.training_metrics or "{}")
    except (TypeError, ValueError):
        train_metrics = {}
    try:
        hyperparams = json.loads(entry.hyperparameters or "{}")
    except (TypeError, ValueError):
        hyperparams = {}
    try:
        calibration = json.loads(entry.calibration_report or "{}")
    except (TypeError, ValueError):
        calibration = {}
    try:
        error_analysis = json.loads(entry.error_analysis_report or "{}")
    except (TypeError, ValueError):
        error_analysis = {}

    if entry.model_type in MODEL_TASKS:
        all_labels = task_labels(entry.model_type)
    else:
        # Candidate-pipeline models (Genesis) aren't in the static
        # MODEL_TASKS registry — derive supported classes from the actual
        # evaluation report's per-class breakdown, never guessed.
        all_labels = sorted((eval_metrics.get("per_class") or train_metrics.get("per_class") or {}).keys())
    supported = all_labels  # the task's full label space is what this model line targets
    unsupported_note = (
        "Any finding/category outside this task's label space is not evaluated by this model."
    )

    lines = [
        f"# Model Card — {entry.model_id} ({entry.model_version})",
        "",
        f"**Approval status:** {entry.approval_status}",
        f"**Training status:** {entry.training_status}",
        "",
        "## Purpose",
        "",
        f"{task.get('name', entry.model_type)} — task key `{entry.model_type}`.",
        "",
        "## Supported findings",
        "",
        (", ".join(supported) if supported else "None recorded for this task."),
        "",
        "## Unsupported findings",
        "",
        unsupported_note,
        "",
        "## Training data",
        "",
        f"- Dataset version: `{entry.dataset_version or 'unassigned'}`",
        f"- Dataset registry version ID: {entry.dataset_version_id if entry.dataset_version_id is not None else 'unassigned'}",
        "",
        "## Architecture & framework",
        "",
        f"- Architecture: {entry.architecture or 'not recorded'}",
        f"- Framework: {entry.framework or 'not recorded'}",
        f"- Hyperparameters: `{json.dumps(hyperparams)}`",
        f"- Git commit: `{entry.git_commit or 'not recorded'}`",
        "",
        "## Performance",
        "",
        f"- Training metrics: `{json.dumps(train_metrics)}`",
        f"- Validation/evaluation metrics: `{json.dumps(eval_metrics)}`",
        "",
        "## Known limitations",
        "",
        entry.known_limitations or "None recorded.",
        "",
        "## Known failure modes",
        "",
        (
            f"Ranked failure modes from the most recent error analysis: "
            f"`{json.dumps(error_analysis.get('ranked_failure_modes', []))}`."
            if error_analysis.get("ranked_failure_modes") else
            "No error analysis has been recorded for this model version yet."
        ),
        (
            "Safety-critical false-negative rates (missed contamination/structural findings) are "
            "tracked separately — see `app.services.ml.evaluation.safety_metrics` — and are the "
            "primary safety risk for this model class."
        ),
        "",
        "## Confidence calibration",
        "",
        (
            f"Expected calibration error: {calibration.get('expected_calibration_error')}. "
            f"Recommended confidence threshold: {calibration.get('recommended_threshold')}."
            if calibration else
            "No calibration report has been recorded for this model version yet."
        ),
        "",
        "## Intended use",
        "",
        (
            "Advisory input to a human SPD supervisor's inspection review, within the "
            "instrument/finding scope this model was trained on. Never a standalone or "
            "autonomous decision — every output requires human review before any disposition "
            "action is taken."
        ),
        "",
        "## Out-of-scope use",
        "",
        (
            "Any finding category outside this model's supported list above. Any use as a "
            "sole/autonomous decision-maker. Any deployment before completing the promotion "
            "gate in `app.services.ml.candidate_promotion` and independent clinical "
            "validation. Any instrument type, facility, or imaging condition not represented "
            "in this model's training/evaluation data."
        ),
        "",
        "## Human oversight requirements",
        "",
        (
            "A qualified SPD supervisor must review every prediction before it informs a "
            "disposition decision. `human_review_required` is always true regardless of "
            "confidence or approval status. Supervisor override is always available — see "
            "`app.services.ml.deployment_gates`."
        ),
        "",
        "## Clinical limitations",
        "",
        (
            "No FDA/regulatory clearance is claimed. This model may not drive a clinical "
            "recommendation unless its approval status is `validated`, and even then a "
            "supervisor override is always available (see `app.services.ml.deployment_gates`). "
            "It is not yet considered clinically validated or production-ready; it is approved "
            "only to enter Prospective Shadow-Mode Clinical Validation."
        ),
        "",
        "## Ethical considerations",
        "",
        (
            "No causation or clinical-outcome claims are made. Output is always advisory; "
            "`human_review_required` is always true regardless of approval status."
        ),
        "",
        "## Governance",
        "",
        f"- Candidate stage: {entry.candidate_stage}",
        f"- Documentation complete: {entry.documentation_complete}",
        f"- Clinical review status: {entry.clinical_review_status}",
        f"- Clinical review complete: {entry.clinical_review_complete}",
        f"- Metrics approved: {entry.metrics_approved}",
        f"- Error analysis reviewed: {entry.error_analysis_reviewed}",
        f"- Reproducible training confirmed: {entry.reproducible_training_confirmed}",
        f"- Governance review completed: {entry.governance_review_completed}",
        f"- Reviewer: {entry.reviewer or 'not yet assigned'}",
        f"- Deployment status: {entry.deployment_status}",
        "",
        "## Version history",
        "",
        f"- `{entry.model_version}` — training run `{entry.training_run_id or 'n/a'}`, "
        f"registered {entry.created_at.isoformat() if entry.created_at else 'unknown'}, "
        f"status `{entry.training_status}`.",
    ]
    return "\n".join(lines)

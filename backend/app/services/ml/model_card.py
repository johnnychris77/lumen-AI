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
    all_labels = task_labels(entry.model_type) if entry.model_type in MODEL_TASKS else []
    supported = all_labels  # the task's full label space is what this model line targets
    unsupported_note = (
        "Any finding/category outside this task's label space is not evaluated by this model."
    )

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
            "Safety-critical false-negative rates (missed contamination/structural findings) are "
            "tracked separately — see `app.services.ml.evaluation.safety_metrics` — and are the "
            "primary safety risk for this model class."
        ),
        "",
        "## Ethical considerations",
        "",
        (
            "No causation or clinical-outcome claims are made. Output is always advisory; "
            "`human_review_required` is always true regardless of approval status."
        ),
        "",
        "## Clinical limitations",
        "",
        (
            "No FDA/regulatory clearance is claimed. This model may not drive a clinical "
            "recommendation unless its approval status is `validated`, and even then a "
            "supervisor override is always available (see `app.services.ml.deployment_gates`)."
        ),
        "",
        "## Governance",
        "",
        f"- Documentation complete: {entry.documentation_complete}",
        f"- Clinical review complete: {entry.clinical_review_complete}",
        f"- Metrics approved: {entry.metrics_approved}",
    ]
    return "\n".join(lines)

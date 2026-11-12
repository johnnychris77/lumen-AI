"""Research-only visual-feature benchmark orchestration.

Pipeline: provenance gate -> group-safe split (reused from the production
splitter) -> embedding extraction -> lightweight research classifier -> evaluation
against the GOVERNED observation labels -> metrics + model-card evidence, with a
fair comparison against the current Project Lens Pillow-feature baseline using the
same classifier.

Hard guarantees: the result is always ``research_only=True`` and
``clinical_promotion_eligible=False``; no output is a clinical result; nothing is
registered as a servable model. A low/absent grouping-reliability signal is
reported, never hidden.
"""
from __future__ import annotations

from typing import Any

from app.services.ml.dataset_split import grouping_is_reliable, split_dataset
from app.services.ml.training_execution import _feature_vector
from research.lens_vision.config import ResearchRunConfig
from research.lens_vision.embeddings import Embedder, StubEmbedder
from research.lens_vision.provenance import assert_research_authorized
from research.lens_vision.research_classifier import ResearchClassifier, accuracy


def _to_split_sample(s: dict) -> dict:
    return {
        "id": s["id"],
        "inspection_id": s.get("inspection_id"),
        "instrument_serial": s.get("instrument_serial") or None,
        "specimen_id": s.get("specimen_id") or None,
        "session_id": s.get("session_id") or None,
        "image_sha256": s.get("image_sha256") or None,
        "instrument_family": s.get("instrument_family", "unknown"),
        "anatomy_zone": s.get("anatomy_zone", "unknown"),
        "finding": s.get("label", "none"),
        "severity": "none",
        "manufacturer": s.get("manufacturer", "unknown"),
        "image_quality": s.get("image_quality", "unknown"),
    }


def run_research_benchmark(
    samples: list[dict],
    *,
    config: ResearchRunConfig,
    embedder: Embedder | None = None,
    allow_approved_clinical: bool = False,
    compare_baseline: bool = True,
) -> dict[str, Any]:
    """Execute the research benchmark and return a research-only result dict."""
    # 1) Provenance gate — only research-authorized inputs may enter.
    assert_research_authorized(samples, allow_approved_clinical=allow_approved_clinical)

    # 2) Group-safe split (reuse the production leakage-safe splitter).
    split = split_dataset([_to_split_sample(s) for s in samples], seed=str(config.seed), group_by_serial=True)
    assignments = split["assignments"]
    reliable = grouping_is_reliable(split)

    by_id = {s["id"]: s for s in samples}
    train = [by_id[i] for i, sp in assignments.items() if sp == "train" and i in by_id]
    test = [by_id[i] for i, sp in assignments.items() if sp == "test" and i in by_id]

    classes = sorted({s["label"] for s in samples})
    emb = embedder or StubEmbedder()

    def _eval_with_features(feature_fn) -> float | None:
        Xtr, ytr, Xte, yte = [], [], [], []
        for s in train:
            v = feature_fn(s)
            if v is not None:
                Xtr.append(v)
                ytr.append(s["label"])
        for s in test:
            v = feature_fn(s)
            if v is not None:
                Xte.append(v)
                yte.append(s["label"])
        if len(set(ytr)) < 2 or not Xte:
            return None
        clf = ResearchClassifier(classes).fit(Xtr, ytr)
        return accuracy(yte, clf.predict(Xte))

    research_acc = _eval_with_features(lambda s: emb.embed(s.get("image_bytes")))
    baseline_acc = (
        _eval_with_features(lambda s: _feature_vector(s.get("image_bytes")))
        if compare_baseline else None
    )

    return {
        "research_only": True,
        "clinical_promotion_eligible": False,
        "status": "completed" if research_acc is not None else "insufficient_data",
        "embedder": emb.name,
        "checkpoint_id": config.checkpoint_id,
        "classes": classes,
        "split_counts": {k: len(v) for k, v in {"train": train, "test": test}.items()},
        "grouping_reliable": reliable,
        "ungrouped_sample_count": split.get("ungrouped_sample_count", 0),
        "metrics": {
            "research_embedding_accuracy": research_acc,
            "baseline_pillow_feature_accuracy": baseline_acc,
            "comparison_note": (
                "Experimental research metric on governed labels. NOT a clinical "
                "accuracy claim. Same classifier head; features differ "
                f"({emb.name} embeddings vs current Pillow baseline features)."
            ),
        },
        "config_fingerprint": config.fingerprint(),
        "note": "RESEARCH ONLY — not clinically validated; not servable; not promotable.",
    }

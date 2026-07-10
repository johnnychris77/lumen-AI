"""v4.4 — Project Catalyst, Section 7: Explainable Responses.

"Nothing is a black box" — every assistant response is required to carry
this exact envelope shape, imitating the trace-panel idiom
`app/agents/orchestrator.py` + `AgentTraceViewer.tsx` already established
for per-inspection pipeline runs (not reused directly, since that trace is
scoped to one inspection's agent pipeline, not a conversational answer,
but the same "show your work" principle applies here).
"""
from __future__ import annotations


def build_evidence_envelope(
    *, evidence_used: list[str], knowledge_sources: list[str], digital_twin_factors: list[str],
    workflow_rules: list[str], reasoning_path: list[str], confidence: float, references: list[dict],
) -> dict:
    return {
        "evidence_used": evidence_used,
        "knowledge_sources": knowledge_sources,
        "digital_twin_factors": digital_twin_factors,
        "workflow_rules": workflow_rules,
        "reasoning_path": reasoning_path,
        "confidence": confidence,
        "references": references,
        "human_review_required": True,
    }

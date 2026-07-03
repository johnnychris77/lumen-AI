"""Phase 23 §2 — Shared Clinical Context.

One immutable context object every module in the Clinical Intelligence
Operating System reads and (via `with_updates`) returns an updated copy
of. Frozen (pydantic `model_config = ConfigDict(frozen=True)`) so no
module can mutate another module's contribution in place — every "update"
is a new object, keeping the pipeline's data flow the same
append-only/traceable shape as the rest of the platform (audit events,
ground-truth labels, ledger entries — nothing here is ever edited after
the fact, only added to).

This composes (does not replace) the typed per-agent context objects from
Phase 22 (app/agents/context.py) — ClinicalContext is the single envelope
the CIOS orchestrator assembles from those agents' outputs so downstream
consumers (the ledger, the event bus, the certificate, the dashboard) have
one object to read instead of ten.
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict


class ClinicalContext(BaseModel):
    model_config = ConfigDict(frozen=True)

    inspection_id: int
    tenant_id: str

    instrument_type: str = ""
    manufacturer: str = ""
    model: str = ""
    instrument_family: str = ""

    anatomy_profile: dict = {}
    inspection_zones: list[str] = []

    coverage: dict = {}
    baseline: dict = {}

    findings: list[dict] = []
    severity: Optional[str] = None
    risk: dict = {}

    recommendation: dict = {}
    supervisor_review: dict = {}
    digital_twin: dict = {}
    knowledge_graph_links: dict = {}
    audit: dict = {}

    def with_updates(self, **kwargs) -> "ClinicalContext":
        """Return a new, updated ClinicalContext — the original is never
        mutated. Every module in the pipeline calls this instead of
        assigning to a field."""
        return self.model_copy(update=kwargs)

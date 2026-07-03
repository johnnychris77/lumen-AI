"""Phase 22 §9 — Continuous Learning Agent.

Reports the knowledge graph's confidence signals (Phase 21
learning_confidence) — knowledge confidence, reasoning confidence,
clinical recommendation confidence, zone confidence, and per-family
instrument profile confidence. Recomputed live from real supervisor
reviews and Phase 18 ground truth on every call — this agent does not
mutate a persisted model state or fabricate a training event.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.agents.context import LearningContext
from app.services.knowledge_graph_service import learning_confidence


class ContinuousLearningAgent:
    NAME = "Continuous Learning Agent"
    VERSION = "1.0.0"
    CAPABILITIES = ["report_knowledge_confidence", "report_reasoning_confidence", "report_instrument_profile_confidence"]
    DEPENDS_ON = ["SupervisorAgent"]

    def run(self, db: Session, tenant_id: str) -> LearningContext:
        confidence = learning_confidence(db, tenant_id)
        return LearningContext(
            knowledge_confidence=confidence["knowledge_confidence"],
            reasoning_confidence=confidence["reasoning_confidence"],
            clinical_recommendation_confidence=confidence["clinical_recommendation_confidence"],
            zone_confidence=confidence["zone_confidence"],
            sample_sizes=confidence["sample_sizes"],
            note=confidence["note"],
        )

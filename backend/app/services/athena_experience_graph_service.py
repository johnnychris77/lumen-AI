"""v4.8 — Project Athena, Section 3: Experience Graph.

Extends the Knowledge Graph with a genuinely new, persisted node/edge
structure — `knowledge_graph_service.py`'s `explore()`/`reasoning_chain()`
are real but recomputed-on-read aggregations with no node/edge tables.
The Finding -> Instrument -> Anatomy -> Recommendation segment of every
chain built here is populated by calling `reasoning_chain()` directly
rather than re-deriving that logic; only the new Person/Experience/
Outcome/Evidence/Organization node types are Athena's own.
"""
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.models.athena_knowledge import (
    DISCLAIMER,
    EDGE_EVIDENCE_OWNED_BY_ORG,
    EDGE_FOUND_ON_INSTRUMENT,
    EDGE_HAS_EXPERIENCE,
    EDGE_INSTRUMENT_HAS_ANATOMY,
    EDGE_LED_TO_RECOMMENDATION,
    EDGE_PRODUCED_OUTCOME,
    EDGE_SUPPORTED_BY_EVIDENCE,
    EDGE_YIELDED_FINDING,
    NODE_ANATOMY,
    NODE_EVIDENCE,
    NODE_EXPERIENCE,
    NODE_FINDING,
    NODE_INSTRUMENT,
    NODE_ORGANIZATION,
    NODE_OUTCOME,
    NODE_PERSON,
    NODE_RECOMMENDATION,
    ExperienceGraphEdge,
    ExperienceGraphNode,
)
from app.services.knowledge_graph_service import reasoning_chain


def _node(db: Session, tenant_id: str, node_type: str, label: str, *, source_type: str = "",
          source_id: int | None = None, details: dict | None = None) -> ExperienceGraphNode:
    row = ExperienceGraphNode(
        tenant_id=tenant_id, node_type=node_type, label=label, source_type=source_type,
        source_id=source_id, details_json=json.dumps(details or {}),
    )
    db.add(row)
    db.flush()
    return row


def _edge(db: Session, tenant_id: str, from_node: ExperienceGraphNode, to_node: ExperienceGraphNode,
          relationship: str, *, notes: str = "") -> ExperienceGraphEdge:
    row = ExperienceGraphEdge(
        tenant_id=tenant_id, from_node_id=from_node.id, to_node_id=to_node.id,
        relationship=relationship, notes=notes,
    )
    db.add(row)
    db.flush()
    return row


def _node_to_dict(n: ExperienceGraphNode) -> dict:
    return {
        "id": n.id, "node_type": n.node_type, "label": n.label, "source_type": n.source_type,
        "source_id": n.source_id, "details": json.loads(n.details_json or "{}"),
        "created_at": n.created_at.isoformat(),
    }


def build_experience_chain(
    db: Session, tenant_id: str, *, person: str, experience_label: str, instrument_type: str, finding_type: str,
    manufacturer: str = "", model: str = "", outcome_label: str = "", evidence_label: str = "",
    organization_label: str = "", source_type: str = "", source_id: int | None = None,
) -> dict:
    """Creates the full Person -> Experience -> Finding -> Instrument ->
    Anatomy -> Recommendation -> Outcome -> Evidence -> Organization chain
    in one call. The Finding/Instrument/Anatomy/Recommendation nodes come
    directly from `reasoning_chain()` — never re-derived."""
    chain = reasoning_chain(instrument_type, finding_type, manufacturer=manufacturer, model=model)
    chain_by_node = {s["node"]: s for s in chain["chain"]}

    person_node = _node(db, tenant_id, NODE_PERSON, person)
    experience_node = _node(
        db, tenant_id, NODE_EXPERIENCE, experience_label, source_type=source_type, source_id=source_id,
    )
    _edge(db, tenant_id, person_node, experience_node, EDGE_HAS_EXPERIENCE)

    finding_node = _node(db, tenant_id, NODE_FINDING, finding_type, details=chain_by_node.get("Clinical Meaning"))
    _edge(db, tenant_id, experience_node, finding_node, EDGE_YIELDED_FINDING)

    instrument_node = _node(db, tenant_id, NODE_INSTRUMENT, instrument_type, details={
        "manufacturer": manufacturer, "model": model, "family": chain["chain"][2]["value"],
    })
    _edge(db, tenant_id, finding_node, instrument_node, EDGE_FOUND_ON_INSTRUMENT)

    anatomy_node = _node(db, tenant_id, NODE_ANATOMY, chain_by_node["Anatomy Zone"]["value"], details=chain_by_node["Anatomy Zone"])
    _edge(db, tenant_id, instrument_node, anatomy_node, EDGE_INSTRUMENT_HAS_ANATOMY)

    recommendation_text = chain_by_node["Recommended Action"]["value"]
    recommendation_node = _node(db, tenant_id, NODE_RECOMMENDATION, recommendation_text, details=chain_by_node["Recommended Action"])
    _edge(db, tenant_id, anatomy_node, recommendation_node, EDGE_LED_TO_RECOMMENDATION)

    result: dict = {
        "person_node": _node_to_dict(person_node), "experience_node": _node_to_dict(experience_node),
        "finding_node": _node_to_dict(finding_node), "instrument_node": _node_to_dict(instrument_node),
        "anatomy_node": _node_to_dict(anatomy_node), "recommendation_node": _node_to_dict(recommendation_node),
        "narrative": chain["narrative"],
    }

    last_node = recommendation_node
    if outcome_label:
        outcome_node = _node(db, tenant_id, NODE_OUTCOME, outcome_label)
        _edge(db, tenant_id, last_node, outcome_node, EDGE_PRODUCED_OUTCOME)
        result["outcome_node"] = _node_to_dict(outcome_node)
        last_node = outcome_node

    if evidence_label:
        evidence_node = _node(db, tenant_id, NODE_EVIDENCE, evidence_label)
        _edge(db, tenant_id, last_node, evidence_node, EDGE_SUPPORTED_BY_EVIDENCE)
        result["evidence_node"] = _node_to_dict(evidence_node)
        last_node = evidence_node

        if organization_label:
            org_node = _node(db, tenant_id, NODE_ORGANIZATION, organization_label)
            _edge(db, tenant_id, evidence_node, org_node, EDGE_EVIDENCE_OWNED_BY_ORG)
            result["organization_node"] = _node_to_dict(org_node)

    db.commit()
    result["human_review_required"] = True
    result["disclaimer"] = DISCLAIMER
    return result


def graph_for_person(db: Session, tenant_id: str, person: str) -> dict:
    """Every experience chain recorded for a given person (Section 3's
    "living Experience Graph")."""
    person_nodes = (
        db.query(ExperienceGraphNode)
        .filter(ExperienceGraphNode.tenant_id == tenant_id, ExperienceGraphNode.node_type == NODE_PERSON,
                ExperienceGraphNode.label == person)
        .all()
    )
    chains = []
    for pn in person_nodes:
        chains.append(_walk_from(db, tenant_id, pn.id))
    return {"person": person, "chains": chains, "human_review_required": True, "disclaimer": DISCLAIMER}


def _walk_from(db: Session, tenant_id: str, node_id: int) -> list[dict]:
    """Walks outgoing edges from a node to the end of the chain."""
    path: list[dict] = []
    current_id = node_id
    visited: set[int] = set()
    while current_id is not None and current_id not in visited:
        visited.add(current_id)
        node = db.query(ExperienceGraphNode).filter(ExperienceGraphNode.id == current_id).first()
        if node is None:
            break
        path.append(_node_to_dict(node))
        edge = (
            db.query(ExperienceGraphEdge)
            .filter(ExperienceGraphEdge.tenant_id == tenant_id, ExperienceGraphEdge.from_node_id == current_id)
            .first()
        )
        current_id = edge.to_node_id if edge else None
    return path


def full_chain(db: Session, tenant_id: str, start_node_id: int) -> dict:
    return {
        "start_node_id": start_node_id, "chain": _walk_from(db, tenant_id, start_node_id),
        "human_review_required": True,
    }


def graph_schema() -> dict:
    from app.models.athena_knowledge import EDGE_RELATIONSHIPS, NODE_CHAIN_ORDER

    return {"node_chain_order": NODE_CHAIN_ORDER, "edge_relationships": EDGE_RELATIONSHIPS}

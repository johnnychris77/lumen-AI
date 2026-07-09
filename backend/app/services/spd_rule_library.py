"""v2.5 — SPD Rule Library (Project Cortex, Section 5).

A structured, versioned repository of explainable clinical decision rules —
the first genuinely new rule abstraction in the platform. Everything else
that looks like a "rule" today (`_integrity_status()`, `evidence_strength()`
in `baseline_comparison_scoring_service.py`, the legacy
`_INSTRUMENT_ZONE_RULES` table in `instrument_zones.py`) is an inline Python
conditional with no explicit ID, evidence binding, or audit trail. Rules here
are declarative dataclasses matched against an evidence bundle
(`app/services/decision_reasoning_service.gather_evidence`) so every match
can be reported as "rule X fired because evidence Y was present."

Zone matching is substring-based against the instrument's own declared zone
name (e.g. "jaw serrations", "o-ring area", "hinge/joint", "cutting flutes",
"insulation coating") since the same anatomical concept is named slightly
differently across the anatomy library's 112 families — this mirrors the
same tolerant-matching approach `instrument_zones.py`'s legacy table uses.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SPDRule:
    id: str
    title: str
    description: str
    finding_types: frozenset[str] = field(default_factory=frozenset)  # empty = any finding
    zone_keywords: frozenset[str] = field(default_factory=frozenset)  # empty = any zone
    requires_high_risk_zone: bool = False
    requires_repeat_finding: bool = False
    min_repeat_occurrences: int = 0
    severity: str = "Moderate"
    spd_risk: str = "Moderate"
    recommendation: tuple[str, ...] = ()

    def matches(self, evidence: dict) -> bool:
        finding_type = (evidence.get("finding_type") or "").strip().lower()
        zone = (evidence.get("zone") or "").strip().lower()

        if self.finding_types and finding_type not in self.finding_types:
            return False
        if self.zone_keywords and not any(kw in zone for kw in self.zone_keywords):
            return False
        if self.requires_high_risk_zone and not evidence.get("high_risk_zone"):
            return False
        if self.requires_repeat_finding and not evidence.get("repeat_finding"):
            return False
        if evidence.get("repeat_occurrences", 0) < self.min_repeat_occurrences:
            return False
        return True

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "evidence": {
                "finding_types": sorted(self.finding_types),
                "zone_keywords": sorted(self.zone_keywords),
                "requires_high_risk_zone": self.requires_high_risk_zone,
                "requires_repeat_finding": self.requires_repeat_finding,
                "min_repeat_occurrences": self.min_repeat_occurrences,
            },
            "severity": self.severity,
            "spd_risk": self.spd_risk,
            "recommendation": list(self.recommendation),
            "source": "spd_rule_library",
        }


SPD_RULE_LIBRARY: tuple[SPDRule, ...] = (
    SPDRule(
        id="blood-in-serrations",
        title="Blood in serrations",
        description="Blood residue in a serrated jaw is difficult to fully remove by visual inspection alone and readily re-contaminates the working surface.",
        finding_types=frozenset({"blood"}),
        zone_keywords=frozenset({"serration"}),
        severity="High",
        spd_risk="High",
        recommendation=("Focused manual reclean of the serrations", "Supervisor review"),
    ),
    SPDRule(
        id="corrosion-in-o-ring",
        title="Corrosion in O-ring",
        description="Corrosion at a sealing O-ring compromises the seal and risks fluid ingress into the instrument's internal mechanism.",
        finding_types=frozenset({"corrosion", "rust"}),
        zone_keywords=frozenset({"o-ring", "o ring"}),
        severity="High",
        spd_risk="High",
        recommendation=("Remove from service pending repair evaluation", "Supervisor review"),
    ),
    SPDRule(
        id="repeated-debris",
        title="Repeated debris",
        description="Particulate debris recurring across this instrument's own inspection history suggests an incomplete cleaning step rather than an isolated event.",
        finding_types=frozenset({"debris"}),
        requires_repeat_finding=True,
        min_repeat_occurrences=2,
        severity="Moderate",
        spd_risk="Moderate",
        recommendation=("Focused reclean", "Technician retraining note", "Repeat inspection"),
    ),
    SPDRule(
        id="crack-in-hinge",
        title="Crack in hinge",
        description="A crack at a hinge/joint is a structural integrity failure — continued use risks mechanical failure during a procedure.",
        finding_types=frozenset({"crack"}),
        zone_keywords=frozenset({"hinge"}),
        severity="Critical",
        spd_risk="Critical",
        recommendation=("Remove from service immediately", "No reprocessing — escalate for repair"),
    ),
    SPDRule(
        id="missing-insulation",
        title="Missing insulation",
        description="Missing or damaged insulation on an electrosurgical instrument is a direct patient-safety hazard (stray energy, burns).",
        finding_types=frozenset({"insulation_damage"}),
        severity="Critical",
        spd_risk="Critical",
        recommendation=("Remove from service immediately", "Escalate to biomedical engineering"),
    ),
    SPDRule(
        id="bone-in-drill-flute",
        title="Bone in drill flute",
        description="Bone fragment residue lodged in a drill flute is hard to visualize and hard to fully clean — a recognized high-retention geometry.",
        finding_types=frozenset({"bone"}),
        zone_keywords=frozenset({"flute"}),
        severity="High",
        spd_risk="High",
        recommendation=("Focused reclean of the flute", "Borescope re-inspection before release"),
    ),
    SPDRule(
        id="blood-jaw-serration-high-risk-repeat",
        title="Blood in a high-risk serrated jaw, previously seen on this instrument",
        description="Blood in a serrated jaw that is both a declared high-risk zone and a finding this specific instrument has shown before is the platform's clearest recurring-contamination signal.",
        finding_types=frozenset({"blood"}),
        zone_keywords=frozenset({"serration"}),
        requires_high_risk_zone=True,
        requires_repeat_finding=True,
        severity="Critical",
        spd_risk="Critical",
        recommendation=("Focused reclean", "Supervisor review", "Repeat inspection"),
    ),
)


def evaluate_rules(evidence: dict) -> list[dict]:
    """Every SPD_RULE_LIBRARY rule whose conditions the evidence bundle
    satisfies, each with its own recommendation — never a single hidden
    winner-take-all rule."""
    return [rule.to_dict() for rule in SPD_RULE_LIBRARY if rule.matches(evidence)]


def get_rule(rule_id: str) -> dict | None:
    for rule in SPD_RULE_LIBRARY:
        if rule.id == rule_id:
            return rule.to_dict()
    return None


def list_rules() -> list[dict]:
    return [rule.to_dict() for rule in SPD_RULE_LIBRARY]

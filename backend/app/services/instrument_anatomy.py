"""Phase 15 — Instrument Anatomy Library.

Extensible, data-driven definitions of instrument anatomy so LumenAI reasons the
way SPD professionals inspect: by anatomy, high-risk zone, retention area, and
required image coverage.

Each instrument definition lists its anatomy zones (with per-zone risk +
retention + typical contamination/condition risks), the high-risk subset, the
images required for a complete inspection, recommended image angles, minimum
image count, and recommended manual inspection steps.

This is structured knowledge, not pixel-level detection — a future CV model that
localizes zones drops into the same schema.
"""
from __future__ import annotations

from app.services.instrument_zones import HIGH_RETENTION_ZONES

# Standard contamination / condition risk vocabularies (per zone).
_CONTAM = ["blood", "bone", "tissue", "organic residue", "debris"]
_COND = ["rust", "corrosion", "pitting", "crack", "discoloration", "insulation damage", "missing component", "wear"]


def _zone(name: str, category: str, risk: str, retention: str,
          contamination: list[str] | None = None,
          condition: list[str] | None = None) -> dict:
    return {
        "zone_name": name,
        "zone_category": category,
        "zone_risk_level": risk,          # low / medium / high / critical
        "retention_risk": retention,      # low / medium / high
        "contamination_risks": contamination if contamination is not None else _CONTAM,
        "condition_risks": condition if condition is not None else _COND,
    }


def _family(match: list[str], category: str, zones: list[dict],
            required_images: list[str] | None = None,
            angles: list[str] | None = None,
            min_images: int = 2,
            manual_steps: list[str] | None = None) -> dict:
    """Family-entry builder — cuts the boilerplate for the v1.10 specialty
    expansion below while keeping every entry's zones/guidance explicit and
    inspectable (nothing generated at import time beyond this call)."""
    zone_names = [z["zone_name"] for z in zones]
    return {
        "category": category,
        "match": match,
        "zones": zones,
        "required_images": required_images or zone_names[: min(3, len(zone_names))],
        "recommended_image_angles": angles or ["overall view", "working end close-up"],
        "min_images": min_images,
        "manual_steps": manual_steps or ["Inspect and brush all working-end zones under magnification."],
    }


# ── v1.10 — Instrument Knowledge Expansion ───────────────────────────────────
# 100+ additional instrument families across the surgical specialties SPD
# processes. Declared BEFORE the original 8 families (and matched first,
# since `resolve_family` returns on first match) so specific multi-word
# phrases here win over the original families' broader single-word keywords
# — every keyword below is a distinctive compound phrase that is never a
# substring of an existing family's match keywords, so none of the original
# 8 families' resolution behavior changes for any input that matched them
# before this expansion.
_EXPANSION_FAMILIES: dict[str, dict] = {
    # -- General surgery: grasping, clamping, retracting --------------------
    "towel_clamp": _family(
        match=["towel clamp", "backhaus towel clamp", "backhaus"],
        category="general surgery - draping",
        zones=[
            _zone("perforating tip", "cutting_working_surface", "medium", "medium"),
            _zone("point alignment", "cutting_working_surface", "medium", "low"),
            _zone("box lock", "mechanical", "high", "high"),
            _zone("ratchet", "mechanical", "medium", "medium"),
            _zone("handle", "handle_external", "low", "low"),
        ],
        manual_steps=["Open the box lock and brush the pivot; confirm tip points align and are sharp."],
    ),
    "sponge_forceps": _family(
        match=["sponge forceps", "sponge stick", "foerster forceps"],
        category="general surgery - grasping",
        zones=[
            _zone("ring jaw", "cutting_working_surface", "medium", "medium"),
            _zone("jaw serrations", "cutting_working_surface", "high", "high"),
            _zone("box lock", "mechanical", "high", "high"),
            _zone("ratchet", "mechanical", "medium", "medium"),
            _zone("handle", "handle_external", "low", "low"),
        ],
        manual_steps=["Brush the ring-jaw serrations and open the box lock to brush the pivot."],
    ),
    "tenaculum": _family(
        match=["tenaculum"],
        category="general surgery - grasping",
        zones=[
            _zone("hook tip", "cutting_working_surface", "high", "high"),
            _zone("box lock", "mechanical", "high", "high"),
            _zone("ratchet", "mechanical", "medium", "medium"),
            _zone("handle", "handle_external", "low", "low"),
        ],
        manual_steps=["Inspect the hook tip for dulling/bending; open the box lock and brush the pivot."],
    ),
    "bone_holding_forceps": _family(
        match=["bone holding forceps", "lane bone clamp", "lowman bone clamp"],
        category="orthopedic - grasping",
        zones=[
            _zone("jaw teeth", "cutting_working_surface", "high", "high"),
            _zone("box lock", "mechanical", "high", "high"),
            _zone("ratchet", "mechanical", "high", "high"),
            _zone("handle", "handle_external", "low", "low"),
        ],
        manual_steps=["Brush between the bone-gripping teeth; open the box lock and brush the pivot."],
    ),
    "vascular_clamp": _family(
        match=["vascular clamp", "debakey clamp", "satinsky clamp", "bulldog clamp", "atraumatic clamp"],
        category="cardiovascular - occluding",
        zones=[
            _zone("atraumatic jaw", "cutting_working_surface", "critical", "high"),
            _zone("jaw serration line", "cutting_working_surface", "high", "high"),
            _zone("box lock", "mechanical", "high", "high"),
            _zone("handle", "handle_external", "low", "low"),
        ],
        manual_steps=["Inspect the atraumatic jaw serration line under magnification for flattened teeth or debris."],
    ),
    "right_angle_clamp": _family(
        match=["right angle clamp", "mixter clamp", "gemini clamp"],
        category="general surgery - occluding",
        zones=[
            _zone("angled jaw tip", "cutting_working_surface", "high", "high"),
            _zone("jaw serrations", "cutting_working_surface", "high", "high"),
            _zone("box lock", "mechanical", "high", "high"),
            _zone("ratchet", "mechanical", "medium", "medium"),
            _zone("handle", "handle_external", "low", "low"),
        ],
        manual_steps=["Brush the angled jaw tip and serrations; open the box lock and brush the pivot."],
    ),
    "intestinal_clamp": _family(
        match=["intestinal clamp", "doyen clamp", "bowel clamp"],
        category="general surgery - occluding",
        zones=[
            _zone("jaw surface", "cutting_working_surface", "high", "high"),
            _zone("box lock", "mechanical", "high", "high"),
            _zone("ratchet", "mechanical", "medium", "medium"),
            _zone("handle", "handle_external", "low", "low"),
        ],
        manual_steps=["Brush the full jaw surface length; open the box lock and brush the pivot."],
    ),
    "rib_approximator": _family(
        match=["rib approximator", "rib spreader", "finochietto retractor"],
        category="thoracic - retracting",
        zones=[
            _zone("blade", "cutting_working_surface", "medium", "medium"),
            _zone("ratchet mechanism", "mechanical", "high", "high"),
            _zone("crank", "mechanical", "medium", "medium"),
            _zone("frame", "handle_external", "low", "low"),
        ],
        min_images=3,
        manual_steps=["Brush the ratchet mechanism and crank threads; confirm the blades open and lock smoothly."],
    ),
    "sternal_retractor": _family(
        match=["sternal retractor", "sternal spreader"],
        category="cardiothoracic - retracting",
        zones=[
            _zone("blade", "cutting_working_surface", "medium", "medium"),
            _zone("ratchet bar", "mechanical", "high", "high"),
            _zone("crank", "mechanical", "medium", "medium"),
            _zone("frame", "handle_external", "low", "low"),
        ],
        min_images=3,
        manual_steps=["Brush the ratchet bar teeth and crank mechanism; confirm smooth full-range opening."],
    ),
    "self_retaining_retractor": _family(
        match=["weitlaner retractor", "gelpi retractor", "self-retaining retractor"],
        category="general surgery - retracting",
        zones=[
            _zone("prong tip", "cutting_working_surface", "medium", "medium"),
            _zone("ratchet", "mechanical", "high", "high"),
            _zone("hinge", "mechanical", "high", "high"),
            _zone("handle", "handle_external", "low", "low"),
        ],
        manual_steps=["Brush the ratchet and hinge; check prong tips for bending/dulling."],
    ),
    "handheld_retractor": _family(
        match=["richardson retractor", "deaver retractor", "army-navy retractor", "malleable retractor"],
        category="general surgery - retracting",
        zones=[
            _zone("blade", "cutting_working_surface", "low", "medium"),
            _zone("blade edge", "cutting_working_surface", "medium", "medium"),
            _zone("shaft", "handle_external", "low", "low"),
            _zone("handle", "handle_external", "low", "low"),
        ],
        min_images=1,
        manual_steps=["Inspect the blade edge for burrs/bending that could injure tissue."],
    ),
    "suction_tip": _family(
        match=["yankauer suction", "poole suction", "suction tip"],
        category="general surgery - suction/irrigation",
        zones=[
            _zone("tip perforations", "lumen_scope", "critical", "high"),
            _zone("lumen", "lumen_scope", "critical", "high"),
            _zone("connector", "handle_external", "low", "low"),
            _zone("handle", "handle_external", "low", "low"),
        ],
        min_images=2,
        manual_steps=["Flush and brush the lumen end-to-end; confirm the tip perforations are clear of debris."],
    ),
    "electrosurgical_pencil": _family(
        match=["electrosurgical pencil", "bovie pencil", "cautery pencil"],
        category="general surgery - electrosurgical",
        zones=[
            _zone("electrode tip", "cutting_working_surface", "high", "medium"),
            _zone("tip receptacle", "mechanical", "medium", "medium"),
            _zone("insulated shaft", "handle_external", "critical", "medium"),
            _zone("button switch", "handle_external", "low", "low"),
        ],
        manual_steps=["Inspect the insulated shaft end-to-end for breaches; clean carbon buildup from the electrode tip."],
    ),
    "bipolar_forceps_open": _family(
        match=["bipolar forceps", "bipolar tip forceps"],
        category="general surgery - electrosurgical",
        zones=[
            _zone("bipolar tip", "cutting_working_surface", "high", "medium"),
            _zone("insulation coating", "handle_external", "critical", "medium"),
            _zone("hinge", "mechanical", "high", "high"),
            _zone("handle", "handle_external", "low", "low"),
        ],
        manual_steps=["Inspect the insulation coating for breaches; brush the hinge and tip."],
    ),
    # -- Orthopedics ----------------------------------------------------------
    "oscillating_saw": _family(
        match=["oscillating saw", "oscillating saw blade"],
        category="orthopedic - powered",
        zones=[
            _zone("saw blade", "rotary_orthopedic", "critical", "high"),
            _zone("blade coupling", "mechanical", "high", "high"),
            _zone("motor housing coupling", "mechanical", "medium", "medium"),
            _zone("cord/hose connection", "handle_external", "low", "low"),
        ],
        min_images=3,
        manual_steps=["Brush bone debris from the blade teeth and coupling; confirm secure blade lock engagement."],
    ),
    "sagittal_saw": _family(
        match=["sagittal saw", "sagittal saw blade"],
        category="orthopedic - powered",
        zones=[
            _zone("saw blade", "rotary_orthopedic", "critical", "high"),
            _zone("blade coupling", "mechanical", "high", "high"),
            _zone("motor housing coupling", "mechanical", "medium", "medium"),
            _zone("cord/hose connection", "handle_external", "low", "low"),
        ],
        min_images=3,
        manual_steps=["Brush bone debris from the blade teeth and coupling; confirm secure blade lock engagement."],
    ),
    "reciprocating_saw": _family(
        match=["reciprocating saw", "reciprocating saw blade"],
        category="orthopedic - powered",
        zones=[
            _zone("saw blade", "rotary_orthopedic", "critical", "high"),
            _zone("blade coupling", "mechanical", "high", "high"),
            _zone("motor housing coupling", "mechanical", "medium", "medium"),
        ],
        manual_steps=["Brush bone debris from the blade coupling; confirm the blade seats and locks fully."],
    ),
    "bone_awl": _family(
        match=["bone awl", "pointed awl"],
        category="orthopedic - powered",
        zones=[
            _zone("point", "rotary_orthopedic", "high", "high"),
            _zone("shaft", "handle_external", "low", "low"),
            _zone("handle", "handle_external", "low", "low"),
        ],
        min_images=1,
        manual_steps=["Inspect the point for bending or dulling; brush any bone debris from the shank."],
    ),
    "orthopedic_reamer": _family(
        match=["orthopedic reamer", "acetabular reamer", "intramedullary reamer", "cannulated reamer"],
        category="orthopedic - powered",
        zones=[
            _zone("reaming head", "rotary_orthopedic", "critical", "high"),
            _zone("cannulation", "lumen_scope", "critical", "high"),
            _zone("shaft", "handle_external", "medium", "medium"),
            _zone("coupling hub", "mechanical", "medium", "medium"),
        ],
        min_images=3,
        manual_steps=["Flush and brush the cannulation; brush bone debris from the reaming-head flutes."],
    ),
    "external_fixator_component": _family(
        match=["external fixator", "external fixation clamp", "fixator pin clamp"],
        category="orthopedic - fixation hardware",
        zones=[
            _zone("clamp jaw", "mechanical", "high", "high"),
            _zone("locking mechanism", "mechanical", "high", "high"),
            _zone("connecting rod interface", "handle_external", "medium", "medium"),
        ],
        manual_steps=["Brush the clamp jaw and locking threads; confirm no bone debris remains in the clamp bore."],
    ),
    "plate_bending_iron": _family(
        match=["plate bending iron", "plate bender"],
        category="orthopedic - instrumentation",
        zones=[
            _zone("bending slot", "mechanical", "medium", "medium"),
            _zone("handle", "handle_external", "low", "low"),
        ],
        min_images=1,
        manual_steps=["Inspect the bending slot for metal shavings or deformation."],
    ),
    "orthopedic_screwdriver": _family(
        match=["orthopedic screwdriver", "cannulated screwdriver"],
        category="orthopedic - instrumentation",
        zones=[
            _zone("tip/blade", "cutting_working_surface", "high", "medium"),
            _zone("cannulation", "lumen_scope", "high", "high"),
            _zone("shaft", "handle_external", "low", "low"),
            _zone("handle", "handle_external", "low", "low"),
        ],
        manual_steps=["Flush the cannulation if present; inspect the tip for stripped or worn flutes."],
    ),
    "bone_tap": _family(
        match=["bone tap", "orthopedic tap"],
        category="orthopedic - instrumentation",
        zones=[
            _zone("cutting flutes", "rotary_orthopedic", "critical", "high"),
            _zone("shank", "handle_external", "low", "low"),
        ],
        min_images=1,
        manual_steps=["Brush bone debris from between the cutting flutes under magnification."],
    ),
    "k_wire_driver": _family(
        match=["k-wire driver", "kirschner wire driver", "wire driver chuck"],
        category="orthopedic - powered",
        zones=[
            _zone("chuck jaws", "mechanical", "high", "high"),
            _zone("chuck key interface", "mechanical", "medium", "medium"),
            _zone("coupling hub", "mechanical", "medium", "medium"),
        ],
        manual_steps=["Brush bone debris from the chuck jaws; confirm the chuck opens and closes fully."],
    ),
    "pin_cutter": _family(
        match=["pin cutter", "wire cutter orthopedic"],
        category="orthopedic - instrumentation",
        zones=[
            _zone("cutting jaw", "cutting_working_surface", "high", "medium"),
            _zone("hinge", "mechanical", "high", "high"),
            _zone("handle", "handle_external", "low", "low"),
        ],
        manual_steps=["Inspect the cutting jaw edge for nicks; brush the hinge pivot."],
    ),
    "cast_saw": _family(
        match=["cast saw", "cast cutting saw"],
        category="orthopedic - powered",
        zones=[
            _zone("oscillating blade", "rotary_orthopedic", "high", "medium"),
            _zone("blade guard", "handle_external", "low", "low"),
            _zone("motor housing coupling", "mechanical", "medium", "medium"),
        ],
        manual_steps=["Brush casting-material debris from the blade and guard."],
    ),
    "bone_reduction_clamp": _family(
        match=["bone reduction clamp", "reduction forceps orthopedic"],
        category="orthopedic - grasping",
        zones=[
            _zone("pointed jaw tip", "cutting_working_surface", "high", "high"),
            _zone("box lock", "mechanical", "high", "high"),
            _zone("ratchet", "mechanical", "high", "high"),
            _zone("handle", "handle_external", "low", "low"),
        ],
        manual_steps=["Brush between the pointed jaw tips; open the box lock and brush the pivot."],
    ),
    # -- Neurosurgery -----------------------------------------------------
    "pituitary_rongeur": _family(
        match=["pituitary rongeur", "pituitary punch"],
        category="neurosurgery - biting",
        zones=[
            _zone("cup jaw", "cutting_working_surface", "critical", "high"),
            _zone("box lock", "mechanical", "high", "high"),
            _zone("shaft", "handle_external", "medium", "medium"),
            _zone("handle", "handle_external", "low", "low"),
        ],
        manual_steps=["Brush the cup jaw closely — tissue lodges in the concave cutting surface."],
    ),
    "dural_hook": _family(
        match=["dural hook", "nerve hook"],
        category="neurosurgery - dissecting",
        zones=[
            _zone("hook tip", "cutting_working_surface", "medium", "medium"),
            _zone("shaft", "handle_external", "low", "low"),
            _zone("handle", "handle_external", "low", "low"),
        ],
        min_images=1,
        manual_steps=["Inspect the fine hook tip under magnification for bending."],
    ),
    "penfield_dissector": _family(
        match=["penfield dissector", "penfield elevator"],
        category="neurosurgery - dissecting",
        zones=[
            _zone("dissecting tip", "cutting_working_surface", "medium", "medium"),
            _zone("shaft", "handle_external", "low", "low"),
            _zone("handle", "handle_external", "low", "low"),
        ],
        min_images=1,
        manual_steps=["Inspect both dissecting tips for bending or residue."],
    ),
    "micro_dissector_neuro": _family(
        match=["micro dissector neurosurgical", "rhoton dissector"],
        category="neurosurgery - micro dissecting",
        zones=[
            _zone("micro tip", "cutting_working_surface", "high", "medium"),
            _zone("shaft", "handle_external", "low", "low"),
            _zone("handle", "handle_external", "low", "low"),
        ],
        min_images=1,
        manual_steps=["Inspect the micro tip under magnification; handle with care to avoid bending."],
    ),
    "brain_retractor": _family(
        match=["brain retractor", "cerebellar retractor", "malleable brain retractor"],
        category="neurosurgery - retracting",
        zones=[
            _zone("blade", "cutting_working_surface", "low", "medium"),
            _zone("shaft", "handle_external", "low", "low"),
        ],
        min_images=1,
        manual_steps=["Inspect the malleable blade for cracking at bend points."],
    ),
    "cranial_perforator": _family(
        match=["cranial perforator", "craniotome bit"],
        category="neurosurgery - powered",
        zones=[
            _zone("perforating tip", "rotary_orthopedic", "critical", "high"),
            _zone("coupling hub", "mechanical", "medium", "medium"),
            _zone("safety clutch", "mechanical", "high", "high"),
        ],
        min_images=2,
        manual_steps=["Brush bone debris from the perforating tip and safety-clutch mechanism."],
    ),
    "mayfield_head_clamp": _family(
        match=["mayfield head clamp", "head clamp neurosurgical", "skull clamp"],
        category="neurosurgery - fixation hardware",
        zones=[
            _zone("pin tip", "cutting_working_surface", "high", "medium"),
            _zone("locking mechanism", "mechanical", "high", "high"),
            _zone("frame", "handle_external", "low", "low"),
        ],
        manual_steps=["Inspect pin tips for dulling; confirm the locking mechanism holds torque."],
    ),
    "spinal_curette": _family(
        match=["spinal curette", "disc curette"],
        category="neurosurgery - biting",
        zones=[
            _zone("cup/loop tip", "cutting_working_surface", "critical", "high"),
            _zone("shaft", "handle_external", "medium", "medium"),
            _zone("handle", "handle_external", "low", "low"),
        ],
        manual_steps=["Brush the concave cup tip closely — disc/bone material lodges here."],
    ),
    "laminectomy_rongeur": _family(
        match=["laminectomy rongeur"],
        category="neurosurgery - biting",
        zones=[
            _zone("jaw", "cutting_working_surface", "critical", "high"),
            _zone("box lock", "mechanical", "high", "high"),
            _zone("spring", "mechanical", "medium", "medium"),
            _zone("handle", "handle_external", "low", "low"),
        ],
        manual_steps=["Open the box lock and brush the jaw and spring channel thoroughly."],
    ),
    # -- ENT --------------------------------------------------------------
    "nasal_speculum": _family(
        match=["nasal speculum"],
        category="ENT - retracting",
        zones=[
            _zone("blade tip", "cutting_working_surface", "low", "medium"),
            _zone("hinge", "mechanical", "medium", "medium"),
            _zone("handle", "handle_external", "low", "low"),
        ],
        min_images=1,
        manual_steps=["Brush the hinge pivot and inspect blade tips for burrs."],
    ),
    "ear_curette": _family(
        match=["ear curette", "wax curette"],
        category="ENT - biting",
        zones=[
            _zone("loop tip", "cutting_working_surface", "medium", "medium"),
            _zone("shaft", "handle_external", "low", "low"),
        ],
        min_images=1,
        manual_steps=["Brush cerumen/debris from the concave loop tip."],
    ),
    "myringotomy_knife": _family(
        match=["myringotomy knife"],
        category="ENT - cutting",
        zones=[
            _zone("blade tip", "cutting_working_surface", "high", "medium"),
            _zone("handle", "handle_external", "low", "low"),
        ],
        min_images=1,
        manual_steps=["Inspect the fine blade tip under magnification for dulling or bending."],
    ),
    "tonsil_forceps": _family(
        match=["tonsil forceps", "tonsil grasping forceps"],
        category="ENT - grasping",
        zones=[
            _zone("jaw", "cutting_working_surface", "high", "high"),
            _zone("box lock", "mechanical", "high", "high"),
            _zone("ratchet", "mechanical", "medium", "medium"),
            _zone("handle", "handle_external", "low", "low"),
        ],
        manual_steps=["Brush the jaw serrations and open the box lock to brush the pivot."],
    ),
    "adenoid_curette": _family(
        match=["adenoid curette"],
        category="ENT - biting",
        zones=[
            _zone("cutting loop", "cutting_working_surface", "high", "medium"),
            _zone("shaft", "handle_external", "low", "low"),
        ],
        min_images=1,
        manual_steps=["Brush tissue residue from the concave cutting loop."],
    ),
    "laryngoscope_blade": _family(
        match=["laryngoscope blade"],
        category="ENT/anesthesia - visualization",
        zones=[
            _zone("blade tip", "cutting_working_surface", "medium", "medium"),
            _zone("light source contact", "handle_external", "medium", "medium"),
            _zone("hinge", "mechanical", "medium", "medium"),
        ],
        manual_steps=["Inspect the light-source contact for corrosion; brush the blade tip and hinge."],
    ),
    "tracheostomy_dilator": _family(
        match=["tracheostomy dilator", "trach dilator"],
        category="ENT - dilating",
        zones=[
            _zone("dilating tip", "cutting_working_surface", "medium", "medium"),
            _zone("hinge", "mechanical", "high", "high"),
            _zone("handle", "handle_external", "low", "low"),
        ],
        manual_steps=["Brush the hinge pivot; confirm the dilating tips open smoothly."],
    ),
    "sinus_forceps": _family(
        match=["sinus forceps", "ethmoid forceps"],
        category="ENT - grasping",
        zones=[
            _zone("jaw", "cutting_working_surface", "high", "high"),
            _zone("box lock", "mechanical", "high", "high"),
            _zone("shaft", "handle_external", "medium", "medium"),
            _zone("handle", "handle_external", "low", "low"),
        ],
        manual_steps=["Brush the jaw serrations; open the box lock and brush the pivot."],
    ),
    "ear_forceps_alligator": _family(
        match=["alligator forceps", "ear alligator forceps"],
        category="ENT - grasping",
        zones=[
            _zone("jaw", "cutting_working_surface", "high", "medium"),
            _zone("hinge", "mechanical", "high", "high"),
            _zone("shaft", "handle_external", "low", "low"),
            _zone("handle", "handle_external", "low", "low"),
        ],
        manual_steps=["Brush the fine jaw serrations and hinge under magnification."],
    ),
    "microdebrider_handpiece": _family(
        match=["microdebrider handpiece", "microdebrider blade"],
        category="ENT - powered",
        zones=[
            _zone("cutting window", "rotary_orthopedic", "critical", "high"),
            _zone("suction lumen", "lumen_scope", "critical", "high"),
            _zone("coupling hub", "mechanical", "medium", "medium"),
        ],
        min_images=3,
        manual_steps=["Flush and brush the suction lumen; brush tissue debris from the cutting window."],
    ),
    # -- Ophthalmology ------------------------------------------------------
    "lens_forceps": _family(
        match=["lens forceps", "iol forceps", "intraocular lens forceps"],
        category="ophthalmology - grasping",
        zones=[
            _zone("micro jaw", "cutting_working_surface", "high", "medium"),
            _zone("hinge", "mechanical", "medium", "medium"),
            _zone("handle", "handle_external", "low", "low"),
        ],
        min_images=1,
        manual_steps=["Inspect the micro jaw tips under magnification for bending or residue."],
    ),
    "capsulorhexis_forceps": _family(
        match=["capsulorhexis forceps", "utrata forceps"],
        category="ophthalmology - grasping",
        zones=[
            _zone("micro jaw tip", "cutting_working_surface", "high", "medium"),
            _zone("hinge", "mechanical", "medium", "medium"),
            _zone("handle", "handle_external", "low", "low"),
        ],
        min_images=1,
        manual_steps=["Inspect the fine jaw tip under magnification; handle with extreme care."],
    ),
    "iris_scissors": _family(
        match=["iris scissors", "vannas scissors"],
        category="ophthalmology - cutting",
        zones=[
            _zone("micro blade tip", "cutting_working_surface", "high", "medium"),
            _zone("hinge", "mechanical", "medium", "medium"),
            _zone("handle", "handle_external", "low", "low"),
        ],
        min_images=1,
        manual_steps=["Inspect the micro blade tips under magnification for nicks."],
    ),
    "keratome": _family(
        match=["keratome", "crescent knife ophthalmic"],
        category="ophthalmology - cutting",
        zones=[
            _zone("micro blade", "cutting_working_surface", "critical", "medium"),
            _zone("handle", "handle_external", "low", "low"),
        ],
        min_images=1,
        manual_steps=["Inspect the micro blade edge under magnification; protect the edge from contact damage."],
    ),
    "corneal_scissors": _family(
        match=["corneal scissors"],
        category="ophthalmology - cutting",
        zones=[
            _zone("curved blade tip", "cutting_working_surface", "high", "medium"),
            _zone("hinge", "mechanical", "medium", "medium"),
            _zone("handle", "handle_external", "low", "low"),
        ],
        min_images=1,
        manual_steps=["Inspect the curved blade tips under magnification."],
    ),
    "eye_speculum": _family(
        match=["eye speculum", "lid speculum", "wire speculum ophthalmic"],
        category="ophthalmology - retracting",
        zones=[
            _zone("blade/wire loop", "cutting_working_surface", "low", "medium"),
            _zone("hinge", "mechanical", "medium", "medium"),
        ],
        min_images=1,
        manual_steps=["Inspect the blade/wire loop for bending; brush the hinge."],
    ),
    "lid_retractor": _family(
        match=["lid retractor ophthalmic", "desmarres retractor"],
        category="ophthalmology - retracting",
        zones=[
            _zone("blade", "cutting_working_surface", "low", "medium"),
            _zone("handle", "handle_external", "low", "low"),
        ],
        min_images=1,
        manual_steps=["Inspect the blade edge for bending."],
    ),
    "vitrectomy_handpiece": _family(
        match=["vitrectomy handpiece", "vitrector probe"],
        category="ophthalmology - powered",
        zones=[
            _zone("cutting port", "rotary_orthopedic", "critical", "high"),
            _zone("infusion/aspiration lumen", "lumen_scope", "critical", "high"),
            _zone("coupling connector", "mechanical", "medium", "medium"),
        ],
        min_images=2,
        manual_steps=["Flush the infusion/aspiration lumen; inspect the cutting port under magnification."],
    ),
    "phaco_handpiece": _family(
        match=["phaco handpiece", "phacoemulsification handpiece"],
        category="ophthalmology - powered",
        zones=[
            _zone("phaco tip", "cutting_working_surface", "critical", "high"),
            _zone("irrigation sleeve", "lumen_scope", "critical", "high"),
            _zone("coupling connector", "mechanical", "medium", "medium"),
        ],
        min_images=2,
        manual_steps=["Flush the irrigation sleeve and phaco tip lumen; inspect the tip for chips."],
    ),
    # -- Cardiothoracic / vascular -------------------------------------------
    "aortic_punch": _family(
        match=["aortic punch", "coronary punch"],
        category="cardiothoracic - biting",
        zones=[
            _zone("punch jaw", "cutting_working_surface", "critical", "high"),
            _zone("box lock", "mechanical", "high", "high"),
            _zone("handle", "handle_external", "low", "low"),
        ],
        manual_steps=["Brush the punch jaw closely — tissue lodges in the biting mechanism."],
    ),
    "valve_sizer": _family(
        match=["valve sizer", "annuloplasty sizer"],
        category="cardiothoracic - measuring",
        zones=[
            _zone("sizing head", "handle_external", "medium", "medium"),
            _zone("shaft", "handle_external", "low", "low"),
            _zone("handle", "handle_external", "low", "low"),
        ],
        min_images=1,
        manual_steps=["Inspect the sizing head for tissue residue in any grooves."],
    ),
    "sternal_saw": _family(
        match=["sternal saw", "sternum saw"],
        category="cardiothoracic - powered",
        zones=[
            _zone("saw blade/wire", "rotary_orthopedic", "critical", "high"),
            _zone("blade coupling", "mechanical", "high", "high"),
            _zone("motor housing coupling", "mechanical", "medium", "medium"),
        ],
        min_images=3,
        manual_steps=["Brush bone debris from the blade/wire and coupling; confirm secure engagement."],
    ),
    "coronary_probe": _family(
        match=["coronary probe", "vessel probe cardiac"],
        category="cardiothoracic - probing",
        zones=[
            _zone("probe tip", "cutting_working_surface", "medium", "medium"),
            _zone("shaft", "handle_external", "low", "low"),
        ],
        min_images=1,
        manual_steps=["Inspect the probe tip for bending."],
    ),
    "cardiac_cannula": _family(
        match=["cardiac cannula", "aortic cannula", "venous cannula"],
        category="cardiothoracic - lumen/perfusion",
        zones=[
            _zone("tip opening", "lumen_scope", "critical", "high"),
            _zone("lumen", "lumen_scope", "critical", "high"),
            _zone("connector", "handle_external", "low", "low"),
        ],
        min_images=2,
        manual_steps=["Flush the lumen end-to-end; confirm the tip opening is clear of debris."],
    ),
    "mitral_valve_retractor": _family(
        match=["mitral valve retractor", "atrial retractor"],
        category="cardiothoracic - retracting",
        zones=[
            _zone("blade", "cutting_working_surface", "medium", "medium"),
            _zone("shaft", "handle_external", "low", "low"),
        ],
        min_images=1,
        manual_steps=["Inspect the blade for bending or tissue residue."],
    ),
    "chest_tube_trocar": _family(
        match=["chest tube trocar", "thoracic trocar"],
        category="cardiothoracic - lumen/access",
        zones=[
            _zone("trocar tip", "cutting_working_surface", "high", "high"),
            _zone("lumen", "lumen_scope", "critical", "high"),
            _zone("handle", "handle_external", "low", "low"),
        ],
        min_images=2,
        manual_steps=["Flush the lumen; inspect the trocar tip for dulling."],
    ),
    "debakey_forceps": _family(
        match=["debakey forceps", "debakey tissue forceps"],
        category="cardiovascular - grasping",
        zones=[
            _zone("atraumatic jaw", "cutting_working_surface", "high", "high"),
            _zone("jaw ridges", "cutting_working_surface", "high", "high"),
            _zone("hinge", "mechanical", "medium", "medium"),
            _zone("handle", "handle_external", "low", "low"),
        ],
        manual_steps=["Brush between the fine atraumatic jaw ridges under magnification."],
    ),
    # -- Urology / gynecology ------------------------------------------------
    "resectoscope": _family(
        match=["resectoscope"],
        category="urology - lumen/scope",
        zones=[
            _zone("cutting loop/electrode", "cutting_working_surface", "critical", "high"),
            _zone("working element", "mechanical", "high", "high"),
            _zone("sheath", "lumen_scope", "critical", "high"),
            _zone("obturator", "handle_external", "medium", "medium"),
        ],
        min_images=3,
        manual_steps=["Flush the sheath lumen; inspect the cutting loop/electrode for pitting."],
    ),
    "uterine_sound": _family(
        match=["uterine sound"],
        category="gynecology - probing",
        zones=[
            _zone("tip", "cutting_working_surface", "medium", "medium"),
            _zone("shaft", "handle_external", "low", "low"),
        ],
        min_images=1,
        manual_steps=["Inspect the tip and shaft for bending."],
    ),
    "uterine_curette": _family(
        match=["uterine curette", "endometrial curette"],
        category="gynecology - biting",
        zones=[
            _zone("cup tip", "cutting_working_surface", "high", "high"),
            _zone("shaft", "handle_external", "medium", "medium"),
            _zone("handle", "handle_external", "low", "low"),
        ],
        manual_steps=["Brush tissue residue from the concave cup tip."],
    ),
    "uterine_tenaculum": _family(
        match=["vulsellum forceps", "uterine tenaculum forceps"],
        category="gynecology - grasping",
        zones=[
            _zone("hook tip", "cutting_working_surface", "high", "high"),
            _zone("box lock", "mechanical", "high", "high"),
            _zone("ratchet", "mechanical", "medium", "medium"),
            _zone("handle", "handle_external", "low", "low"),
        ],
        manual_steps=["Brush the hook-tip teeth; open the box lock and brush the pivot."],
    ),
    "vaginal_speculum": _family(
        match=["vaginal speculum"],
        category="gynecology - retracting",
        zones=[
            _zone("blade", "cutting_working_surface", "low", "medium"),
            _zone("hinge/ratchet", "mechanical", "medium", "medium"),
            _zone("handle", "handle_external", "low", "low"),
        ],
        min_images=1,
        manual_steps=["Brush the hinge/ratchet; inspect blades for residue."],
    ),
    "colposcope": _family(
        match=["colposcope"],
        category="gynecology - visualization",
        zones=[
            _zone("lens", "lumen_scope", "medium", "medium"),
            _zone("focusing mechanism", "mechanical", "low", "low"),
        ],
        min_images=1,
        manual_steps=["Clean the lens surface with an approved lens solution."],
    ),
    "laparoscopic_uterine_manipulator": _family(
        match=["uterine manipulator"],
        category="gynecology - MIS",
        zones=[
            _zone("tip cup", "cutting_working_surface", "high", "high"),
            _zone("lumen/cannulated channel", "lumen_scope", "critical", "high"),
            _zone("shaft", "handle_external", "medium", "medium"),
            _zone("handle", "handle_external", "low", "low"),
        ],
        min_images=3,
        manual_steps=["Flush the internal channel; brush residue from the tip cup."],
    ),
    "urology_biopsy_forceps": _family(
        match=["urology biopsy forceps", "cystoscopic biopsy forceps"],
        category="urology - grasping",
        zones=[
            _zone("cup jaw", "cutting_working_surface", "critical", "high"),
            _zone("shaft", "lumen_scope", "medium", "medium"),
            _zone("actuation handle", "handle_external", "low", "low"),
        ],
        manual_steps=["Brush the cup jaw closely; flush the shaft channel if cannulated."],
    ),
    "lithotripsy_probe": _family(
        match=["lithotripsy probe", "laser lithotripsy fiber"],
        category="urology - powered",
        zones=[
            _zone("probe tip", "cutting_working_surface", "high", "medium"),
            _zone("fiber/shaft", "handle_external", "medium", "medium"),
            _zone("coupling connector", "mechanical", "low", "low"),
        ],
        manual_steps=["Inspect the probe tip for pitting; check fiber/shaft for kinks."],
    ),
    # -- Plastics / microsurgery ----------------------------------------------
    "micro_scissors": _family(
        match=["micro scissors", "microsurgical scissors"],
        category="plastics/micro - cutting",
        zones=[
            _zone("micro blade tip", "cutting_working_surface", "high", "medium"),
            _zone("hinge", "mechanical", "medium", "medium"),
            _zone("handle", "handle_external", "low", "low"),
        ],
        min_images=1,
        manual_steps=["Inspect the micro blade tips under magnification for nicks."],
    ),
    "micro_forceps": _family(
        match=["micro forceps", "microsurgical forceps"],
        category="plastics/micro - grasping",
        zones=[
            _zone("micro jaw tip", "cutting_working_surface", "high", "medium"),
            _zone("hinge", "mechanical", "medium", "medium"),
            _zone("handle", "handle_external", "low", "low"),
        ],
        min_images=1,
        manual_steps=["Inspect the micro jaw tip under magnification; handle with care to avoid bending."],
    ),
    "micro_needle_holder": _family(
        match=["micro needle holder", "microsurgical needle holder"],
        category="plastics/micro - grasping",
        zones=[
            _zone("micro jaw inserts", "cutting_working_surface", "high", "medium"),
            _zone("hinge", "mechanical", "medium", "medium"),
            _zone("handle", "handle_external", "low", "low"),
        ],
        min_images=1,
        manual_steps=["Inspect micro jaw inserts under magnification for grip loss."],
    ),
    "dermatome": _family(
        match=["dermatome"],
        category="plastics - powered",
        zones=[
            _zone("blade", "cutting_working_surface", "critical", "medium"),
            _zone("depth guard", "mechanical", "medium", "medium"),
            _zone("motor housing coupling", "mechanical", "low", "low"),
        ],
        manual_steps=["Confirm the blade is single-use/replaced; brush the depth guard and housing."],
    ),
    "liposuction_cannula": _family(
        match=["liposuction cannula"],
        category="plastics - lumen/suction",
        zones=[
            _zone("port openings", "lumen_scope", "critical", "high"),
            _zone("lumen", "lumen_scope", "critical", "high"),
            _zone("connector", "handle_external", "low", "low"),
        ],
        min_images=2,
        manual_steps=["Flush and brush the lumen end-to-end; confirm port openings are clear."],
    ),
    "skin_graft_mesher": _family(
        match=["skin graft mesher", "mesh dermatome"],
        category="plastics - mechanical",
        zones=[
            _zone("roller/blade assembly", "cutting_working_surface", "high", "high"),
            _zone("carrier plate slot", "mechanical", "medium", "medium"),
        ],
        manual_steps=["Brush tissue residue from the roller/blade assembly."],
    ),
    "micro_hook": _family(
        match=["micro hook", "skin hook micro"],
        category="plastics/micro - retracting",
        zones=[
            _zone("hook tip", "cutting_working_surface", "medium", "medium"),
            _zone("handle", "handle_external", "low", "low"),
        ],
        min_images=1,
        manual_steps=["Inspect the fine hook tip for bending."],
    ),
    # -- Podiatry / dental ----------------------------------------------------
    "nail_nipper": _family(
        match=["nail nipper", "podiatry nipper"],
        category="podiatry - cutting",
        zones=[
            _zone("jaw blade", "cutting_working_surface", "high", "medium"),
            _zone("hinge", "mechanical", "high", "high"),
            _zone("handle", "handle_external", "low", "low"),
        ],
        manual_steps=["Brush debris from the jaw blade and hinge."],
    ),
    "bone_rasp": _family(
        match=["bone rasp", "podiatry rasp"],
        category="podiatry/orthopedic - shaping",
        zones=[
            _zone("rasp surface", "cutting_working_surface", "critical", "high"),
            _zone("handle", "handle_external", "low", "low"),
        ],
        manual_steps=["Brush bone debris from between the rasp teeth under magnification."],
    ),
    "dental_elevator": _family(
        match=["dental elevator", "periosteal elevator dental"],
        category="dental - elevating",
        zones=[
            _zone("blade tip", "cutting_working_surface", "medium", "medium"),
            _zone("shaft", "handle_external", "low", "low"),
            _zone("handle", "handle_external", "low", "low"),
        ],
        min_images=1,
        manual_steps=["Inspect the blade tip for bending; brush any tissue residue."],
    ),
    "dental_extraction_forceps": _family(
        match=["dental extraction forceps", "tooth extraction forceps"],
        category="dental - grasping",
        zones=[
            _zone("jaw beaks", "cutting_working_surface", "high", "high"),
            _zone("hinge", "mechanical", "high", "high"),
            _zone("handle", "handle_external", "low", "low"),
        ],
        manual_steps=["Brush the jaw beak serrations closely; brush the hinge pivot."],
    ),
    "root_tip_pick": _family(
        match=["root tip pick", "dental root pick"],
        category="dental - elevating",
        zones=[
            _zone("tip", "cutting_working_surface", "medium", "medium"),
            _zone("shaft", "handle_external", "low", "low"),
        ],
        min_images=1,
        manual_steps=["Inspect the fine tip for bending or dulling."],
    ),
    "dental_scaler": _family(
        match=["dental scaler"],
        category="dental - scraping",
        zones=[
            _zone("working tip", "cutting_working_surface", "high", "medium"),
            _zone("handle", "handle_external", "low", "low"),
        ],
        min_images=1,
        manual_steps=["Brush calculus/debris from the working tip under magnification."],
    ),
    "dental_curette": _family(
        match=["dental curette", "periodontal curette"],
        category="dental - scraping",
        zones=[
            _zone("cutting edge", "cutting_working_surface", "high", "medium"),
            _zone("shaft", "handle_external", "low", "low"),
            _zone("handle", "handle_external", "low", "low"),
        ],
        min_images=1,
        manual_steps=["Brush debris from the curette's cutting edge."],
    ),
    "periosteal_elevator": _family(
        match=["periosteal elevator"],
        category="orthopedic/dental - elevating",
        zones=[
            _zone("blade tip", "cutting_working_surface", "medium", "medium"),
            _zone("shaft", "handle_external", "low", "low"),
            _zone("handle", "handle_external", "low", "low"),
        ],
        min_images=1,
        manual_steps=["Inspect the blade tip for bending; brush residue."],
    ),
    # -- MIS / laparoscopic expansion -----------------------------------------
    "veress_needle": _family(
        match=["veress needle"],
        category="MIS - access",
        zones=[
            _zone("spring-loaded tip", "mechanical", "critical", "high"),
            _zone("lumen", "lumen_scope", "critical", "high"),
            _zone("stopcock", "mechanical", "medium", "medium"),
        ],
        min_images=2,
        manual_steps=["Flush the lumen; confirm the spring-loaded tip retracts and extends freely."],
    ),
    "robotic_instrument_arm": _family(
        match=["robotic instrument arm", "robotic wristed instrument"],
        category="MIS - robotic",
        zones=[
            _zone("wristed end effector", "cutting_working_surface", "critical", "high"),
            _zone("cable/pulley mechanism", "mechanical", "critical", "high"),
            _zone("shaft", "handle_external", "medium", "medium"),
            _zone("interface disc", "mechanical", "medium", "medium"),
        ],
        min_images=3,
        manual_steps=["Inspect the cable/pulley mechanism for fraying; brush the wristed end effector."],
    ),
    "camera_head_laparoscopic": _family(
        match=["laparoscopic camera head", "endoscopic camera head"],
        category="MIS - visualization",
        zones=[
            _zone("lens window", "lumen_scope", "medium", "medium"),
            _zone("cable connector", "mechanical", "low", "low"),
            _zone("housing", "handle_external", "low", "low"),
        ],
        min_images=1,
        manual_steps=["Clean the lens window with an approved lens solution; inspect the cable connector."],
    ),
    "laparoscopic_stapler": _family(
        match=["laparoscopic stapler", "endoscopic stapler"],
        category="MIS - stapling",
        zones=[
            _zone("anvil/staple jaw", "cutting_working_surface", "critical", "high"),
            _zone("firing mechanism", "mechanical", "high", "high"),
            _zone("shaft", "handle_external", "medium", "medium"),
            _zone("handle", "handle_external", "low", "low"),
        ],
        min_images=3,
        manual_steps=["Brush tissue/staple debris from the anvil jaw; confirm the firing mechanism resets fully."],
    ),
    "laparoscopic_clip_applier": _family(
        match=["laparoscopic clip applier", "endoscopic clip applier"],
        category="MIS - clipping",
        zones=[
            _zone("jaw tip", "cutting_working_surface", "high", "high"),
            _zone("clip feed mechanism", "mechanical", "high", "high"),
            _zone("shaft", "handle_external", "medium", "medium"),
            _zone("handle", "handle_external", "low", "low"),
        ],
        min_images=3,
        manual_steps=["Brush the jaw tip and clip feed mechanism; confirm smooth clip advancement."],
    ),
    "hand_assist_port": _family(
        match=["hand assist port", "hand-assist device"],
        category="MIS - access",
        zones=[
            _zone("seal ring", "handle_external", "critical", "medium"),
            _zone("sleeve", "lumen_scope", "medium", "medium"),
            _zone("base ring", "handle_external", "low", "low"),
        ],
        min_images=1,
        manual_steps=["Inspect the seal ring for tears or degradation."],
    ),
    # -- Energy devices --------------------------------------------------------
    "harmonic_scalpel_handpiece": _family(
        match=["harmonic scalpel handpiece", "ultrasonic shears"],
        category="energy device - powered",
        zones=[
            _zone("blade tip", "cutting_working_surface", "critical", "high"),
            _zone("clamp arm pad", "cutting_working_surface", "high", "high"),
            _zone("transducer coupling", "mechanical", "medium", "medium"),
        ],
        min_images=2,
        manual_steps=["Inspect the clamp arm pad for wear/tissue buildup; check blade tip alignment."],
    ),
    "ligasure_handpiece": _family(
        match=["ligasure handpiece", "vessel sealing handpiece"],
        category="energy device - powered",
        zones=[
            _zone("sealing jaw", "cutting_working_surface", "critical", "high"),
            _zone("cutting element", "cutting_working_surface", "high", "high"),
            _zone("shaft", "handle_external", "medium", "medium"),
        ],
        min_images=2,
        manual_steps=["Brush tissue char from the sealing jaw surfaces; inspect the cutting element."],
    ),
    "argon_beam_probe": _family(
        match=["argon beam probe", "argon beam coagulator probe"],
        category="energy device - coagulating",
        zones=[
            _zone("electrode tip", "cutting_working_surface", "high", "medium"),
            _zone("gas lumen", "lumen_scope", "high", "high"),
            _zone("insulated shaft", "handle_external", "critical", "medium"),
        ],
        min_images=2,
        manual_steps=["Flush the gas lumen; inspect the insulated shaft for breaches."],
    ),
    "monopolar_pencil": _family(
        match=["monopolar pencil", "monopolar cautery pencil"],
        category="general surgery - electrosurgical",
        zones=[
            _zone("electrode tip", "cutting_working_surface", "high", "medium"),
            _zone("tip receptacle", "mechanical", "medium", "medium"),
            _zone("insulated shaft", "handle_external", "critical", "medium"),
        ],
        manual_steps=["Inspect the insulated shaft for breaches; clean carbon buildup from the electrode tip."],
    ),
    # -- Suction / irrigation / accessories ------------------------------------
    "irrigation_cannula": _family(
        match=["irrigation cannula"],
        category="general surgery - suction/irrigation",
        zones=[
            _zone("tip opening", "lumen_scope", "critical", "high"),
            _zone("lumen", "lumen_scope", "critical", "high"),
            _zone("connector", "handle_external", "low", "low"),
        ],
        min_images=2,
        manual_steps=["Flush the lumen end-to-end; confirm the tip opening is clear."],
    ),
    "bulb_syringe": _family(
        match=["bulb syringe", "ear syringe bulb"],
        category="general - irrigation",
        zones=[
            _zone("tip", "lumen_scope", "medium", "medium"),
            _zone("bulb interior", "lumen_scope", "high", "high"),
        ],
        min_images=1,
        manual_steps=["Flush and inspect the bulb interior for retained fluid/debris."],
    ),
    "biopsy_punch": _family(
        match=["biopsy punch", "skin biopsy punch"],
        category="general surgery - biting",
        zones=[
            _zone("cutting edge", "cutting_working_surface", "high", "medium"),
            _zone("lumen", "lumen_scope", "medium", "medium"),
            _zone("handle", "handle_external", "low", "low"),
        ],
        min_images=1,
        manual_steps=["Inspect the circular cutting edge for nicks; flush the lumen."],
    ),
    "wound_probe": _family(
        match=["wound probe", "fistula probe"],
        category="general surgery - probing",
        zones=[
            _zone("tip", "cutting_working_surface", "low", "medium"),
            _zone("shaft", "handle_external", "low", "low"),
        ],
        min_images=1,
        manual_steps=["Inspect the tip and shaft for bending."],
    ),
    # -- Containers / trays -----------------------------------------------------
    "rigid_sterilization_container": _family(
        match=["rigid sterilization container", "rigid container system"],
        category="SPD - containment",
        zones=[
            _zone("filter/valve", "mechanical", "critical", "high"),
            _zone("gasket seal", "handle_external", "high", "high"),
            _zone("latch mechanism", "mechanical", "medium", "medium"),
        ],
        min_images=2,
        manual_steps=["Inspect the gasket seal for cracking; confirm the filter/valve seats and the latch engages fully."],
    ),
    "wire_basket_tray": _family(
        match=["wire basket tray", "instrument wire tray"],
        category="SPD - containment",
        zones=[
            _zone("wire mesh", "handle_external", "medium", "medium"),
            _zone("corner welds", "mechanical", "medium", "medium"),
        ],
        min_images=1,
        manual_steps=["Inspect corner welds for cracking; confirm mesh openings are unobstructed."],
    ),
    "instrument_mat_tray": _family(
        match=["instrument mat tray", "silicone mat tray"],
        category="SPD - containment",
        zones=[
            _zone("peg/finger mounts", "handle_external", "medium", "medium"),
            _zone("mat surface", "handle_external", "low", "low"),
        ],
        min_images=1,
        manual_steps=["Inspect peg/finger mounts for tearing; confirm the mat surface is intact."],
    ),
}


# ── Instrument anatomy definitions ───────────────────────────────────────────
# Keyed by canonical instrument family. `match` keywords resolve free-text
# instrument_type onto a family. Extend by adding entries — no manufacturer is
# hardcoded.
INSTRUMENT_ANATOMY: dict[str, dict] = {
    **_EXPANSION_FAMILIES,
    # Flexible endoscopes are declared BEFORE rigid scopes so their specific
    # keywords resolve first (a rigid scope's generic "scope"/"endoscope" match
    # would otherwise swallow them).
    "flexible_endoscope": {
        "category": "flexible endoscope",
        "match": [
            "flexible", "flex scope", "colonoscope", "gastroscope", "bronchoscope",
            "duodenoscope", "enteroscope", "sigmoidoscope", "choledochoscope",
            "flexible ureteroscope", "flexible cystoscope",
        ],
        "zones": [
            _zone("distal end", "lumen_scope", "critical", "high"),
            _zone("bending section", "lumen_scope", "high", "high"),
            _zone("insertion tube", "handle_external", "medium", "medium"),
            _zone("suction channel", "lumen_scope", "critical", "high"),
            _zone("biopsy channel", "lumen_scope", "critical", "high"),
            _zone("air/water nozzle", "lumen_scope", "high", "high"),
            _zone("light guide lens", "lumen_scope", "medium", "medium"),
            _zone("control body", "handle_external", "low", "low"),
        ],
        "required_images": ["distal end", "biopsy channel", "suction channel", "bending section", "control body"],
        "recommended_image_angles": ["distal end-on", "channel opening", "bending section", "control body"],
        "min_images": 4,
        "manual_steps": [
            "Flush and brush the biopsy and suction channels; leak-test the endoscope.",
            "Borescope the internal channels if available — retained soil hides inside pathways.",
            "Inspect the distal end, air/water nozzle, and bending section closely.",
        ],
    },
    "rigid_scope": {
        "category": "rigid endoscope",
        "match": ["rigid scope", "scope", "endoscope", "arthroscope", "cystoscope", "laparoscope camera", "hysteroscope", "ureteroscope"],
        "zones": [
            _zone("distal tip", "lumen_scope", "high", "high"),
            _zone("lens edge", "lumen_scope", "medium", "medium"),
            _zone("o-ring area", "lumen_scope", "high", "high"),
            _zone("light post", "lumen_scope", "medium", "medium"),
            _zone("eyepiece", "handle_external", "low", "low"),
            _zone("working channel", "lumen_scope", "critical", "high"),
            _zone("sheath connection", "lumen_scope", "high", "high"),
            _zone("seal", "lumen_scope", "high", "high"),
        ],
        "required_images": ["distal tip", "o-ring area", "light post", "lens edge", "working channel"],
        "recommended_image_angles": ["distal end-on", "side profile", "port-on"],
        "min_images": 3,
        "manual_steps": [
            "Flush and brush the working channel; borescope if available.",
            "Inspect the o-ring/seal for soil and wear.",
            "Check the distal tip and lens edge under magnification.",
        ],
    },
    "drill_bit": {
        "category": "rotary orthopedic",
        "match": ["drill", "bit", "reamer", "burr"],
        "zones": [
            _zone("tip", "rotary_orthopedic", "high", "high"),
            _zone("flutes", "rotary_orthopedic", "critical", "high"),
            _zone("threaded region", "rotary_orthopedic", "high", "high"),
            _zone("cutting edge", "rotary_orthopedic", "high", "medium"),
            _zone("shank", "handle_external", "low", "low"),
            _zone("hub", "mechanical", "medium", "medium"),
        ],
        "required_images": ["flutes", "threaded region", "tip", "hub"],
        "recommended_image_angles": ["flute close-up", "tip end-on", "shank/hub"],
        "min_images": 3,
        "manual_steps": [
            "Brush the flutes and threaded region; confirm no residue between spirals.",
            "Inspect the cutting tip for wear and residue.",
        ],
    },
    "kerrison_rongeur": {
        "category": "orthopedic biter",
        "match": ["kerrison", "rongeur", "punch", "biter"],
        "zones": [
            _zone("jaw", "cutting_working_surface", "high", "high"),
            _zone("serrations", "cutting_working_surface", "high", "high"),
            _zone("box lock", "mechanical", "high", "high"),
            _zone("hinge", "mechanical", "high", "high"),
            _zone("spring", "mechanical", "medium", "medium"),
            _zone("ratchet", "mechanical", "high", "high"),
            _zone("handle", "handle_external", "low", "low"),
        ],
        "required_images": ["jaw", "serrations", "box lock", "hinge", "spring", "ratchet"],
        "recommended_image_angles": ["jaw close-up", "box lock", "hinge/spring"],
        "min_images": 3,
        "manual_steps": [
            "Open the box lock and brush the pivot; actuate the hinge.",
            "Brush the jaw serrations and spring channel.",
        ],
    },
    "scissors": {
        "category": "cutting",
        "match": ["scissor", "shear"],
        "zones": [
            _zone("tip", "cutting_working_surface", "medium", "medium"),
            _zone("blade", "cutting_working_surface", "medium", "medium"),
            _zone("cutting edge", "cutting_working_surface", "medium", "medium"),
            _zone("serration", "cutting_working_surface", "high", "high"),
            _zone("box lock", "mechanical", "high", "high"),
            _zone("handle", "handle_external", "low", "low"),
        ],
        "required_images": ["blade", "cutting edge", "box lock"],
        "recommended_image_angles": ["blade side", "box lock", "tip close-up"],
        "min_images": 2,
        "manual_steps": [
            "Inspect the cutting edge and tip; brush any serrations.",
            "Open and brush the box lock.",
        ],
    },
    "needle_holder": {
        "category": "grasping",
        "match": ["needle holder", "needle_holder", "needle-holder"],
        "zones": [
            _zone("jaw inserts", "cutting_working_surface", "high", "high"),
            _zone("serrations", "cutting_working_surface", "high", "high"),
            _zone("box lock", "mechanical", "high", "high"),
            _zone("ratchet", "mechanical", "high", "high"),
            _zone("tungsten carbide inserts", "cutting_working_surface", "medium", "medium"),
            _zone("handle", "handle_external", "low", "low"),
        ],
        "required_images": ["jaw inserts", "serrations", "box lock", "ratchet"],
        "recommended_image_angles": ["jaw close-up", "box lock", "ratchet"],
        "min_images": 2,
        "manual_steps": [
            "Brush the jaw inserts and serrations.",
            "Open the box lock and brush the ratchet teeth.",
        ],
    },
    "laparoscopic": {
        "category": "MIS / laparoscopic",
        "match": ["laparoscop", "grasper", "maryland", "dissector", "bipolar", "monopolar", "trocar", "cannula"],
        "zones": [
            _zone("distal jaws", "cutting_working_surface", "high", "high"),
            _zone("hinge", "mechanical", "high", "high"),
            _zone("insulation edge", "handle_external", "critical", "high"),
            _zone("shaft", "handle_external", "medium", "medium"),
            _zone("handle seam", "handle_external", "high", "high"),
            _zone("rotation knob", "mechanical", "medium", "medium"),
            _zone("lumen/cannulated channel", "lumen_scope", "critical", "high"),
        ],
        "required_images": ["distal jaws", "insulation edge", "shaft", "handle seam", "rotation knob"],
        "recommended_image_angles": ["distal jaws", "insulation length", "handle seam"],
        "min_images": 3,
        "manual_steps": [
            "Flush the lumen/cannulated channel if present.",
            "Inspect the full insulation length for breaches; test integrity.",
            "Brush the distal jaws and handle seam.",
        ],
    },
    "general_forceps": {
        "category": "grasping / clamping",
        "match": ["forcep", "hemostat", "clamp", "kocher", "mosquito", "kelly", "allis", "babcock", "tissue forcep"],
        "zones": [
            _zone("jaws", "cutting_working_surface", "high", "high"),
            _zone("serrations", "cutting_working_surface", "high", "high"),
            _zone("box lock", "mechanical", "high", "high"),
            _zone("hinge", "mechanical", "high", "high"),
            _zone("ratchet", "mechanical", "high", "high"),
            _zone("handle", "handle_external", "low", "low"),
        ],
        "required_images": ["jaws", "serrations", "box lock", "hinge"],
        "recommended_image_angles": ["jaw close-up", "box lock", "hinge/ratchet"],
        "min_images": 2,
        "manual_steps": [
            "Open the box lock and brush the pivot; actuate the hinge and ratchet.",
            "Brush the jaw serrations and re-inspect under magnification.",
        ],
    },
    "default": {
        "category": "general instrument",
        "match": [],
        "zones": [
            _zone("working surface", "cutting_working_surface", "medium", "medium"),
            _zone("hinge/joint", "mechanical", "high", "high"),
            _zone("box lock", "mechanical", "high", "high"),
            _zone("handle", "handle_external", "low", "low"),
        ],
        "required_images": ["working surface", "hinge/joint"],
        "recommended_image_angles": ["overall", "working surface", "joint close-up"],
        "min_images": 1,
        "manual_steps": [
            "Inspect the working surface and any hinge/box lock.",
        ],
    },
}


def list_anatomy_families() -> list[dict]:
    """Summary of every declared anatomy family, for the Anatomy Library page.
    Excludes the ``default`` fallback (that is the generic profile, not a family)."""
    return [
        {
            "family": family,
            "category": defn["category"],
            "zone_names": [z["zone_name"] for z in defn["zones"]],
            "required_images": defn["required_images"],
            "min_images": defn["min_images"],
            "high_risk_zones": [
                z["zone_name"] for z in defn["zones"]
                if z["zone_risk_level"] in ("high", "critical") or z["retention_risk"] == "high"
            ],
        }
        for family, defn in INSTRUMENT_ANATOMY.items()
        if family != "default"
    ]


def resolve_family(instrument_type: str) -> str:
    """Resolve free-text instrument_type onto an anatomy family key.

    Two normalizations, both fixing real gaps found by review:

    1. Underscore/hyphen slugs (e.g. "towel_clamp" — the canonical form the
       inspection form actually submits via its slug-fallback validator)
       are normalized to spaces before matching, so they resolve the same
       way as the human-readable form ("towel clamp") every match keyword
       is written in.
    2. The LONGEST matching keyword across every family wins, not simply
       the first family declared in dict order. A first-match scheme let a
       later, more specific alias (e.g. "uterine tenaculum forceps") get
       shadowed by an earlier, shorter generic keyword from a different
       family ("tenaculum") that also happens to be a substring — since
       family declaration order can't simultaneously satisfy every pair of
       specific/generic keywords as more families are added, matching on
       specificity (keyword length) instead of declaration order is the
       fix that scales.
    """
    def _norm(s: str) -> str:
        return s.replace("_", " ").replace("-", " ")

    name = _norm((instrument_type or "").lower())
    best_family: str | None = None
    best_len = 0
    for family, defn in INSTRUMENT_ANATOMY.items():
        if family == "default":
            continue
        for k in defn["match"]:
            k_norm = _norm(k)
            if k_norm in name and len(k_norm) > best_len:
                best_family = family
                best_len = len(k_norm)
    return best_family or "default"


def get_anatomy(instrument_type: str) -> dict:
    """Full anatomy definition for an instrument type."""
    family = resolve_family(instrument_type)
    defn = INSTRUMENT_ANATOMY[family]
    zones = defn["zones"]
    return {
        "family": family,
        "category": defn["category"],
        "zones": zones,
        "zone_names": [z["zone_name"] for z in zones],
        "high_risk_zones": [
            z["zone_name"] for z in zones
            if z["zone_risk_level"] in ("high", "critical") or z["retention_risk"] == "high"
            or z["zone_name"] in HIGH_RETENTION_ZONES
        ],
        "required_images": defn["required_images"],
        "recommended_image_angles": defn["recommended_image_angles"],
        "min_images": defn["min_images"],
        "manual_steps": defn["manual_steps"],
    }


def _zone_description(z: dict) -> str:
    """Human-readable, honest one-liner per zone (from the zone's risk profile)."""
    from app.services.instrument_zones import ZONE_INFO

    info = ZONE_INFO.get(z["zone_name"].lower())
    if info and info.get("reason"):
        return info["reason"]
    retention = z["retention_risk"]
    if retention == "high":
        return f"{z['zone_name'].capitalize()} is a high-retention zone where residual soil can persist after cleaning."
    return f"{z['zone_name'].capitalize()} ({z['zone_category'].replace('_', ' ')}); {z['zone_risk_level']} inherent risk."


def anatomy_profile(
    instrument_type: str,
    manufacturer: str | None = None,
    model: str | None = None,
    instrument_name: str | None = None,
) -> dict:
    """Architecture step 2 — the Anatomy Profile Service.

    Given an instrument's type (and optionally name/manufacturer/model), return
    the full anatomy profile the AI pipeline reasons over: family, anatomy zones,
    required zones, high-risk zones, per-zone descriptions, contamination/condition
    risks, recommended image views, and manual-check steps.

    When the instrument cannot be classified the family resolves to ``unknown``
    and a generic high-risk SPD profile is returned with a supervisor-review
    warning — nothing is fabricated as a specific match.
    """
    # Consider every available identity hint when resolving the family.
    hint = " ".join(x for x in (instrument_type, instrument_name, model, manufacturer) if x)
    family = resolve_family(hint or (instrument_type or ""))
    profile_found = family != "default"
    defn = INSTRUMENT_ANATOMY[family]
    zones = defn["zones"]
    base = get_anatomy(hint or (instrument_type or ""))

    return {
        **base,
        # `family` is a real family key when matched, else the honest "unknown".
        "instrument_family": family if profile_found else "unknown",
        "profile_found": profile_found,
        "manufacturer": manufacturer or "",
        "model": model or "",
        "anatomy_zones": base["zone_names"],
        "required_zones": defn["required_images"],
        "recommended_image_views": defn["required_images"],
        "zone_descriptions": {z["zone_name"]: _zone_description(z) for z in zones},
        "contamination_risks": {z["zone_name"]: z["contamination_risks"] for z in zones},
        "condition_risks": {z["zone_name"]: z["condition_risks"] for z in zones},
        "manual_check_steps": defn["manual_steps"],
        "warning": (
            None if profile_found else
            "Instrument anatomy profile not found. Supervisor review recommended."
        ),
    }

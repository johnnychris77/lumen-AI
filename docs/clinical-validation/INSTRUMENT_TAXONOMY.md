# LumenAI — Instrument Taxonomy

Objective 2 review. `instrument_family` (`app/models/instrument_knowledge.py`) and `Inspection.instrument_type` are both free-text (`String(100)`) — there is no hard database enum anywhere. The nearest thing to a controlled vocabulary is `_ALLOWED_INSTRUMENT_TYPES` in `app/routes/inspections.py` (15 values: `rigid_scope`, `flexible_endoscope`, `drill_bit`, `kerrison_rongeur`, `laparoscopic_grasper`, `retractor`, `scissors`, `needle_holder`, `forceps`, `trocar`, `electrosurgical`, `suction_irrigation`, `clip_applier`, `stapler`, `other`) — but even this allows any lowercase slug matching `^[a-z0-9]+(?:_[a-z0-9]+)*$`, so it is a soft guardrail, not a closed enum.

The real anatomy/knowledge taxonomy is **112 instrument families** (`app/services/instrument_anatomy.py`'s `INSTRUMENT_ANATOMY` dict, plus a `default` fallback), documented as the "v1.10 instrument knowledge expansion" (`docs/instrument-knowledge/v1.10-instrument-knowledge-expansion.md`), spanning general surgery, orthopedics, neurosurgery, ENT, ophthalmology, cardiothoracic/vascular, urology/gynecology, plastics/microsurgery, podiatry/dental, and the MIS/laparoscopic expansion.

## Verification against the brief's 12 example families

| Family | Modeled? | Evidence |
|---|---|---|
| Kerrisons | Yes | `INSTRUMENT_ANATOMY["kerrison_rongeur"]`, `INSTRUMENT_FAMILY_PROFILES["kerrison"]`, real seed data (`"Kerrison Rongeur 3mm"`) |
| Rongeurs | Yes | `kerrison_rongeur`, plus dedicated `pituitary_rongeur`, `laminectomy_rongeur` |
| **Osteotomes** | **No — not found anywhere** | `grep -ri osteotome` across backend, docs, and frontend returns zero matches. Not a family, not a keyword, not a test fixture, not documented. **This is a real gap, not an oversight in this review — it should not be listed as a supported family in any customer-facing material until it is actually modeled.** |
| Forceps | Yes | `general_forceps` (matches forcep/hemostat/clamp/kocher/mosquito/kelly/allis/babcock/tissue forcep) plus 10+ specialty forceps families |
| Clamps | Yes | `towel_clamp`, `vascular_clamp`, `right_angle_clamp`, `intestinal_clamp`, `bone_reduction_clamp`, plus "clamp" as a `general_forceps` keyword |
| Needle holders | Yes | `needle_holder` (original 8) + `micro_needle_holder` |
| Retractors | **Yes, but as an assembled category, not one literal family** | `rib_approximator`, `sternal_retractor`, `self_retaining_retractor`, `handheld_retractor`, `brain_retractor`, `lid_retractor`, `mitral_valve_retractor` — no single `INSTRUMENT_ANATOMY["retractor"]` entry; "retractor" is a category label spanning several concrete families |
| Scissors | Yes | `scissors` (original 8) + `iris_scissors`, `corneal_scissors`, `micro_scissors` |
| Rigid scopes | Yes | `rigid_scope`, kept deliberately distinct from `flexible_endoscope` |
| Cannulated instruments | **Yes, but as a cross-cutting attribute, not a standalone family** | `INSTRUMENT_FAMILY_PROFILES["cannulated_instruments"]` exists and points at `orthopedic_reamer`'s cannulation zone; "cannulated"/"cannula" keywords route to `orthopedic_reamer`, `orthopedic_screwdriver`, `laparoscopic` — there is no `INSTRUMENT_ANATOMY["cannulated_instrument"]` entry of its own |
| Powered orthopedic instruments | **Yes, conceptually, but not under that literal name** | Category `"orthopedic - powered"` covers `oscillating_saw`, `sagittal_saw`, `reciprocating_saw`, `cast_saw`, `k_wire_driver`, `cranial_perforator`; the literal phrase "powered orthopedic" never appears as a key |
| Laparoscopic instruments | Yes | `laparoscopic` (original 8) + MIS-expansion families `laparoscopic_stapler`, `laparoscopic_clip_applier`, `veress_needle`, `robotic_instrument_arm`, `camera_head_laparoscopic`, `hand_assist_port`, `laparoscopic_uterine_manipulator` |

**Verdict**: 11 of the brief's 12 example families have real, verifiable modeling; **osteotomes have none**. Three families (retractors, cannulated instruments, powered orthopedic instruments) are supported as assembled categories spanning multiple concrete families rather than one single named entry — clinical/sales material should describe these as categories, not claim a literal 1:1 family match.

## Naming consistency finding

Naming is not fully uniform across layers: the anatomy layer uses `kerrison_rongeur`, seed/demo data uses `"Kerrison Rongeur 3mm"`, and the knowledge-graph profile layer (`INSTRUMENT_FAMILY_PROFILES`, 10 keys) uses the shorter `kerrison`. This is a cosmetic/documentation consistency issue, not a data-integrity one — each layer's internal usage is self-consistent, but a reader moving between layers will see three different spellings for the same instrument. Recommend a canonical display-name mapping table as a Phase 4 follow-up (does not require a schema change).

## Anatomy zones and terminology

See [ANATOMY_REFERENCE.md](./ANATOMY_REFERENCE.md) for the full zone taxonomy, per-zone metadata, and inspection-coverage model that each instrument family's anatomy definition composes.

## `InstrumentKnowledge` fields (the knowledge-library record backing each family)

`manufacturer`, `model`, `instrument_family`, `ifu_reference` (free-text, unstructured — see [AI_LIMITATIONS.md](./AI_LIMITATIONS.md)), `anatomy_zones`/`high_risk_zones`/`known_failure_modes` (JSON-encoded lists), `maintenance_interval`, `repair_criteria`, `replacement_criteria`. This is a knowledge-library row, not a device master record — it carries no regulatory clearance or risk-classification field, consistent with LumenAI's scope as a decision-support tool rather than a device registry of record.

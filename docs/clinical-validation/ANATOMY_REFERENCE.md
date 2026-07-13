# LumenAI — Anatomy Reference

Objective 3 review. Anatomy-zone logic is real orchestration wrapping (`app/agents/anatomy_agent.py`) over two service layers: `app/services/instrument_zones.py` (the taxonomy/risk layer) and `app/services/instrument_anatomy.py` (the per-family zone definition layer, 112 families).

## Zone category taxonomy

`ZONE_TAXONOMY` defines 6 top-level categories, each a bucket of concrete zone strings:

| Category | Example zones |
|---|---|
| `cutting_working_surface` | serrations, grooves, teeth, jaws, cutting edge |
| `rotary_orthopedic` | drill-bit flute, threaded region, cutting channel, burr surface |
| `lumen_scope` | lumen opening, inner channel, o-ring area, rigid scope port, lens edge, sheath connection |
| `mechanical` | hinge, box lock, joint, ratchet, spring area |
| `handle_external` | handle seam, insulation edge, outer sheath, surface discoloration area |
| `unknown` | unspecified region, image quality insufficient |

## Per-zone metadata (Objective 3's required fields, verified against what actually exists)

Every named zone in `ZONE_INFO` (18 entries) carries, per the brief's requirement:

| Required field | What actually exists |
|---|---|
| Purpose | Implicit in the zone name/category; not a separate prose field |
| Clinical significance | `risk` (low/medium/high) + `reason` (a short clinical-rationale string) |
| Common findings | `TYPICAL_FINDINGS_BY_CATEGORY` (in `instrument_anatomy.py`) attaches a default contamination/condition vocabulary per zone category; every per-family zone declaration additionally carries its own `contamination_risks`/`condition_risks` |
| Known inspection challenges | `manual_check` (a recommended human action per zone) plus the explicit, honest caveat in `instrument_zones.py`'s own docstring that instrument→zone mapping is "the same placeholder-grade heuristic... NOT pixel-level localization," with confidence capped at 0.7 |

`HIGH_RETENTION_ZONES` is a separate, explicit set flagging zones where soil is disproportionately hard to remove (e.g. box locks, serrations, lumens) — this is the zone-level equivalent of a "known inspection challenge" flag and should be read alongside `manual_check` guidance.

## Instrument → zone mapping

`_INSTRUMENT_ZONE_RULES` (`instrument_zones.py`) is a deterministic keyword-substring match producing a `(contamination_zone, condition_zone)` pair per instrument type — not real per-pixel image localization. `_zone_confidence()` caps its output at 0.70, which is itself an honest signal that this is a heuristic, not a measured detection confidence. The richer, family-specific zone list per instrument (112 families) lives in `instrument_anatomy.py`'s `INSTRUMENT_ANATOMY` dict, each entry declaring its own zones via `_zone()` calls carrying `zone_risk_level`, `retention_risk`, `contamination_risks`, and `condition_risks`.

## `AnatomyProfile` — the separate standardized taxonomy (Genesis AI)

`app/models/genesis_ai_intelligence_cloud.py`'s `AnatomyProfile` (`profile_type`, `name`, `description`, `standard_terminology_json`, `zones_json`) is a reference taxonomy explicitly documented as **not** foreign-key-linked to either `RegistryInstrument.anatomy_profile_id` or `InstrumentKnowledge.instrument_family` — both of those predate `AnatomyProfile` and remain free-text. This is a real integration gap: two anatomy systems exist (the operational `instrument_zones.py`/`instrument_anatomy.py` pair used at inspection time, and the standardized `AnatomyProfile` reference table), and they are not currently reconciled into one canonical source. Flagged in [AI_LIMITATIONS.md](./AI_LIMITATIONS.md); a unification pass is a reasonable Phase 4 candidate but is out of scope for this documentation-only review.

## Inspection coverage

Coverage completeness (whether an inspection actually captured every clinically-relevant zone for a given instrument) is computed by `inspection_coverage.compute_coverage` and consumed by Veritas's evidence-readiness scoring (`limited`/`insufficient` coverage categories subtract 15-30 points from the readiness score — see [CLINICAL_RECOMMENDATIONS.md](./CLINICAL_RECOMMENDATIONS.md)). Incomplete anatomy coverage is a real, tested scenario (`test_veritas_evidence.py::test_missing_critical_zone_lowers_evidence_readiness`) — see [CLINICAL_VALIDATION_PLAN.md](./CLINICAL_VALIDATION_PLAN.md).

## Terminology consistency

The zone/category naming is internally consistent within `instrument_zones.py`/`instrument_anatomy.py`. The one cross-system inconsistency is the `AnatomyProfile` disconnection noted above — its `standard_terminology_json` is a separate vocabulary not reconciled with the operational zone strings used elsewhere.

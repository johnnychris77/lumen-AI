# LumenAI Instrument Intelligence Architecture

LumenAI reasons the way an experienced SPD educator does: from the instrument,
to its anatomy, to the specific high-retention zone, to the finding, to a
zone-weighted risk, to a clinical decision, and finally to a plain-language
mentor explanation. This document is the canonical description of that
architecture and must be preserved by all AI analysis changes.

## The preserved sequence

Every AI analysis follows this pipeline. Do not bypass it.

```
1. Identify instrument type          (inspection intake / decoded identifier)
2. Load instrument anatomy profile   (instrument_anatomy.anatomy_profile)
3. Determine required inspection zones (anatomy.required_zones)
4. Analyze uploaded image / metadata (baseline_comparison_scoring_service)
5. Assign findings to anatomy zones  (instrument_zones.zone_fields — pilot)
6. Apply zone-specific SPD risk rules (zone risk + retention escalation)
7. Generate clinical decision        (build_clinical_decision / _overall_result)
8. Generate AI mentor explanation    (clinical_mentor.build_mentor)
9. Store supervisor feedback         (SupervisorReview — labeled training data)
```

```
Instrument ─▶ Anatomy ─▶ Zone ─▶ Finding ─▶ Risk ─▶ Clinical Decision ─▶ Mentor
     │            │         │                 │
 resolve_     get_anatomy  zone_fields   zone_risk +      build_clinical_decision
 family()     / anatomy_   (pilot_zone_  retention        + build_mentor()
              profile()    assignment)   escalation
```

## Instrument families

Each family carries its own anatomy profile (zones, high-risk subset, required
image views, manual-check steps). Supported families:

- `rigid_scope` — rigid endoscope
- `flexible_endoscope` — flexible endoscope (distinct from rigid scope)
- `drill_bit` — rotary orthopedic
- `kerrison_rongeur` — orthopedic biter
- `scissors` — cutting
- `needle_holder` — grasping
- `laparoscopic` — MIS / laparoscopic
- `general_forceps` — grasping / clamping
- `default` → reported as `unknown` — generic high-risk SPD profile + warning

## Honesty guarantees

- Zone assignment is **pilot logic** (`pilot_zone_assignment`), not pixel-level
  CV segmentation. It is deterministic from instrument type + tagged views.
- No fabricated heatmaps, overlays, or metrics.
- `human_review_required: true` on all correlation/decision outputs.
- Unknown instruments never masquerade as a specific match — they resolve to
  `unknown` with a supervisor-review warning.
- No FDA clearance or regulatory-approval claims.

## Future true-CV roadmap

The schema is CV-ready: a trained zone-localization model drops into
`zone_fields`/`build_risk_map` without changing the pipeline. Supervisor
zone/family corrections (§9) are captured today as the labeled dataset for that
future model. See `zone-assignment-engine.md` for the migration path.

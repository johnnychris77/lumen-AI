# Educational Knowledge Library (v1.4)

## What it does
`backend/app/services/education_library.py` exposes a structured knowledge
article for each of the twelve contamination/condition categories LumenAI
recognizes: Blood, Bone, Tissue, Organic residue, Debris, Rust, Corrosion,
Cracks, Wear, Pitting, Missing component, Insulation damage.

Nothing here is duplicated content — every article is reshaped from the same
source of truth the AI Mentor already uses
(`clinical_mentor.FINDING_EDUCATION`) plus the corrective-action chains from
`spd_mentor_engine.py`, so the library and the live coaching can never drift
apart.

## Article shape
```
{
  "finding": "crack",
  "finding_type": "crack",
  "definition": "...",
  "clinical_importance": "...",
  "typical_anatomy_locations": ["box lock", "hinge", "jaw", ...],
  "inspection_tips": "...",
  "cleaning_considerations": "...",
  "corrective_actions": ["Remove from service immediately.", ...],
  "reference": "AAMI ST79 (institution-specific implementation may vary)."
}
```

## Typical anatomy locations
`instrument_anatomy.py`'s per-zone `contamination_risks`/`condition_risks`
lists are the same default vocabulary on every zone (no instrument family
customizes them), so they cannot distinguish "typical" locations for one
finding from another. Instead, `_typical_anatomy_locations()` derives them
honestly from what the anatomy data *does* differentiate:

- **Contamination findings** (blood, bone, tissue, organic residue, debris):
  zones marked `retention_risk == "high"` across every instrument family.
- **Structural/condition findings** (rust, corrosion, pitting, crack, wear,
  missing component): zones with `zone_risk_level` of `high` or `critical`.
- **Insulation damage**: the one zone actually named for it (`insulation
  edge`), rather than the broad structural set.

## API
- `GET /api/mentor/education` — all twelve articles.
- `GET /api/mentor/education/{finding_type}` — one article, 404 if unknown.
- `POST /api/mentor/education/{finding_type}/complete` — mark an article
  completed for the current user (feeds Competency Support).

# LumenAI — Synthetic Data Guide

Objective 11 review. Documents what the real demo-data generators produce today, what statistical realism they actually offer, and where the gap is between existing generators and the brief's full requirement list.

## Real, runnable generators — what each one actually produces

| Generator | What it produces | Realism mechanism | Real or aspirational |
|---|---|---|---|
| `backend/scripts/seed_pilot_data.py` | 10 hand-authored instrument records, 25 baseline library entries, 50 inspection records with a hand-tuned finding distribution | Deterministic seed (`random.Random(42)`) for numeric jitter only — no statistical distribution modeling, hand-authored base data | **Real** |
| `backend/scripts/seed-demo-data.sh` | 5 named enterprise demo tenants (Northstar Surgical Network, MetroCare System, Riverside Health, Summit Specialty Partners, Atlantic Care Alliance) via live API calls | Hand-authored health/risk attributes per tenant | **Real** |
| `scripts/seed_enterprise_investor_demo.sh` | One hand-scripted enterprise intake/finding/CAPA flow against a hosted backend | Hand-scripted, single flow | **Real**, narrow |
| `backend/app/services/connectors/spd_connectors.py` | Mock third-party connector previews (CensiTrac, SPM, ReadySet, Abacus, VendorMade) | `hashlib.md5(...)` → `random.Random(...)`, explicitly labeled `sample_only: True` | **Real**, but integration-preview data, not clinical data |
| `digital_quality_twin_service.py`'s seeded-mock fallback | Plausible-looking twin scores/forecasts when real ML scoring isn't available | `hashlib.md5` → `random.Random`, explicit comment: "real scoring engine would require ML model" | **Real** |

**No `Faker`/`faker` package is used anywhere in `backend/app/`.** All synthetic data in this codebase is hand-authored base records with `random`-seeded numeric jitter, not a statistical-distribution-based generator. "Ensure statistical realism" (the brief's exact phrasing) should therefore be read as "the hand-authored numbers look plausible to a domain expert," not "the data was drawn from a modeled distribution matching real-world SPD statistics" — this repo does not currently do the latter.

## Gaps between what's asked for and what exists

| Brief requirement | Gap |
|---|---|
| Synthetic inspection records | Real (50 records) but far short of what marketing collateral claims (`docs/demo/executive-demo-walkthrough.md`'s "~2,847") — see [DEMO_MASTER_PLAN.md](./DEMO_MASTER_PLAN.md) |
| Synthetic Digital Twins | `digital_quality_twin_service.py` has a real seeded path; Apollo's twin has none and needs genuine history |
| Instrument inventories | Real, 10 records — small scale for a "realistic hospital" demo; consider expanding if a live demo needs to show inventory-scale browsing |
| Facilities | Real, 5 enterprise tenants + 1 pilot facility ("Bon Secours (demo tenant)") |
| Technicians | **No dedicated technician-roster generator** — technician identifiers appear as fields on inspection records, not as a standalone synthetic-staff directory |
| Manufacturers | Referenced in baseline/vendor data, no dedicated large-scale manufacturer-roster generator found |
| Repair history | Present in Vulcan's reliability data model; volume depends on how many of the 50 seeded inspections were tagged as repair-related |
| Findings | Real, hand-tuned distribution in `seed_pilot_data.py` |
| Images | **Not real** — `pilotImageManifest.ts`'s 20 entries are all `available: false`; only 4 SVG placeholders exist on disk. This is the single largest gap in the synthetic-data picture. |
| Workflows | Real inspection workflow-state data exists; the fuller 8-stage SPD workflow is only partially tracked (4 of 8 stages), per `docs/clinical-validation/HUMAN_OVERSIGHT_MODEL.md` — synthetic data cannot show stages the platform doesn't track |
| KPIs | Real — computed live from seeded inspection/CAPA/baseline data by the same dashboards production tenants use |

## No PHI — how it's actually enforced

Enforcement is layered, and each layer should be described accurately in any customer-facing material:
1. **By construction**: the seed generators simply never include patient-identifying fields.
2. **By field-name blocklist**: `backend/app/routes/integrations.py`'s `_PHI_FORBIDDEN` set (`patient_id`, `mrn`, `dob`, `patient_name`, `name`, `ssn`) strips those keys from incoming event dicts.
3. **By human self-attestation**: `no_phi_confirmed` boolean flags (`olympus_exchange_service.py`, `genesis_ai_intelligence_cloud.py`) and `phi_review_status` (`sage_image_library_service.py`) record a human's clearance decision — the system trusts the attestation, it does not independently verify content.

**There is no automated content-scanning guardrail** (no regex/ML detection of names, dates, or IDs embedded in free-text fields or image bytes) anywhere in this codebase. This should be stated plainly in any data-governance claim made under this program, consistent with `docs/data-governance/pilot-data-governance.md`'s existing framing.

## Recommendation

1. **Correct the inspection-count and image-count figures** in existing demo collateral (`docs/demo/executive-demo-walkthrough.md`) to match what `seed_pilot_data.py` and `pilotImageManifest.ts` actually produce, or expand the generators to genuinely reach those numbers before a demo cites them.
2. **Real instrument photography (or licensed stock images clearly marked synthetic/illustrative) is the single highest-priority gap** — the image library is currently a data scaffold with zero backing content.
3. **A dedicated technician/staff-roster generator** would strengthen any demo requiring believable multi-technician workflow variety; today this must be improvised from inspection-record technician fields.
4. Continue relying on hand-authored data with seeded jitter rather than introducing a statistical/Faker-based generator purely for this program — the existing approach is simpler, deterministic (good for repeatable demos), and sufficient for the scale these demos operate at.

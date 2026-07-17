# Pilot Site Selection — Record and Criteria

**STATUS: NO SITE SELECTED.** Every field below is deliberately blank.
Filling this record requires a real engagement with a real facility;
inventing names here would be fabricated evidence. This document
provides the selection criteria and the record structure so that, when
an engagement exists, it is captured completely on day one.

## Selection criteria

* An SPD performing routine borescope inspection of lumened instruments,
  willing to run LumenAI **advisory-only** alongside (never instead of)
  its existing process.
* A named clinical sponsor with authority over the pilot and its stop
  conditions.
* IT capacity to provision or approve the managed environment
  (`PILOT_SITE_GUIDE.md`): managed PostgreSQL, durable object storage,
  TLS, an alert destination, and network access from the inspection
  workstation.
* Infection Prevention and Biomedical Engineering participation for
  workflow and equipment sign-off.
* Agreement to the data-governance terms (tenant isolation, PHI-free
  imaging metadata, LCID/audit governance) before the first image is
  captured.

## Site record (to be completed by real people)

| Field | Value |
|---|---|
| Pilot hospital | _unassigned_ |
| Department | _unassigned_ |
| Clinical sponsor (name, role) | _unassigned_ |
| SPD leadership contact | _unassigned_ |
| IT contact | _unassigned_ |
| Infection Prevention representative | _unassigned_ |
| Biomedical Engineering representative | _unassigned_ |
| Pilot objectives (site-specific) | _unassigned_ |
| Pilot duration / dates | _unassigned_ |
| Daily inspection cap | _unassigned_ |
| Success criteria + targets (pre-agreed) | _unassigned_ |
| Data-governance sign-off (date, signatory) | _unassigned_ |
| Stop-condition authority | _unassigned_ |

Completion of this record is a precondition for every downstream
Phase-1 activity (`PILOT_PROTOCOL.md` scope section).

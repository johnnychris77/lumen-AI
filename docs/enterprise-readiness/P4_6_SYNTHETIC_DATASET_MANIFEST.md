# P4.6 — Synthetic Pilot Dataset Manifest (template + register)

**Purpose:** a dataset may enter the synthetic research pilot **only** after a complete, evidenced
entry exists here and the RGI-01 (synthetic) authorization (`P4_6_SYNTHETIC_GOVERNANCE_DECISIONS.md`
§C) references it. **Fail-closed:** any missing/empty required field, or a synthetic status asserted
without evidence, means the dataset is **NOT permitted**. This manifest records provenance; it does
**not** itself authorize use.

**Non-negotiable rules:**
- **Synthetic status requires evidence**, not a label — record the generation method and the
  no-real-derivation / no-PHI checks. Unverified ⇒ not permitted.
- **No real patient / institution-controlled data, no PHI** — in images, labels, metadata, or
  filenames. Prohibited data never gets a manifest entry; it is a pilot stop condition.
- **LumenAI-owned + internal-research licensing only.**
- This manifest is populated by the **Synthetic Data-Governance Owner** (not the dataset's
  generator/author — separation of duties).

---

## 1. Required fields (per dataset)

| Field | Requirement |
|---|---|
| Dataset ID / name | Unique, stable identifier |
| **Provenance** | Generator tool + **version**, generation config/seed, operator, generation date; source assets (if any) and proof they are themselves synthetic/LumenAI-owned |
| **Content classification** | `synthetic-research`; **evidence** of synthetic generation; explicit **no-PHI** determination + method |
| **Labeling method** | How ground-truth/labels were produced (procedural / synthetic-by-construction / annotator); annotator identity + protocol if human; label integrity check |
| Ownership | LumenAI-owned (confirmed) |
| **Permitted use** | Internal synthetic research only; research-only, **not clinically validated**; no production/hospital use |
| Licensing / use-rights | LumenAI internal research; any third-party generator license noted + compatible |
| Tenancy | Owning research tenant(s); must not be shared cross-tenant |
| **Retention** | Retention period + disposal method + responsible owner |
| **Verification evidence** | Resolvable reference(s): generation log/config hash, no-PHI check artifact, label-integrity check, reviewer who verified |
| Verified by (role) | Synthetic Data-Governance Owner (name/role) — **not** the generator |
| Verification date | |
| Status | `Pending` / `Verified-Permitted` / `Rejected` (default `Pending`) |

A dataset is **`Verified-Permitted`** only when every field above is complete **and** the synthetic
status and no-PHI determination are evidenced. Otherwise it stays `Pending` (not usable) or
`Rejected`.

## 2. Blank entry template (copy per dataset — DO NOT prepopulate as verified)

```
Dataset ID / name:
Provenance (generator+version, config/seed, operator, date, source-asset proof):
Content classification + synthetic evidence + no-PHI method:
Labeling method (+ annotator/protocol if human, + integrity check):
Ownership (LumenAI-owned?):
Permitted use (internal synthetic research only; research-only):
Licensing / use-rights:
Tenancy (owning research tenant):
Retention (period + disposal + owner):
Verification evidence (resolvable refs):
Verified by (role — not the generator):
Verification date:
Status (Pending / Verified-Permitted / Rejected):
```

## 3. Dataset register (empty until entries are authored and verified)

| # | Dataset ID | Classification | Permitted use | Verified by | Date | Status |
|---|-----------|----------------|---------------|-------------|------|--------|
| — | *(none recorded)* | | | | | |

*No dataset is marked verified or permitted by this template. Entries are completed by the Synthetic
Data-Governance Owner with evidence; synthetic status is never treated as verified on a label alone.
No real/PHI/institution-controlled data is eligible for an entry.*

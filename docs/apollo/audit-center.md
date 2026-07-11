# Project Apollo — Audit Center

LumenAI OS v4.7, Section 4.

## No second audit-package generator

`accreditation_engine.py` and `regulatory_standards_catalogue.py` already
covered Joint Commission, AAMI ST79, FDA, CMS, and ISO before Apollo. Apollo
extends both rather than building a parallel system:

* `regulatory_standards_catalogue.STANDARDS` gained AAMI ST91 (flexible/
  semi-rigid endoscope reprocessing — body code `aami_st91`, distinct from
  ST79's `aami`), AORN (perioperative practice standards), and DNV
  (accreditation body, alternative to Joint Commission).
* `accreditation_engine.generate_audit_package`'s `body_map` gained
  `aami_st91`, `aorn`, `dnv`, `internal`, and `vendor` package types.
  Internal and vendor audits aren't tied to one regulatory body's standards,
  so — like `"full"` — they include the whole standards catalogue rather
  than a single-body slice.

## Every finding is linked to evidence

Every `AccreditationFinding` on a generated audit package already carries
its `standard_code`, `citation_text`, and `remediation_guidance` from the
standards catalogue mapping — this was true before Apollo and remains true
for every one of the 9 supported package types.

## Supported audit types

```
joint_commission | aami | aami_st91 | fda | cms | aorn | dnv | internal | vendor | full
```

## API

```
GET   /api/apollo/audit/summary
POST  /api/apollo/audit/generate   { "package_type": "aami_st91", ... }
```

`audit/summary` composes `accreditation_engine.compute_regulatory_
dashboard` — readiness scores, standards summary, top findings — unchanged
computation, just surfaced under Apollo's Audit Center tab. Audit package
generation is audit-logged.

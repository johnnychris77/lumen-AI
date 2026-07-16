# LumenAI — Legal & Governance Package

Objective 10 review. The central finding of this document: several legal artifacts this objective asks for are treated throughout the repository as **required, gating preconditions** (referenced in onboarding checklists, pilot runbooks, and compliance docs dozens of times) — but **none of them has actual agreement text anywhere in this codebase.** This gap must be closed with real legal drafting before any commercial pilot proceeds; this document cannot substitute for that drafting, only identify precisely what's missing and what real supporting content already exists to build from.

## Terms of Service — does not exist

Zero references to actual Terms of Service content were found anywhere in the repository. This requires entirely new legal authorship.

## Privacy Policy — does not exist; only "required" markers

`docs/global/privacy-and-data-residency.md` references a public privacy policy as a requirement (including jurisdiction-specific versions for Korea and markets under Arabic PDPL) but contains no actual policy text. `docs/global/international-readiness-scorecard.md` marks privacy-policy localization as "not started." This requires new legal authorship, informed by the real data-handling commitments already documented in `docs/data-governance/pilot-data-governance.md` (see below).

## Business Associate Agreement (BAA), Master Service Agreement (MSA), Data Processing Addendum (DPA) — referenced everywhere as preconditions, drafted nowhere

These three documents are named as required, signed preconditions in at least ten places across `docs/global/`, `docs/pilot/`, `docs/enterprise/`, and `docs/platform/` — every onboarding and pilot-launch checklist in this repository has a literal checkbox for "BAA executed" or "MSA signed." **None has actual contract text.** This is the single most consequential legal gap this review found: **customer onboarding checklists throughout this codebase assume these documents exist and are simply awaiting a signature — they do not exist as drafts to sign.**

## What real content exists to build from

- **`docs/data-governance/pilot-data-governance.md`** is a genuine, dated (effective 2026-06-21), substantive policy that functions as the technical backbone a real DPA should be built from: explicit PHI-exclusion commitments (no patient names/identifiers collected; images retained only as SHA-256 hashes), a real data-retention table (inspection records: pilot period + 30 days; audit logs: 7 years; auth tokens: session-only), a GDPR Article 15/16/17/20 subject-rights table with 30-day response commitments, defined Data Controller (pilot site) / Data Processor (LumenAI) / DPO roles, and a tiered breach-notification schedule (1hr/4hr/24hr by severity). **This document should be the primary input for drafting a real DPA**, not superseded by one.

## Responsible AI Statement, Clinical Use Statement, Limitations of Use — content exists, just not under these names

No document uses these exact titles anywhere in the repository, but substantial, real content already serves this purpose and should be assembled by citation rather than rewritten from scratch:
- **`docs/clinical-validation/CLINICAL_SCOPE.md`**'s "Unsupported environments and known limitations" section (from Phase 3 of this document program) already states plainly: no trained model weights ship in this repository; osteotomes are unmodeled; anatomy-zone resolution is placeholder-grade with confidence capped at 0.70; pre-market clinical data is mock/synthetic; no FDA clearance is claimed; root-cause categorization is deliberately human-only; Oracle's research hypotheses are non-clinical until human-gated. **This is the Limitations of Use statement**, already written and already disciplined about not overclaiming.
- **`docs/architecture/patient-safety-governance.md`** is, functionally, a Responsible AI statement: it states outright that "LumenAI NEVER claims causation between instrument quality signals and patient harm events," provides an approved-vs-prohibited language table ("potential association" vs. "caused"/"proven link"), and documents the non-overridable `human_review_required = True` design and its review-state machine.
- **`docs/architecture/cv-data-governance.md`** documents real image-data classification, a 7-year regulatory retention policy for permanent baseline images, 90-day auto-purge for quarantined images, and a literal database-level tamper-prevention statement (`REVOKE UPDATE ON cv_inference_records FROM lumenai_app;`).

**Recommendation**: formally retitle and consolidate these three existing documents (or a curated excerpt of each) into a standalone "Responsible AI & Clinical Use Statement" for legal/customer-facing distribution, rather than authoring new content — the substance is already correct and disciplined; it simply needs to be packaged under the name this objective asks for.

## A discrepancy worth flagging for whoever owns this package

`docs/regulatory/cybersecurity-readiness.md` claims "GitHub Dependabot: Continuous (automated alerts)" as an implemented control. Per this review's security-operations recon, **no `dependabot.yml` configuration exists anywhere in `.github/`.** This document — which is regulatory-submission-facing — should not claim an unimplemented control as active; either implement Dependabot or correct the claim before this package is finalized. The same document's claim of "bcrypt hashing" also does not match the actual codebase (real password hashing is PBKDF2-SHA256, per the Phase 1 architecture review).

## Recommendation — priority order

1. Commission real legal drafting for ToS, Privacy Policy, BAA, MSA, and DPA — these cannot be produced by this documentation review; they require qualified legal counsel and should use `pilot-data-governance.md` as the DPA's factual foundation.
2. Assemble the existing Responsible AI / Clinical Use / Limitations content (cited above) into one named, distributable document rather than leaving it scattered under architecture-doc titles.
3. Correct `docs/regulatory/cybersecurity-readiness.md`'s Dependabot and bcrypt claims to match actual implementation before this document is used in any regulatory submission context.

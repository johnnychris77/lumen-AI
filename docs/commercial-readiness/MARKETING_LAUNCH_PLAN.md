# LumenAI — Marketing Launch Plan

Objective 12 review. This is the objective with the least existing real content to build from — most marketing-shaped artifacts already in this repository are scoped to an unrelated side feature ("Enterprise Governance Suite"), not LumenAI's core SPD inspection product, and this must be stated plainly before any launch planning proceeds.

## Website content, product brochure, solution brief, executive one-pager

Real marketing-document *templates* exist (`docs/investor/ENTERPRISE_GOVERNANCE_SUITE_FINAL_EXECUTIVE_ONE_PAGER_v1.md` and matching PDF assets in `frontend/public/downloads/`), and are genuinely well-produced as templates. **But their content is entirely about the Enterprise Governance Suite (audit/CAPA/vendor-governance evidence features), not LumenAI's core AI lumen-inspection/contamination-detection value proposition.** Using these as-is for a core-product launch would send the wrong message. Recommend: reuse their visual/structural template, replace all content with the core product's real value proposition (per `docs/sales/sales-playbook.md`'s pitch and `docs/investor/technical-narrative.md`'s sober technical framing), and do not present them as ready-to-ship core-product marketing without that substitution.

## Clinical overview and technical overview

Do not author new content here — cite `docs/clinical-validation/CLINICAL_SCOPE.md` (Phase 3) directly for the clinical overview, and `docs/investor/technical-narrative.md` for the technical overview. Both are real, honest, and already scoped correctly (no FDA-clearance claims, clear distinction between deployed inference and design-layer taxonomy).

## Product screenshots — a genuine, notable gap

**There are no real product screenshots anywhere in this repository.** `docs/screenshots/README.md` is a bare checklist of 13 recommended screenshots with zero actual image files behind it. `docs/public-demo/assets/screenshots/` contains 9 PNG files that, on inspection, collapse to only 2 unique images via checksum — and both of those unique images are, on direct visual inspection, **screenshots of a markdown file listing recommended screenshot filenames to add**, mistakenly saved under the real filenames rather than being actual product UI captures. `frontend/public/demo-images/lumened-instruments/` contains only 4 generic placeholder SVG icons. **This is a clean, unambiguous gap requiring real screen captures from a properly-seeded demo environment** (see `docs/demo-program/SYNTHETIC_DATA_GUIDE.md` for what to seed first) before any launch collateral referencing product screenshots can ship.

## Launch announcement

`docs/releases/ENTERPRISE_GOVERNANCE_SUITE_FINAL_PRODUCT_LAUNCH_SUMMARY_v1.md` exists as a real template but, again, is scoped to the Governance Suite side-feature and references a Render.com demo URL as if it were production. Do not repurpose this document's specific claims for a core-product launch announcement; its structure is reusable, its content is not.

## Case studies and testimonials — do not fabricate

Per `docs/commercial-readiness/SALES_PLAYBOOK.md`'s identical finding: `docs/evidence/case-studies.md` and `customer-success-stories.md` both state "none published yet." Any launch collateral must either omit customer-proof-point sections entirely or clearly label them as forthcoming — fabricating a testimonial or logo to fill this gap is out of scope for what this program authorizes and would violate this repository's own honesty discipline.

## Recommendation — priority order

1. Do not reuse the existing Enterprise Governance Suite marketing templates' *content* for a core-product launch — only their visual structure, after full content replacement.
2. Real product screenshots are the single highest-priority asset gap; commission them from a properly-seeded demo environment before any other marketing asset production begins.
3. Anchor clinical and technical messaging on the existing, already-honest `CLINICAL_SCOPE.md` and `technical-narrative.md` documents rather than writing new copy that risks drifting from the disciplined framing those documents already establish.
4. Do not include a customer case study, logo, or quote in launch materials until at least one real one exists and consent has been obtained per `docs/evidence/case-studies.md`'s documented policy.

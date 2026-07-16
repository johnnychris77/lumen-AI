# LumenAI — Sales Playbook (Commercial Readiness Edition)

Objective 11 review. Consolidates the real, existing sales content in `docs/sales/sales-playbook.md` with the demo-scripting content from Phase 5 rather than re-authoring either — this document is a thin index and honesty layer on top of both.

## Sales playbook — cite the existing document directly

`docs/sales/sales-playbook.md` is real, substantive, and marked CONFIDENTIAL. Use its persona table, competitive landscape (Censitrac/Censis/Meditrax, MasterControl/Veeva, IBM Maximo), ICP tiers, and objection-handling framework directly. Its FDA-objection response language ("our regulatory pathway is under active assessment") is the correct hedge and should be preserved verbatim in any updated version.

## Competitive positioning

Use `docs/sales/sales-playbook.md`'s existing competitive-landscape section. No new competitive research was conducted as part of this review — this objective is fully satisfied by the existing document.

## ROI calculator

`ROICenterPage.tsx`/`ValueRealizationPage.tsx` are the real, live ROI calculators. **Critical framing constraint, carried forward from `docs/demo-program/EXECUTIVE_PRESENTATION.md`**: these pages compute real inspection/finding/CAPA/baseline-coverage counts, but the dollar figures are those real counts multiplied by hardcoded industry-benchmark constants ($28,000/SSI, $5,000/critical finding, $2,500/CAPA, $35/hr labor) — not measured customer outcomes. A salesperson using this tool live must present it as "estimated value from disclosed industry benchmarks," never as "your measured ROI," and should rehearse the screen beforehand to confirm the live API path is rendering rather than the silent hardcoded fallback both pages fall back to on API failure.

## Value proposition

Use `docs/sales/sales-playbook.md`'s one-sentence pitch as the anchor, but soften its "before a single patient is at risk" framing to match the disclosed scoping in `docs/clinical-validation/CLINICAL_SCOPE.md` and `PATIENT_SAFETY_MODEL.md` — the platform is decision support, not a guaranteed harm-prevention system, and overstating this in a sales conversation creates exactly the kind of clinical overclaim this repository's own `CLAUDE.md` and prior review phases have consistently disciplined against.

## Customer personas

`docs/ux-review/USER_PERSONAS.md` (Phase 4) is the more rigorously-verified persona document — it maps each of the brief's named roles onto the platform's actual, enforced RBAC (or explicitly notes where no distinct role exists, e.g. Supervisor, Market Director, Infection Prevention). Use it as the technical-accuracy backstop against `docs/sales/sales-playbook.md`'s persona table, which is written from a sales-messaging angle rather than a system-capability angle — the two should agree on who the buyer/user is, even if they differ in tone.

## Objection handling

`docs/sales/sales-playbook.md`'s existing framework covers FDA-clearance objections correctly. Add one objection this review surfaced that isn't yet in that document: **"Why do some of your dashboard numbers look different in different screens?"** — answer honestly, per `docs/ux-review/DASHBOARD_STANDARDS.md`'s finding that several core KPIs are currently computed independently across multiple dashboards; this is a known, disclosed platform maturity item, not a data-integrity failure, and should be handled the same way the FDA objection is: directly and without evasion.

## Demo scripts

Do not re-author demo scripts here — `docs/demo-program/DEMO_SCRIPT_LIBRARY.md` and `docs/demo-program/ROLE_BASED_DEMOS.md` (Phase 5) are the canonical, already-built demo scripts, including the corrected honest framing for the "AI specialist collaboration chain" narrative and the Supervisor-approval staging workaround. Reference them directly.

## Case study template

`docs/evidence/case-studies.md` and `docs/evidence/customer-success-stories.md` both explicitly state "Status: none published yet" — **zero real customer case studies or testimonials exist in this repository.** Both documents do have real templates and a documented consent/sourcing policy. Use the existing templates; do not fabricate a customer quote, logo, or outcome figure to fill a placeholder — this would violate the same no-fabrication discipline this review has applied throughout.

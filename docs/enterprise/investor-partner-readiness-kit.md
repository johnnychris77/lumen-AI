# Investor & Partner Readiness Kit

Points to the existing materials that answer an investor's or strategic
partner's standard diligence questions, rather than duplicating them.

## The eight materials

| Material | Source |
|---|---|
| **Platform One-Pager** | `PITCH_DECK.md`, `PORTFOLIO_SUMMARY.md` |
| **Technical Overview** | `ARCHITECTURE_SUMMARY.md`, `docs/architecture/lumenai-clinical-intelligence-architecture.md` |
| **Clinical Overview** | `docs/enterprise/clinical-safety.md`, `docs/architecture/pre-sterilization-boundary.md` |
| **Competitive Differentiation** | `PORTFOLIO_POSITIONING.md` |
| **Vision** | `VERSION_1_0.md` §Vision |
| **Mission** | `VERSION_1_0.md` §Mission, `README.md` |
| **Roadmap** | `VERSION_1_0.md` §Future Roadmap, `docs/architecture/future-ai-roadmap.md` |
| **Architecture Summary** | `ARCHITECTURE_SUMMARY.md` |

## Standard diligence questions and where the answer lives

| Question | Answer location |
|---|---|
| What does LumenAI actually do? | `README.md`, `VERSION_1_0.md` |
| How is it differentiated from generic CV/AI vendors? | `PORTFOLIO_POSITIONING.md` — the Clinical Intelligence Operating System framing, not just image classification |
| Is this FDA cleared? | No — explicitly not claimed anywhere (`VERSION_1_0.md` §Known Limitations, CLAUDE.md constraint) |
| What clinical evidence exists? | `docs/evidence/README.md` — honest current state, including what's framework-only vs. real |
| How is patient safety protected? | `docs/enterprise/clinical-safety.md` |
| What's the commercial model? | `docs/enterprise/commercial-packaging.md`, `docs/commercial/pricing-strategy.md` |
| What's the total addressable market / segment strategy? | `docs/commercial/enterprise-sales-playbook.md`, `docs/commercial/roi-model.md`'s segment definitions |
| What's the technical moat? | The clinical ontology + knowledge graph + multi-agent architecture (Phases 19.5–23) — a competitor copying computer vision alone does not replicate the explainable, governed reasoning layer |
| What are the known gaps/risks? | `VERSION_1_0.md` §Known Limitations, `docs/regulatory/qms-readiness-gap-analysis.md` |
| What's the roadmap to regulatory submission, if pursued? | `docs/regulatory/fda-submission-readiness-checklist.md`, `docs/regulatory/submission-strategy.md` |

## Principles for investor/partner conversations

1. **Never overstate clinical validation status.** `docs/evidence/`
   states plainly what's real (framework, prior seeded-data pilot
   exercises) versus what's pending (live multi-site validation). This
   is the same standard applied everywhere else in the platform's
   documentation — an investor conversation is not an exception.
2. **Lead with the architecture, not just the AI.** LumenAI's
   differentiation is the governed, explainable, ontology-driven system
   (Phases 19.5–23), not a single model's accuracy number — see
   `PORTFOLIO_POSITIONING.md`.
3. **Be precise about regulatory status.** LumenAI is a clinical
   inspection decision-support tool operating before sterilization, not
   a cleared diagnostic device — this framing protects both the company
   and the investor relationship from a future mischaracterization risk.

## Refreshing this kit

Update the cross-referenced source documents when they change (a new
edition, a completed pilot validation, a regulatory milestone) — this kit
itself should rarely need to change, since it's an index, not primary
content.

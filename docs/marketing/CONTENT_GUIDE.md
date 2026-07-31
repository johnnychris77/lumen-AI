# LumenAI Marketing — Content & Voice Guide

## Voice

Precise, clinical, trustworthy, executive-ready. Confident about the evidence
and governance layer; honest about the limits of the AI. Never fear-based,
never hyped.

## Non-negotiable framing rules

1. LumenAI is **decision support and evidence governance** — never a replacement
   for trained technicians, infection preventionists, surgeons, manufacturers,
   or regulatory authorities.
2. AI is **assistive**; a qualified human owns every disposition. Say "suggested
   finding", "assistive analysis", "routed for review".
3. Use **"possible association" / "quality review recommended"** — never
   causation.
4. No claims about infection rates, regulatory/accreditation compliance, FDA,
   HIPAA, SOC 2, diagnostic/AI accuracy, cost savings, or labor reduction. See
   `PRODUCT_CLAIMS_REVIEW.md`.
5. All demonstration content is labeled **"Demonstration Data — Not for Clinical
   Use"** and uses synthetic data only. No PHI, ever.
6. Capabilities carry a **maturity tag** (In product / Demonstrated with
   simulated data / Concept stage). Never present concept-stage as shipping.

## Terminology

| Use | Avoid |
|---|---|
| lumen / internal channel | "the inside" |
| assistive analysis, suggested finding | "the AI detects/diagnoses" |
| approved baseline, baseline comparison | "gold image" |
| routed for human review | "auto-approved / auto-failed" |
| audit trail, evidence integrity | "blockchain", "tamper-proof" (use "tamper-evident") |
| designed with … principles in mind | "compliant", "certified" |

## Editing the site copy

- Almost all copy lives in `frontend/src/marketing/lib/content.ts`
  (capabilities, specialists, use cases, video scenes) — edit there, not in the
  page JSX, so tone stays consistent.
- Specialist descriptions must match
  `docs/production-readiness/AI_SPECIALIST_CATALOG.md`. If the catalog changes,
  update `content.ts` `SPECIALISTS` and re-run the claims review.
- After any copy change: re-read `PRODUCT_CLAIMS_REVIEW.md` and re-classify new
  statements; run `npm --prefix frontend run build`.

## Audience emphasis

| Audience | Lead with |
|---|---|
| SPD leaders / techs | Workflow, standardization, less rework |
| Infection Prevention | Evidence, escalation, review consistency |
| Quality / Patient Safety | Audit readiness, trends, governance |
| Risk Management | Traceability, documented rationale |
| Executives | Operational visibility, governance posture |
| Manufacturers | Baseline lineage, vendor/instrument trends |
| Investors / partners | Category framing, honesty as a differentiator |

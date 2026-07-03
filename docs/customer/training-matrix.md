# Training Matrix

Who needs to be trained on what, before they use LumenAI unsupervised.

## Role-based training requirements

| Role | Required training | Format | Sign-off owner |
|---|---|---|---|
| SPD Technician (operator) | Capture workflow (image capture, zone tagging, instrument identification); reading AI feedback; when to escalate | Hands-on, ≥1 supervised session | SPD Champion |
| SPD Supervisor (spd_manager) | Everything above, plus: reviewing AI recommendations, agree/partial-agree/disagree workflow, override policy, reading the reasoning chain (`/knowledge-graph`) | Hands-on + reasoning-chain walkthrough | SPD Champion |
| SPD Manager / Department Lead | Everything above, plus: Pre-Sterilization Command Center (`/pre-sterilization-command-center`), Pilot Validation Dashboard (`/pilot-validation`), safety queue triage | Dashboard walkthrough | Executive Sponsor |
| Executive Sponsor | Executive Command Center, CIOS Dashboard (`/cios-dashboard`), value realization reporting | Executive briefing | LumenAI implementation lead |
| IT/Security Administrator | RBAC configuration, SSO/OIDC setup, audit log review, tenant configuration | Technical walkthrough | LumenAI implementation lead |

## What "trained" means, concretely

A technician is considered trained when they can, unsupervised:

- Correctly identify and tag the required inspection zones for their
  site's most common instrument families
- Correctly interpret a "requires supervisor review" flag and route it
  appropriately
- Explain, in their own words, why LumenAI is a pre-sterilization tool
  and not a sterilization-validation system

A supervisor is considered trained when they can, unsupervised:

- Use the reasoning chain to explain an AI recommendation to a
  technician or auditor
- Correctly apply the agree/partially-agree/disagree/override workflow,
  including writing a rationale when required
- Recognize when a finding should escalate to the safety review queue vs.
  routine reprocessing

## Refresher training triggers

- A recurring override or correction pattern identified during the Day
  60 optimization review (`docs/customer/60-day-optimization-plan.md`)
- A new instrument family or manufacturer added to the site's baseline
  library
- Staff turnover — new hires require the full role-based training before
  unsupervised use, not an abbreviated version
- A platform version upgrade that changes the reasoning chain,
  recommendation vocabulary, or reviewed workflow

## Training materials

Point-in-time training content should reference the live product, not a
static screenshot deck that goes stale — walk trainees through the actual
`/knowledge-graph`, `/pilot-validation`, and
`/pre-sterilization-command-center` pages using a real (or sandboxed
demo) inspection, per `docs/deployment/GITHUB_PAGES_DEMO.md` for a safe,
non-production environment to train in.

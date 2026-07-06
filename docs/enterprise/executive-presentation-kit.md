# Executive Presentation Kit

A guide to the materials available for presenting LumenAI to hospital
executives, health-system leadership, and internal stakeholders — pointing
to existing source material rather than duplicating slide content here.

## The eight presentation modules

| Module | Source material | Audience |
|---|---|---|
| **Executive Overview** | `README.md`'s mission/vision section, `VERSION_1_0.md` | C-suite, board |
| **Product Overview** | `VERSION_1_0.md` §Core Capabilities, `docs/enterprise/commercial-packaging.md` | VP Perioperative Services, SPD Director |
| **Architecture Overview** | `ARCHITECTURE_SUMMARY.md`, `docs/architecture/lumenai-clinical-intelligence-architecture.md` | IT leadership, technical evaluators |
| **Clinical Workflow** | `docs/architecture/pre-sterilization-boundary.md`, `docs/cios/lumenai-clinical-intelligence-operating-system.md` | Clinical leadership, Infection Prevention |
| **AI Explainability** | `docs/knowledge-graph/reasoning-engine.md`, `docs/agents/explainable-agent-trace.md` | Clinical leadership, IT security/AI governance reviewers |
| **Security Overview** | `docs/security/security-compliance-center.md` | IT security, compliance/legal |
| **ROI Presentation** | `docs/enterprise/roi-framework.md`, `docs/commercial/roi-model.md` | CFO, Executive Sponsor |
| **Implementation Roadmap** | `docs/customer/implementation-timeline.md` | Executive Sponsor, SPD Champion |

## Recommended presentation sequence for a first executive meeting

1. Executive Overview — what LumenAI is and why it matters (2–3 minutes)
2. Clinical Workflow — where LumenAI fits in the SPD process, emphasizing
   the pre-sterilization boundary (`docs/architecture/pre-sterilization-boundary.md`)
   so there's no confusion about sterilization-validation claims
3. AI Explainability — the reasoning chain example
   ("I detected probable blood in the Kerrison jaw serrations...") to
   ground the "explainable, not a black box" claim concretely
4. Security Overview — high-level only for a first meeting; full detail
   reserved for IT security's dedicated review
5. ROI Presentation — segment-appropriate benchmark figures
   (`docs/commercial/roi-model.md`) if pre-implementation, or the
   customer's own real figures (`docs/enterprise/roi-framework.md`) if
   post-implementation
6. Implementation Roadmap — the 30/60/90-day plan, setting expectations

## What NOT to present

- Any figure not traceable to a real computation or a clearly-labeled
  industry benchmark (`docs/enterprise/roi-framework.md`'s honesty
  constraint)
- Any claim of FDA clearance or regulatory approval (none exists —
  CLAUDE.md constraint, `VERSION_1_0.md` §Known Limitations)
- Any capability from the future roadmap (`docs/architecture/future-ai-roadmap.md`,
  `VERSION_1_0.md`'s Version 2.0–5.0 roadmap) presented as if it exists
  today

## Building a deck from this kit

Each module above should pull directly from its source document at
presentation time rather than maintaining a separately-drifting slide
deck — when the underlying doc updates (e.g. a new edition is added to
`docs/enterprise/commercial-packaging.md`), the presentation content
should update with it.

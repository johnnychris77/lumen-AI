# LPZ-DIR-007 — Baseline Comparison Standard

**Purpose:** define how a future inspection is compared against an approved
baseline. The comparison framework **supports human review and future AI
assistance without replacing expert judgment**. Under this directive, no new
comparison algorithm is implemented and no AI is trained; this document sets the
**principles** any comparison (human or future AI-assisted) must follow.

Guardrail: comparison outputs are decision **support**, never an autonomous
disposition. All results are advisory and route to human review; no clinical or
regulatory claim is made.

## Comparison principles

### Structural comparison
Compare the instrument's structure/appearance in the inspection image against the
approved baseline reference for the **same** Digital Twin (same instrument
identity, compatible configuration). Structural mismatch (wrong instrument,
wrong configuration) is a **compatibility failure**, not a finding — it halts
comparison and routes to review.

### Coverage comparison
Assess whether the inspection image covers the same regions as the baseline
(e.g., the lumen, hinge, serrations). **Incomplete coverage** means the
comparison is inconclusive for the uncovered regions — this must be surfaced, not
silently treated as "clean."

### Finding comparison
Compare observations against the baseline's known-good state using the Directive
006 taxonomy. A deviation from baseline is a **candidate finding** for human
confirmation — never an automatic pass/fail.

### Confidence handling
Any confidence attached to a comparison is **advisory**. Where the comparison is
AI-assisted in the future, model confidence is displayed as such and kept
distinct from reviewer confidence; a high score never overrides a required human
review.

### Unknown conditions
If the comparison cannot be resolved (novel appearance, ambiguous deviation), the
outcome is **Unknown / Unable to Determine** — a governed, acceptable result that
routes to review and may feed the Unknown-finding learning loop. The system never
forces a pass/fail to avoid an Unknown.

### Image quality considerations
Comparison validity is bounded by image quality. On a **Poor/Reject** image the
comparison is not authoritative; the correct output is a quality-limited result
routing to re-capture or review, **never** a confident "matches baseline."

### Escalation criteria
Escalate to human review (and, where defined, supervisor review) when: structural
incompatibility; incomplete coverage of a required region; a contamination-type
deviation; an Unknown condition; low image quality; or any safety-relevant
deviation. **Fail-closed:** ambiguity escalates, it does not pass.

## Safety invariant

Absence of a detected deviation is **not** evidence of cleanliness or acceptability
when identity, coverage, quality, or evidence is insufficient. The comparison must
distinguish "confirmed match against a valid baseline" from "could not
determine." (This mirrors the platform's existing contamination-safety and
false-PASS-remediation invariants.)

## Human-in-the-loop requirement

Every comparison result is **decision support**: it is reviewed by a qualified
human before any disposition. Future AI assistance may rank, highlight, or
pre-populate — it may **not** finalize. Expert judgment is the authority.

## Governance note (existing system)

The repository already contains comparison machinery —
`baseline_comparison_service`, `baseline_comparison_scoring_service`,
`baseline_compatibility_service`, `image_similarity_service`, and the
Veritas/Sentinel baseline services — wired into the live inspection path with a
compatibility contract and fail-closed states (per the false-PASS remediation and
Vision Sprint 2 work). This standard **governs** that machinery; it does not add a
new algorithm. Governance additions recorded for a future authorized change:
ensure every comparison records the baseline **version** used, the coverage
assessment, the quality bound, and an explicit Unknown path, and that no
comparison can emit a confident match on insufficient identity/coverage/quality.

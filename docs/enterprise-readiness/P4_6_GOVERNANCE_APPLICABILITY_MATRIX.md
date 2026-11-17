# P4.6 — Governance Applicability Matrix

**Purpose:** record **which** governance requirements apply to the **internal synthetic pilot**, and
**which remain prerequisites** for any **future institution-sponsored research** on real data.
Narrowing scope to synthetic data **relaxes nothing on the security or scientific-integrity axes** —
it only changes the *data-rights* basis from an external IRB to a LumenAI-controlled synthetic
provenance record. This matrix prevents scope-narrowing from being misread as a waiver.

**Legend:** **Applies-now** = required for the synthetic pilot. **Prerequisite-future** = not
required to *start* the synthetic pilot but **required before** any real / institution-sponsored
research or production. **Both** = required now **and** stricter later.

---

## 1. Requirement applicability

| Requirement | Synthetic pilot | Future institution-sponsored / real-data / production | Notes |
|---|---|---|---|
| **Authentication (OIDC-only, no bypass)** | **Applies-now** | Both | Identical control; no relaxation |
| **Object-level authorization** | **Applies-now** | Both | Per-owner authorization enforced |
| **Tenant isolation** | **Applies-now** | Both | Cross-tenant impossible either way |
| **Audit durability (hash-chained)** | **Applies-now** | Both | Every access decision audited |
| **Artifact-store hex encoding / traversal defense (RGI-04)** | **Applies-now** | Both | No plaintext fallback |
| **Benchmark integrity gates (RGI-03/05/08/09/11..13)** | **Applies-now** | Both | Fail-closed scientific gating |
| **Authorization/approval value validation (RGI-01/02 floor)** | **Applies-now** | Both | Rejects invalid/false values |
| **SEC-174-02 disposition (non-author)** | **Applies-now** | Both | Latent, but security axis — not waivable |
| **SEC-175-01 independent non-author review** | **Applies-now** | Both | Author/CI/Codex insufficient; **prerequisite for the pilot's security axis** |
| **RGI-01 — data provenance/authorization** | **Applies-now (LumenAI synthetic form)** | **Prerequisite-future (external IRB form)** | Synthetic: LumenAI-owned provenance record. Real: genuine institutional/IRB authorization — **John/LumenAI alone cannot supply it** |
| **RGI-02 — reviewer framework** | **Applies-now (internal reviewers)** | **Prerequisite-future (institution-authorized reviewers + scope binding)** | Internal delegated authority suffices for synthetic; institutional scope binding required for real data |
| **RGI-10 — pixel-metric convention** | **Applies-now (if metrics reported)** | Both | Decision needed before any reported pixel metric, synthetic included |
| **Synthetic dataset manifest (evidence-based)** | **Applies-now** | Superseded by governed real-data acquisition + IRB | Synthetic status must be evidenced, not asserted |
| **Real-data acquisition governance (consent/rights/PHI/retention/quality)** | **N/A (prohibited)** | **Prerequisite-future** | Real data is prohibited in the synthetic pilot |
| **Institutional/IRB authorization** | **N/A** | **Prerequisite-future** | Required before any real/institution research |
| **Prospective clinical-study protocol + clinical validation** | **N/A (prohibited)** | **Prerequisite-future** | No clinical claims in the synthetic pilot |
| **Regulatory clearance (FDA)** | **N/A (prohibited to claim)** | **Prerequisite-future (if ever pursued)** | Never claimed anywhere |
| **Upstream #162–#169 Codex-chain remediation + review (RK-07)** | **Prerequisite-future** | **Prerequisite-future** | Separate open track; not fixed by #176/#177; required before integrating that chain |
| **RK-04 artifact-inventory condition** | **Applies-now** | Both | Pre-start filesystem inventory |

## 2. What the synthetic pilot explicitly does NOT authorize
- Any use of real patient or institution-controlled data, or PHI.
- Any hospital / institution-sponsored research.
- Any production deployment or clinically actionable output.
- Any closure of SEC-174-02 or SEC-175-01 (they apply **now** and remain OPEN).
- Any assertion of clinical validation or regulatory clearance.

## 3. Summary
- **Security axis:** every control **applies now** to the synthetic pilot; SEC-174-02 and SEC-175-01
  are **prerequisites for the pilot**, not deferred.
- **Scientific axis:** RGI-10 and the RGI-02 reviewer framework **apply now** if any metric is
  reported; real benchmarks remain BLOCKED.
- **Data-rights axis:** the synthetic pilot uses a **LumenAI-controlled synthetic** authorization;
  the **external-IRB authorization and real-data acquisition governance remain prerequisites** for
  any future institution-sponsored research and are **not** satisfied by this pilot.

*Scope narrowing changes the data-rights basis only. It does not waive, relax, or close any security
or scientific-integrity control. HOLD remains for the pilot until the applicable decisions are
recorded.*

# LumenAI Research Data Exchange

> **Audience:** Clinical researchers, IRBs, quality leadership, and governance teams. Defines how LumenAI creates, governs, and releases anonymized research datasets derived from the national SPD intelligence network. No causation claims; IRB and governance approval required before release.

---

## 1. Purpose

Enable peer-reviewed research on sterile processing quality, instrument lifecycle, and contamination patterns by providing governed, anonymized datasets to qualified researchers — while maintaining the platform's no-causation discipline and k-anonymity standards.

---

## 2. Dataset Lifecycle

```
created (draft) → governance review → approved → released
                                              ↓
                                         withdrawn (if needed)
```

No dataset enters `released` status without:
1. k-anonymity floor of 5 contributing facilities
2. Governance approval (`governance_approved: true`)
3. IRB approval number recorded (required for clinical studies)

---

## 3. Dataset Types

| `dataset_type` | Contents |
|----------------|---------|
| `benchmark_series` | Time-series of network benchmark metrics |
| `lifecycle_cohort` | Anonymized instrument lifecycle records (category level) |
| `recall_signal_cohort` | Aggregated recall signal history |

All datasets use the standard anonymization stack: pseudonyms + coarse attributes + Laplace noise + k-anonymity floor of 5.

---

## 4. Research Study Framework

Studies are linked to one or more released datasets. The principal investigator must acknowledge the **no-causation claims discipline** at study registration — studies that publish causal findings from LumenAI network data violate the governance agreement.

### Study Lifecycle

```
proposed → approved → active → completed → published
```

---

## 5. Publication Governance

Publications citing LumenAI network data must:

- Not include causation claims (`causation_claim_present: false`)
- Be recorded in the platform (`POST /research/publications`)
- Receive governance clearance (`governance_cleared: true`) before being cited in LumenAI marketing or external communications

A publication with `causation_claim_present: true` is **rejected at the API layer** — it cannot be recorded under LumenAI network data governance.

---

## 6. Claims Discipline

All LumenAI-supported research outputs must use appropriately qualified language:

| Allowed | Not Allowed |
|---------|-------------|
| "Potential association between X and Y" | "X causes Y" |
| "Quality review recommended" | "X proves Y" |
| "Investigation candidate" | "X predicts Y with certainty" |
| "Observed pattern in the network" | "This finding applies to all SPD departments" |

---

## 7. Endpoints

| Endpoint | Purpose |
|----------|---------|
| `POST /api/network-intelligence/research/datasets` | Create anonymized dataset (draft) |
| `POST /api/network-intelligence/research/datasets/{id}/approve` | Governance approval |
| `POST /api/network-intelligence/research/datasets/{id}/release` | Release (requires prior approval) |
| `GET /api/network-intelligence/research/datasets` | List datasets |
| `POST /api/network-intelligence/research/studies` | Register a study (PI acknowledges claims discipline) |
| `GET /api/network-intelligence/research/studies` | List studies |
| `POST /api/network-intelligence/research/publications` | Record publication (causation claim check enforced) |

---

## 8. Governance

| Principle | Enforcement |
|-----------|-------------|
| k-anonymity | Hard 5-facility floor on all datasets |
| IRB documentation | IRB approval number required for clinical studies |
| Governance approval | Dual sign-off (LumenAI governance + IRB) before release |
| No causation | API rejects publications with `causation_claim_present: true` |
| PI acknowledgment | `claims_discipline_acknowledged: true` required at study registration |
| Immutable release history | Released datasets are versioned and audit-logged |
| Audit trail | Every dataset creation, approval, release, and study registration is compliance-flagged |

---

## 9. Roadmap

| Horizon | Milestone |
|---------|-----------|
| Q3–Q4 Year 1 | First governed dataset released to external researchers |
| Year 2 | 3+ published peer-reviewed studies citing LumenAI network data |
| Year 3 | Research platform recognized as category authority for SPD quality evidence |

---

*LumenAI does not claim FDA clearance or regulatory approval. All research datasets are anonymized aggregates. No published findings should be interpreted as causation; all outputs are candidate signals and observational associations requiring qualified clinical review.*

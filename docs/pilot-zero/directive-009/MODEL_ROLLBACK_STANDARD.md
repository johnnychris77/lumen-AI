# LPZ-DIR-009 — Model Rollback Standard

**Purpose:** ensure that any candidate model in use (in a governed pilot or as a
reference) can be **reverted quickly and safely** to a known-good prior version,
with full audit preservation. Rollback is a safety control, not an afterthought.

## Rollback capabilities (every model shall support)

| Capability | Meaning |
|---|---|
| **Immediate rollback** | Revert to the designated known-good prior version without redeploying/retraining. |
| **Historical retrieval** | Retrieve any prior version's artifact + metadata (immutable). |
| **Previous version restoration** | Restore the prior version as the active reference. |
| **Audit preservation** | The rollback event and both versions are preserved in the audit trail. |
| **Performance history** | Evaluation/monitoring history is retained across versions. |
| **Reason for rollback** | The cause is recorded (defect, drift, error spike, policy). |

## Rules

1. **Rollback reference required.** Every promoted model version records a
   **rollback reference** to a specific known-good prior version
   (`MODEL_VERSIONING_STANDARD.md`).
2. **No destruction.** Rollback **supersedes**, it never deletes. The rolled-back-
   from version is retained (retired/archived), not erased.
3. **Immediate + attributable.** Rollback is a single governed action recording who,
   when, from/to versions, and why.
4. **Integrity verified.** The restored version's artifact `checksum` is verified on
   restoration.
5. **Audit preserved.** The full history (both versions, evaluation/monitoring
   records, rollback reason) survives the rollback.
6. **Trigger-ready.** Rollback triggers include: monitored drift, error-rate spike,
   a discovered defect, a failed governance check, or a policy decision
   (`AI_GOVERNANCE_STANDARD.md`).
7. **Human-decided.** Rollback is authorized by the AI Governance Lead / owner; it
   is never an autonomous clinical action.

## Rollback procedure (governed)

1. **Detect/decide** — a trigger or governance decision initiates rollback.
2. **Record reason** — cause + affected version.
3. **Restore** — designate the rollback-reference version active; verify checksum.
4. **Preserve** — retire (not delete) the superseded version; retain history.
5. **Audit** — emit an attributable rollback event; update status.
6. **Review** — schedule root-cause review of the rolled-back version.

## Expected outcome (validation)

Given a model in use and a rollback trigger, the designated prior version is
restored, its checksum verifies, the superseded version and all history remain
retrievable, and the rollback event (who/when/from→to/why) is in the audit trail.

## Governance note (existing system)

`ModelRegistryEntry` retains versioned entries with `artifact_checksum` and a
candidate-stage status, and the promotion services track stage transitions —
providing the substrate for historical retrieval and restoration. Governance
additions recorded for a future authorized change: add an explicit **rollback
reference** pointer, a **rollback event** record (from/to/reason/actor), and a
checksum-verified restore action. No code is changed under this directive.

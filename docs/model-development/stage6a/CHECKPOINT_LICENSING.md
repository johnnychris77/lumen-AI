# Stage 6A — Pretrained Checkpoint Licensing Verification

Status: **ResNet18 ImageNet weights remain BLOCKED for research use pending an
operator's documented licensing verification.** This document records the licensing
questions that must be answered before any pretrained backbone is approved, and the
mechanism by which an operator approves one.

## 1. Why a backbone checkpoint needs licensing review

PaDiM and PatchCore are *feature-based* anomaly detectors: they rely on a pretrained
CNN backbone (here ResNet18) as a frozen feature extractor. The **model code**
(Anomalib, Apache-2.0; torchvision, BSD-3) and the **pretrained weights** have
*separate* licenses. Using the weights requires verifying:

| Question | Must be answered before approval |
|---|---|
| **Weights license** | What license governs the specific weights file? |
| **Redistribution** | May the weights be redistributed / stored in our environment? |
| **Commercial vs research** | Are commercial uses permitted, or research-only? |
| **Training-data terms** | Do the *training dataset's* terms (e.g. ImageNet) restrict downstream use? |
| **Provenance** | Is the file's source authentic and its SHA-256 recorded? |

## 2. torchvision ResNet18 / ImageNet — status: BLOCKED

- The torchvision **code** is BSD-3-Clause.
- The torchvision ResNet18 `IMAGENET1K_V1` **weights** are trained on ImageNet-1k.
  **ImageNet's own terms** are commonly understood to permit **non-commercial
  research** use and restrict commercial redistribution; this must be **verified
  against the current upstream terms by a human**, not assumed.
- Therefore `resnet18_imagenet` ships `approved=False, rights_cleared=False` in the
  checkpoint registry and **`verify_checkpoint` raises `CheckpointNotApprovedError`**.
  LumenAI never auto-downloads these weights.

**Resolution required (operator action):** a human with authority verifies the exact
weights file, its license, redistribution and commercial-research permissions, records
the file's SHA-256, and approves it — only then may real-ImageNet-backbone PaDiM run.

## 3. Operator approval mechanism (implemented)

`checkpoint.register_operator_approved_checkpoint(...)` records an operator-approved
backbone that an operator has **placed on disk in an isolated research environment**:

- it computes and stores the file's **SHA-256**, so a later swap is rejected;
- it keeps verification **fail-closed** (`requires_file=True`, digest-checked);
- `rights_cleared` is the operator's **explicit assertion** — the function never
  infers rights;
- an optional `compatibility_policy` may mark a backbone
  `scientifically_valid=False` (e.g. a locally-generated research-execution backbone,
  used in this stage's benchmark to verify the pipeline without any licensed weights).

No automatic downloads, and no research-to-clinical promotion, are introduced.

## 4. What the Stage 6A benchmark used (and did not)

The governed benchmark (`stage6a_governed_benchmark.py`) used a **locally-generated,
random-init** ResNet18 feature extractor — **no ImageNet or other third-party-rights
weights** — approved only as a research-execution checkpoint
(`scientifically_valid=False`). This verifies the *pipeline*; it is **not** scientific
performance.

## 5. Outstanding before a real approved-backbone run

1. Human verification of the exact pretrained ResNet18 weights' license, redistribution
   rights, and commercial-research permissions (or selection of a permissively-licensed
   alternative backbone).
2. The verified weights file placed in the isolated research environment and approved
   via `register_operator_approved_checkpoint` with its recorded SHA-256.
3. Confirmation that the backbone's license is compatible with the project's intended
   use (research benchmark; **not** clinical deployment, which is a separate review).

# Sealed Test Set Evaluation Protocol

## Purpose
The sealed (holdout) test set is evaluated ONCE, immediately before regulatory submission,
by an independent evaluator who has had no access to training or validation data.

## Seal Process
1. Dataset curator exports 15% holdout from validation dataset (stratified by category)
2. SHA-256 hash of each image file recorded in `sealed_test_manifest.json`
3. Manifest signed by Clinical Validation Committee chair
4. Set stored in separate S3 prefix with no read access for model team
5. Seal date and hash stored in `SealedTestSetRegistry` (immutable DB record)

## Evaluation Process
1. Independent evaluator receives sealed set credentials (time-limited, audited)
2. LumenAI inference run on sealed set — results written to `SealedTestResult` table
3. Ground truth unlocked and joined — confusion matrix computed
4. Results reviewed by CVC within 5 business days
5. Report signed and archived — cannot be altered

## Pass Criteria
- Overall accuracy ≥ 88%
- Critical finding sensitivity ≥ 95%
- Overall kappa ≥ 0.80
- Critical FN rate ≤ 2%

## Failure Response
If sealed test fails any criterion:
1. Evaluation paused — no submission
2. Root cause analysis within 10 business days
3. Model remediation → re-validation (full cycle restarts)
4. Sealed test set rotated (new holdout drawn)

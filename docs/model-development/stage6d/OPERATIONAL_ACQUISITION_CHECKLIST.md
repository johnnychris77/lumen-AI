# Stage 6D — Operational Acquisition Checklist

The concrete, ordered steps to run LumenAI's **first authorized nonclinical
instrument research study**. Each step resolves against an authoritative record, so
the software gates are satisfied only by real approvals — not by caller assertions.
Nothing in this checklist authorizes clinical use, deployment, or model promotion.

## A. Authorizations (external — record-backed)

- [ ] **Institutional / ethics determination** that this nonclinical instrument study
      is authorized → recorded as a `GovernanceApproval` (`request_type =
      research_data_authorization`, `target_resource_id = <dataset_id>`, `status =
      approved`, `reviewed_by = <authenticated approver>`).
- [ ] **Dataset-scoped research-use consent / data-use agreement** → `GovernanceApproval`
      (`request_type = research_use_consent`, `target_resource_id = <dataset_id>`).
- [ ] **Tenant research-use consent** live and not withdrawn (`ConsentRecord`,
      `consent_type ∈ {benchmarking_contribution, analytics}`).
- [ ] **Scientific approver(s)** provisioned as authenticated identities with an allowed
      role (`UserRoleAssignment.role ∈ {admin, quality_director}`); approvals are bound
      to the **authenticated request context**, not a typed username.

## B. Specimens & imaging (research-only, segregated from clinical)

- [ ] Research-only instruments sourced and **segregated from clinical instruments**;
      they never return to clinical use.
- [ ] Required categories represented: independently-verified clean references,
      documented corrosion, measured pitting, known residue simulants (or confirmed
      residue), and difficult visual confounders; plus **borescope lumen** captures.
- [ ] External-camera and borescope captures kept as **separate** evaluation cohorts.
- [ ] Per image recorded: instrument, specimen, session, laboratory batch, modality,
      source rights, **SHA-256**, annotation version, review status. **Visually normal
      appearance is never recorded as verified cleanliness.**

## C. Laboratory reference evidence (record-backed)

- [ ] For corrosion/pitting/residue specimens, an independently-reviewed
      `VeritasEvidenceProvenanceRecord` (`approval_status = approved`, `reviewer` set,
      `file_hash = <image SHA-256>`, `instrument_id` matching). Laboratory confirmation
      is resolved from this record for the **exact image + specimen** — never a boolean.

## D. Checkpoint (record-backed, licensed)

- [ ] Independent verification of the exact pretrained checkpoint's **source, license,
      permitted use and file digest**, recorded as two `GovernanceApproval`s
      (`scientific_checkpoint_license`, `scientific_checkpoint_source`, each with
      `requested_payload.use_scope = scientific_research`).
- [ ] Register via `register_scientific_checkpoint(db, …, auth=<approver context>, …)`;
      `assert_scientific_checkpoint` then passes. **Random-weight backbones are never
      eligible for scientific performance claims.**

## E. Ingestion (existing governed service)

- [ ] `acquire_research_cohort(db, manifest, tenant_id=…, dataset_id=…, auth=…,
      import_images=True)` — resolves authorization, validates each image against the
      acquisition contract, verifies supplied bytes' SHA-256 against the registered hash,
      and hands them to the existing `image_retention_service.retain_image` (EXIF-stripped,
      deduped, access-controlled). The **actual imported count** and resolved
      `RetainedImage` storage ids are recorded. No new image store; no bypass.

## F. Protocol-approved evaluation

- [ ] Statistical reviewer (authenticated) + approved statistical protocol
      (`GovernanceApproval`, `statistical_protocol_approval`) sign off on cohort sizes.
- [ ] Physical-specimen grouping with verified independence across fit / calibration /
      validation / sealed-test; thresholds frozen on calibration images before the sealed
      test; external-camera and borescope evaluated separately.
- [ ] Report real denominators, uncertainty, **false negatives**, false positives, and
      confounders. No clinical-performance or independent-validation claim beyond what the
      cohort supports.

## Gate

`assess_scientific_readiness(...)` returns `ready_for_scientific_benchmark = True` only
when A, C, D and F resolve against records. Until then the benchmark returns
**`BLOCKED_REAL_IMAGE_BENCHMARK`**.

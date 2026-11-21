# GD-3 Clinical Workflow Approval Checklist (v2 — legacy quarantine & attribution packet)

**Program:** P472-03 · **PR #181 (DRAFT)** · supersedes
`gd3-clinical-workflow-approval-checklist-v1.md` (preserved). Prepared for the **clinical operations
& inspection-workflow owner**. This is an approval *packet*, not an approval. **No production
migration or attribution is performed.** Explicit owner acceptance is required before any production
data is attributed or migrated.

## 1. Records that remain inaccessible by design (fail-closed quarantine)
| Data | Why inaccessible | Scope of impact |
|------|------------------|-----------------|
| Vendor baseline rows written before GD-3 (`tenant_id IS NULL`) | GD-3 migration `d8f3a6b914c7` leaves legacy rows NULL; tenant-scoped reads never match NULL | Legacy baselines cannot drive clinical scoring until attributed |
| Manufacturer / repair-partner portal data (AW-07) | `require_manufacturer_auth` now requires a verified `ManufacturerMembership`; none exist until onboarding seeds them | Manufacturer portals return 403 until memberships are attributed |
| Accreditation evidence / readiness / survey / certifications / programs for a caller whose verified tenant holds no such rows | Batch 3 scopes these to the caller's verified tenant | A client that previously relied on passing a `tenant_id` query to read another tenant's data no longer can (intended) |

## 2. Evidence required to establish ownership (before attribution)
- For a NULL-tenant vendor baseline: the submitting organization of record, a verifiable link to that
  tenant, and the baseline's provenance (manufacturer source + approval).
- For a manufacturer membership: an authorized manufacturer-onboarding record binding the user to the
  manufacturer organization, with role and enablement.
- No ownership may be **guessed**; guessing re-opens the exact cross-tenant exposure these controls close.

## 3. Authorized attribution / rejection / escalation procedures (to be executed by the owner, not this agent)
- **Attribute:** owner confirms ownership evidence → records the attribution decision (who/when/why) →
  an authorized migration job sets the tenant/membership → an audit event is written.
- **Reject:** evidence insufficient → the record stays quarantined; a rejection reason is recorded.
- **Escalate:** conflicting ownership claims → escalate to security + clinical governance jointly; no
  attribution until resolved.

## 4. Clinical inspection-workflow effects to evaluate
- Dashboards/readiness that previously aggregated NULL-tenant or cross-tenant data will show reduced or
  zero counts until attribution; confirm this does not mask a clinically-relevant gap.
- Confirm no clinical decision path depends on a now-quarantined record.
- Confirm the manufacturer portals' 403-until-onboarded behaviour does not block a time-critical
  clinical workflow (these portals are intelligence/analytics, not bedside).

## 5. Owner acceptance (required before any production migration)
- [ ] Ownership-evidence standard accepted · approver / date: __________ **PENDING**
- [ ] Attribution / rejection / escalation procedure accepted · __________ **PENDING**
- [ ] Clinical-workflow impact reviewed and accepted · __________ **PENDING**
- [ ] Explicit authorization to run the production attribution/migration · __________ **PENDING**

**No item is signed. Disposition: HOLD / NO-GO.**

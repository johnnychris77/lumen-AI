# LumenAI — Network Analytics

Objectives 5 (Cross-Facility Collaboration) and 9 (Customer Governance) review. Both objectives ultimately depend on the same underlying finding: this codebase has a real, if narrow, collaboration layer, and a proliferation of role-vocabulary labels that mostly don't gate anything.

## Customer Governance — the 4 proposed admin tiers do not exist as 4 distinct enforced roles

**"Enterprise administrator / Regional administrator / Facility administrator / Department manager" collapse onto the same handful of real, enforced roles already established throughout this document program (`admin`/`spd_manager`/`operator`/`viewer`/`vendor_user`).** Every layer that appears to add a distinct enterprise-governance role turns out, on direct trace, to be an unenforced label:

- `backend/app/portfolio_authz.py`'s `GLOBAL_PORTFOLIO_ROLES = {"platform_admin", "portfolio_admin", "tenant_admin"}` gates exactly one thing (a portfolio-wide QBR/executive read surface, two route files) — and it's a **flat** single scope, not a hierarchy, plus it accepts the literal `dev-token` bearer string and three hardcoded dev emails as an alternate bypass path.
- `atlas_enterprise.py`'s `ENTERPRISE_ROLES` vocabulary (`regional_administrator`, `market_director`, `facility_director`, `supervisor`, `technician`, plus others) is stored in a real `EnterpriseRoleAssignment` ledger table — but **every actual route that exposes or checks this ledger, including the role-grant/revoke endpoints themselves, is gated by the same real 4-role set** (`admin`/`spd_manager`/`operator`/`viewer`), not by the ledger's own role vocabulary. The ledger records who holds a label; it never itself authorizes anything.
- `catalyst_persona_service.py`'s `_EXECUTIVE_ROLES` set (`enterprise_admin`, `hospital_admin`, `facility_director`, `market_director`, `regional_administrator`) exists purely to select which canned KPI view a chatbot persona shows — not an access gate.
- `routes/executive.py` uses a role string only as a dict key to pick which KPI block to return, behind the same generic `require_enterprise_auth` dependency used for every role.
- `platform_identity_service.py` itself documents this directly: it unions three separate role vocabularies (`_DEV_AUTHZ_ROLES`, `_ENTERPRISE_AUTHZ_ROLES`, `_ATLAS_RBAC_ROLES`) into a read-only catalog, explicitly noting it is *"not a new source of truth."*

**`atlas_rbac_service.py`'s own docstring is the most direct confirmation available**: *"There is no central role registry anywhere in this codebase today — four independent auth modules (`authz.py`, `enterprise_auth.py`, `tenant_authz.py`, `portfolio_authz.py`) each declare their own ad hoc role strings, checked per-route with no shared enum."* This is not a new finding this review is introducing — it is a documented, self-aware architectural characteristic of the codebase.

**Region and Department are real data models, but carry no access control**: `enterprise_hierarchy.py` has a genuine `EnterpriseRegion` table and a genuine `EnterpriseDepartment` table (with a `manager_email` field) — but `manager_email` is a single plain-string field, not a link to a role-assignment record, and no route anywhere checks "is this caller the department's manager." A second, competing `EnterpriseDepartment` model exists in `enterprise_quality.py` with no manager field at all, and a second, competing region concept in `enterprise_quality.py`'s `EnterpriseFacility.region` is a free-text label unrelated to the real `EnterpriseRegion` table.

**Recommendation**: before building any Version 1.3 feature that assumes "Regional Administrator" or "Department Manager" is an enforceable permission tier, either (a) wire `atlas_rbac_service`'s existing membership-check mechanism into the routes it's meant to protect (the same fix needed for the `system_id` authorization gap in `ENTERPRISE_OPERATIONS.md`), or (b) explicitly document that these are organizational labels/personas today, not enforced permission tiers, and scope Version 1.3's actual RBAC work around the real 5-role set.

## Cross-Facility Collaboration — real, but narrower than proposed

The "Collaboration Hub" (Project Beacon, `backend/app/services/beacon_*.py`) is real but does not implement shared playbooks, shared SOPs, or shared education content as distinct artifacts:

- Its participant roster reuses `AdvisoryConsortiumMember` (from `p24_standards.py`), not a new playbook/SOP model.
- Its "knowledge sharing" reuses `horizon_contribution_service.py`'s `KnowledgeContribution` — already documented in that file's own docstring as "cross-organization, de-identified, approval-gated."
- Genuinely new Beacon-specific tables are an advisory-board meeting/action-item/recommendation tracker (`AdvisoryBoardMeeting`, `AdvisoryBoardActionItem`, `AdvisoryBoardRecommendation`) and a k-anonymized repair-intelligence snapshot — not shared playbooks or SOPs.
- **Governed baseline sharing does exist, separately, under Project Atlas**: `atlas_enterprise.py`'s `SharedKnowledgeArticle` model implements a real "publish-a-copy" pattern with a `sharing_scope` (facility/market/system_wide) and approver/version/effective-date fields, served via `atlas_knowledge_sharing_service.py`.
- No dedicated cross-facility "shared education content" model was found — Sage's `education_content` field is per-learner, tenant-scoped, not a shared cross-facility artifact.

**Collaboration is genuinely configurable, but at a narrower granularity than "per facility"**: two real, independently-settable boolean opt-in flags exist on the shared consortium-membership row — `observatory_opt_in` (Project Olympus) and `research_opt_in` (Project Genesis AI's Research Collaboration Hub) — plus a coarser `membership_status` (pending/active/suspended/resigned) gate used by the Beacon collaboration hub to filter to active members only. These are real, working, and correctly scoped per named program, but there is no single general "Cross-Facility Collaboration" toggle with Enterprise/Regional/Facility-level granularity as the brief's Objective 5 implies.

## Recommendation

1. Reframe "Customer Governance" (Objective 9) around the real 5-role RBAC set, either by wiring the existing-but-disconnected `EnterpriseRoleAssignment`/`atlas_rbac_service` mechanism into real enforcement points, or by explicitly retitling the Enterprise/Regional/Facility/Department vocabulary as organizational labels rather than security tiers.
2. Consolidate Atlas's `SharedKnowledgeArticle` (governed baseline/knowledge sharing) and Beacon's advisory-board tracker into one clearly-documented "Cross-Facility Collaboration" feature area, since they currently live as two unrelated projects with overlapping conceptual scope.
3. Building genuine shared-SOP or shared-education-content artifacts is new work — no existing model to repurpose.

# LumenAI — Customer Onboarding Guide

Objective 2 review. Consolidates real, existing onboarding content rather than authoring a new process from scratch — the repository already has substantial, specific material for every checklist item this objective asks for.

## Pre-installation checklist and infrastructure assessment

Reference `docs/enterprise/site-onboarding-guide.md`'s real onboarding-document checklist directly: it lists the exact set of signed documents a site must provide before onboarding begins, including a Business Associate Agreement ("if applicable") and a Master Service Agreement. **Important honesty note carried from `docs/commercial-readiness/LEGAL_GOVERNANCE_PACKAGE.md`**: while this checklist correctly requires these documents, no actual BAA or MSA template exists anywhere in this repository yet — that gap must be closed before this checklist can be operated in a real customer engagement.

## Network requirements and security review

`docs/pilot/deployment-verification-checklist.md` gives concrete, curl-level verification steps (health endpoint, auth, dashboard, navigation) appropriate for a network/connectivity pre-check. For the security review step, reference `docs/production-readiness/PRODUCTION_READINESS_SCORECARD.md`'s three named Critical Gaps directly with a new customer's security team — disclosing them here is more credible than a security review that omits them and is later discovered independently.

## User provisioning and SSO integration

`docs/customer/customer-onboarding-playbook.md` has real, concrete SSO/OIDC setup instructions for Azure AD, Okta, and Epic. Use this directly. **Role-provisioning caveat, carried from `docs/ux-review/USER_PERSONAS.md`**: the real, enforced role set is `admin`/`spd_manager`/`operator`/`viewer`/`vendor_user`. `admin_users.py`'s assignable-role list also includes `supervisor`, which is not independently enforced anywhere else in the platform — provision customers with this understanding rather than implying "Supervisor" is a distinct permission tier.

## Training schedule

Reference `docs/demo-program/TRAINING_GUIDE.md` (Phase 5) directly — it already indexes the real quick-start guide, role-based training matrix, and 4-session onboarding curriculum. Do not re-author a training schedule here; this document only confirms training is a required onboarding milestone and points to where the actual schedule lives.

## Go-live checklist

Reference `docs/pilot/pilot-launch-runbook.md`'s Pre-Launch Checklist (T-14 days: infrastructure, tenant provisioning, BAA/DPA, integration verification) and Launch Day checklist (with documented abort criteria) directly. The consolidated operational go-live checklist for this Phase 6 program is `docs/commercial-readiness/PRODUCTION_GO_LIVE_CHECKLIST.md` — this onboarding guide's go-live section defers to that document rather than duplicating its content.

## What this guide adds vs. what already existed

The real contribution of this document is sequencing: pointing a new customer-onboarding lead to the right existing source (site-onboarding-guide → customer-onboarding-playbook → deployment-verification-checklist → pilot-launch-runbook → TRAINING_GUIDE → PRODUCTION_GO_LIVE_CHECKLIST) in the order an actual onboarding would proceed, rather than requiring them to discover this content scattered across `docs/enterprise/`, `docs/customer/`, `docs/pilot/`, and `docs/demo-program/` unassisted — the same reuse discipline applied throughout this document set.

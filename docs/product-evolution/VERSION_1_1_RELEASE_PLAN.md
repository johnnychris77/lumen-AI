# LumenAI — Version 1.1 Release Plan

Applies the Validation checklist (customer evidence, measurable value, clinical review, architecture review, security review, testing plan, rollback plan) to every Approved item in `docs/product-evolution/PRODUCT_BACKLOG.md`. Where an item cannot honestly satisfy "customer evidence" — because no real customer exists yet — that gap is stated explicitly rather than checked off.

## Validation status per Approved item

| Feature ID | Customer evidence | Measurable value | Clinical review | Architecture review | Security review | Testing plan | Rollback plan |
|---|---|---|---|---|---|---|---|
| FR-001 (Supervisor approve/return) | ⚠️ Not yet — internal review only | ✅ Closes a named workflow gap | ✅ Aligns with `docs/clinical-validation/HUMAN_OVERSIGHT_MODEL.md` | ✅ UI-only change, no new backend | ✅ Uses existing RBAC, no new attack surface | Add integration test exercising the new control end-to-end | Feature-flag the new control (real flag infrastructure confirmed in `docs/commercial-readiness/PRODUCT_OPERATIONS_GUIDE.md`); disable flag to roll back |
| FR-003 (Wire orphaned routes) | ⚠️ Not yet | ✅ Confirmed 45-route gap | N/A — navigation only | ✅ No backend change | ✅ No new authorization surface (client-side nav only) | Manual navigation smoke test per role | Revert the nav-config commit; no data impact |
| FR-005 (Atlas N+1 fix) | ⚠️ Not yet | ✅ Confirmed query-count reduction (code-verifiable) | N/A | ✅ Service-internal refactor only | ✅ No security surface change | Add a query-count assertion test against `atlas_dashboard_service.py` | Revert the refactor commit; read-only service, no data risk |
| FR-006 (Consistent AI inference queuing) | ⚠️ Not yet | ✅ Confirmed latency-path fix | N/A | ✅ Uses existing RQ infrastructure | ✅ No new surface | Add a test confirming `stream_frame` enqueues rather than blocks | Revert to synchronous call if RQ worker capacity issues arise |
| FR-007 (Mount Veritas panel / GuardianX tab) | ⚠️ Not yet | ✅ Closes a named explainability-field gap | ✅ Directly serves `docs/clinical-validation/AI_LIMITATIONS.md`'s explainability standard | ✅ Wires existing components/endpoints, no new ones | ✅ No new data exposure — same data, now rendered | Add a UI test confirming the panel renders `limitations`/`alternative_explanations` | Revert the mounting commit; underlying services untouched |
| FR-008 (Bind human-review disclaimer) | ⚠️ Not yet | ✅ Closes a fidelity gap between claim and behavior | ✅ Directly relevant to `docs/clinical-validation/PATIENT_SAFETY_MODEL.md` | ✅ Template-binding change only | ✅ No security surface | Add a test asserting the disclaimer reflects a false `human_review_required` value correctly | Revert to static text if binding introduces a rendering regression |

## The honest gap in this release plan

**No item in this Version 1.1 release satisfies "customer evidence" in the sense this program's mission statement primarily intends** (real pilot-hospital feedback). Every item instead satisfies the evidence bar through usability studies, performance metrics, and clinical validation reviews — all explicitly acceptable per this program's own input-source list, but not the primary source the mission emphasizes. **This release plan recommends proceeding with these items regardless**, because they close verified, real gaps between the platform's stated governance principles and its actual behavior — the same logic underlying `docs/product-evolution/VERSION_1_1_ROADMAP.md`'s Stage 1 sequencing. Recommend explicitly informing the Feature Review Board of this evidentiary gap before final approval, rather than presenting these items as if real customer validation already occurred.

## Deployment approach

Consistent with `docs/commercial-readiness/DEPLOYMENT_GUIDE.md`'s findings: deploy via the existing Render auto-deploy path; do not deploy to any Kubernetes/Helm target, since neither has ever been applied to a real cluster. Each item above should ship as its own small, independently-revertable commit, following the same pattern established in `docs/release-management/PATCH_APPROVAL_RECORD.md` for this cycle's bug fixes — no "big bang" 1.1 release; a sequence of small, tested, individually-rollback-able patches culminating in the 1.1 minor-version tag once all Stage 1-3 items are complete.

## Customer notification plan

Since no real customers exist yet, this section is a template for future use: once a pilot customer exists, notify them of each Version 1.1 change via the release-notes mechanism already established in `docs/release-management/PATCH_NOTES.md`, extended to a `VERSION_1_1_RELEASE_NOTES.md` at the point of the actual 1.1 tag.

"""Project Atlas Sprint 1 — Baseline Image Library tests.

Covers the 18-item checklist: linking an existing LCID image (no byte
duplication), hash storage/verification, provenance requirements,
governed activation, multi-anatomy-zone baselines, the compatibility
contract, the resolution hierarchy, cross-tenant isolation, RBAC,
supersession history, the legacy IMAGE_EVIDENCE_MISSING report, the
training-eligibility/baseline-approval separation, and audit persistence.
"""
import io
import uuid

import pytest
from fastapi.testclient import TestClient
from PIL import Image, PngImagePlugin

from app.db.session import SessionLocal
from app.main import app
from app.models.audit_log import AuditLog
from app.models.baseline_image_library import (
    BASELINE_NOT_ACTIVE,
    COMPATIBLE,
    INCOMPATIBLE_ANATOMY_ZONE,
    INCOMPATIBLE_VIEW,
    NO_APPROVED_BASELINE,
    RESOLUTION_DIGITAL_TWIN_EXACT,
    RESOLUTION_MANUFACTURER_MODEL_ZONE,
    RESOLUTION_NONE,
    SOURCE_DIGITAL_TWIN_INITIAL_REFERENCE,
    SOURCE_MANUFACTURER_REFERENCE,
    SOURCE_ORGANIZATION_KNOWN_GOOD,
    STATE_ACTIVE,
    STATE_APPROVED,
    STATE_DRAFT,
    STATE_SUPERSEDED,
    IMAGE_TYPE_ANATOMY_ZONE_REFERENCE,
    IMAGE_TYPE_DIGITAL_TWIN_BASELINE,
    IMAGE_TYPE_MANUFACTURER_BASELINE,
    BaselineImageLink,
)
from app.models.baseline_library import BaselineLibraryEntry
from app.models.retained_image import RetainedImage
from app.services import baseline_compatibility_service as compat
from app.services import baseline_image_library_service as bil
from app.services.ml import dataset_registry

client = TestClient(app)
AUTH_ADMIN = {"Authorization": "Bearer dev-token"}
AUTH_MANAGER = {"Authorization": "Bearer manager-token"}
AUTH_OPERATOR = {"Authorization": "Bearer operator-token"}
AUTH_VIEWER = {"Authorization": "Bearer viewer-token"}
TENANT = "default-tenant"
OTHER_TENANT = "other-tenant"

_lcid_counter = 0


def _img(brightness=140, size=200) -> bytes:
    global _lcid_counter
    _lcid_counter += 1
    img = Image.new("RGB", (size, size), (brightness, brightness, brightness))
    px = img.load()
    for x in range(0, size, 5):
        for y in range(size):
            px[x, y] = (255 - brightness, 255 - brightness, 255 - brightness)
    buf = io.BytesIO()
    # A random per-call PNG text chunk guarantees a unique SHA-256 even
    # across separate pytest invocations sharing the same persistent
    # SQLite test DB (a fixed brightness/counter sequence alone would
    # regenerate byte-identical images run-to-run and collide with a
    # prior run's leftover DatasetRegistryEntry row).
    meta = PngImagePlugin.PngInfo()
    meta.add_text("test-nonce", uuid.uuid4().hex)
    img.save(buf, format="PNG", pnginfo=meta)
    return buf.getvalue()


def _make_retained_image(db, data: bytes, *, tenant_id: str = TENANT) -> RetainedImage:
    import hashlib
    row = RetainedImage(
        tenant_id=tenant_id, deident_name="baseline-test", instrument_type="scissors",
        content_type="image/png", size_bytes=len(data), sha256=hashlib.sha256(data).hexdigest(),
        exif_stripped=True, source="test", consent_recorded=True, uploaded_by="tester",
        image_bytes=data,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _make_lcid_entry(
    db, *, tenant_id: str = TENANT, data: bytes | None = None, manufacturer="Acme",
    instrument_family="scissors", instrument_model="X1", anatomy_zone="tip", catalog_number="CAT-1",
    usage_rights="internal_use", phi_verification="verified", image_quality="Good",
    instrument_barcode="", instrument_udi="",
):
    global _lcid_counter
    _lcid_counter += 1
    data = data or _img(140 + _lcid_counter)
    retained = _make_retained_image(db, data, tenant_id=tenant_id)
    version = dataset_registry.create_dataset_version(db, tenant_id=tenant_id, version_label=f"v-{_lcid_counter}")
    entry = dataset_registry.register_image(
        db, tenant_id=tenant_id, dataset_version_id=version.id, retained_image_id=retained.id,
        image_sha256=retained.sha256, instrument_family=instrument_family, instrument_model=instrument_model,
        manufacturer=manufacturer, anatomy_zone=anatomy_zone, capture_device="phone", image_resolution="200x200",
        facility="Test Hospital", operator="tech1", usage_rights=usage_rights, phi_verification=phi_verification,
        instrument_barcode=instrument_barcode, instrument_udi=instrument_udi,
    )
    entry.catalog_number = catalog_number
    entry.image_quality = image_quality
    db.commit()
    db.refresh(entry)
    return entry


def _make_baseline_entry(db, *, manufacturer="Acme", instrument_category="scissors") -> BaselineLibraryEntry:
    row = BaselineLibraryEntry(
        udi=None, instrument_category=instrument_category, manufacturer_name=manufacturer,
        model_name="X1", baseline_type="manufacturer", approval_status="approved",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _link_and_approve(db, *, baseline_entry, lcid_entry, tenant_id=TENANT, source_type=SOURCE_ORGANIZATION_KNOWN_GOOD,
                       source_organization="", source_reference="", anatomy_zone="tip", inspection_view="lateral",
                       image_type=IMAGE_TYPE_MANUFACTURER_BASELINE) -> BaselineImageLink:
    link = bil.link_lcid_image_to_baseline(
        db, tenant_id=tenant_id, baseline_library_entry_id=baseline_entry.id, lcid_image_id=lcid_entry.id,
        anatomy_zone=anatomy_zone, inspection_view=inspection_view, image_type=image_type,
        source_type=source_type, source_organization=source_organization, source_reference=source_reference,
        created_by="ingest@test",
    )
    link = bil.submit_for_review(db, link=link, actor="ingest@test")
    bil.review_baseline_image(
        db, link=link, reviewer="reviewer@test", reviewer_role="spd_manager", decision="approve",
        rationale="Looks correct.", anatomy_compatibility_confirmed=True, image_quality_assessment="Good",
    )
    db.refresh(link)
    return link


# ── 1/2 — link an existing LCID image, no byte duplication ─────────────────

class TestLinkingAndByteReuse:
    def test_existing_lcid_image_can_be_linked(self):
        db = SessionLocal()
        try:
            baseline_entry = _make_baseline_entry(db)
            lcid_entry = _make_lcid_entry(db)
            link = bil.link_lcid_image_to_baseline(
                db, tenant_id=TENANT, baseline_library_entry_id=baseline_entry.id, lcid_image_id=lcid_entry.id,
                anatomy_zone="tip", inspection_view="lateral", image_type=IMAGE_TYPE_MANUFACTURER_BASELINE,
                source_type=SOURCE_ORGANIZATION_KNOWN_GOOD, created_by="ingest@test",
            )
            assert link.lifecycle_status == STATE_DRAFT
            assert link.lcid_image_id == lcid_entry.id
            assert link.manufacturer == lcid_entry.manufacturer
        finally:
            db.close()

    def test_image_bytes_are_not_duplicated(self):
        db = SessionLocal()
        try:
            assert not hasattr(BaselineImageLink, "image_bytes")
            baseline_entry = _make_baseline_entry(db)
            lcid_entry = _make_lcid_entry(db)
            link = bil.link_lcid_image_to_baseline(
                db, tenant_id=TENANT, baseline_library_entry_id=baseline_entry.id, lcid_image_id=lcid_entry.id,
                anatomy_zone="tip", inspection_view="lateral", image_type=IMAGE_TYPE_MANUFACTURER_BASELINE,
                source_type=SOURCE_ORGANIZATION_KNOWN_GOOD, created_by="ingest@test",
            )
            # Same retained_image_id as the LCID entry — a reference, not a copy.
            assert link.retained_image_id == lcid_entry.retained_image_id
        finally:
            db.close()

    def test_baseline_image_hash_is_stored_and_verified(self):
        db = SessionLocal()
        try:
            baseline_entry = _make_baseline_entry(db)
            data = _img(77)
            lcid_entry = _make_lcid_entry(db, data=data)
            link = _link_and_approve(db, baseline_entry=baseline_entry, lcid_entry=lcid_entry)
            assert link.image_sha256 == lcid_entry.image_sha256
            loaded = bil.load_and_verify_baseline_bytes(db, link=link, accessed_by="tester@test")
            assert loaded == data

            # Corrupt the stored bytes independently of the hash column —
            # verification must reject it, never silently use it.
            retained = db.query(RetainedImage).filter(RetainedImage.id == link.retained_image_id).first()
            retained.image_bytes = b"corrupted"
            db.commit()
            with pytest.raises(bil.ImageIdentityMismatchError):
                bil.load_and_verify_baseline_bytes(db, link=link, accessed_by="tester@test")
        finally:
            db.close()


# ── 4 — manufacturer source requires provenance ─────────────────────────────

class TestProvenance:
    def test_manufacturer_source_requires_provenance(self):
        db = SessionLocal()
        try:
            baseline_entry = _make_baseline_entry(db)
            lcid_entry = _make_lcid_entry(db)
            with pytest.raises(bil.ProvenanceRequiredError):
                bil.link_lcid_image_to_baseline(
                    db, tenant_id=TENANT, baseline_library_entry_id=baseline_entry.id, lcid_image_id=lcid_entry.id,
                    anatomy_zone="tip", inspection_view="lateral", image_type=IMAGE_TYPE_MANUFACTURER_BASELINE,
                    source_type=SOURCE_MANUFACTURER_REFERENCE, created_by="ingest@test",
                )
            # With real provenance, it succeeds.
            link = bil.link_lcid_image_to_baseline(
                db, tenant_id=TENANT, baseline_library_entry_id=baseline_entry.id, lcid_image_id=lcid_entry.id,
                anatomy_zone="tip", inspection_view="lateral", image_type=IMAGE_TYPE_MANUFACTURER_BASELINE,
                source_type=SOURCE_MANUFACTURER_REFERENCE, source_organization="Acme Corp",
                source_reference="Acme IFU doc #4471", created_by="ingest@test",
            )
            assert link.source_organization == "Acme Corp"
        finally:
            db.close()


# ── 5/6 — governed lifecycle gating ─────────────────────────────────────────

class TestLifecycleGating:
    def test_unapproved_baseline_cannot_become_active(self):
        db = SessionLocal()
        try:
            baseline_entry = _make_baseline_entry(db)
            lcid_entry = _make_lcid_entry(db)
            link = bil.link_lcid_image_to_baseline(
                db, tenant_id=TENANT, baseline_library_entry_id=baseline_entry.id, lcid_image_id=lcid_entry.id,
                anatomy_zone="tip", inspection_view="lateral", image_type=IMAGE_TYPE_MANUFACTURER_BASELINE,
                source_type=SOURCE_ORGANIZATION_KNOWN_GOOD, created_by="ingest@test",
            )
            with pytest.raises(bil.InvalidTransitionError):
                bil.activate_baseline_image(db, link=link, actor="admin@test", actor_role="admin")
        finally:
            db.close()

    def test_inactive_baseline_cannot_influence_comparison(self):
        db = SessionLocal()
        try:
            baseline_entry = _make_baseline_entry(db)
            lcid_entry = _make_lcid_entry(db)
            link = _link_and_approve(db, baseline_entry=baseline_entry, lcid_entry=lcid_entry)
            assert link.lifecycle_status == STATE_APPROVED  # approved, not yet ACTIVE
            candidate = compat.CandidateContext(
                tenant_id=TENANT, instrument_family="scissors", manufacturer="Acme",
                anatomy_zone="tip", inspection_view="lateral",
            )
            assert compat.check_compatibility(candidate=candidate, baseline_link=link) == BASELINE_NOT_ACTIVE
        finally:
            db.close()


# ── 7/8/9 — multi-anatomy-zone baselines + compatibility ────────────────────

class TestMultiZoneAndCompatibility:
    def test_baseline_may_contain_multiple_anatomy_zone_images(self):
        db = SessionLocal()
        try:
            baseline_entry = _make_baseline_entry(db)
            tip_entry = _make_lcid_entry(db, anatomy_zone="tip")
            hinge_entry = _make_lcid_entry(db, anatomy_zone="hinge")
            tip_link = _link_and_approve(db, baseline_entry=baseline_entry, lcid_entry=tip_entry, anatomy_zone="tip")
            hinge_link = _link_and_approve(
                db, baseline_entry=baseline_entry, lcid_entry=hinge_entry, anatomy_zone="hinge",
                image_type=IMAGE_TYPE_ANATOMY_ZONE_REFERENCE,
            )
            assert tip_link.baseline_library_entry_id == hinge_link.baseline_library_entry_id
            assert tip_link.anatomy_zone != hinge_link.anatomy_zone
        finally:
            db.close()

    def test_wrong_anatomy_zone_is_incompatible(self):
        db = SessionLocal()
        try:
            baseline_entry = _make_baseline_entry(db)
            lcid_entry = _make_lcid_entry(db, anatomy_zone="tip")
            link = _link_and_approve(db, baseline_entry=baseline_entry, lcid_entry=lcid_entry, anatomy_zone="tip")
            bil.activate_baseline_image(db, link=link, actor="admin@test", actor_role="admin")
            db.refresh(link)
            candidate = compat.CandidateContext(
                tenant_id=TENANT, instrument_family="scissors", manufacturer="Acme",
                anatomy_zone="hinge", inspection_view="lateral",
            )
            assert compat.check_compatibility(candidate=candidate, baseline_link=link) == INCOMPATIBLE_ANATOMY_ZONE
        finally:
            db.close()

    def test_wrong_view_is_incompatible(self):
        db = SessionLocal()
        try:
            baseline_entry = _make_baseline_entry(db)
            lcid_entry = _make_lcid_entry(db)
            link = _link_and_approve(db, baseline_entry=baseline_entry, lcid_entry=lcid_entry, inspection_view="lateral")
            bil.activate_baseline_image(db, link=link, actor="admin@test", actor_role="admin")
            db.refresh(link)
            candidate = compat.CandidateContext(
                tenant_id=TENANT, instrument_family="scissors", manufacturer="Acme",
                anatomy_zone="tip", inspection_view="frontal",
            )
            assert compat.check_compatibility(candidate=candidate, baseline_link=link) == INCOMPATIBLE_VIEW
        finally:
            db.close()

    def test_matching_candidate_is_compatible(self):
        db = SessionLocal()
        try:
            baseline_entry = _make_baseline_entry(db)
            lcid_entry = _make_lcid_entry(db)
            link = _link_and_approve(db, baseline_entry=baseline_entry, lcid_entry=lcid_entry)
            bil.activate_baseline_image(db, link=link, actor="admin@test", actor_role="admin")
            db.refresh(link)
            candidate = compat.CandidateContext(
                tenant_id=TENANT, instrument_family="scissors", manufacturer="Acme",
                anatomy_zone="tip", inspection_view="lateral", image_quality_status="Good",
            )
            assert compat.check_compatibility(candidate=candidate, baseline_link=link) == COMPATIBLE
        finally:
            db.close()


# ── 10/11 — resolution hierarchy ────────────────────────────────────────────

class TestResolutionHierarchy:
    def test_no_approved_baseline_returns_no_approved_baseline(self):
        db = SessionLocal()
        try:
            candidate = compat.CandidateContext(
                tenant_id=TENANT, instrument_family="nonexistent-family-xyz", anatomy_zone="tip",
            )
            result = compat.resolve_baseline_image(db, candidate=candidate)
            assert result.resolution_scope == RESOLUTION_NONE
            assert result.baseline_image_link_id is None
            assert compat.check_compatibility(candidate=candidate, baseline_link=None) == NO_APPROVED_BASELINE
        finally:
            db.close()

    def test_exact_digital_twin_resolves_before_broader_manufacturer_baseline(self):
        db = SessionLocal()
        try:
            baseline_entry = _make_baseline_entry(db, instrument_category="forceps-dt-test")
            # Broader manufacturer/model/zone baseline.
            broad_entry = _make_lcid_entry(
                db, instrument_family="forceps-dt-test", instrument_model="Model-DT", anatomy_zone="jaw",
            )
            broad_link = _link_and_approve(
                db, baseline_entry=baseline_entry, lcid_entry=broad_entry, anatomy_zone="jaw",
            )
            bil.activate_baseline_image(db, link=broad_link, actor="admin@test", actor_role="admin")

            # Exact physical-instrument Digital Twin baseline (real barcode).
            twin_entry = _make_lcid_entry(
                db, instrument_family="forceps-dt-test", instrument_model="Model-DT", anatomy_zone="jaw",
                instrument_barcode="BC-DT-001",
            )
            twin_link = _link_and_approve(
                db, baseline_entry=baseline_entry, lcid_entry=twin_entry, anatomy_zone="jaw",
                source_type=SOURCE_DIGITAL_TWIN_INITIAL_REFERENCE, image_type=IMAGE_TYPE_DIGITAL_TWIN_BASELINE,
            )
            bil.activate_baseline_image(db, link=twin_link, actor="admin@test", actor_role="admin")
            db.refresh(broad_link)
            db.refresh(twin_link)

            candidate = compat.CandidateContext(
                tenant_id=TENANT, instrument_family="forceps-dt-test", manufacturer="Acme", model_name="Model-DT",
                anatomy_zone="jaw", digital_twin_id="barcode:BC-DT-001",
            )
            result = compat.resolve_baseline_image(db, candidate=candidate)
            assert result.resolution_scope == RESOLUTION_DIGITAL_TWIN_EXACT
            assert result.baseline_image_link_id == twin_link.id

            # A candidate with no tracked twin identity falls to the broader
            # manufacturer/model/zone level — both links qualify at that
            # level (the twin instrument shares the same manufacturer/model/
            # zone), so only the resolution SCOPE is asserted here, not
            # which of the two equally-valid level-2 matches is chosen.
            candidate_untracked = compat.CandidateContext(
                tenant_id=TENANT, instrument_family="forceps-dt-test", manufacturer="Acme", model_name="Model-DT",
                anatomy_zone="jaw",
            )
            result2 = compat.resolve_baseline_image(db, candidate=candidate_untracked)
            assert result2.resolution_scope == RESOLUTION_MANUFACTURER_MODEL_ZONE
            assert result2.baseline_image_link_id in (broad_link.id, twin_link.id)
        finally:
            db.close()


# ── 12 — cross-tenant isolation ─────────────────────────────────────────────

class TestCrossTenantIsolation:
    def test_cross_tenant_baseline_access_denied(self):
        db = SessionLocal()
        try:
            baseline_entry = _make_baseline_entry(db, instrument_category="cross-tenant-test")
            lcid_entry = _make_lcid_entry(db, tenant_id=TENANT, instrument_family="cross-tenant-test")
            link = _link_and_approve(db, baseline_entry=baseline_entry, lcid_entry=lcid_entry, tenant_id=TENANT)
            bil.activate_baseline_image(db, link=link, actor="admin@test", actor_role="admin")
            db.refresh(link)

            # A resolution attempt scoped to a different tenant must not see it.
            candidate = compat.CandidateContext(
                tenant_id=OTHER_TENANT, instrument_family="cross-tenant-test", manufacturer="Acme",
                anatomy_zone="tip", inspection_view="lateral",
            )
            result = compat.resolve_baseline_image(db, candidate=candidate)
            assert result.baseline_image_link_id is None

            # Direct compatibility check against the other tenant's link also denied.
            assert compat.check_compatibility(candidate=candidate, baseline_link=link) == NO_APPROVED_BASELINE

            # A cross-tenant LCID image cannot even be linked in the first place.
            with pytest.raises(bil.LcidImageNotFound):
                bil.linked_lcid_entry(db, tenant_id=OTHER_TENANT, lcid_image_id=lcid_entry.id)
        finally:
            db.close()

    def test_cross_tenant_denied_over_http(self):
        db = SessionLocal()
        try:
            baseline_entry = _make_baseline_entry(db, instrument_category="cross-tenant-http-test")
            lcid_entry = _make_lcid_entry(db, tenant_id=TENANT, instrument_family="cross-tenant-http-test")
            link = _link_and_approve(db, baseline_entry=baseline_entry, lcid_entry=lcid_entry, tenant_id=TENANT)
            link_id = link.id
        finally:
            db.close()
        r = client.get(
            f"/api/baseline-library/images/{link_id}",
            headers={**AUTH_ADMIN, "x-lumenai-tenant-id": OTHER_TENANT},
        )
        assert r.status_code == 404


# ── 13/14 — RBAC ─────────────────────────────────────────────────────────────

class TestRBAC:
    def test_technician_cannot_approve_baseline(self):
        db = SessionLocal()
        try:
            baseline_entry = _make_baseline_entry(db)
            lcid_entry = _make_lcid_entry(db)
            link = bil.link_lcid_image_to_baseline(
                db, tenant_id=TENANT, baseline_library_entry_id=baseline_entry.id, lcid_image_id=lcid_entry.id,
                anatomy_zone="tip", inspection_view="lateral", image_type=IMAGE_TYPE_MANUFACTURER_BASELINE,
                source_type=SOURCE_ORGANIZATION_KNOWN_GOOD, created_by="ingest@test",
            )
            link = bil.submit_for_review(db, link=link, actor="ingest@test")
            with pytest.raises(bil.PermissionDeniedError):
                bil.review_baseline_image(
                    db, link=link, reviewer="tech@test", reviewer_role="operator", decision="approve",
                    rationale="Looks fine to me.",
                )
        finally:
            db.close()

    def test_ai_researcher_cannot_declare_clinical_approval(self):
        db = SessionLocal()
        try:
            baseline_entry = _make_baseline_entry(db)
            lcid_entry = _make_lcid_entry(db)
            link = _link_and_approve(db, baseline_entry=baseline_entry, lcid_entry=lcid_entry)
            with pytest.raises(bil.PermissionDeniedError):
                bil.activate_baseline_image(db, link=link, actor="researcher@test", actor_role="ai_researcher")

            link2 = bil.link_lcid_image_to_baseline(
                db, tenant_id=TENANT, baseline_library_entry_id=baseline_entry.id,
                lcid_image_id=_make_lcid_entry(db).id, anatomy_zone="jaw", inspection_view="lateral",
                image_type=IMAGE_TYPE_MANUFACTURER_BASELINE, source_type=SOURCE_ORGANIZATION_KNOWN_GOOD,
                created_by="ingest@test",
            )
            link2 = bil.submit_for_review(db, link=link2, actor="ingest@test")
            with pytest.raises(bil.PermissionDeniedError):
                bil.review_baseline_image(
                    db, link=link2, reviewer="researcher@test", reviewer_role="ai_researcher",
                    decision="approve", rationale="Approving as researcher.",
                )
        finally:
            db.close()

    def test_operator_cannot_review_over_http(self):
        db = SessionLocal()
        try:
            baseline_entry = _make_baseline_entry(db)
            lcid_entry = _make_lcid_entry(db)
            link = bil.link_lcid_image_to_baseline(
                db, tenant_id=TENANT, baseline_library_entry_id=baseline_entry.id, lcid_image_id=lcid_entry.id,
                anatomy_zone="tip", inspection_view="lateral", image_type=IMAGE_TYPE_MANUFACTURER_BASELINE,
                source_type=SOURCE_ORGANIZATION_KNOWN_GOOD, created_by="ingest@test",
            )
            bil.submit_for_review(db, link=link, actor="ingest@test")
            link_id = link.id
        finally:
            db.close()
        r = client.post(
            f"/api/baseline-library/images/{link_id}/review", headers=AUTH_OPERATOR,
            json={"decision": "approve", "rationale": "fine"},
        )
        assert r.status_code == 403


# ── 15 — supersession keeps history visible ─────────────────────────────────

class TestSupersession:
    def test_superseded_baseline_remains_historically_visible(self):
        db = SessionLocal()
        try:
            baseline_entry = _make_baseline_entry(db, instrument_category="supersede-test")
            old_entry = _make_lcid_entry(db, instrument_family="supersede-test")
            old_link = _link_and_approve(db, baseline_entry=baseline_entry, lcid_entry=old_entry)
            bil.activate_baseline_image(db, link=old_link, actor="admin@test", actor_role="admin")
            db.refresh(old_link)

            new_entry = _make_lcid_entry(db, instrument_family="supersede-test")
            new_link = _link_and_approve(db, baseline_entry=baseline_entry, lcid_entry=new_entry, source_type=SOURCE_ORGANIZATION_KNOWN_GOOD)

            old_link, new_link = bil.supersede_baseline_image(
                db, old_link=old_link, new_link=new_link, actor="admin@test", actor_role="admin",
            )
            assert old_link.lifecycle_status == STATE_SUPERSEDED
            assert new_link.lifecycle_status == STATE_ACTIVE
            assert new_link.supersedes_link_id == old_link.id

            # Old link is still directly queryable — never deleted.
            still_there = db.query(BaselineImageLink).filter(BaselineImageLink.id == old_link.id).first()
            assert still_there is not None
            assert still_there.lifecycle_status == STATE_SUPERSEDED
        finally:
            db.close()


# ── 16 — legacy metadata-only baselines ─────────────────────────────────────

class TestLegacyReport:
    def test_legacy_metadata_only_baseline_marked_image_evidence_missing(self):
        db = SessionLocal()
        try:
            legacy_entry = _make_baseline_entry(db, instrument_category="legacy-no-image-test")
            report = bil.legacy_baseline_report(db, tenant_id=TENANT)
            assert legacy_entry.id in report["missing_image_evidence"]
            assert legacy_entry.id not in report["with_active_image"]
            assert report["missing_image_evidence_marker"] == "IMAGE_EVIDENCE_MISSING"
        finally:
            db.close()


# ── 17 — training eligibility stays separate from baseline approval ────────

class TestTrainingEligibilitySeparation:
    def test_training_eligibility_unaffected_by_baseline_activation(self):
        db = SessionLocal()
        try:
            assert not hasattr(BaselineImageLink, "training_eligibility")
            baseline_entry = _make_baseline_entry(db)
            lcid_entry = _make_lcid_entry(db)
            assert lcid_entry.training_eligibility is False
            link = _link_and_approve(db, baseline_entry=baseline_entry, lcid_entry=lcid_entry)
            bil.activate_baseline_image(db, link=link, actor="admin@test", actor_role="admin")
            db.refresh(lcid_entry)
            # Activating this image as a baseline must never itself flip
            # training eligibility — that remains governed exclusively by
            # LCID/Ground Truth rules (dataset_eligibility_service).
            assert lcid_entry.training_eligibility is False
        finally:
            db.close()


# ── 18 — audit events persisted ─────────────────────────────────────────────

class TestAuditTrail:
    def test_audit_events_are_persisted(self):
        db = SessionLocal()
        try:
            baseline_entry = _make_baseline_entry(db)
            lcid_entry = _make_lcid_entry(db)
            link = _link_and_approve(db, baseline_entry=baseline_entry, lcid_entry=lcid_entry)
            bil.activate_baseline_image(db, link=link, actor="admin@test", actor_role="admin")

            rows = (
                db.query(AuditLog)
                .filter(AuditLog.resource_type == "baseline_image_link", AuditLog.resource_id == str(link.id))
                .all()
            )
            action_types = {r.action_type for r in rows}
            assert "baseline_image_proposed" in action_types
            assert "baseline_image_submitted_for_review" in action_types
            assert "baseline_image_approved" in action_types
            assert "baseline_image_activated" in action_types
        finally:
            db.close()

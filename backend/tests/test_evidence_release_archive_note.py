from pathlib import Path


def test_evidence_release_archive_note_exists_and_confirms_archive():
    path = Path("../docs/public/evidence-release-archive-note.md")

    assert path.exists()

    text = path.read_text()

    assert "LumenAI Compliance Evidence Release Archive Note" in text
    assert "Status: Archived for public portfolio and enterprise customer review." in text
    assert "LumenAI Compliance Evidence v1.0" in text
    assert "compliance-evidence-v1.0" in text
    assert "Archive: Complete." in text


def test_evidence_release_archive_note_lists_archived_artifacts():
    path = Path("../docs/public/evidence-release-archive-note.md")
    text = path.read_text()

    assert "docs/public/compliance-evidence.md" in text
    assert "docs/public/lumenai-compliance-evidence-badge.md" in text
    assert "docs/public/final-launch-summary.md" in text
    assert "docs/public/compliance-evidence-release-lock.md" in text
    assert "docs/public/evidence-index.md" in text
    assert "docs/public/evidence-release-tag.md" in text
    assert "docs/public/final-repository-closure-summary.md" in text
    assert "docs/public/evidence-release-archive-note.md" in text
    assert "scripts/demo_compliance_evidence_bundle.sh" in text


def test_evidence_release_archive_note_lists_services_endpoints_and_controls():
    path = Path("../docs/public/evidence-release-archive-note.md")
    text = path.read_text()

    assert "backend/app/services/audit_export_service.py" in text
    assert "backend/app/services/audit_export_verification_service.py" in text
    assert "backend/app/services/compliance_evidence_bundle_service.py" in text
    assert "backend/app/services/compliance_evidence_bundle_verification_service.py" in text
    assert "backend/app/services/compliance_evidence_summary_service.py" in text
    assert "frontend/src/components/VendorBaselineSubscriptionPortal.tsx" in text

    assert "/api/enterprise/audit/events/export.csv" in text
    assert "/api/enterprise/audit/events/export/verify" in text
    assert "/api/enterprise/audit/events/export/manifest/verify" in text
    assert "/api/enterprise/audit/evidence-bundle" in text
    assert "/api/enterprise/audit/evidence-bundle/download.json" in text
    assert "/api/enterprise/audit/evidence-bundle/verify" in text
    assert "/api/enterprise/audit/evidence-bundle/verification-summary" in text

    assert "centralized_audit_logging" in text
    assert "audit_event_integrity_hash" in text
    assert "audit_chain_verification" in text
    assert "request_correlation_id" in text
    assert "audit_export_manifest" in text


def test_readme_links_to_evidence_release_archive_note():
    path = Path("../README.md")

    assert path.exists()

    text = path.read_text()

    assert "docs/public/evidence-release-archive-note.md" in text

from pathlib import Path


def test_public_evidence_index_exists_and_links_public_artifacts():
    path = Path("../docs/public/evidence-index.md")

    assert path.exists()

    text = path.read_text()

    assert "LumenAI Evidence Index" in text
    assert "docs/public/compliance-evidence.md" in text
    assert "docs/public/lumenai-compliance-evidence-badge.md" in text
    assert "docs/public/final-launch-summary.md" in text
    assert "docs/public/compliance-evidence-release-lock.md" in text
    assert "docs/compliance/evidence-bundle-demo.md" in text
    assert "scripts/demo_compliance_evidence_bundle.sh" in text


def test_public_evidence_index_lists_backend_services_and_endpoints():
    path = Path("../docs/public/evidence-index.md")
    text = path.read_text()

    assert "backend/app/services/audit_export_service.py" in text
    assert "backend/app/services/audit_export_verification_service.py" in text
    assert "backend/app/services/compliance_evidence_bundle_service.py" in text
    assert "backend/app/services/compliance_evidence_bundle_verification_service.py" in text
    assert "backend/app/services/compliance_evidence_summary_service.py" in text

    assert "/api/enterprise/audit/events/export.csv" in text
    assert "/api/enterprise/audit/events/export/verify" in text
    assert "/api/enterprise/audit/events/export/manifest/verify" in text
    assert "/api/enterprise/audit/evidence-bundle" in text
    assert "/api/enterprise/audit/evidence-bundle/download.json" in text
    assert "/api/enterprise/audit/evidence-bundle/verify" in text
    assert "/api/enterprise/audit/evidence-bundle/verification-summary" in text


def test_public_evidence_index_lists_frontend_and_tests():
    path = Path("../docs/public/evidence-index.md")
    text = path.read_text()

    assert "frontend/src/components/VendorBaselineSubscriptionPortal.tsx" in text
    assert "Generate evidence bundle" in text
    assert "Verify pasted bundle hash" in text

    assert "backend/tests/test_audit_csv_export.py" in text
    assert "backend/tests/test_audit_export_hash.py" in text
    assert "backend/tests/test_compliance_evidence_bundle.py" in text
    assert "backend/tests/test_compliance_evidence_summary.py" in text
    assert "backend/tests/test_compliance_evidence_release_lock.py" in text


def test_readme_links_to_public_evidence_index():
    path = Path("../README.md")

    assert path.exists()

    text = path.read_text()

    assert "docs/public/evidence-index.md" in text

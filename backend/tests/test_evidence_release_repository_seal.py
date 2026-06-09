from pathlib import Path


def test_evidence_release_repository_seal_exists_and_confirms_status():
    path = Path("../docs/public/evidence-release-repository-seal.md")

    assert path.exists()

    text = path.read_text()

    assert "LumenAI Evidence Release Repository Seal" in text
    assert "Status: Sealed." in text
    assert "LumenAI Compliance Evidence v1.0" in text
    assert "compliance-evidence-v1.0" in text
    assert "Repository Seal: Complete." in text


def test_evidence_release_repository_seal_lists_sealed_scope():
    path = Path("../docs/public/evidence-release-repository-seal.md")
    text = path.read_text()

    assert "Backend compliance evidence services" in text
    assert "Enterprise evidence API endpoints" in text
    assert "Audit CSV export hashing" in text
    assert "Audit export manifest generation" in text
    assert "Evidence bundle generation" in text
    assert "Evidence bundle verification" in text
    assert "Public verification summary" in text
    assert "Downloadable evidence bundle JSON artifact" in text
    assert "Frontend bundle verification panel" in text
    assert "Repository seal" in text


def test_evidence_release_repository_seal_lists_docs_services_and_endpoints():
    path = Path("../docs/public/evidence-release-repository-seal.md")
    text = path.read_text()

    assert "docs/public/compliance-evidence.md" in text
    assert "docs/public/evidence-release-completion-summary.md" in text
    assert "docs/public/evidence-release-repository-seal.md" in text
    assert "scripts/demo_compliance_evidence_bundle.sh" in text

    assert "backend/app/services/audit_export_service.py" in text
    assert "backend/app/services/audit_export_verification_service.py" in text
    assert "backend/app/services/compliance_evidence_bundle_service.py" in text
    assert "backend/app/services/compliance_evidence_bundle_verification_service.py" in text
    assert "backend/app/services/compliance_evidence_summary_service.py" in text
    assert "frontend/src/components/VendorBaselineSubscriptionPortal.tsx" in text

    assert "/api/enterprise/audit/events/export/verify" in text
    assert "/api/enterprise/audit/events/export/manifest/verify" in text
    assert "/api/enterprise/audit/evidence-bundle/verify" in text
    assert "/api/enterprise/audit/evidence-bundle/verification-summary" in text
    assert "/api/enterprise/audit/evidence-bundle/download.json" in text


def test_evidence_release_repository_seal_lists_controls_and_validation():
    path = Path("../docs/public/evidence-release-repository-seal.md")
    text = path.read_text()

    assert "centralized_audit_logging" in text
    assert "audit_event_integrity_hash" in text
    assert "audit_chain_verification" in text
    assert "request_correlation_id" in text
    assert "filtered_audit_export" in text
    assert "audit_export_manifest" in text

    assert "ruff check app tests" in text
    assert "npm run build" in text
    assert "tests/test_compliance_evidence_bundle.py" in text


def test_readme_links_to_evidence_release_repository_seal():
    path = Path("../README.md")

    assert path.exists()

    text = path.read_text()

    assert "docs/public/evidence-release-repository-seal.md" in text

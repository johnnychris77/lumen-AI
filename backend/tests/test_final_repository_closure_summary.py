from pathlib import Path


def test_final_repository_closure_summary_exists_and_confirms_closure():
    path = Path("../docs/public/final-repository-closure-summary.md")

    assert path.exists()

    text = path.read_text()

    assert "LumenAI Final Repository Closure Summary" in text
    assert "Status: Final repository closure complete" in text
    assert "LumenAI Compliance Evidence v1.0" in text
    assert "compliance-evidence-v1.0" in text
    assert "Closure: Complete." in text


def test_final_repository_closure_summary_lists_core_artifacts():
    path = Path("../docs/public/final-repository-closure-summary.md")
    text = path.read_text()

    assert "docs/public/compliance-evidence.md" in text
    assert "docs/public/lumenai-compliance-evidence-badge.md" in text
    assert "docs/public/final-launch-summary.md" in text
    assert "docs/public/compliance-evidence-release-lock.md" in text
    assert "docs/public/evidence-index.md" in text
    assert "docs/public/evidence-release-tag.md" in text
    assert "docs/public/final-repository-closure-summary.md" in text
    assert "scripts/demo_compliance_evidence_bundle.sh" in text


def test_final_repository_closure_summary_lists_services_and_endpoints():
    path = Path("../docs/public/final-repository-closure-summary.md")
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


def test_final_repository_closure_summary_lists_controls_and_validation():
    path = Path("../docs/public/final-repository-closure-summary.md")
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
    assert "tests/test_evidence_release_tag.py" in text


def test_readme_links_to_final_repository_closure_summary():
    path = Path("../README.md")

    assert path.exists()

    text = path.read_text()

    assert "docs/public/final-repository-closure-summary.md" in text

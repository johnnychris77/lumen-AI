from pathlib import Path


def test_evidence_release_completion_summary_exists_and_confirms_completion():
    path = Path("../docs/public/evidence-release-completion-summary.md")

    assert path.exists()

    text = path.read_text()

    assert "LumenAI Evidence Release Completion Summary" in text
    assert "Status: Complete." in text
    assert "LumenAI Compliance Evidence v1.0" in text
    assert "compliance-evidence-v1.0" in text
    assert "Completion Summary: Complete." in text


def test_evidence_release_completion_summary_lists_completion_scope():
    path = Path("../docs/public/evidence-release-completion-summary.md")
    text = path.read_text()

    assert "Backend compliance evidence services" in text
    assert "Protected enterprise evidence endpoints" in text
    assert "Audit CSV export hashing" in text
    assert "Audit export manifest generation" in text
    assert "Evidence bundle generation" in text
    assert "Evidence bundle verification" in text
    assert "Public verification summary" in text
    assert "Downloadable evidence bundle JSON artifact" in text
    assert "Frontend evidence verification panel" in text
    assert "Completion badge" in text


def test_evidence_release_completion_summary_lists_docs_and_endpoints():
    path = Path("../docs/public/evidence-release-completion-summary.md")
    text = path.read_text()

    assert "docs/public/compliance-evidence.md" in text
    assert "docs/public/evidence-release-completion-badge.md" in text
    assert "docs/public/evidence-release-completion-summary.md" in text
    assert "scripts/demo_compliance_evidence_bundle.sh" in text

    assert "/api/enterprise/audit/events/export/verify" in text
    assert "/api/enterprise/audit/events/export/manifest/verify" in text
    assert "/api/enterprise/audit/evidence-bundle/verify" in text
    assert "/api/enterprise/audit/evidence-bundle/verification-summary" in text
    assert "/api/enterprise/audit/evidence-bundle/download.json" in text


def test_evidence_release_completion_summary_lists_controls_and_validation():
    path = Path("../docs/public/evidence-release-completion-summary.md")
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


def test_readme_links_to_evidence_release_completion_summary():
    path = Path("../README.md")

    assert path.exists()

    text = path.read_text()

    assert "docs/public/evidence-release-completion-summary.md" in text

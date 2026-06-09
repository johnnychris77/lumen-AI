from pathlib import Path


def test_evidence_release_executive_summary_exists_and_confirms_status():
    path = Path("../docs/public/evidence-release-executive-summary.md")

    assert path.exists()

    text = path.read_text()

    assert "LumenAI Evidence Release Executive Summary" in text
    assert "Status: Complete and sealed." in text
    assert "LumenAI Compliance Evidence v1.0" in text
    assert "compliance-evidence-v1.0" in text
    assert "Executive Summary: Complete." in text


def test_evidence_release_executive_summary_lists_business_value():
    path = Path("../docs/public/evidence-release-executive-summary.md")
    text = path.read_text()

    assert "What evidence was generated?" in text
    assert "Who generated it?" in text
    assert "When was it generated?" in text
    assert "Was the export hashed?" in text
    assert "Can the evidence bundle be verified?" in text
    assert "customer-facing verification summary" in text


def test_evidence_release_executive_summary_lists_delivered_capabilities():
    path = Path("../docs/public/evidence-release-executive-summary.md")
    text = path.read_text()

    assert "Centralized enterprise audit logging" in text
    assert "Filtered audit CSV export" in text
    assert "SHA-256 audit export hash" in text
    assert "SHA-256 manifest hash" in text
    assert "SHA-256 evidence bundle hash" in text
    assert "Downloadable JSON evidence artifact" in text
    assert "Evidence bundle generation card" in text
    assert "Pasted bundle hash verification panel" in text


def test_evidence_release_executive_summary_lists_positioning_controls_and_validation():
    path = Path("../docs/public/evidence-release-executive-summary.md")
    text = path.read_text()

    assert "Enterprise Review Positioning" in text
    assert "Auditability" in text
    assert "Traceability" in text
    assert "Vendor governance" in text
    assert "Executive compliance reporting" in text

    assert "centralized_audit_logging" in text
    assert "audit_event_integrity_hash" in text
    assert "audit_chain_verification" in text
    assert "request_correlation_id" in text
    assert "audit_export_manifest" in text

    assert "ruff check app tests" in text
    assert "npm run build" in text
    assert "tests/test_compliance_evidence_bundle.py" in text


def test_readme_links_to_evidence_release_executive_summary():
    path = Path("../README.md")

    assert path.exists()

    text = path.read_text()

    assert "docs/public/evidence-release-executive-summary.md" in text

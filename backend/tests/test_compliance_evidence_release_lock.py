from pathlib import Path


def test_compliance_evidence_release_lock_exists_and_confirms_status():
    path = Path("../docs/public/compliance-evidence-release-lock.md")

    assert path.exists()

    text = path.read_text()

    assert "LumenAI Compliance Evidence Release Lock" in text
    assert "Status: Locked for public portfolio and enterprise customer review." in text
    assert "Release Lock: Complete." in text


def test_release_lock_lists_core_evidence_capabilities():
    path = Path("../docs/public/compliance-evidence-release-lock.md")
    text = path.read_text()

    assert "Centralized enterprise audit logging" in text
    assert "Audit chain verification" in text
    assert "Filtered audit event CSV export" in text
    assert "CSV export SHA-256 hash" in text
    assert "Audit export manifest generation" in text
    assert "Evidence bundle generation" in text
    assert "Evidence bundle SHA-256 hash" in text
    assert "Evidence bundle public verification summary" in text
    assert "Downloadable evidence bundle JSON artifact" in text
    assert "Compliance evidence bundle generation card" in text


def test_release_lock_lists_verification_endpoints_and_controls():
    path = Path("../docs/public/compliance-evidence-release-lock.md")
    text = path.read_text()

    assert "/api/enterprise/audit/events/export/verify" in text
    assert "/api/enterprise/audit/events/export/manifest/verify" in text
    assert "/api/enterprise/audit/evidence-bundle/verify" in text
    assert "/api/enterprise/audit/evidence-bundle/verification-summary" in text
    assert "/api/enterprise/audit/evidence-bundle/download.json" in text

    assert "centralized_audit_logging" in text
    assert "audit_event_integrity_hash" in text
    assert "audit_chain_verification" in text
    assert "request_correlation_id" in text
    assert "audit_export_manifest" in text


def test_readme_links_to_compliance_evidence_release_lock():
    path = Path("../README.md")

    assert path.exists()

    text = path.read_text()

    assert "docs/public/compliance-evidence-release-lock.md" in text

from pathlib import Path


def test_evidence_release_customer_review_packet_exists_and_confirms_status():
    path = Path("../docs/public/evidence-release-customer-review-packet.md")

    assert path.exists()

    text = path.read_text()

    assert "LumenAI Evidence Release Customer Review Packet" in text
    assert "Status: Ready for customer review." in text
    assert "LumenAI Compliance Evidence v1.0" in text
    assert "compliance-evidence-v1.0" in text
    assert "Customer Review Packet: Complete." in text


def test_evidence_release_customer_review_packet_lists_customer_value():
    path = Path("../docs/public/evidence-release-customer-review-packet.md")
    text = path.read_text()

    assert "What evidence was generated?" in text
    assert "Who generated the evidence?" in text
    assert "When was the evidence generated?" in text
    assert "Was the audit export hashed?" in text
    assert "Was the evidence bundle hashed?" in text
    assert "Can the bundle be independently verified?" in text


def test_evidence_release_customer_review_packet_lists_capabilities_and_endpoints():
    path = Path("../docs/public/evidence-release-customer-review-packet.md")
    text = path.read_text()

    assert "Centralized enterprise audit logging" in text
    assert "Filtered audit CSV export" in text
    assert "SHA-256 audit export hash" in text
    assert "SHA-256 audit manifest hash" in text
    assert "SHA-256 evidence bundle hash" in text
    assert "Downloadable JSON evidence artifact" in text
    assert "Bundle hash verification panel" in text

    assert "/api/enterprise/audit/events/export/verify" in text
    assert "/api/enterprise/audit/events/export/manifest/verify" in text
    assert "/api/enterprise/audit/evidence-bundle/verify" in text
    assert "/api/enterprise/audit/evidence-bundle/verification-summary" in text
    assert "/api/enterprise/audit/evidence-bundle/download.json" in text


def test_evidence_release_customer_review_packet_lists_artifacts_controls_and_demo():
    path = Path("../docs/public/evidence-release-customer-review-packet.md")
    text = path.read_text()

    assert "docs/public/evidence-release-executive-summary.md" in text
    assert "docs/public/evidence-release-customer-review-packet.md" in text
    assert "docs/compliance/evidence-bundle-demo.md" in text
    assert "scripts/demo_compliance_evidence_bundle.sh" in text

    assert "centralized_audit_logging" in text
    assert "audit_event_integrity_hash" in text
    assert "audit_chain_verification" in text
    assert "request_correlation_id" in text
    assert "audit_export_manifest" in text

    assert "Generate the compliance evidence bundle" in text
    assert "Download the bundle JSON artifact" in text
    assert "Load the public verification summary" in text


def test_readme_links_to_evidence_release_customer_review_packet():
    path = Path("../README.md")

    assert path.exists()

    text = path.read_text()

    assert "docs/public/evidence-release-customer-review-packet.md" in text

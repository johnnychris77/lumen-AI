from pathlib import Path


def test_compliance_evidence_bundle_demo_readme_exists():
    path = Path("../docs/compliance/evidence-bundle-demo.md")

    assert path.exists()

    text = path.read_text()

    assert "LumenAI Compliance Evidence Bundle Demo" in text
    assert "Generate Evidence Bundle" in text
    assert "Download Evidence Bundle JSON" in text
    assert "Verify Evidence Bundle" in text
    assert "Public Verification Summary" in text
    assert "centralized_audit_logging" in text


def test_compliance_evidence_bundle_demo_script_exists_and_documents_flow():
    path = Path("../scripts/demo_compliance_evidence_bundle.sh")

    assert path.exists()

    text = path.read_text()

    assert "api/enterprise/audit/evidence-bundle" in text
    assert "api/enterprise/audit/evidence-bundle/verify" in text
    assert "api/enterprise/audit/evidence-bundle/verification-summary" in text
    assert "api/enterprise/audit/evidence-bundle/download.json" in text
    assert "BUNDLE_HASH" in text

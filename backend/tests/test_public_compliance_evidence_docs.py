from pathlib import Path


def test_public_compliance_evidence_page_exists_and_describes_workflow():
    path = Path("../docs/public/compliance-evidence.md")

    assert path.exists()

    text = path.read_text()

    assert "LumenAI Compliance Evidence" in text
    assert "tamper-evident compliance evidence workflow" in text
    assert "SHA-256 audit export hash" in text
    assert "Audit Export Verification" in text
    assert "Audit Manifest Verification" in text
    assert "Evidence Bundle Verification" in text
    assert "Public Verification Summary" in text
    assert "centralized_audit_logging" in text
    assert "audit_chain_verification" in text
    assert "scripts/demo_compliance_evidence_bundle.sh" in text


def test_readme_links_to_public_compliance_evidence_page_when_present():
    readme = Path("../README.md")

    if not readme.exists():
        return

    text = readme.read_text()

    assert "docs/public/compliance-evidence.md" in text

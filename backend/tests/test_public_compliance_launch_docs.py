from pathlib import Path


def test_public_compliance_evidence_badge_exists():
    path = Path("../docs/public/lumenai-compliance-evidence-badge.md")

    assert path.exists()

    text = path.read_text()

    assert "LumenAI Compliance Evidence Badge" in text
    assert "LumenAI Compliance Evidence Ready" in text
    assert "Centralized enterprise audit logging" in text
    assert "SHA-256 audit export hash" in text
    assert "Compliance evidence bundle" in text
    assert "Frontend bundle verification panel" in text
    assert "Implemented" in text


def test_final_launch_summary_exists_and_lists_enterprise_capabilities():
    path = Path("../docs/public/final-launch-summary.md")

    assert path.exists()

    text = path.read_text()

    assert "LumenAI Enterprise Compliance Evidence Final Launch Summary" in text
    assert "Centralized Enterprise Audit Logging" in text
    assert "Audit Export Hash" in text
    assert "Audit Export Manifest" in text
    assert "Compliance Evidence Bundle" in text
    assert "Bundle Hash" in text
    assert "Verification Endpoints" in text
    assert "Frontend Evidence UI" in text
    assert "Enterprise compliance evidence workflow implemented" in text


def test_readme_includes_compliance_evidence_ready_links():
    path = Path("../README.md")

    assert path.exists()

    text = path.read_text()

    assert "Enterprise Compliance Evidence Ready" in text
    assert "docs/public/compliance-evidence.md" in text
    assert "docs/public/lumenai-compliance-evidence-badge.md" in text
    assert "docs/public/final-launch-summary.md" in text
    assert "docs/compliance/evidence-bundle-demo.md" in text

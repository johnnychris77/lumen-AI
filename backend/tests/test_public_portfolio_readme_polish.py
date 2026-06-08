from pathlib import Path


def test_readme_contains_public_portfolio_summary():
    path = Path("../README.md")

    assert path.exists()

    text = path.read_text()

    assert "Public Portfolio Summary" in text
    assert "LumenAI is a healthcare operations intelligence platform" in text
    assert "Compliance Evidence v1.0" in text
    assert "compliance-evidence-v1.0" in text


def test_readme_lists_compliance_evidence_capabilities():
    path = Path("../README.md")
    text = path.read_text()

    assert "Centralized enterprise audit logging" in text
    assert "Filtered audit CSV exports" in text
    assert "SHA-256 audit export hashes" in text
    assert "Audit export manifests" in text
    assert "Compliance evidence bundles" in text
    assert "Bundle verification endpoints" in text
    assert "Public verification summaries" in text
    assert "Frontend evidence bundle verification panel" in text


def test_readme_lists_public_compliance_evidence_links():
    path = Path("../README.md")
    text = path.read_text()

    assert "docs/public/evidence-index.md" in text
    assert "docs/public/compliance-evidence.md" in text
    assert "docs/public/lumenai-compliance-evidence-badge.md" in text
    assert "docs/public/final-launch-summary.md" in text
    assert "docs/public/compliance-evidence-release-lock.md" in text
    assert "docs/public/evidence-release-tag.md" in text
    assert "docs/public/final-repository-closure-summary.md" in text
    assert "docs/compliance/evidence-bundle-demo.md" in text


def test_readme_includes_demo_and_validation_commands():
    path = Path("../README.md")
    text = path.read_text()

    assert "./scripts/demo_compliance_evidence_bundle.sh" in text
    assert "ruff check app tests" in text
    assert "npm run build" in text
    assert "tests/test_public_evidence_index.py" in text
    assert "tests/test_final_repository_closure_summary.py" in text

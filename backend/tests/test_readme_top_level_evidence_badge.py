from pathlib import Path


def test_readme_top_level_evidence_badge_exists():
    path = Path("../README.md")

    assert path.exists()

    text = path.read_text()

    assert "Compliance Evidence v1.0 — Public Portfolio Ready" in text
    assert "Complete · Sealed · Tagged · Indexed · Archived · Customer-Ready" in text
    assert "compliance-evidence-v1.0" in text


def test_readme_top_level_badge_describes_evidence_workflow():
    path = Path("../README.md")
    text = path.read_text()

    assert "tamper-evident enterprise compliance evidence workflow" in text
    assert "healthcare operations" in text
    assert "sterile processing governance" in text
    assert "vendor accountability" in text
    assert "audit readiness" in text
    assert "customer-facing trust review" in text


def test_readme_top_level_badge_links_fast_review_documents():
    path = Path("../README.md")
    text = path.read_text()

    assert "docs/public/evidence-release-portfolio-landing-summary.md" in text
    assert "docs/public/evidence-index.md" in text
    assert "docs/public/evidence-release-customer-review-packet.md" in text
    assert "docs/public/evidence-release-executive-summary.md" in text
    assert "docs/public/evidence-release-sales-one-pager.md" in text
    assert "docs/public/evidence-release-investor-brief.md" in text
    assert "docs/public/evidence-release-demo-walkthrough-guide.md" in text
    assert "docs/public/evidence-release-repository-seal.md" in text


def test_readme_top_level_badge_includes_demo_command():
    path = Path("../README.md")
    text = path.read_text()

    assert 'BASE_URL="http://127.0.0.1:8000" ./scripts/demo_compliance_evidence_bundle.sh' in text

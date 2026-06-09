from pathlib import Path


def test_evidence_release_portfolio_landing_summary_exists_and_confirms_status():
    path = Path("../docs/public/evidence-release-portfolio-landing-summary.md")

    assert path.exists()

    text = path.read_text()

    assert "LumenAI Evidence Release Portfolio Landing Summary" in text
    assert "Status: Ready for public portfolio review." in text
    assert "LumenAI Compliance Evidence v1.0" in text
    assert "compliance-evidence-v1.0" in text
    assert "Portfolio Landing Summary: Complete." in text


def test_evidence_release_portfolio_landing_summary_lists_one_sentence_summary_and_proof():
    path = Path("../docs/public/evidence-release-portfolio-landing-summary.md")
    text = path.read_text()

    assert "LumenAI converts healthcare operations audit activity into tamper-evident compliance evidence" in text
    assert "Record enterprise audit events" in text
    assert "Export filtered audit evidence" in text
    assert "Hash exported evidence with SHA-256" in text
    assert "Generate compliance evidence bundles" in text
    assert "Present safe public verification summaries" in text


def test_evidence_release_portfolio_landing_summary_lists_review_paths():
    path = Path("../docs/public/evidence-release-portfolio-landing-summary.md")
    text = path.read_text()

    assert "Executive Review" in text
    assert "Technical Review" in text
    assert "Release Review" in text
    assert "Demo Review" in text

    assert "docs/public/evidence-release-executive-summary.md" in text
    assert "docs/public/evidence-release-customer-review-packet.md" in text
    assert "docs/public/evidence-release-sales-one-pager.md" in text
    assert "docs/public/evidence-release-market-positioning-brief.md" in text
    assert "docs/public/evidence-index.md" in text
    assert "docs/public/evidence-release-demo-walkthrough-guide.md" in text


def test_evidence_release_portfolio_landing_summary_lists_capabilities_and_controls():
    path = Path("../docs/public/evidence-release-portfolio-landing-summary.md")
    text = path.read_text()

    assert "Centralized enterprise audit logging" in text
    assert "Filtered audit CSV export" in text
    assert "SHA-256 audit export hash" in text
    assert "Audit export manifest" in text
    assert "SHA-256 manifest hash" in text
    assert "Compliance evidence bundle" in text
    assert "SHA-256 bundle hash" in text
    assert "Public verification summary" in text
    assert "Downloadable JSON evidence artifact" in text

    assert "centralized_audit_logging" in text
    assert "audit_event_integrity_hash" in text
    assert "audit_chain_verification" in text
    assert "request_correlation_id" in text
    assert "audit_export_manifest" in text


def test_evidence_release_portfolio_landing_summary_lists_demo_and_positioning():
    path = Path("../docs/public/evidence-release-portfolio-landing-summary.md")
    text = path.read_text()

    assert 'BASE_URL="http://127.0.0.1:8000" ./scripts/demo_compliance_evidence_bundle.sh' in text
    assert "healthcare operations intelligence platform with an enterprise trust layer" in text
    assert "public portfolio presentation" in text
    assert "enterprise customer review" in text
    assert "investor discussion" in text


def test_readme_links_to_evidence_release_portfolio_landing_summary():
    path = Path("../README.md")

    assert path.exists()

    text = path.read_text()

    assert "docs/public/evidence-release-portfolio-landing-summary.md" in text

from pathlib import Path


def test_evidence_release_market_positioning_brief_exists_and_confirms_status():
    path = Path("../docs/public/evidence-release-market-positioning-brief.md")

    assert path.exists()

    text = path.read_text()

    assert "LumenAI Evidence Release Market Positioning Brief" in text
    assert "Status: Ready for market positioning" in text
    assert "LumenAI Compliance Evidence v1.0" in text
    assert "compliance-evidence-v1.0" in text
    assert "Market Positioning Brief: Complete." in text


def test_evidence_release_market_positioning_brief_lists_market_category_and_problem():
    path = Path("../docs/public/evidence-release-market-positioning-brief.md")
    text = path.read_text()

    assert "Healthcare operations intelligence" in text
    assert "Sterile processing quality governance" in text
    assert "Vendor accountability" in text
    assert "Enterprise compliance evidence" in text

    assert "disconnected systems" in text
    assert "manual spreadsheets" in text
    assert "Verifying exported files" in text
    assert "Building customer trust" in text


def test_evidence_release_market_positioning_brief_lists_buyers_and_use_cases():
    path = Path("../docs/public/evidence-release-market-positioning-brief.md")
    text = path.read_text()

    assert "Hospital executives" in text
    assert "Perioperative leaders" in text
    assert "Sterile processing directors" in text
    assert "Vendor governance stakeholders" in text
    assert "Enterprise healthcare buyers" in text

    assert "Sterile Processing Quality Oversight" in text
    assert "Vendor Governance" in text
    assert "Compliance Readiness" in text
    assert "Executive Reporting" in text
    assert "Customer Due Diligence" in text


def test_evidence_release_market_positioning_brief_lists_proof_points_and_controls():
    path = Path("../docs/public/evidence-release-market-positioning-brief.md")
    text = path.read_text()

    assert "Filtered audit CSV export" in text
    assert "SHA-256 audit export hash" in text
    assert "Audit export manifest" in text
    assert "SHA-256 manifest hash" in text
    assert "Compliance evidence bundle" in text
    assert "SHA-256 bundle hash" in text
    assert "Frontend bundle verification panel" in text

    assert "centralized_audit_logging" in text
    assert "audit_event_integrity_hash" in text
    assert "audit_chain_verification" in text
    assert "request_correlation_id" in text
    assert "audit_export_manifest" in text


def test_evidence_release_market_positioning_brief_lists_demo_and_competitive_narrative():
    path = Path("../docs/public/evidence-release-market-positioning-brief.md")
    text = path.read_text()

    assert "Many healthcare tools focus on dashboards" in text
    assert "tamper-evident proof generation" in text
    assert "Generate compliance evidence from enterprise audit records." in text
    assert "Display audit export hash, manifest hash, and bundle hash." in text
    assert "Show the customer-facing verification summary." in text


def test_readme_links_to_evidence_release_market_positioning_brief():
    path = Path("../README.md")

    assert path.exists()

    text = path.read_text()

    assert "docs/public/evidence-release-market-positioning-brief.md" in text

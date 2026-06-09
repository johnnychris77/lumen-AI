from pathlib import Path


def test_evidence_release_investor_brief_exists_and_confirms_status():
    path = Path("../docs/public/evidence-release-investor-brief.md")

    assert path.exists()

    text = path.read_text()

    assert "LumenAI Evidence Release Investor Brief" in text
    assert "Status: Ready for investor and strategic partner review." in text
    assert "LumenAI Compliance Evidence v1.0" in text
    assert "compliance-evidence-v1.0" in text
    assert "Investor Brief: Complete." in text


def test_evidence_release_investor_brief_lists_market_problem_and_solution():
    path = Path("../docs/public/evidence-release-investor-brief.md")
    text = path.read_text()

    assert "Fragmented audit trails" in text
    assert "Manual evidence collection" in text
    assert "Limited export verification" in text
    assert "Weak vendor accountability documentation" in text
    assert "Enterprise audit events are recorded." in text
    assert "Exports receive SHA-256 hashes." in text
    assert "Public verification summaries provide safe customer-facing proof." in text


def test_evidence_release_investor_brief_lists_capabilities_and_differentiation():
    path = Path("../docs/public/evidence-release-investor-brief.md")
    text = path.read_text()

    assert "Operational intelligence" in text
    assert "Audit traceability" in text
    assert "Tamper-evident evidence packaging" in text
    assert "Hash-backed export verification" in text
    assert "Compliance evidence bundle generation" in text
    assert "Evidence bundle JSON download endpoint" in text
    assert "Verify pasted bundle hash" in text


def test_evidence_release_investor_brief_lists_buyers_controls_and_demo():
    path = Path("../docs/public/evidence-release-investor-brief.md")
    text = path.read_text()

    assert "Hospital executives" in text
    assert "Sterile processing directors" in text
    assert "Quality and safety leaders" in text
    assert "Enterprise healthcare buyers" in text

    assert "centralized_audit_logging" in text
    assert "audit_event_integrity_hash" in text
    assert "audit_chain_verification" in text
    assert "request_correlation_id" in text
    assert "audit_export_manifest" in text

    assert "Generate compliance evidence bundle." in text
    assert "Show verified public summary." in text


def test_readme_links_to_evidence_release_investor_brief():
    path = Path("../README.md")

    assert path.exists()

    text = path.read_text()

    assert "docs/public/evidence-release-investor-brief.md" in text

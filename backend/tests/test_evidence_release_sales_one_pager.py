from pathlib import Path


def test_evidence_release_sales_one_pager_exists_and_confirms_status():
    path = Path("../docs/public/evidence-release-sales-one-pager.md")

    assert path.exists()

    text = path.read_text()

    assert "LumenAI Evidence Release Sales One-Pager" in text
    assert "Status: Ready for sales, demo, customer, investor, and strategic partner conversations." in text
    assert "LumenAI Compliance Evidence v1.0" in text
    assert "compliance-evidence-v1.0" in text
    assert "Sales One-Pager: Complete." in text


def test_evidence_release_sales_one_pager_lists_problem_and_message():
    path = Path("../docs/public/evidence-release-sales-one-pager.md")
    text = path.read_text()

    assert "Healthcare operations and sterile processing teams need a reliable way" in text
    assert "LumenAI is a healthcare operations intelligence platform with built-in compliance evidence generation." in text
    assert "Audit evidence is often scattered" in text
    assert "Vendor quality issues are difficult to prove consistently." in text
    assert "Exported evidence can be hard to verify after download." in text


def test_evidence_release_sales_one_pager_lists_evidence_capabilities():
    path = Path("../docs/public/evidence-release-sales-one-pager.md")
    text = path.read_text()

    assert "Tamper-Evident Audit Export" in text
    assert "Filtered audit CSV export" in text
    assert "SHA-256 audit export hash" in text
    assert "Audit Manifest" in text
    assert "SHA-256 manifest hash" in text
    assert "Compliance Evidence Bundle" in text
    assert "SHA-256 bundle hash" in text
    assert "Public verification summary" in text
    assert "Verify pasted bundle hash" in text


def test_evidence_release_sales_one_pager_lists_customers_demo_and_artifacts():
    path = Path("../docs/public/evidence-release-sales-one-pager.md")
    text = path.read_text()

    assert "Hospital executives" in text
    assert "Sterile processing directors" in text
    assert "Quality and safety leaders" in text
    assert "Enterprise healthcare buyers" in text

    assert "Generate an evidence bundle from enterprise audit data." in text
    assert "Display the audit export hash, manifest hash, and bundle hash." in text
    assert "Show the verified customer-facing summary." in text

    assert "docs/public/evidence-release-customer-review-packet.md" in text
    assert "docs/public/evidence-release-investor-brief.md" in text
    assert "scripts/demo_compliance_evidence_bundle.sh" in text


def test_readme_links_to_evidence_release_sales_one_pager():
    path = Path("../README.md")

    assert path.exists()

    text = path.read_text()

    assert "docs/public/evidence-release-sales-one-pager.md" in text

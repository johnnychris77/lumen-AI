from pathlib import Path


def test_evidence_index_contains_final_public_navigation():
    path = Path("../docs/public/evidence-index.md")

    assert path.exists()

    text = path.read_text()

    assert "Final Public Navigation" in text
    assert "Executive Review Path" in text
    assert "Technical Evidence Path" in text
    assert "Release Closure Path" in text
    assert "Demo and Proof Path" in text
    assert "Buyer-Facing Short Links" in text
    assert "Final Navigation Status" in text


def test_evidence_index_links_review_paths():
    path = Path("../docs/public/evidence-index.md")
    text = path.read_text()

    assert "evidence-release-executive-summary.md" in text
    assert "evidence-release-customer-review-packet.md" in text
    assert "evidence-release-sales-one-pager.md" in text
    assert "evidence-release-market-positioning-brief.md" in text
    assert "compliance-evidence.md" in text
    assert "evidence-release-demo-walkthrough-guide.md" in text
    assert "compliance-evidence-release-lock.md" in text


def test_evidence_index_links_release_closure_documents():
    path = Path("../docs/public/evidence-index.md")
    text = path.read_text()

    assert "final-launch-summary.md" in text
    assert "evidence-release-tag.md" in text
    assert "final-repository-closure-summary.md" in text
    assert "evidence-release-archive-note.md" in text
    assert "evidence-release-completion-badge.md" in text
    assert "evidence-release-completion-summary.md" in text
    assert "evidence-release-repository-seal.md" in text


def test_evidence_index_links_demo_and_proof_assets():
    path = Path("../docs/public/evidence-index.md")
    text = path.read_text()

    assert "../compliance/evidence-bundle-demo.md" in text
    assert "scripts/demo_compliance_evidence_bundle.sh" in text
    assert "frontend/src/components/VendorBaselineSubscriptionPortal.tsx" in text


def test_readme_contains_final_navigation_quick_links():
    path = Path("../README.md")

    assert path.exists()

    text = path.read_text()

    assert "docs/public/evidence-release-demo-walkthrough-guide.md" in text
    assert "docs/public/evidence-release-customer-review-packet.md" in text
    assert "docs/public/evidence-release-investor-brief.md" in text
    assert "docs/public/evidence-release-sales-one-pager.md" in text
    assert "docs/public/evidence-release-market-positioning-brief.md" in text

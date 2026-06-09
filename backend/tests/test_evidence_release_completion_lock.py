from pathlib import Path


def test_evidence_release_completion_lock_exists_and_confirms_status():
    path = Path("../docs/public/evidence-release-completion-lock.md")

    assert path.exists()

    text = path.read_text()

    assert "LumenAI Evidence Release Completion Lock" in text
    assert "Status: Locked and complete." in text
    assert "LumenAI Compliance Evidence v1.0" in text
    assert "compliance-evidence-v1.0" in text
    assert "Completion Lock: Complete." in text


def test_evidence_release_completion_lock_lists_locked_scope():
    path = Path("../docs/public/evidence-release-completion-lock.md")
    text = path.read_text()

    assert "Enterprise audit logging" in text
    assert "Filtered audit CSV export" in text
    assert "SHA-256 audit export hashing" in text
    assert "Audit export manifest generation" in text
    assert "Compliance evidence bundle generation" in text
    assert "Frontend evidence bundle generation card" in text
    assert "Frontend bundle hash verification panel" in text
    assert "Customer review packet" in text
    assert "Investor brief" in text
    assert "Sales one-pager" in text
    assert "Portfolio landing summary" in text
    assert "README top-level badge" in text
    assert "Repository seal" in text


def test_evidence_release_completion_lock_lists_public_review_and_demo_paths():
    path = Path("../docs/public/evidence-release-completion-lock.md")
    text = path.read_text()

    assert "Recommended public review path" in text
    assert "README.md" in text
    assert "docs/public/evidence-release-portfolio-landing-summary.md" in text
    assert "docs/public/evidence-index.md" in text
    assert "docs/public/evidence-release-customer-review-packet.md" in text
    assert "docs/public/evidence-release-completion-lock.md" in text

    assert "Recommended demo path" in text
    assert "scripts/demo_compliance_evidence_bundle.sh" in text
    assert "demo_summary.txt" in text
    assert "downloaded evidence bundle JSON" in text
    assert "public verification summary" in text


def test_evidence_release_completion_lock_lists_verification_controls_and_validation():
    path = Path("../docs/public/evidence-release-completion-lock.md")
    text = path.read_text()

    assert "Audit export hash" in text
    assert "Audit export manifest hash" in text
    assert "Compliance evidence bundle hash" in text
    assert "Customer-facing verification summary" in text

    assert "centralized_audit_logging" in text
    assert "audit_event_integrity_hash" in text
    assert "audit_chain_verification" in text
    assert "request_correlation_id" in text
    assert "audit_export_manifest" in text

    assert "ruff check app tests" in text
    assert "npm run build" in text
    assert "git tag --list | grep compliance-evidence-v1.0" in text
    assert "git ls-remote --tags origin | grep compliance-evidence-v1.0" in text


def test_readme_links_to_evidence_release_completion_lock():
    path = Path("../README.md")

    assert path.exists()

    text = path.read_text()

    assert "docs/public/evidence-release-completion-lock.md" in text

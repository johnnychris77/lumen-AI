from pathlib import Path


def test_evidence_release_completion_badge_exists_and_confirms_completion():
    path = Path("../docs/public/evidence-release-completion-badge.md")

    assert path.exists()

    text = path.read_text()

    assert "LumenAI Evidence Release Completion Badge" in text
    assert "LumenAI Compliance Evidence v1.0 — Complete" in text
    assert "Status: Complete, release-locked, tagged, indexed, archived" in text
    assert "compliance-evidence-v1.0" in text
    assert "Completion: Confirmed." in text


def test_evidence_release_completion_badge_lists_completed_capabilities():
    path = Path("../docs/public/evidence-release-completion-badge.md")
    text = path.read_text()

    assert "Centralized enterprise audit logging" in text
    assert "Audit event integrity metadata" in text
    assert "Filtered audit CSV export" in text
    assert "SHA-256 audit export hashing" in text
    assert "Audit export manifest generation" in text
    assert "Compliance evidence bundle generation" in text
    assert "Evidence bundle verification" in text
    assert "Public verification summary" in text
    assert "Downloadable evidence bundle JSON artifact" in text
    assert "Frontend bundle hash verification panel" in text
    assert "Release lock" in text
    assert "Evidence index" in text
    assert "Archive note" in text


def test_evidence_release_completion_badge_lists_verification_coverage():
    path = Path("../docs/public/evidence-release-completion-badge.md")
    text = path.read_text()

    assert "Audit export hash" in text
    assert "Audit export manifest hash" in text
    assert "Compliance evidence bundle hash" in text
    assert "Customer-facing evidence summary" in text


def test_readme_links_to_evidence_release_completion_badge():
    path = Path("../README.md")

    assert path.exists()

    text = path.read_text()

    assert "docs/public/evidence-release-completion-badge.md" in text

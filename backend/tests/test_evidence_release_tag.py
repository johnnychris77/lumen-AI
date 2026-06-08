from pathlib import Path


def test_evidence_release_tag_doc_exists_and_names_tag():
    path = Path("../docs/public/evidence-release-tag.md")

    assert path.exists()

    text = path.read_text()

    assert "LumenAI Compliance Evidence Release Tag" in text
    assert "compliance-evidence-v1.0" in text
    assert "Release compliance evidence workflow v1.0" in text
    assert "Status: Ready for final repository clean-up and release tag." in text


def test_evidence_release_tag_doc_lists_release_scope():
    path = Path("../docs/public/evidence-release-tag.md")
    text = path.read_text()

    assert "Centralized enterprise audit logging" in text
    assert "Audit CSV export" in text
    assert "Audit export SHA-256 hashing" in text
    assert "Audit export manifest generation" in text
    assert "Compliance evidence bundle generation" in text
    assert "Bundle verification" in text
    assert "Public verification summary" in text
    assert "Bundle JSON download" in text
    assert "Compliance evidence bundle card" in text
    assert "Evidence bundle hash verification panel" in text


def test_evidence_release_tag_doc_lists_validation_and_tag_commands():
    path = Path("../docs/public/evidence-release-tag.md")
    text = path.read_text()

    assert "ruff check app tests" in text
    assert "npm run build" in text
    assert "git tag -a compliance-evidence-v1.0" in text
    assert "git push origin compliance-evidence-v1.0" in text


def test_readme_links_to_evidence_release_tag_doc():
    path = Path("../README.md")

    assert path.exists()

    text = path.read_text()

    assert "docs/public/evidence-release-tag.md" in text

from pathlib import Path


def test_evidence_release_demo_walkthrough_guide_exists_and_confirms_status():
    path = Path("../docs/public/evidence-release-demo-walkthrough-guide.md")

    assert path.exists()

    text = path.read_text()

    assert "LumenAI Evidence Release Demo Walkthrough Guide" in text
    assert "Status: Ready for public portfolio, customer review, investor demo" in text
    assert "LumenAI Compliance Evidence v1.0" in text
    assert "compliance-evidence-v1.0" in text
    assert "Demo Walkthrough Guide: Complete." in text


def test_evidence_release_demo_walkthrough_guide_lists_prerequisites_and_command():
    path = Path("../docs/public/evidence-release-demo-walkthrough-guide.md")
    text = path.read_text()

    assert "uvicorn app.main:app --reload --port 8000" in text
    assert "npm run dev" in text
    assert 'BASE_URL="http://127.0.0.1:8000" ./scripts/demo_compliance_evidence_bundle.sh' in text
    assert 'OUTPUT_DIR="/tmp/my-lumenai-demo"' in text
    assert "/tmp/lumenai-compliance-evidence-demo" in text


def test_evidence_release_demo_walkthrough_guide_lists_artifacts_and_steps():
    path = Path("../docs/public/evidence-release-demo-walkthrough-guide.md")
    text = path.read_text()

    assert "audit_event.json" in text
    assert "bundle_response.json" in text
    assert "bundle_verify.json" in text
    assert "bundle_summary.json" in text
    assert "lumenai-compliance-evidence-bundle.json" in text
    assert "demo_summary.txt" in text

    assert "Preflight backend check" in text
    assert "Creating demo audit event" in text
    assert "Generating compliance evidence bundle" in text
    assert "Verifying bundle hash" in text
    assert "Loading public verification summary" in text
    assert "Downloading evidence bundle JSON artifact" in text


def test_evidence_release_demo_walkthrough_guide_lists_evidence_chain_and_ui():
    path = Path("../docs/public/evidence-release-demo-walkthrough-guide.md")
    text = path.read_text()

    assert "Export receives SHA-256 hash." in text
    assert "Manifest receives SHA-256 hash." in text
    assert "Bundle receives SHA-256 hash." in text
    assert "Public verification summary provides safe proof." in text

    assert "Compliance Evidence Bundle card" in text
    assert "Generate Evidence Bundle button" in text
    assert "Download Bundle JSON button" in text
    assert "Evidence Bundle Verification panel" in text
    assert "Paste bundle hash verification workflow" in text


def test_evidence_release_demo_walkthrough_guide_lists_talk_track_and_questions():
    path = Path("../docs/public/evidence-release-demo-walkthrough-guide.md")
    text = path.read_text()

    assert "LumenAI converts healthcare operations audit activity into tamper-evident compliance evidence." in text
    assert "SHA-256 audit export hash" in text
    assert "SHA-256 manifest hash" in text
    assert "SHA-256 bundle hash" in text
    assert "What evidence was generated?" in text
    assert "Can the bundle be verified?" in text


def test_readme_links_to_evidence_release_demo_walkthrough_guide():
    path = Path("../README.md")

    assert path.exists()

    text = path.read_text()

    assert "docs/public/evidence-release-demo-walkthrough-guide.md" in text

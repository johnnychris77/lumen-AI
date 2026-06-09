from pathlib import Path


def test_demo_script_exists_and_uses_output_directory():
    path = Path("../scripts/demo_compliance_evidence_bundle.sh")

    assert path.exists()

    text = path.read_text()

    assert 'OUTPUT_DIR="${OUTPUT_DIR:-/tmp/lumenai-compliance-evidence-demo}"' in text
    assert "DEMO_SUMMARY_FILE" in text
    assert "BUNDLE_DOWNLOAD_HEADERS_FILE" in text
    assert "mkdir -p" in text


def test_demo_script_includes_preflight_and_required_steps():
    path = Path("../scripts/demo_compliance_evidence_bundle.sh")
    text = path.read_text()

    assert "Preflight backend check" in text
    assert "/openapi.json" in text
    assert "Creating demo audit event" in text
    assert "Generating compliance evidence bundle" in text
    assert "Verifying bundle hash" in text
    assert "Loading public verification summary" in text
    assert "Downloading evidence bundle JSON artifact" in text
    assert "Writing demo summary" in text


def test_demo_script_references_core_evidence_endpoints():
    path = Path("../scripts/demo_compliance_evidence_bundle.sh")
    text = path.read_text()

    assert "/api/enterprise/audit/events" in text
    assert "/api/enterprise/audit/evidence-bundle" in text
    assert "/api/enterprise/audit/evidence-bundle/verify" in text
    assert "/api/enterprise/audit/evidence-bundle/verification-summary" in text
    assert "/api/enterprise/audit/evidence-bundle/download.json" in text


def test_demo_readme_documents_output_artifacts():
    path = Path("../docs/compliance/evidence-bundle-demo.md")

    assert path.exists()

    text = path.read_text()

    assert "Demo Output Artifacts" in text
    assert "/tmp/lumenai-compliance-evidence-demo" in text
    assert "demo_summary.txt" in text
    assert "bundle_download_headers.txt" in text
    assert "OUTPUT_DIR" in text
    assert "/openapi.json" in text

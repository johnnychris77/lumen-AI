diff --git a/backend/tests/test_baseline_ranking_audit_evidence.py b/backend/tests/test_baseline_ranking_audit_evidence.py
new file mode 100644
index 0000000000000000000000000000000000000000..d1cf92d6f542ab74ed77fff93e7f98e742005e6a
--- /dev/null
+++ b/backend/tests/test_baseline_ranking_audit_evidence.py
@@ -0,0 +1,130 @@
+import pytest
+
+from app.core.baseline_ranking_contract import build_baseline_ranking_audit_evidence
+
+
+@pytest.fixture(autouse=True)
+def ensure_test_database_tables():
+    yield
+
+
+def test_approved_payload_emits_deterministic_audit_evidence():
+    result = build_baseline_ranking_audit_evidence(
+        {
+            "instrument_match_status": "Matched",
+            "baseline_status": "Approved Baseline Found",
+            "baseline_confidence": "High",
+            "capture_method": "Barcode",
+            "barcode_value": "STRYKER-BARCODE-001",
+            "instrument_name": "Kerrison Rongeur",
+            "model_number": "KR-45",
+            "instrument_category": "Spine",
+        }
+    )
+
+    assert result == {
+        "instrument_match_status": "Matched",
+        "baseline_status": "Approved Baseline Found",
+        "baseline_confidence": "High",
+        "ranking_mode": "Baseline-confirmed ranking",
+        "baseline_review_required": False,
+        "final_ranking_allowed": True,
+        "baseline_review_reason": "Approved baseline matched.",
+        "capture_method": "Barcode",
+        "barcode_value": "STRYKER-BARCODE-001",
+        "instrument_name": "Kerrison Rongeur",
+        "model_number": "KR-45",
+        "instrument_category": "Spine",
+    }
+
+
+def test_pending_payload_emits_review_required_audit_evidence():
+    result = build_baseline_ranking_audit_evidence(
+        {
+            "instrument_match_status": "Partial Match",
+            "baseline_status": "Pending Baseline Review",
+            "baseline_confidence": "Medium",
+            "capture_method": "Manual Entry",
+        }
+    )
+
+    assert result == {
+        "instrument_match_status": "Partial Match",
+        "baseline_status": "Pending Baseline Review",
+        "baseline_confidence": "Medium",
+        "ranking_mode": "Provisional ranking",
+        "baseline_review_required": True,
+        "final_ranking_allowed": False,
+        "baseline_review_reason": "Baseline pending approval; ranking remains provisional.",
+        "capture_method": "Manual Entry",
+    }
+
+
+def test_manual_review_payload_emits_manual_review_audit_evidence():
+    result = build_baseline_ranking_audit_evidence(
+        {
+            "instrument_match_status": "Not Matched",
+            "baseline_status": "No Approved Baseline",
+            "baseline_confidence": "Unknown",
+            "instrument_name": "Forceps",
+        }
+    )
+
+    assert result == {
+        "instrument_match_status": "Not Matched",
+        "baseline_status": "No Approved Baseline",
+        "baseline_confidence": "Unknown",
+        "ranking_mode": "Manual review required",
+        "baseline_review_required": True,
+        "final_ranking_allowed": False,
+        "baseline_review_reason": "No approved baseline available for final ranking.",
+        "instrument_name": "Forceps",
+    }
+
+
+def test_malformed_payload_emits_safe_review_required_audit_evidence():
+    result = build_baseline_ranking_audit_evidence(
+        {
+            "instrument_match_status": ["Matched"],
+            "baseline_status": {"value": "Approved Baseline Found"},
+            "baseline_confidence": 100,
+            "capture_method": "Barcode",
+            "barcode_value": "STRYKER-BARCODE-001",
+        }
+    )
+
+    assert result == {
+        "instrument_match_status": "",
+        "baseline_status": "",
+        "baseline_confidence": "",
+        "ranking_mode": "Pending baseline check",
+        "baseline_review_required": True,
+        "final_ranking_allowed": False,
+        "baseline_review_reason": "Baseline status has not been confirmed.",
+        "capture_method": "Barcode",
+        "barcode_value": "STRYKER-BARCODE-001",
+    }
+
+
+def test_unsafe_payload_cannot_force_audit_evidence_final_ranking():
+    result = build_baseline_ranking_audit_evidence(
+        {
+            "instrument_match_status": "Not Matched",
+            "baseline_status": "Approved Baseline Found",
+            "baseline_confidence": "High",
+            "ranking_mode": "Baseline-confirmed ranking",
+            "baseline_review_required": False,
+            "final_ranking_allowed": True,
+            "baseline_review_reason": "client supplied",
+        }
+    )
+
+    assert result == {
+        "instrument_match_status": "Not Matched",
+        "baseline_status": "Approved Baseline Found",
+        "baseline_confidence": "High",
+        "ranking_mode": "Pending baseline check",
+        "baseline_review_required": True,
+        "final_ranking_allowed": False,
+        "baseline_review_reason": "Baseline status has not been confirmed.",
+    }

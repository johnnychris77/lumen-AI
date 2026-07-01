"""Phase 14 — Clinical Mentor: interpretation, why-this-matters, expanded
actions, standards, learning mode, risk separation, AI Mentor."""
from app.db.session import SessionLocal
from app.models.baseline_library import BaselineLibraryEntry
from app.services.baseline_comparison_scoring_service import analyze_inspection
from app.services.clinical_mentor import (
    FINDING_EDUCATION,
    NEXT_ACTIONS,
    STANDARDS_GUIDANCE,
    contamination_risk,
    integrity_risk,
    detailed_interpretation,
)

SHA = "a1b2c3d4" + "0" * 56


def _baseline(itype: str) -> None:
    db = SessionLocal()
    try:
        db.query(BaselineLibraryEntry).filter(
            BaselineLibraryEntry.instrument_category == itype
        ).delete()
        db.add(BaselineLibraryEntry(
            udi=f"cm-{itype}", instrument_category=itype, manufacturer_name="M",
            model_name="X", baseline_type="manufacturer", approval_status="approved",
        ))
        db.commit()
    finally:
        db.close()


def _analyze(itype, declared=None):
    _baseline(itype)
    db = SessionLocal()
    try:
        return analyze_inspection(
            db, instrument_type=itype, tenant_id="default-tenant",
            has_image=True, image_sha256=SHA, declared_findings=declared,
        )
    finally:
        db.close()


class TestMentorWiring:
    def test_clinical_decision_has_mentor_sections(self):
        cd = _analyze("scissors")["clinical_decision"]
        for key in (
            "clinical_interpretation", "why_this_matters", "next_actions",
            "standards_guidance", "learning_mode", "contamination_risk",
            "integrity_risk", "ai_mentor",
        ):
            assert key in cd, f"missing {key}"


class TestInterpretation:
    def test_crack_interpretation_is_structural(self):
        cd = _analyze("forceps", declared=["crack"])["clinical_decision"]
        text = " ".join(cd["clinical_interpretation"]).lower()
        assert "structural" in text
        assert "clinical use" in text  # "should not be returned to clinical use"

    def test_interpretation_not_generic(self):
        # Interpretation must reference the baseline match (grounded, not filler).
        cd = _analyze("needle_holder")["clinical_decision"]
        assert any("baseline" in ln.lower() for ln in cd["clinical_interpretation"])


class TestWhyThisMatters:
    def test_declared_blood_has_education(self):
        cd = _analyze("scissors", declared=["blood"])["clinical_decision"]
        entries = {e["finding"] for e in cd["why_this_matters"]}
        assert "blood" in entries
        blood = next(e for e in cd["why_this_matters"] if e["finding"] == "blood")
        assert "incomplete cleaning" in blood["why_it_matters"].lower()

    def test_education_library_complete(self):
        for kpi in ("blood", "tissue", "rust", "corrosion", "crack",
                    "discoloration", "missing_component", "insulation_damage"):
            assert kpi in FINDING_EDUCATION
            for field in ("why_it_matters", "definition", "typical_causes",
                          "clinical_significance", "spd_response", "supervisor_tips"):
                assert FINDING_EDUCATION[kpi][field]


class TestNextActionsAndStandards:
    def test_remove_actions_are_multistep(self):
        acts = NEXT_ACTIONS["REMOVE FROM SERVICE"]
        assert "Generate repair work order." in acts
        assert "Document serial number." in acts

    def test_all_outcomes_have_actions_and_standards(self):
        for outcome in ("PASS", "MONITOR", "SUPERVISOR REVIEW", "REPROCESS", "REMOVE FROM SERVICE"):
            assert NEXT_ACTIONS[outcome]
            assert STANDARDS_GUIDANCE[outcome]

    def test_standards_not_quoting_copyright(self):
        # Summaries reference standards by name but must not be long quotations.
        for text in STANDARDS_GUIDANCE.values():
            assert len(text) < 400


class TestRiskSeparation:
    def test_clean_but_cracked_separates_risk(self):
        cd = _analyze("forceps", declared=["crack"])["clinical_decision"]
        # Crack drives integrity risk high/critical while contamination stays low.
        assert cd["integrity_risk"] in ("High", "Critical")
        assert cd["contamination_risk"] in ("Low", "Medium")
        assert cd["overall_result"] == "REMOVE FROM SERVICE"

    def test_blood_drives_contamination_risk(self):
        cd = _analyze("scissors", declared=["blood"])["clinical_decision"]
        assert cd["contamination_risk"] in ("High", "Critical")

    def test_risk_bands_valid(self):
        cd = _analyze("scissors")["clinical_decision"]
        assert cd["contamination_risk"] in ("Low", "Medium", "High", "Critical")
        assert cd["integrity_risk"] in ("Low", "Medium", "High", "Critical")


class TestAIMentor:
    def test_mentor_answers_all_questions(self):
        cd = _analyze("scissors", declared=["blood"])["clinical_decision"]
        m = cd["ai_mentor"]
        for key in ("what_was_detected", "why_it_matters", "how_confident",
                    "standard_practice", "what_should_happen_next"):
            assert key in m
        assert m["what_was_detected"]
        assert m["what_should_happen_next"]

    def test_no_baseline_interpretation_defers(self):
        db = SessionLocal()
        try:
            db.query(BaselineLibraryEntry).filter(
                BaselineLibraryEntry.instrument_category == "clip_applier"
            ).delete()
            db.commit()
            out = analyze_inspection(
                db, instrument_type="clip_applier", tenant_id="default-tenant",
                has_image=True, image_sha256=SHA,
            )
        finally:
            db.close()
        interp = out["clinical_decision"]["clinical_interpretation"]
        assert any("supervisor" in ln.lower() for ln in interp)


def test_contamination_and_integrity_helpers_direct():
    r = {"analysis_status": "completed",
         "predicted_findings": [{"type": "crack", "severity_index": 2}]}
    assert integrity_risk(r) == "Critical"
    assert contamination_risk(r) == "Low"
    assert detailed_interpretation(r, "REMOVE FROM SERVICE")

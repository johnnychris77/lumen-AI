"""v1.10 — Instrument Knowledge Expansion.

Covers the acceptance criteria: 100+ instrument families, anatomy profiles,
high-risk inspection zones, inspection guidance, the Knowledge Graph
explorer's new instrument_family category, and the resolved borrowed-anatomy
debt in instrument_family_profiles.py.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.services.instrument_anatomy import (
    INSTRUMENT_ANATOMY, anatomy_profile, get_anatomy, list_anatomy_families, resolve_family,
)
from app.services.instrument_family_profiles import INSTRUMENT_FAMILY_PROFILES, get_family_profile
from app.services.knowledge_graph_service import explore, reasoning_chain

client = TestClient(app)
AUTH_ADMIN = {"Authorization": "Bearer dev-token"}
AUTH_VIEWER = {"Authorization": "Bearer viewer-token"}


class TestFamilyCountAcceptanceCriterion:
    def test_at_least_100_real_families_declared(self):
        families = list_anatomy_families()
        assert len(families) >= 100

    def test_default_fallback_excluded_from_family_list(self):
        assert "default" not in {f["family"] for f in list_anatomy_families()}
        assert "default" in INSTRUMENT_ANATOMY


class TestAnatomyProfilesAndHighRiskZones:
    def test_every_declared_family_has_zones_and_guidance(self):
        for family, defn in INSTRUMENT_ANATOMY.items():
            assert defn["zones"], f"{family} has no zones"
            assert defn["required_images"], f"{family} has no required_images"
            assert defn["manual_steps"], f"{family} has no manual_steps"
            assert defn["min_images"] >= 1

    def test_every_family_required_image_is_a_real_zone(self):
        for family, defn in INSTRUMENT_ANATOMY.items():
            zone_names = {z["zone_name"] for z in defn["zones"]}
            for img in defn["required_images"]:
                assert img in zone_names, f"{family}: required image '{img}' is not a declared zone"

    def test_high_risk_zones_are_a_real_subset_of_declared_zones(self):
        for family in list_anatomy_families():
            zone_names = set(family["zone_names"])
            for z in family["high_risk_zones"]:
                assert z in zone_names

    def test_new_family_resolves_and_has_full_profile_shape(self):
        p = anatomy_profile("towel clamp")
        assert p["profile_found"] is True
        assert p["instrument_family"] == "towel_clamp"
        for key in (
            "anatomy_zones", "required_zones", "high_risk_zones", "zone_descriptions",
            "contamination_risks", "condition_risks", "recommended_image_views", "manual_check_steps",
        ):
            assert key in p
        assert p["warning"] is None

    def test_specialty_coverage_spot_check(self):
        # One representative family per major specialty added in v1.10.
        expectations = {
            "acetabular reamer": "orthopedic_reamer",
            "kerrison pituitary": None,  # not a real phrase; falls back to default below
            "pituitary rongeur": "pituitary_rongeur",
            "myringotomy knife": "myringotomy_knife",
            "capsulorhexis forceps": "capsulorhexis_forceps",
            "aortic punch": "aortic_punch",
            "resectoscope": "resectoscope",
            "micro scissors": "micro_scissors",
            "dental extraction forceps": "dental_extraction_forceps",
            "veress needle": "veress_needle",
            "harmonic scalpel handpiece": "harmonic_scalpel_handpiece",
            "rigid sterilization container": "rigid_sterilization_container",
        }
        for instrument_type, expected_family in expectations.items():
            if expected_family is None:
                continue
            assert resolve_family(instrument_type) == expected_family


class TestCodeReviewFixes:
    """Regression coverage for issues flagged by automated review on PR #82."""

    def test_canonical_underscore_slugs_resolve_to_the_new_family(self):
        # Regression: the inspection form's slug-fallback validator submits
        # instrument_type as an underscore slug (e.g. "towel_clamp"), but
        # match keywords are written as space-separated phrases — a plain
        # substring check never matched the slug form, so real submissions
        # silently fell through to an unrelated, broader family instead.
        assert resolve_family("towel_clamp") == "towel_clamp"
        assert resolve_family("oscillating_saw") == "oscillating_saw"
        assert resolve_family("rib_approximator") == "rib_approximator"

    def test_more_specific_alias_wins_over_a_shadowing_generic_keyword(self):
        # Regression: first-declaration-order matching let an earlier,
        # shorter generic keyword ("tenaculum") shadow a later, more
        # specific alias ("uterine tenaculum forceps") for a completely
        # different declared family.
        assert resolve_family("uterine tenaculum forceps") == "uterine_tenaculum"
        assert resolve_family("mesh dermatome") == "skin_graft_mesher"
        assert resolve_family("monopolar cautery pencil") == "monopolar_pencil"

    def test_kerrisons_own_biter_keyword_no_longer_shadowed_by_drill_bit(self):
        # Pre-existing bug in the original 8 families (unrelated to any
        # Codex comment), found by the same self-match sweep: drill_bit's
        # "bit" is a substring of kerrison_rongeur's own "biter" keyword,
        # and drill_bit is declared first.
        assert resolve_family("biter") == "kerrison_rongeur"

    def test_generic_family_terms_still_resolve_correctly_after_the_keyword_fix(self):
        # Regression: an earlier attempt at the fix above matched on
        # keyword LENGTH instead of declaration order, which broke this —
        # rigid_scope's generic "endoscope" keyword (9 chars) outweighed
        # flexible_endoscope's "flexible" keyword (8 chars) even though
        # flexible_endoscope is deliberately declared first specifically so
        # its keywords win. A second attempt hoisted whole shadowed
        # *families* ahead instead, which just shadowed OTHER families
        # sharing that family's own generic keywords in turn (kerrison_rongeur's
        # "rongeur"/"punch" swallowing pituitary_rongeur/aortic_punch/etc.).
        # The final fix targets only the single literal problem keyword.
        assert resolve_family("flexible endoscope") == "flexible_endoscope"
        assert resolve_family("pituitary rongeur") == "pituitary_rongeur"
        assert resolve_family("laminectomy rongeur") == "laminectomy_rongeur"
        assert resolve_family("aortic punch") == "aortic_punch"
        assert resolve_family("biopsy punch") == "biopsy_punch"

    def test_every_new_familys_own_keywords_resolve_to_itself(self):
        # Broad sweep: no family's own declared match keyword should ever
        # resolve to a different family (the bug class above, generalized).
        mismatches = []
        for family, defn in INSTRUMENT_ANATOMY.items():
            if family == "default":
                continue
            for kw in defn["match"]:
                got = resolve_family(kw)
                if got != family:
                    mismatches.append((family, kw, got))
        assert mismatches == []

    def test_orthopedic_instruments_profile_points_at_matching_anatomy(self):
        # Regression: pointed at oscillating_saw (saw-blade-only zones) while
        # this profile's own inspection/cleaning priorities call out
        # threaded/cannulated regions and cannulation patency — now points
        # at a family whose declared zones actually include a cannulation.
        profile = get_family_profile("orthopedic_instruments")
        assert "cannulation" in profile["typical_anatomy"]

    def test_reasoning_chain_never_reports_a_zone_the_family_does_not_declare(self):
        # Regression: the legacy pilot zone-assignment taxonomy has no rule
        # written for v1.10's new families, so a coincidental keyword match
        # (e.g. "clamp") reported a zone ("serrations") that towel_clamp
        # never declares, leaving Typical Contamination/Damage empty.
        result = reasoning_chain("towel clamp", "blood")
        nodes = {s["node"]: s["value"] for s in result["chain"]}
        assert nodes["Inspection Zone"] in get_anatomy("towel clamp")["zone_names"]
        assert nodes["Typical Contamination"]

    def test_reasoning_chain_unchanged_for_original_families(self):
        # The 8 pre-v1.10 families keep their existing (tested) legacy zone
        # mapping even where it names the mechanical pivot differently than
        # instrument_anatomy.py does for the same family.
        result = reasoning_chain("scissors", "blood")
        nodes = {s["node"]: s["value"] for s in result["chain"]}
        assert nodes["Inspection Zone"] == "hinge"

    def test_explorer_category_reachable_from_frontend_category_list(self):
        import re

        source = (
            __import__("pathlib").Path(__file__).resolve().parents[2]
            / "frontend" / "src" / "pages" / "KnowledgeGraphExplorer.tsx"
        ).read_text()
        match = re.search(r"EXPLORE_CATEGORIES\s*=\s*\[(.*?)\]", source, re.DOTALL)
        assert match and '"instrument_family"' in match.group(1)


class TestExistingResolutionUnchanged:
    """The v1.10 expansion is declared before the original 8 families so its
    specific multi-word keywords win — this must not change resolution for
    any input the original 8 families already matched."""

    def test_original_families_still_resolve_the_same(self):
        checks = {
            "rigid scope": "rigid_scope",
            "flexible colonoscope": "flexible_endoscope",
            "gastroscope": "flexible_endoscope",
            "orthopedic drill bit": "drill_bit",
            "drill bit": "drill_bit",
            "reamer": "drill_bit",
            "kerrison rongeur": "kerrison_rongeur",
            "kerrison": "kerrison_rongeur",
            "kelly forceps": "general_forceps",
            "forceps": "general_forceps",
            "serrated forceps": "general_forceps",
            "curved scissors": "scissors",
            "needle holder": "needle_holder",
            "laparoscopic grasper": "laparoscopic",
            "trocar": "laparoscopic",
            "scope": "rigid_scope",
            "mystery tool": "default",
        }
        for instrument_type, expected_family in checks.items():
            assert resolve_family(instrument_type) == expected_family, instrument_type

    def test_get_anatomy_zone_names_unchanged_for_original_families(self):
        assert "o-ring area" in get_anatomy("rigid scope")["zone_names"]
        assert "biopsy channel" in get_anatomy("flexible gastroscope")["zone_names"]
        assert "flutes" in get_anatomy("drill bit")["zone_names"]


class TestBorrowedAnatomyDebtResolved:
    def test_previously_borrowed_families_now_have_dedicated_anatomy(self):
        assert get_family_profile("cannulated_instruments")["anatomy_family_key"] != "laparoscopic"
        assert get_family_profile("orthopedic_instruments")["anatomy_family_key"] != "drill_bit"
        assert get_family_profile("micro_instruments")["anatomy_family_key"] != "default"

    def test_dedicated_anatomy_keys_resolve_to_themselves(self):
        for key in ("cannulated_instruments", "orthopedic_instruments", "micro_instruments"):
            profile = get_family_profile(key)
            assert profile["typical_anatomy"], key
            assert profile["high_risk_zones"], key

    def test_ten_family_profile_key_set_unchanged(self):
        # v1.10 only changed anatomy_family_key values inside existing
        # profiles — the profile key set itself is a fixed contract
        # (test_knowledge_graph.py::test_all_ten_families_defined).
        assert len(INSTRUMENT_FAMILY_PROFILES) == 10


class TestKnowledgeGraphInstrumentFamilyCategory:
    def test_explore_instrument_family_category_lists_all_families(self):
        from app.db.session import SessionLocal

        db = SessionLocal()
        try:
            result = explore(db, "default-tenant", "instrument_family")
        finally:
            db.close()
        assert result["category"] == "instrument_family"
        assert result["total_families"] >= 100
        assert any(r["family"] == "towel_clamp" for r in result["results"])

    def test_explore_instrument_family_query_filters(self):
        from app.db.session import SessionLocal

        db = SessionLocal()
        try:
            result = explore(db, "default-tenant", "instrument_family", query="reamer")
        finally:
            db.close()
        assert result["results"]
        assert all("reamer" in r["family"].lower() or "reamer" in r["category"].lower() for r in result["results"])

    def test_api_lists_all_families_still_returns_10_knowledge_profiles(self):
        res = client.get("/api/knowledge-graph/instrument-families", headers=AUTH_VIEWER)
        assert res.status_code == 200
        assert len(res.json()["families"]) == 10

    def test_highest_risk_anatomy_zone_no_longer_crashes(self):
        # Regression: enterprise_knowledge_analytics used to double-index
        # the already-resolved zone string, 500ing whenever any supervisor
        # review had a missed-zone entry.
        res = client.get("/api/analytics/zone-intelligence", headers=AUTH_ADMIN)
        assert res.status_code == 200


class TestAnatomyLibraryEndpointsExposeExpansion:
    def test_list_endpoint_returns_100_plus_families(self):
        res = client.get("/api/instrument-anatomy", headers=AUTH_ADMIN)
        assert res.status_code == 200
        assert len(res.json()["families"]) >= 100

    def test_profile_endpoint_resolves_a_new_family(self):
        res = client.get("/api/instrument-anatomy/pituitary%20rongeur", headers=AUTH_ADMIN)
        assert res.status_code == 200
        body = res.json()
        assert body["instrument_family"] == "pituitary_rongeur"
        assert "cup jaw" in body["anatomy_zones"]

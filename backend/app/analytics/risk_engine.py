_ISSUE_BASE: dict[str, int] = {
    "none": 0,
    "debris": 45,
    "stain": 45,
    "blood": 60,
    "bone": 55,
    "tissue": 55,
    "corrosion": 70,
    "crack": 85,
    "insulation_damage": 85,
    "other": 30,
}


def calculate_risk(issue: str, confidence: float) -> int:
    """Return 0–100 risk score from finding category and AI confidence.

    Blood, bone, tissue, crack, and insulation_damage previously returned 0.
    All clinically significant categories now carry non-zero base scores.
    human_review_required=True must be set by the caller on every output.
    """
    base = _ISSUE_BASE.get(issue, 30)
    conf_bonus = 15 if confidence > 0.9 else 10 if confidence > 0.8 else 0
    return min(base + conf_bonus, 100)

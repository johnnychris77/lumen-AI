"""Phase 18 §3 — Ground-truth derivation for pilot validation.

Turns a supervisor's review into a ground-truth label (true/false positive/
negative, or inconclusive) by comparing what the AI flagged against what the
supervisor confirmed. Deterministic and honest — when the signal is ambiguous
the label is `inconclusive`, never guessed.
"""
from __future__ import annotations

TRUE_POSITIVE = "true_positive"
TRUE_NEGATIVE = "true_negative"
FALSE_POSITIVE = "false_positive"
FALSE_NEGATIVE = "false_negative"
INCONCLUSIVE = "inconclusive"

GROUND_TRUTH_LABELS = [
    TRUE_POSITIVE, TRUE_NEGATIVE, FALSE_POSITIVE, FALSE_NEGATIVE, INCONCLUSIVE,
]


def classify_ground_truth(
    ai_finding_present: bool | None,
    supervisor_finding_present: bool | None,
    agreement: str | None = None,
) -> str:
    """Compare AI vs supervisor to a ground-truth label.

    - AI flagged + supervisor confirmed  → true_positive
    - AI clear   + supervisor clear       → true_negative
    - AI flagged + supervisor says clean  → false_positive
    - AI clear   + supervisor found one   → false_negative
    - either signal missing               → inconclusive
    """
    if ai_finding_present is None or supervisor_finding_present is None:
        return INCONCLUSIVE
    if ai_finding_present and supervisor_finding_present:
        return TRUE_POSITIVE
    if not ai_finding_present and not supervisor_finding_present:
        return TRUE_NEGATIVE
    if ai_finding_present and not supervisor_finding_present:
        return FALSE_POSITIVE
    return FALSE_NEGATIVE


def derive_flags_from_review(
    *,
    ai_finding_present: bool | None,
    supervisor_finding_present: bool | None,
    finding_correct: bool | None,
    agreement: str | None,
    ai_recommendation: str | None,
    corrected_recommendation: str | None,
    final_disposition: str | None,
) -> tuple[bool | None, bool | None]:
    """Best-effort recovery of the two flags when they were not sent explicitly.

    Falls back to the AI recommendation (a non-pass recommendation means the AI
    flagged something) and the supervisor's finding_correct signal. Returns
    (ai_finding_present, supervisor_finding_present); either may stay None, which
    yields an `inconclusive` ground truth."""
    ai_flag = ai_finding_present
    if ai_flag is None and ai_recommendation:
        ai_flag = _rec_means_finding(ai_recommendation)

    sup_flag = supervisor_finding_present
    if sup_flag is None and finding_correct is not None and ai_flag is not None:
        # If the AI's call was correct, the supervisor agrees with the AI's flag;
        # if incorrect, the supervisor's truth is the opposite of the AI's flag.
        sup_flag = ai_flag if finding_correct else (not ai_flag)
    if sup_flag is None:
        disp = (corrected_recommendation or final_disposition or "")
        if disp:
            sup_flag = _rec_means_finding(disp)
    return ai_flag, sup_flag


def _rec_means_finding(rec: str) -> bool:
    """A recommendation other than a clean pass/monitor implies a finding."""
    r = (rec or "").strip().lower()
    clean = {"pass", "monitor", "no action", "release", ""}
    return r not in clean

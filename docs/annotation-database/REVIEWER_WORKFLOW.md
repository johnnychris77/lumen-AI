# Reviewer Workflow

## Role hierarchy (Section 14)

| Spec role | Enforced role string | May annotate | May review | May adjudicate / finalize GT | May export |
|---|---|---|---|---|---|
| Administrator | `admin` | ✓ | ✓ | ✓ | ✓ |
| Clinical Reviewer | `clinical_reviewer` | ✓ | ✓ | ✓ | — |
| Reviewer | `spd_manager` | ✓ | ✓ | — | — |
| Annotator | `operator` | ✓ | — | — | — |
| AI Researcher | `ai_researcher` | — | — | — | ✓ |
| Viewer | `viewer` | — | — | — | — |

`role` columns (`app.models.user.User`, `app.db.models.TenantMembership`)
are free-form `String` columns, not an enum — `clinical_reviewer` and
`ai_researcher` are additive role values requiring no change to core auth
infrastructure, only that an org admin assigns them via the existing
role-assignment path.

## Workflow

1. An Annotator (or higher) creates an `Annotation` (`review_status = UNLABELED`).
2. A Reviewer submits the **primary** review
   (`POST /annotations/{id}/review/primary`).
3. A **different** Reviewer submits the **independent secondary** review
   (`POST /annotations/{id}/review/secondary`) — blind by construction,
   the service never surfaces the primary label to the caller first, and
   rejects a secondary reviewer who is the same person as the primary one.
4. `AnnotationReview.agreement` is computed automatically
   (`primary_label == secondary_label`).
5. If they agree, a Clinical Reviewer/Administrator may promote to Ground
   Truth directly. If they disagree, see `ADJUDICATION_GUIDE.md`.

## Tracked per review

Reviewer identity, submission timestamp, confidence, comments, computed
agreement, and (on disagreement) a disagreement reason — all real columns
on `AnnotationReview`, never inferred.

# images/approved/

Images whose Ground Truth has reached the `APPROVED` annotation state
(`app.models.dataset_governance.APPROVED`) — the only state Section 7
permits calling Ground Truth. An entry only reaches `APPROVED` after a
completed `DoubleBlindReview` (primary + independent reviewer agreement)
or an explicit clinical adjudication. **AI predictions are never Ground
Truth** — nothing in this codebase writes an `APPROVED` annotation event
from a model's own output.

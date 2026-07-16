# Dataset Split Report — Project Vision Sprint 2 (Section 4)

This is the exact-filename doc Sprint 2 Section 4/21 requires. The full,
already-written split/leakage report — grouping identity, real split
numbers, duplicate control, class-distribution table, diversity check — is
`DATASET_SPLIT_AND_LEAKAGE_REPORT.md` (Project Lens Sprint 4). Nothing about
the split methodology changed in Sprint 2; this doc exists only to satisfy
the required filename and to record what Sprint 2 verified about it.

See `DATASET_SPLIT_AND_LEAKAGE_REPORT.md` for the full report. Summary of
what it establishes, verified unchanged as of this sprint:

- Grouping is by the strongest available real identity (Digital Twin ID,
  excluding `untracked:` fallback IDs — an untracked ID would incorrectly
  collapse every image of one *instrument type* into a single group, since
  it means no real serial/UDI was ever captured for that image).
- No related images cross splits — `dataset_split.has_no_group_leakage()`
  is checked, and `run_lens_training()` fails the run outright when it does
  not hold (Section 4's "fail training on leakage" requirement).
- Class distribution and diversity are reported honestly, including the
  known small-sample artifacts (a 0-sample validation split on this run's
  46-image dataset, 1 facility) — never padded or hidden behind an
  aggregate number.
- `tests/test_dataset_registry.py::test_build_training_dataset_split_has_no_leakage`
  and `tests/test_project_lens.py` pin this behavior in automated tests.

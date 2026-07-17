# Digital Twin Persistence

## Contract (pre-existing, verified this sprint)

Each instrument's Digital Twin (`app/models/digital_twin.py` and the
timeline services built for Project Canvas) accumulates, per instrument:
inspection history, baseline history, AI observations (with the model
version that produced them), maintenance/repair events, sterilization
history, and condition-progression records (corrosion/contamination
trajectories in the quality-twin services).

**Nothing is deleted.** Twin history is written as event/history rows;
corrections append, they do not rewrite. AI observations remain immutable
once recorded (the Sprint-2 contract keeps the original observation even
when a supervisor overrides the disposition — the override is its own
audited record).

## Foundation Sprint 1 status

Objective met by existing design; this sprint added PostgreSQL executed
evidence (twin tables migrated + suite-exercised on PostgreSQL 16) and
backup coverage (twin rows are ordinary database rows and were part of
the executed DR round-trip).

## Honest limitations

Twin depth in current environments reflects dev/test data only. The
retention semantics are enforced; longitudinal real-instrument history
requires the managed persistent deployment.

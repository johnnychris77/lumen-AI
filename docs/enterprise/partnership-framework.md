# Partnership Framework

How LumenAI engages with each partner type. Each section below is the
starting brief for that audience — detailed per-partner agreements are
handled through `docs/commercial/enterprise-sales-playbook.md` and legal
review, not defined here.

## Hospitals

Direct customers. Onboard via `docs/customer/` (the implementation
playbook) into Community or Professional Edition
(`docs/enterprise/commercial-packaging.md`). Primary relationship owners:
Executive Sponsor + SPD Champion (customer-side), Customer Success
Manager (LumenAI-side).

## Health Systems

Multi-facility customers, typically Enterprise Edition. Requires
multi-tenant deployment planning
(`docs/deployment/multi-tenant-deployment-guide.md`) and a rollout
sequence across facilities — see
`docs/enterprise/multi-site-rollout-playbook.md` for the existing
multi-site onboarding sequence this framework builds on.

## Instrument Manufacturers

Engage via the Manufacturer Edition
(`docs/enterprise/commercial-packaging.md`). Manufacturers contribute
baseline data (`app/models/baseline_library.py`, vendor baseline
governance), IFU references, and known failure modes
(`app/models/instrument_knowledge.py`), and receive anonymized network
performance visibility for their own products — never access to any
hospital's raw clinical data. This is the same boundary enforced for
network intelligence generally (Phase 15, CLAUDE.md's cross-hospital
anonymization constraint).

## SPD Vendors

Distinct from instrument manufacturers — SPD vendors (reprocessing
service providers, third-party sterile processing operators) may
integrate via the external system connector framework
(`app/models/external_connector.py`) for CMMS/ERP-adjacent data exchange,
gated by the same BAA/consent requirements as any integration touching
PHI-adjacent data.

## Consulting Partners

Implementation and change-management consultants who support hospital
customers through the 30/60/90-day playbook
(`docs/customer/implementation-timeline.md`). LumenAI provides consulting
partners with the same training-matrix content
(`docs/customer/training-matrix.md`) used to train customer staff, plus
partner-specific enablement (not yet formalized as a separate
certification program — tracked as a future enhancement).

## Academic Research

Research collaborations use the Real-World Evidence (RWE) enrollment
framework already built for this purpose
(`app/models/validation.py::RWEEnrollment`,
`docs/clinical/real-world-evidence-plan.md`) — facility opt-in, versioned
consent, and contribution tracking. Research use is always subject to the
same no-PHI and anonymization constraints as every other data use in the
platform.

## Quality Organizations

Accreditation bodies, sterile processing professional associations
(AAMI, AORN, IAHCSMM-equivalent), and quality benchmarking organizations.
Engagement is informational/advisory at this stage — LumenAI's clinical
rule registry (`docs/cios/clinical-rule-registry.md`) and clinical
performance metrics (`docs/validation/clinical-performance-metrics.md`)
are built to be legible to this audience, paraphrasing accepted SPD
practice rather than reproducing copyrighted standards text.

## Cross-cutting partnership principles

- No partner type receives access beyond what its role requires — a
  manufacturer never sees hospital clinical data; a hospital never sees
  another hospital's data; a consulting partner sees only what their
  assigned customer grants.
- Every cross-tenant or cross-partner data flow is audit-logged
  (`app/audit.py`) with `compliance_flag=True` where required.
- No partnership claim implies FDA clearance, regulatory endorsement, or
  a level of clinical validation beyond what `docs/evidence/` documents
  as actually complete.

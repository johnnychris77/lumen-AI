# LPR-DIR-015 — Capacity Planning Report (Phase 4)

**Basis:** measured baselines + data-model growth drivers at `bd94bc5`. **All
projections are parametric estimates** (per-unit costs × assumed volumes), **not**
measured production figures — the volume assumptions must be set with the business
and confirmed by the deferred load test.

## Measured per-instance baselines

| Resource | Measured | Source |
|---|---|---|
| Per-worker memory (import) | ~198 MB | tracemalloc |
| Startup time | ~24 s | benchmark |
| k8s backend pod | 250m CPU req / 1Gi mem limit; 2 replicas | `k8s/backend-deployment.yaml` |

## Growth drivers (per unit)

| Object | Growth driver | Storage tier | Notes |
|---|---|---|---|
| Image | per captured image (bytes) | **object storage** | dominant raw-byte growth; `image_sha256` dedup (non-unique) |
| Audit event | per governed action (append-only, hash-chained) | **DB** | monotonic; never deleted |
| Evidence package | per evidence bundle (checksummed) | DB + object storage | retention-first |
| Annotation/GT | per version (append-only) | DB | monotonic |
| Reports | per generated report | object storage | retention-first |
| Digital Twin | per instrument identity + composed history | DB | bounded by instrument count |
| Dataset/model | per version/registry entry | DB + object storage | batch |

**Key property:** deletion is **retention-first** (soft-deactivate), so DB (audit,
annotations, evidence metadata) and object storage (images, reports) grow
**monotonically** — capacity planning must assume no reclamation without an explicit
retention/archival policy (**CAP-01**).

## Parametric projection (illustrative — set real inputs with business)

Let: I = images/inspection, N = inspections/day, B = avg image bytes,
A = audit events/inspection, E = evidence bytes/package.

| Horizon | Object storage (images) | DB (audit) | Note |
|---|---|---|---|
| 1 yr | ≈ N×365×I×B | ≈ N×365×A rows | linear |
| 3 yr | ≈ 3× | ≈ 3× | linear; index bloat grows write cost |
| 5 yr | ≈ 5× | ≈ 5× | consider partitioning audit + object-storage lifecycle tiers |

*(Concrete GB/TB numbers require the business's N, I, B, A, E — deliberately not
fabricated here.)*

## Compute / network

- **CPU:** dominated by report/packet builders (F/66) + image hashing; scale with
  pods once multi-worker + pool tuning are in place.
- **Memory:** ~198 MB baseline/worker + PDF/ZIP buffers; size pods ≥ 512Mi–1Gi and
  validate under load.
- **Network:** image upload/download bandwidth is the largest flow; object storage
  offloads it from the app tier.
- **DB connections:** budget against pool config (DB-01) + PgBouncer for many pods.

## Recommendations
1. Define **retention/archival policy** for audit + images + reports (CAP-01) — the
   dominant long-term cost.
2. Plan **audit table partitioning** + object-storage lifecycle tiers for 3–5 yr.
3. Set volume assumptions with the business and **confirm per-unit costs in the load
   test** before committing hardware.

## Findings
| ID | Sev | Finding |
|---|---|---|
| CAP-01 | MEDIUM | Retention-first (no reclamation) → monotonic DB + storage growth; needs retention/archival policy |
| CAP-02 | MEDIUM | Projections are parametric (unmeasured volumes); confirm per-unit costs in load test |

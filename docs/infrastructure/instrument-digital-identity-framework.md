# Instrument Digital Identity Framework

**Version:** 1.0 | **Classification:** Technical Standard | **Status:** Active

---

## Purpose

This framework defines how surgical instruments are uniquely identified, verified, and tracked throughout their lifecycle within the Lumen AI platform. It establishes identity schema, verification confidence levels, and the rules governing identity transitions.

---

## Identity Schema

Each instrument identity record contains:

```
InstrumentDigitalIdentity {
  id                  : internal UUID
  tenant_id           : owning tenant
  udi                 : string | null   — FDA/EUDAMED Unique Device Identifier
  barcode             : string | null   — GS1-128 or equivalent
  qr_code             : string | null   — ISO 18004 QR payload
  keydot_id           : string | null   — KeyDot optical encoding
  internal_id         : string | null   — facility-assigned tracking ID
  instrument_type     : string          — e.g. "laparoscope", "retractor"
  manufacturer        : string | null
  model               : string | null
  serial_number       : string | null
  manufacture_date    : date | null
  lifecycle_status    : enum            — active | in_maintenance | quarantined | retired | lost
  total_cycle_count   : integer         — cumulative sterilization cycles
  max_cycle_count     : integer | null  — manufacturer-rated cycle limit
  identity_verified   : boolean         — true only for UDI or KeyDot verification
  verification_method : string          — udi | keydot | qr | barcode | manual
  created_at          : timestamp
  updated_at          : timestamp
}
```

---

## Verification Confidence Hierarchy

Verification confidence is binary in the system (`identity_verified` field) but maps to three practical tiers:

**Tier 1 — Verified (identity_verified = true)**
- UDI: Globally unique, manufacturer-issued, regulatory-grade identifier
- KeyDot: Optical encoding with cryptographic binding to physical substrate

**Tier 2 — Tracked but Unverified (identity_verified = false)**
- QR Code: Facility-generated or manufacturer-attached, not globally unique
- Barcode: Standard facility inventory barcodes

**Tier 3 — Manual (identity_verified = false)**
- Manual entry: Human-entered identifiers, highest risk of transcription error

Rules:
- An instrument requires at least one identifier (UDI, barcode, QR, KeyDot, or internal_id)
- Verification method is immutable once set — to upgrade, a new identity must be created with a passport transfer
- Instruments with `identity_verified = false` are flagged in readiness scoring

---

## Lifecycle Status Transitions

```
              ┌─────────────────────────────────────┐
              ▼                                     │
[active] ──► [in_maintenance] ──► [active]          │ (repair complete)
   │                                                │
   ├──► [quarantined] ──► [active]                  │ (cleared)
   │         │                                      │
   │         └──► [retired]                         │ (condemned)
   │                                                │
   └──► [retired]                                   │ (end-of-life)
   └──► [lost]                                      │ (inventory loss)
```

Status changes are recorded as `InstrumentPassportEvent` entries, creating an immutable audit trail.

**Automatic transitions via passport events:**
- Recording a `quarantine` passport event → status set to `quarantined`
- Recording a `retirement` passport event → status set to `retired`

---

## Identity Creation Rules

1. At least one identifier must be provided (UDI, barcode, QR, KeyDot, or internal_id)
2. `tenant_id` is injected from the authenticated request — not from the request body
3. UDI and KeyDot identifiers must be unique within a tenant
4. `total_cycle_count` starts at 0; incremented only via sterilization passport events
5. `max_cycle_count` is informational; the system does not auto-retire at limit (requires human decision)

---

## Cross-Facility Considerations

When instruments transfer between facilities:
- A `transfer` passport event is recorded
- The receiving facility's tenant ID becomes the owner
- Full passport history remains accessible to both original and receiving facility
- For network-level analytics, manufacturer and instrument type are included; patient data is never attached to instrument records

---

## Privacy and Security

- Instrument records are tenant-scoped; tenants cannot query each other's instruments
- Serial numbers and internal IDs are treated as sensitive operational data
- Manufacturer data may be used in aggregated, anonymized registry contributions (k-anonymity ≥ 5)
- No patient identifiers are stored in any instrument identity or passport record

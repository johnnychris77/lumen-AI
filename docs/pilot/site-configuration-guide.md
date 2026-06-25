# Pilot Site Configuration Guide

**Version:** 1.0  
**Phase:** 7 — Pilot Site Deployment  
**Site:** Bon Secours Pilot — Richmond, VA

---

## Overview

This guide documents the configuration records created for the Bon Secours pilot site. All records are scoped to tenant `bon-secours-pilot` and contain no PHI.

---

## 1. Facility Configuration

| Field | Value |
|-------|-------|
| Tenant ID | `bon-secours-pilot` |
| Tenant Name | Bon Secours Pilot |
| Region | North America (HIPAA) |
| Pilot Start Date | 2026-06-23 |
| Primary Contact | SPD Manager (see user provisioning) |
| Backend URL | Configured per deployment env |
| Frontend URL | Configured per deployment env |
| Data Residency | US-East |
| Storage Backend | S3 (us-east-1) or local fallback |

---

## 2. Departments

| Department ID | Name | Description |
|---------------|------|-------------|
| `SPD-DECON` | SPD Decontamination | Instrument decontamination and initial inspection |
| `SPD-PREP` | SPD Preparation & Packaging | Pre-sterilization assembly |
| `SPD-STERILE` | SPD Sterile Processing | Sterilization and release |
| `OR-CIRC` | OR Circulating | Point-of-use inspection before procedure |

---

## 3. Tray Configuration

| Tray ID | Tray Name | Department | Instruments |
|---------|-----------|------------|-------------|
| `TRAY-OR-GEN-001` | General Laparoscopic Set | OR-CIRC | Laparoscopes, graspers, scissors |
| `TRAY-OR-ENDO-001` | Endoscopy Set | OR-CIRC | Ureteroscopes, cystoscopes |
| `TRAY-OR-ORTHO-001` | Orthopedic Scope Set | OR-CIRC | Arthroscopes |
| `TRAY-SPD-FLEX-001` | Flexible Scope Reprocessing | SPD-DECON | All flexible scopes |
| `TRAY-SPD-RIGID-001` | Rigid Scope Reprocessing | SPD-DECON | All rigid scopes |

---

## 4. Instrument Categories (10 Lumened Instruments)

All 10 instruments are registered in the Instrument Digital Identity registry (table `p25_instrument_identities`, tenant `bon-secours-pilot`).

| Internal ID | Category | Manufacturer | Model | UDI Present | KeyDot Present |
|-------------|----------|-------------|-------|-------------|----------------|
| FURO-001 | flexible_ureteroscope | Olympus | URF-V3 | ✅ | ✅ |
| FURO-002 | flexible_ureteroscope | Olympus | URF-V3 | ✅ | ✅ |
| LAPO-001 | laparoscope | Storz | Hopkins II 30° | ✅ | ✅ |
| LAPO-002 | laparoscope | Storz | Hopkins II 0° | ✅ | — |
| CYSO-001 | cystoscope | Olympus | CYF-VH | ✅ | ✅ |
| BRON-001 | bronchoscope | Fujifilm | EB-590S | ✅ | — |
| HYST-001 | hysteroscope | Bettocchi | 5.0 Fr | — | ✅ |
| ARTH-001 | arthroscope | Arthrex | NanoScope | ✅ | — |
| COLO-001 | colonoscope | Olympus | CF-HQ190L | ✅ | ✅ |
| NEPH-001 | nephroscope | Wolf | Compact 26Fr | — | ✅ |

---

## 5. Vendor Configuration

| Vendor Name | Role | Baseline Type | Contact |
|-------------|------|---------------|---------|
| Aesculap | Instrument vendor | Vendor baseline | vendor@aesculap.com |
| Medline | Instrument vendor | Vendor baseline | vendor@medline.com |
| Symmetry Surgical | Instrument vendor | Vendor baseline | vendor@symmetry.com |
| Sklar Instruments | Instrument vendor | Vendor baseline | vendor@sklar.com |
| Integra LifeSciences | Instrument vendor | Vendor baseline | vendor@integra.com |

Vendor users are provisioned with role `vendor_user`. They can submit baselines via `/vendor-baseline-portal` and `/vendor-intake` but cannot view inspection records.

---

## 6. Manufacturer Configuration

| Manufacturer | Instruments | Baseline Type | UDI Issuing Agency |
|-------------|-------------|---------------|-------------------|
| Olympus | URF-V3, CYF-VH, CF-HQ190L | Manufacturer baseline | GS1 |
| Storz | Hopkins II 30°, Hopkins II 0° | Manufacturer baseline | GS1 |
| Fujifilm | EB-590S | Manufacturer baseline | GS1 |
| Bettocchi | 5.0 Fr | Manufacturer baseline | Manual (no UDI) |
| Arthrex | NanoScope | Manufacturer baseline | GS1 |
| Wolf | Compact 26Fr | Manufacturer baseline | Manual (no UDI) |

---

## 7. User Provisioning

| Role | Username | Scope | Access |
|------|----------|-------|--------|
| `admin` | `admin@bonsecours.org` | Full system | All routes, all data |
| `spd_manager` | `spd.manager@bonsecours.org` | Facility | Inspections, baselines, CAPA, reports |
| `technician` | `spd.tech1@bonsecours.org` | Facility | New inspection, history |
| `technician` | `spd.tech2@bonsecours.org` | Facility | New inspection, history |
| `viewer` | `spd.educator@bonsecours.org` | Facility | Read-only all routes |
| `vendor_user` | `vendor@aesculap.com` | Vendor only | Vendor intake, baseline portal |

**Token setup:** Each user account requires a token provisioned via `POST /auth/login`. For the pilot, tokens are set via environment variables (`DEV_AUTH_TOKEN`, `DEV_SPD_MANAGER_TOKEN`, etc.) until the JWT authentication path is fully activated.

---

## 8. Baseline Configuration

25 baseline records are pre-seeded via `scripts/seed_pilot_data.py`:

| Status | Count | Instruments Covered |
|--------|-------|---------------------|
| Approved | 16 | All 8 instrument categories |
| Pending Review | 9 | Network-contributed and some vendor |

Baseline approval workflow: vendor submits → SPD Manager reviews at `/baseline-review` → approve/reject → approved baselines feed into AI scoring (20% baseline component).

---

## 9. Finding Category Configuration

| Category | Code | Severity Weight | Color |
|----------|------|-----------------|-------|
| None | `none` | 0 | Grey |
| Debris | `debris` | Low-Medium | Amber |
| Blood | `blood` | Medium-High | Red |
| Tissue | `tissue` | Medium | Orange |
| Bone | `bone` | Medium | Orange |
| Corrosion | `corrosion` | High | Red |
| Crack | `crack` | Critical | Dark Red |
| Insulation Damage | `insulation_damage` | Critical | Dark Red |

---

## 10. Integration Configuration

| Integration | Status | Notes |
|-------------|--------|-------|
| S3 Image Storage | Required for pilot | Set `LUMENAI_S3_BUCKET`, `LUMENAI_S3_REGION` |
| Email Alerts | Optional | Set `SMTP_*` env vars for CAPA notifications |
| SSO | Deferred | Not activated for pilot |
| EHR Integration | Deferred | Out of scope for Phase 7 |

---

*LumenAI Pilot Program — Internal Use Only*  
*Site configuration last updated: 2026-06-23*

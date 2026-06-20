# Cybersecurity Readiness
LumenAI Surgical Instrument Inspection Software | Version 1.0
**FDA 2023 Cybersecurity Guidance Compliance Assessment**
**Subject to regulatory counsel review.**

Reference: `docs/clinical/cybersecurity-threat-model.md` (P12)
Reference: FDA "Cybersecurity in Medical Devices: Quality System Considerations and Content of Premarket Submissions" (September 2023)

---

## 1. Cybersecurity Design Controls

LumenAI's cybersecurity posture is designed as a core architectural feature, not a bolt-on. The following design controls are implemented:

| Control | Implementation | Milestone |
|---------|---------------|----------|
| Authentication | JWT-based authentication with configurable expiry | P1 |
| Authorization | Role-based access control (RBAC) with 5 defined roles | P1 |
| Multi-tenancy isolation | Row-level tenant isolation; cross-tenant query prevention | P2 |
| Encryption at rest | AES-256 for sensitive data fields; database-level encryption | P11 |
| Encryption in transit | TLS 1.3 enforced; HTTP redirect to HTTPS | P11 |
| Rate limiting | Per-endpoint rate limiting on auth and inference endpoints | P1/P11 |
| Input validation | Pydantic schema validation on all API inputs | P0-P12 |
| Output sanitization | No raw SQL; ORM-based queries prevent injection | P0 |
| Audit logging | Immutable audit log; all security events captured | P0 |
| Session management | Token expiry; refresh token rotation | P1 |
| Password policy | bcrypt hashing; minimum complexity enforced | P1 |
| SBOM generation | CycloneDX SBOM at every build (GitHub Actions) | P11 |
| Dependency scanning | GitHub Dependabot; automated vulnerability alerts | P11 |

---

## 2. Threat Modeling Summary

Full threat model documented in `docs/clinical/cybersecurity-threat-model.md`. STRIDE analysis summary:

| Threat Category | Key Threats Identified | Controls Applied |
|----------------|----------------------|-----------------|
| Spoofing | Credential theft; session hijacking; JWT forgery | JWT with RS256; token expiry; rate limiting on login |
| Tampering | SQL injection; API payload manipulation; audit log modification | ORM (no raw SQL); Pydantic validation; append-only audit log |
| Repudiation | User denies performing inspection or override action | Immutable audit log with user ID, timestamp, action type |
| Information Disclosure | Cross-tenant data leak; PHI-adjacent data exposure; API over-sharing | Row-level isolation; field-level access control; minimal response payloads |
| Denial of Service | Inference endpoint flooding; database exhaustion | Rate limiting; K8s pod autoscaling; connection pooling |
| Elevation of Privilege | Privilege escalation via RBAC bypass; admin endpoint exposure | RBAC enforcement on every endpoint; role validation in JWT claims |

---

## 3. Security Architecture

### 3.1 Authentication Layer
- **Mechanism**: JSON Web Tokens (JWT) with RS256 signing
- **Token lifetime**: Access token 15 minutes; refresh token 7 days (configurable)
- **MFA**: Required for Manager and Admin roles; planned for all roles in v1.1
- **Failed login**: Account lockout after 5 consecutive failures (configurable)
- **Password storage**: bcrypt with cost factor 12 minimum

### 3.2 Authorization Layer
| Role | Permissions |
|------|------------|
| SPD Technician | Submit inspections; view own findings; override own pending findings |
| SPD Educator | All technician permissions; view all findings in facility |
| SPD Manager | All educator permissions; view dashboard; manage users in facility; review escalations |
| Infection Prevention Specialist | Read-only access to findings and trends; outbreak investigation tools |
| Hospital IT Administrator | System configuration; user management; no access to clinical findings |

### 3.3 Network Security
- All external traffic via HTTPS (TLS 1.3)
- Internal cluster communication via Kubernetes NetworkPolicy (pod-to-pod restrictions)
- Nginx reverse proxy with security headers (HSTS, CSP, X-Frame-Options)
- No direct database exposure to internet; database accessible only from backend pods

### 3.4 Multi-Tenant Isolation
- All database queries include tenant_id filter enforced at ORM layer
- Middleware validates tenant_id in JWT claim against requested resource
- Cross-tenant access returns 403 (not 404) to prevent enumeration
- Tenant isolation verified by dedicated test suite (P2 tests)

### 3.5 Data Encryption
- **At rest**: Database fields containing sensitive data encrypted with AES-256
- **In transit**: TLS 1.3 with certificate pinning for API clients (planned v1.1)
- **Backups**: Encrypted before transmission to S3; encryption keys in AWS KMS
- **Model artifacts**: Signed and integrity-checked at load time

---

## 4. Software Bill of Materials (SBOM)

SBOM is generated automatically at every build as part of the GitHub Actions CI/CD pipeline (`deploy.yml`).

### 4.1 SBOM Generation
- **Tool**: CycloneDX (Python and Node.js plugins)
- **Format**: CycloneDX JSON v1.4
- **Trigger**: Every build (commit to main and release branches)
- **Artifact retention**: SBOM stored in GitHub Actions artifacts + S3 archive (7 years)

### 4.2 SBOM Contents
Each SBOM includes:
- All direct and transitive Python dependencies (from requirements.txt)
- All direct and transitive Node.js dependencies (from package-lock.json)
- Component name, version, PURL, and SHA-256 hash
- Known vulnerabilities at time of build (via OSV/NVD cross-reference)

### 4.3 SBOM Access
SBOM is available to:
- Internal security team (automated delivery)
- Customers (on request, per FDA guidance recommendation)
- FDA (as part of premarket submission)

---

## 5. Vulnerability Management Program

### 5.1 Vulnerability Sources Monitored
| Source | Monitoring Frequency | Responsible |
|--------|--------------------|-----------| 
| GitHub Dependabot | Continuous (automated alerts) | Engineering |
| NVD (NIST National Vulnerability Database) | Weekly review | Security Lead |
| CVE announcements for key dependencies | Continuous (RSS/email) | Security Lead |
| CISA Known Exploited Vulnerabilities catalog | Weekly | Security Lead |
| Vendor security advisories | Per-vendor cadence | Engineering |

### 5.2 Patch Management Timeline
| CVSS Score | Severity | Target Patch Deployment |
|-----------|---------|------------------------|
| 9.0-10.0 | Critical | 24 hours (emergency patch process) |
| 7.0-8.9 | High | 7 calendar days |
| 4.0-6.9 | Medium | 30 calendar days |
| 0.1-3.9 | Low | Next scheduled release |
| 0.0 | Informational | At discretion |

### 5.3 Patch Process
1. Vulnerability identified via automated scan or advisory
2. Severity assessment and exploitability in LumenAI context
3. Patch or workaround identified
4. Test regression (automated test suite)
5. Security review sign-off
6. Deployment (emergency process for Critical/High; standard release for others)
7. SBOM updated; vulnerability record closed
8. Customer notification if actively exploited vulnerability in deployed version

---

## 6. Security Testing Evidence

| Test Type | Tool/Method | Frequency | Last Executed | Evidence Location |
|-----------|------------|----------|--------------|------------------|
| Unit security tests (auth, RBAC, tenant isolation) | pytest | Every commit | Continuous (CI) | GitHub Actions |
| Dependency vulnerability scan | Dependabot + pip-audit | Every build | Continuous (CI) | GitHub Actions |
| Static analysis / secrets scan | ruff + truffleHog | Every commit | Continuous (CI) | GitHub Actions |
| DAST (dynamic application security testing) | OWASP ZAP (planned) | Quarterly | Planned Q2 2026 | TBD |
| Penetration test (external) | Third-party pentest firm | Annual | Planned Q2 2026 | TBD |
| Container image scan | Trivy (planned in CI) | Every build | Planned Q1 2026 | TBD |
| Infrastructure security review | Manual + Checkov | Quarterly | Planned Q2 2026 | TBD |

**Gap**: External penetration test and DAST have not yet been executed. These are planned for Q2 2026 before commercial launch.

---

## 7. Incident Response

Reference: P11 reliability documentation.

### 7.1 Incident Classification
| Level | Definition | Examples | Response Time |
|-------|-----------|---------|--------------|
| P0 — Critical | Active breach; patient data exposed; system compromised | Data exfiltration; ransomware; active account takeover | 1 hour to containment |
| P1 — High | Vulnerability actively exploited; service degraded by attack | DDoS reducing availability; high-severity CVE exploited | 4 hours |
| P2 — Medium | Security control failure; potential exposure | Auth bypass discovered; misconfiguration identified | 24 hours |
| P3 — Low | Informational security finding | Low-severity CVE; minor security configuration deviation | 7 days |

### 7.2 Incident Response Steps
1. **Detection**: Automated monitoring alert or user report
2. **Triage**: On-call engineer classifies severity (15 minutes)
3. **Containment**: Isolate affected component; revoke compromised credentials; block attacking IP
4. **Notification**: Internal escalation per severity level; customer notification per SLA
5. **Eradication**: Remove threat; patch vulnerability; restore from clean backup if needed
6. **Recovery**: Restore service; verify integrity; confirm monitoring active
7. **Post-incident review**: Root cause analysis within 5 business days; update threat model
8. **Regulatory notification**: If PHI-adjacent data breached → HIPAA breach notification; if MDR-reportable → 21 CFR Part 803

### 7.3 MDR Reporting Consideration
If a cybersecurity incident causes or contributes to patient harm, or causes the device to malfunction in a way that could cause harm, a Medical Device Report (MDR) must be filed per 21 CFR Part 803. Regulatory Affairs must be notified of all P0 and P1 incidents to make this determination.

---

## 8. Patch Management Timeline

See Section 5.2. Additional notes:
- Emergency patches (Critical CVEs) bypass standard release cycle; deployed via hotfix branch after minimal regression testing
- All patches accompanied by updated SBOM
- Patch history maintained in security changelog (7-year retention)
- Customers notified of Critical and High patches within 24 hours of deployment

---

## 9. Cybersecurity Labeling Elements

Per FDA 2023 guidance, the following cybersecurity information must be included in device labeling:

### 9.1 Required Labeling Elements
| Element | LumenAI Implementation |
|---------|----------------------|
| Device hardware/software configuration | Architecture documented in software-lifecycle-readiness.md; SOUP list included |
| Known vulnerabilities and unresolved anomalies | Security changelog; SBOM |
| Cybersecurity contact information | security@lumenai.com |
| SBOM availability statement | "SBOM available on request; generated at every build via CycloneDX" |
| End of support timeline | v1.0 security support through [TBD — minimum 5 years from release] |
| Supported operating environments | See technical specifications |

### 9.2 Labeling Text (Draft)
```
CYBERSECURITY NOTICE: LumenAI is a networked software system. Users should:
- Ensure the system is deployed only on secured networks behind organizational firewalls
- Enable MFA for all user accounts (required for Manager and Admin roles)
- Apply all security patches within the timelines specified in the LumenAI Security Policy
- Report cybersecurity vulnerabilities to security@lumenai.com
- Contact your IT security team if any unauthorized access to the system is suspected

A Software Bill of Materials (SBOM) is available on request.
```

---

## 10. Post-Market Cybersecurity Monitoring

| Activity | Frequency | Responsible | Output |
|---------|----------|------------|--------|
| Dependency vulnerability review | Continuous (automated) | Engineering | Dependabot alerts |
| NVD/CISA review | Weekly | Security Lead | Security bulletin |
| SBOM refresh | Every build | CI/CD (automated) | Updated SBOM artifact |
| Penetration test | Annual | Third-party firm | Pentest report |
| Threat model review | Annual | Security Lead + Regulatory | Updated threat model |
| Incident trend analysis | Quarterly | Security Lead | Quarterly security report |
| Cybersecurity risk management review | Annual | Regulatory Affairs | Updated risk management file (cybersecurity section) |

---

## 11. Unresolved Cybersecurity Gaps and Mitigations

| Gap | Risk Level | Planned Mitigation | Target Date |
|----|-----------|-------------------|------------|
| External penetration test not yet conducted | Medium | Engage third-party pentest firm | Q2 2026 |
| DAST (OWASP ZAP) not yet implemented in CI | Medium | Add to GitHub Actions pipeline | Q1 2026 |
| Container image scanning (Trivy) not yet in CI | Medium | Add to GitHub Actions pipeline | Q1 2026 |
| MFA not yet mandatory for Technician role | Low | Implement in v1.1 | Q3 2026 |
| Certificate pinning for API clients not implemented | Low | Implement in v1.1 | Q3 2026 |
| Infrastructure security audit (Checkov) pending | Low | Execute as part of Q2 2026 review | Q2 2026 |

**None of the above gaps are assessed as blocking go-live**, as compensating controls are in place (rate limiting, RBAC, tenant isolation, monitoring). However, the external penetration test and DAST should be completed before commercial launch to identify any unknown vulnerabilities.

These gaps are documented as open risk items in the risk management file and will be tracked to closure prior to 510(k) submission.

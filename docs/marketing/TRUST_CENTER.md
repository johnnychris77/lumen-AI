# Trust Center (reference)

Backs the `/trust` page. Describes **design intent + implemented controls**, not
third-party attestations.

| Area | Approach |
|---|---|
| Authentication | Authenticated identity required; no shared dev tokens in production. |
| Authorization | Role-based, **server-enforced**; client never trusted for authz. |
| Tenant isolation | Tenants cannot see each other's raw data; enforced in the data layer. |
| Encryption | HTTPS transport; secrets in environment config, never in source. |
| Audit logging | Evidence/decisions/actions appended to a hash-chained audit trail. |
| Evidence integrity | Each stage adds to the record; baselines are governed records. |
| Responsible AI | Assistive/non-autonomous; correlation outputs carry a human-review requirement. |
| Human oversight | Uncertain/higher-risk findings route to a qualified reviewer. |
| Data governance | No PHI in demos; production data governed by customer agreements. |

**Not claimed:** FDA clearance, HIPAA, SOC 2, or any cybersecurity/regulatory
certification. Compliance posture is established with the customer and the
appropriate authorities.

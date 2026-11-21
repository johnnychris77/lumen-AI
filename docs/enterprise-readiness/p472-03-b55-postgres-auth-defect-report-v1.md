# P472-03 B5.5 — PostgreSQL `users.username` Defect Report (v1)

**Issue #187 · PR #181 (DRAFT) · Risk R-PG-USERS.** Fixed in code, **not closed** — pending independent review.

## Defect
`app/routers/auth_simple.py` queried columns that do not exist in the canonical `users` table:

| Function | Query (before) | Canonical schema (ORM `app/models/user.py`; Alembic `4b336d3ed612`) |
|---|---|---|
| `_user_role` | `SELECT role FROM users WHERE LOWER(username)=…` | `users(email, hashed_password, role)` |
| `_verify_user` | `SELECT username, password_hash FROM users WHERE LOWER(username)=…` | — (`username`/`password_hash` exist only on `admin_credentials`) |

Every call raised and the exception was swallowed (`except Exception: pass`). `_user_role` is called by
**every** authentication path (`deps.get_current_user`, `auth.get_current_user`, `enterprise_auth` ×2,
`enterprise_access_control`) — always with the **validated JWT `sub`**, never a client-supplied identity
(verified). Effects:
* a role stored on the user's `users` row was never applied (fell back to `viewer` whenever no
  role-assignment row existed) — fail-closed, but a broken query was indistinguishable from "no role";
* PostgreSQL logged an `ERROR` per call (2,450 in CI job `135840665397`; 54,493 in the local server log
  across runs), with nothing in the application log;
* case-variant assignment rows with different roles were resolved by an arbitrary `fetchone()`;
* `_verify_user` (legacy users-table login) always raised → `/api/auth/login` returned 401.

## Reproduction (before the fix, commit `189094d`)
`tests/test_p472_03_batch5_auth_role_lookup.py`: **6 failed / 7 passed on SQLite and on PostgreSQL 16.15**
(stored role ignored ×2, ambiguous case variants, swallowed error, JWT principal role, legacy login raising).

## Fix
* `_user_role`: assignment table, then `users.role` **by `email`**; exact-case match wins; case-variant rows
  that disagree → logged, fail closed to `viewer`; any database error → **logged with traceback**, fail
  closed to `viewer`; empty identity → `viewer`.
* `_verify_user`: **explicitly disabled** and logged (returns `None` → 401). It never authenticated anyone
  against the canonical schema and no mounted code creates `users` rows; enabling it would add an
  unreviewed credential source. Decision **AUTH-1** (authentication owner): enable users-table login or
  remove it.

## Results (after)
| Run | Result |
|---|---|
| B5.5 tests, SQLite | 13/13 |
| B5.5 + B5.1 tests, PostgreSQL 16.15 | 36/36; **0** application-issued `column "username" does not exist` errors (the single logged one is the test's deliberate schema probe `SELECT username FROM users WHERE 1=0`) |
| Existing login/auth/role suites (10 files) | 303/303 |

## Contract changes (for the authentication owner)
1. A principal with a `users` row and **no** role-assignment row now receives `users.role` instead of
   `viewer`. This is the documented resolution order; it can raise a principal's role if such rows exist in
   a deployed database. **No production data was examined** — the owner should inventory `users.role`
   values before deployment.
2. Case-variant role-assignment rows that disagree now resolve to `viewer` (the exact-case principal still
   gets its own row).
3. Legacy users-table password login remains unavailable (unchanged effective behaviour, now explicit).

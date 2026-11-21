/**
 * Decision logic for `audit-allowlist.mjs`, kept separate so it can be unit
 * tested without running `npm audit` (see tests/auditPolicy.test.mts).
 *
 * An allow-list entry is either
 *   - a string: an unconditional, documented exception (the original form), or
 *   - an object: a CONDITIONAL exception that lapses by itself:
 *       reason             required justification
 *       reviewBy           "YYYY-MM-DD"; after this day the entry no longer
 *                          applies and the gate fails until it is re-triaged
 *       onlyWhileUnpatched true: the entry stops applying as soon as npm
 *                          reports a non-breaking fix for the package
 */

/**
 * @param {string | {reason?: string, reviewBy?: string, onlyWhileUnpatched?: boolean}} entry
 * @param {{ now: number, fixAvailable: unknown }} context  `fixAvailable` is the
 *        value npm audit reports for the vulnerable package: `true` means a
 *        non-breaking fix exists; an object means only a semver-major change of
 *        a direct dependency would clear it; `false` means none.
 * @returns {{ applies: true, reason: string } | { applies: false, why: string }}
 */
export function allowlistDecision(entry, { now, fixAvailable }) {
  if (typeof entry === "string") {
    return entry.trim()
      ? { applies: true, reason: entry }
      : { applies: false, why: "the allow-list entry has no justification" };
  }
  if (!entry || typeof entry.reason !== "string" || !entry.reason.trim()) {
    return { applies: false, why: "the allow-list entry has no justification" };
  }
  if (entry.reviewBy !== undefined) {
    const due = Date.parse(`${entry.reviewBy}T23:59:59Z`);
    if (Number.isNaN(due)) {
      return { applies: false, why: `the allow-list entry has an invalid reviewBy date (${entry.reviewBy})` };
    }
    if (now > due) {
      return {
        applies: false,
        why: `the documented exception was due for review on ${entry.reviewBy} — re-triage it`,
      };
    }
  }
  if (entry.onlyWhileUnpatched && fixAvailable === true) {
    return {
      applies: false,
      why: "a non-breaking fix is now available — upgrade instead of relying on the exception",
    };
  }
  return { applies: true, reason: entry.reason };
}

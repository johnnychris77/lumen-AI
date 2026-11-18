/**
 * The dependency-audit gate's exception policy (scripts/audit-policy.mjs).
 *
 * A conditional allow-list entry must stop applying by itself — when its review
 * date passes, or when a non-breaking fix exists — so a documented exception
 * can never silently outlive its justification.
 */
import assert from "node:assert/strict";
import { test } from "node:test";

// @ts-expect-error - plain .mjs module without type declarations
import { allowlistDecision } from "../scripts/audit-policy.mjs";

const DAY = 24 * 60 * 60 * 1000;
const at = (iso: string) => Date.parse(iso);
const conditional = { reason: "not reachable", reviewBy: "2026-12-18", onlyWhileUnpatched: true };
// What npm audit reports while only a semver-major change would clear the advisory.
const majorOnly = { name: "vite", version: "6.2.7", isSemVerMajor: true };

test("an unconditional string entry applies", () => {
  assert.deepEqual(
    allowlistDecision("documented reason", { now: at("2030-01-01T00:00:00Z"), fixAvailable: true }),
    { applies: true, reason: "documented reason" },
  );
});

test("a conditional entry applies before its review date while no fix exists", () => {
  for (const fixAvailable of [false, majorOnly, undefined]) {
    const decision = allowlistDecision(conditional, { now: at("2026-11-18T12:00:00Z"), fixAvailable });
    assert.deepEqual(decision, { applies: true, reason: "not reachable" });
  }
});

test("a conditional entry applies through the whole review day and lapses the day after", () => {
  const lastMoment = allowlistDecision(conditional, { now: at("2026-12-18T23:59:00Z"), fixAvailable: false });
  assert.equal(lastMoment.applies, true);
  const nextDay = allowlistDecision(conditional, { now: at("2026-12-18T23:59:00Z") + DAY, fixAvailable: false });
  assert.equal(nextDay.applies, false);
  assert.match(nextDay.why, /2026-12-18/);
});

test("a conditional entry lapses as soon as a non-breaking fix is available", () => {
  const decision = allowlistDecision(conditional, { now: at("2026-11-18T12:00:00Z"), fixAvailable: true });
  assert.equal(decision.applies, false);
  assert.match(decision.why, /fix is now available/);
});

test("an entry without onlyWhileUnpatched does not lapse on a fix, only on its date", () => {
  const entry = { reason: "r", reviewBy: "2026-12-18" };
  assert.equal(allowlistDecision(entry, { now: at("2026-11-18T00:00:00Z"), fixAvailable: true }).applies, true);
  assert.equal(allowlistDecision(entry, { now: at("2027-01-01T00:00:00Z"), fixAvailable: true }).applies, false);
});

test("an entry with no justification never applies", () => {
  for (const entry of ["", "   ", {}, { reason: "" }, { reviewBy: "2099-01-01" }, null, undefined]) {
    const decision = allowlistDecision(entry as never, { now: at("2026-11-18T00:00:00Z"), fixAvailable: false });
    assert.equal(decision.applies, false);
  }
});

test("an unparseable review date fails closed", () => {
  const decision = allowlistDecision(
    { reason: "r", reviewBy: "next quarter" }, { now: at("2026-11-18T00:00:00Z"), fixAvailable: false });
  assert.equal(decision.applies, false);
});

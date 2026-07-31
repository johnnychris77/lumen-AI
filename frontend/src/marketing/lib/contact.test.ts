/**
 * Unit tests for the contact form schema + mock submission.
 * Run with Vitest (see docs/marketing/DEPLOYMENT_GUIDE.md).
 */
import { describe, it, expect } from "vitest";
import { AREAS_OF_INTEREST, contactSchema, submitContact } from "./contact";

const valid = {
  name: "Jordan Lee",
  organization: "Example Health",
  role: "SPD Manager",
  email: "jordan@example.org",
  interest: AREAS_OF_INTEREST[0],
  consent: true as const,
};

describe("contactSchema", () => {
  it("accepts a valid submission", () => {
    expect(contactSchema.safeParse(valid).success).toBe(true);
  });

  it("rejects an invalid email", () => {
    expect(contactSchema.safeParse({ ...valid, email: "nope" }).success).toBe(false);
  });

  it("requires consent to be true", () => {
    const r = contactSchema.safeParse({ ...valid, consent: false });
    expect(r.success).toBe(false);
  });

  it("rejects a short name/organization", () => {
    expect(contactSchema.safeParse({ ...valid, name: "" }).success).toBe(false);
    expect(contactSchema.safeParse({ ...valid, organization: "" }).success).toBe(false);
  });
});

describe("submitContact (mock mode)", () => {
  it("returns a mock reference when no endpoint is configured", async () => {
    const r = await submitContact({ ...valid });
    expect(r.ok).toBe(true);
    if (r.ok) {
      expect(r.mode).toBe("mock");
      expect(r.reference).toMatch(/^LMN-/);
    }
  });

  it("silently ignores a tripped honeypot", async () => {
    const r = await submitContact({ ...valid, company_website: "spam" });
    expect(r.ok).toBe(true);
    if (r.ok) expect(r.reference).toBe("IGNORED");
  });
});

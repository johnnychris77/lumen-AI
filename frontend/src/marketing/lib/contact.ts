/**
 * Contact / demo-request form schema and submission adapter.
 *
 * Uses zod (already a project dependency). Submission runs in MOCK mode unless
 * a secure endpoint is configured via `VITE_CONTACT_ENDPOINT` — there is no
 * embedded mail relay and no credentials in source. See
 * docs/marketing/DEPLOYMENT_GUIDE.md for wiring a real provider.
 */
import { z } from "zod";

export const AREAS_OF_INTEREST = [
  "Request a demonstration",
  "Discuss a pilot",
  "Join the product-validation program",
  "Partnership / investment",
  "General question",
] as const;

export const contactSchema = z.object({
  name: z.string().trim().min(2, "Please enter your name."),
  organization: z.string().trim().min(2, "Please enter your organization."),
  role: z.string().trim().min(2, "Please enter your role."),
  email: z.string().trim().email("Please enter a valid email address."),
  interest: z.enum(AREAS_OF_INTEREST, {
    // zod v4 uses `message` for enum mismatch
    message: "Please choose an area of interest.",
  }),
  message: z.string().trim().max(2000, "Please keep the message under 2000 characters.").optional(),
  // Honeypot — must stay empty. Basic spam protection placeholder.
  company_website: z.string().max(0).optional(),
  consent: z.literal(true, { message: "Please acknowledge the consent notice." }),
});

export type ContactFormValues = z.infer<typeof contactSchema>;

export type SubmitResult =
  | { ok: true; mode: "mock" | "live"; reference: string }
  | { ok: false; error: string };

const endpoint = (import.meta.env.VITE_CONTACT_ENDPOINT as string | undefined) || "";

export async function submitContact(values: ContactFormValues): Promise<SubmitResult> {
  // Honeypot tripped → silently succeed without doing anything.
  if (values.company_website) {
    return { ok: true, mode: "mock", reference: "IGNORED" };
  }

  const reference = `LMN-${Date.now().toString(36).toUpperCase()}`;

  if (!endpoint) {
    // MOCK mode: no network call, safe to ship publicly.
    if (import.meta.env.DEV) {
      // eslint-disable-next-line no-console
      console.info("[contact:mock] submission", { ...values, reference });
    }
    return { ok: true, mode: "mock", reference };
  }

  try {
    const res = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...values, reference, source: "lumenai-marketing" }),
    });
    if (!res.ok) return { ok: false, error: `Submission failed (${res.status}).` };
    return { ok: true, mode: "live", reference };
  } catch {
    return { ok: false, error: "Network error — please try again or email us directly." };
  }
}

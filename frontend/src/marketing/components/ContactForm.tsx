import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { CheckCircle2, AlertCircle } from "lucide-react";
import {
  AREAS_OF_INTEREST,
  ContactFormValues,
  contactSchema,
  submitContact,
  SubmitResult,
} from "../lib/contact";
import { track } from "../lib/analytics";

const fieldClass =
  "mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/30";
const labelClass = "block text-sm font-medium text-slate-700";
const errClass = "mt-1 text-xs text-danger";

export function ContactForm() {
  const [result, setResult] = useState<SubmitResult | null>(null);
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<ContactFormValues>({
    resolver: zodResolver(contactSchema),
    defaultValues: { interest: AREAS_OF_INTEREST[0] },
  });

  const onSubmit = async (values: ContactFormValues) => {
    const r = await submitContact(values);
    setResult(r);
    if (r.ok) {
      track("contact_submit", { mode: r.mode, interest: values.interest });
      reset();
    }
  };

  if (result?.ok) {
    return (
      <div role="status" className="rounded-xl border border-success/30 bg-success-subtle p-6 text-center">
        <CheckCircle2 className="mx-auto mb-3 text-success" size={32} aria-hidden />
        <h3 className="text-lg font-semibold text-slate-900">Thank you — we&apos;ve received your request.</h3>
        <p className="mt-1 text-sm text-slate-600">
          Reference <span className="font-mono">{result.reference}</span>. A member of the LumenAI team will
          follow up.
        </p>
        {result.mode === "mock" && (
          <p className="mt-3 text-xs text-slate-500">
            (Demo mode — no message was sent. Configure a secure endpoint to enable live delivery.)
          </p>
        )}
        <button
          type="button"
          onClick={() => setResult(null)}
          className="mt-4 text-sm font-medium text-primary hover:text-primary-hover"
        >
          Submit another request
        </button>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-4">
      {result && !result.ok && (
        <div role="alert" className="flex items-center gap-2 rounded-md bg-danger-subtle p-3 text-sm text-danger">
          <AlertCircle size={16} aria-hidden /> {result.error}
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <label htmlFor="c-name" className={labelClass}>Name</label>
          <input id="c-name" autoComplete="name" className={fieldClass} {...register("name")} aria-invalid={!!errors.name} />
          {errors.name && <p className={errClass}>{errors.name.message}</p>}
        </div>
        <div>
          <label htmlFor="c-org" className={labelClass}>Organization</label>
          <input id="c-org" autoComplete="organization" className={fieldClass} {...register("organization")} aria-invalid={!!errors.organization} />
          {errors.organization && <p className={errClass}>{errors.organization.message}</p>}
        </div>
        <div>
          <label htmlFor="c-role" className={labelClass}>Role</label>
          <input id="c-role" autoComplete="organization-title" className={fieldClass} {...register("role")} aria-invalid={!!errors.role} />
          {errors.role && <p className={errClass}>{errors.role.message}</p>}
        </div>
        <div>
          <label htmlFor="c-email" className={labelClass}>Work email</label>
          <input id="c-email" type="email" autoComplete="email" className={fieldClass} {...register("email")} aria-invalid={!!errors.email} />
          {errors.email && <p className={errClass}>{errors.email.message}</p>}
        </div>
      </div>

      <div>
        <label htmlFor="c-interest" className={labelClass}>Area of interest</label>
        <select id="c-interest" className={fieldClass} {...register("interest")} aria-invalid={!!errors.interest}>
          {AREAS_OF_INTEREST.map((a) => (
            <option key={a} value={a}>{a}</option>
          ))}
        </select>
        {errors.interest && <p className={errClass}>{errors.interest.message}</p>}
      </div>

      <div>
        <label htmlFor="c-message" className={labelClass}>Message <span className="text-slate-400">(optional)</span></label>
        <textarea id="c-message" rows={4} className={fieldClass} {...register("message")} aria-invalid={!!errors.message} />
        {errors.message && <p className={errClass}>{errors.message.message}</p>}
      </div>

      {/* Honeypot — visually hidden, must stay empty. */}
      <div aria-hidden className="absolute left-[-9999px] h-0 w-0 overflow-hidden">
        <label htmlFor="c-website">Company website</label>
        <input id="c-website" tabIndex={-1} autoComplete="off" {...register("company_website")} />
      </div>

      <div className="flex items-start gap-2">
        <input id="c-consent" type="checkbox" className="mt-1 h-4 w-4 rounded border-slate-300 text-primary focus:ring-primary" {...register("consent")} aria-invalid={!!errors.consent} />
        <label htmlFor="c-consent" className="text-xs leading-relaxed text-slate-600">
          I agree to be contacted about LumenAI and understand my details are used only to respond to
          this request. No protected health information should be submitted through this form.
        </label>
      </div>
      {errors.consent && <p className={errClass}>{errors.consent.message}</p>}

      <button
        type="submit"
        disabled={isSubmitting}
        className="inline-flex h-11 w-full items-center justify-center rounded-md bg-primary px-6 text-base font-medium text-white transition-colors hover:bg-primary-hover disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 sm:w-auto"
      >
        {isSubmitting ? "Sending…" : "Send request"}
      </button>
    </form>
  );
}

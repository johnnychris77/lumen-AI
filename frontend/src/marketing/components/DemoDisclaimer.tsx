import { AlertTriangle } from "lucide-react";

/** Persistent, unmissable label for all synthetic demonstration content. */
export function DemoDisclaimer({ className = "" }: { className?: string }) {
  return (
    <div
      role="note"
      aria-label="Demonstration data notice"
      className={`flex items-center gap-2 rounded-md border border-warning/40 bg-warning-subtle px-3 py-2 text-xs font-semibold text-warning ${className}`}
    >
      <AlertTriangle size={14} aria-hidden className="shrink-0" />
      <span>Demonstration Data — Not for Clinical Use. Synthetic content; no PHI.</span>
    </div>
  );
}

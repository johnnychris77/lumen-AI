import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { apiFetch } from "@/lib/api";
import { useAuth } from "@/lib/auth";

// v2.5 — Supervisor Rule Builder (Project Cortex, Section 7). Governed,
// versioned clinical decision rules a supervisor authors — organization
// rules, local best practices, escalation thresholds, education rules.

const RULE_TYPES = [
  { value: "organization_rule", label: "Organization Rule" },
  { value: "local_best_practice", label: "Local Best Practice" },
  { value: "escalation_threshold", label: "Escalation Threshold" },
  { value: "education_rule", label: "Education Rule" },
] as const;

type RuleType = (typeof RULE_TYPES)[number]["value"];

interface Rule {
  id: number;
  rule_type: string;
  title: string;
  description: string;
  evidence: {
    finding_types: string[];
    zone_keywords: string[];
    requires_high_risk_zone: boolean;
    requires_repeat_finding: boolean;
    min_repeat_occurrences: number;
  };
  severity: string;
  spd_risk: string;
  recommendation: string[];
  is_active: boolean;
  version: number;
}

const RISK_TAG: Record<string, string> = {
  Low: "bg-emerald-50 text-emerald-800 border-emerald-200",
  Moderate: "bg-amber-50 text-amber-800 border-amber-200",
  High: "bg-orange-50 text-orange-800 border-orange-200",
  Critical: "bg-red-50 text-red-800 border-red-200",
};

const emptyForm = {
  rule_type: "local_best_practice" as RuleType,
  title: "",
  description: "",
  finding_type: "",
  zone_keyword: "",
  requires_high_risk_zone: false,
  requires_repeat_finding: false,
  min_repeat_occurrences: 0,
  severity: "Moderate",
  spd_risk: "Moderate",
  recommendation: "",
};

export default function SupervisorRuleBuilderPage() {
  const { role } = useAuth();
  const canAuthor = role === "admin" || role === "spd_manager" || role === "supervisor";
  const [rules, setRules] = useState<Rule[]>([]);
  const [form, setForm] = useState(emptyForm);
  const [submitting, setSubmitting] = useState(false);
  const [banner, setBanner] = useState<{ type: "success" | "error"; message: string } | null>(null);

  const load = () => {
    apiFetch<{ rules: Rule[] }>("/api/decision-rules").then((d) => setRules(d.rules)).catch(() => {});
  };

  useEffect(() => { load(); }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setBanner(null);
    try {
      await apiFetch("/api/decision-rules", {
        method: "POST",
        body: {
          ...form,
          recommendation: form.recommendation.split(",").map((r) => r.trim()).filter(Boolean),
        },
      });
      setBanner({ type: "success", message: "Rule created." });
      setForm(emptyForm);
      load();
    } catch {
      setBanner({ type: "error", message: "Failed to create the rule." });
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDeactivate(id: number) {
    try {
      await apiFetch(`/api/decision-rules/${id}/deactivate`, { method: "POST" });
      load();
    } catch {
      setBanner({ type: "error", message: "Failed to deactivate the rule." });
    }
  }

  return (
    <div className="max-w-4xl mx-auto px-4 py-6 space-y-6">
      <div>
        <h1 className="text-xl font-bold text-slate-900">Supervisor Rule Builder</h1>
        <p className="text-sm text-slate-500 mt-1">
          Author governed, versioned clinical decision rules — organization rules, local best practices,
          escalation thresholds, education rules. Every edit creates a new version rather than overwriting history.{" "}
          <Link to="/knowledge-graph" className="text-blue-600 hover:underline">View the SPD Rule Library →</Link>
        </p>
      </div>

      {!canAuthor && (
        <p className="text-sm text-amber-800 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">
          Viewer/operator access is read-only here. Ask an admin, SPD manager, or supervisor to author rules.
        </p>
      )}

      {canAuthor && (
        <form onSubmit={handleSubmit} className="rounded-lg border border-slate-200 bg-white p-4 space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">Rule Type</label>
              <select
                value={form.rule_type}
                onChange={(e) => setForm((f) => ({ ...f, rule_type: e.target.value as RuleType }))}
                className="w-full rounded border border-slate-300 px-2 py-1.5 text-sm"
              >
                {RULE_TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">Title</label>
              <input
                required value={form.title} onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))}
                className="w-full rounded border border-slate-300 px-2 py-1.5 text-sm" placeholder="e.g. Focused reclean for repeat corrosion"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Description</label>
            <textarea
              value={form.description} onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
              rows={2} className="w-full rounded border border-slate-300 px-2 py-1.5 text-sm"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">Finding Type (optional)</label>
              <input
                value={form.finding_type} onChange={(e) => setForm((f) => ({ ...f, finding_type: e.target.value }))}
                className="w-full rounded border border-slate-300 px-2 py-1.5 text-sm" placeholder="e.g. blood"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">Zone Keyword (optional)</label>
              <input
                value={form.zone_keyword} onChange={(e) => setForm((f) => ({ ...f, zone_keyword: e.target.value }))}
                className="w-full rounded border border-slate-300 px-2 py-1.5 text-sm" placeholder="e.g. serration"
              />
            </div>
          </div>

          <div className="flex flex-wrap gap-4">
            <label className="flex items-center gap-2 text-sm text-slate-700">
              <input type="checkbox" checked={form.requires_high_risk_zone} onChange={(e) => setForm((f) => ({ ...f, requires_high_risk_zone: e.target.checked }))} />
              Requires high-risk zone
            </label>
            <label className="flex items-center gap-2 text-sm text-slate-700">
              <input type="checkbox" checked={form.requires_repeat_finding} onChange={(e) => setForm((f) => ({ ...f, requires_repeat_finding: e.target.checked }))} />
              Requires repeat finding
            </label>
            <label className="flex items-center gap-2 text-sm text-slate-700">
              Min repeat occurrences
              <input
                type="number" min={0} value={form.min_repeat_occurrences}
                onChange={(e) => setForm((f) => ({ ...f, min_repeat_occurrences: Number(e.target.value) }))}
                className="w-16 rounded border border-slate-300 px-2 py-1 text-sm"
              />
            </label>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">Severity</label>
              <select value={form.severity} onChange={(e) => setForm((f) => ({ ...f, severity: e.target.value }))} className="w-full rounded border border-slate-300 px-2 py-1.5 text-sm">
                {["Low", "Moderate", "High", "Critical"].map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">SPD Risk</label>
              <select value={form.spd_risk} onChange={(e) => setForm((f) => ({ ...f, spd_risk: e.target.value }))} className="w-full rounded border border-slate-300 px-2 py-1.5 text-sm">
                {["Low", "Moderate", "High", "Critical"].map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Recommendation (comma-separated)</label>
            <input
              value={form.recommendation} onChange={(e) => setForm((f) => ({ ...f, recommendation: e.target.value }))}
              className="w-full rounded border border-slate-300 px-2 py-1.5 text-sm" placeholder="Focused reclean, Supervisor review"
            />
          </div>

          {banner && (
            <p className={`text-sm rounded-lg px-3 py-2 ${banner.type === "success" ? "bg-emerald-50 text-emerald-800" : "bg-red-50 text-red-800"}`}>
              {banner.message}
            </p>
          )}

          <button type="submit" disabled={submitting} className="rounded-lg bg-indigo-600 text-white text-sm font-medium px-4 py-2 disabled:opacity-50">
            {submitting ? "Creating…" : "Create Rule"}
          </button>
        </form>
      )}

      <div>
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-3">Active Supervisor Rules</p>
        {rules.length === 0 ? (
          <p className="text-sm text-slate-400">No supervisor-authored rules yet.</p>
        ) : (
          <div className="space-y-2">
            {rules.map((rule) => (
              <div key={rule.id} className="rounded-lg border border-slate-200 bg-white p-3">
                <div className="flex items-center justify-between gap-2">
                  <p className="text-sm font-medium text-slate-800">{rule.title} <span className="text-xs text-slate-400">v{rule.version}</span></p>
                  <div className="flex items-center gap-2">
                    <span className={`text-xs font-medium rounded-full border px-2 py-0.5 ${RISK_TAG[rule.spd_risk] ?? RISK_TAG.Moderate}`}>{rule.spd_risk}</span>
                    {canAuthor && (
                      <button onClick={() => handleDeactivate(rule.id)} className="text-xs text-red-600 hover:underline">Deactivate</button>
                    )}
                  </div>
                </div>
                <p className="text-xs text-slate-500 mt-1">{rule.description}</p>
                <p className="text-xs text-slate-400 mt-1 capitalize">{rule.rule_type.replace(/_/g, " ")}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

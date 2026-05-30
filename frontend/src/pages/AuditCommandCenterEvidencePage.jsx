import React, { useEffect, useState } from "react";

const API_BASE =
  import.meta.env.VITE_API_BASE_URL || "https://lumen-ai-53u4.onrender.com";

const evidenceLinks = [
  {
    label: "Audit PDF",
    path: "/api/enterprise/audit-command-center/pdf",
    type: "application/pdf",
  },
  {
    label: "Audit CSV",
    path: "/api/enterprise/audit-command-center/csv",
    type: "text/csv",
  },
  {
    label: "Power BI CSV",
    path: "/api/enterprise/audit-command-center/powerbi-csv",
    type: "text/csv",
  },
  {
    label: "Data Dictionary PDF",
    path: "/api/enterprise/audit-command-center/data-dictionary/pdf",
    type: "application/pdf",
  },
  {
    label: "Toolkit ZIP",
    path: "/api/enterprise/audit-command-center/toolkit.zip",
    type: "application/zip",
  },
];

export default function AuditCommandCenterEvidencePage() {
  const [health, setHealth] = useState(null);
  const [loading, setLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState("");

  useEffect(() => {
    async function loadHealth() {
      try {
        setLoading(true);
        setErrorMessage("");

        const response = await fetch(
          `${API_BASE}/api/enterprise/audit-command-center/health`
        );

        if (!response.ok) {
          throw new Error(`Health endpoint returned ${response.status}`);
        }

        const data = await response.json();
        setHealth(data);
      } catch (error) {
        setErrorMessage(error.message || "Unable to load validation health.");
      } finally {
        setLoading(false);
      }
    }

    loadHealth();
  }, []);

  const status = health?.status || "unknown";
  const passed = health?.passed ?? 0;
  const failed = health?.failed ?? 0;
  const warnings = health?.warnings ?? 0;
  const totalChecks = health?.total_checks ?? 0;
  const auditEvents = health?.audit_events ?? 0;
  const highValueEvents = health?.high_value_events ?? 0;

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      <div className="mx-auto max-w-7xl px-6 py-10">
        <div className="mb-8 rounded-3xl border border-emerald-400/30 bg-gradient-to-br from-slate-900 to-slate-950 p-8 shadow-2xl">
          <div className="mb-4 inline-flex rounded-full border border-emerald-400/40 bg-emerald-400/10 px-4 py-2 text-sm font-semibold text-emerald-300">
            Portfolio Evidence Page · Production Validated
          </div>

          <h1 className="text-4xl font-bold tracking-tight md:text-5xl">
            LumenAI Enterprise Audit Command Center
          </h1>

          <p className="mt-4 max-w-4xl text-lg text-slate-300">
            A production-validated governance and audit-readiness module for
            centralized visibility, export traceability, Power BI analytics,
            compliance evidence review, and leadership reporting.
          </p>

          <div className="mt-8 grid gap-4 md:grid-cols-4">
            <MetricCard
              label="Validation Status"
              value={status.toUpperCase()}
              helper="Production health endpoint"
            />
            <MetricCard
              label="Checks Passed"
              value={`${passed}/${totalChecks}`}
              helper="Automated readiness checks"
            />
            <MetricCard
              label="Failed / Warnings"
              value={`${failed} / ${warnings}`}
              helper="Expected: 0 / 0"
            />
            <MetricCard
              label="Toolkit Version"
              value={health?.toolkit_version || "1.0.0"}
              helper="Validation package"
            />
          </div>
        </div>

        {loading && (
          <div className="rounded-2xl border border-slate-700 bg-slate-900 p-6 text-slate-300">
            Loading production validation status...
          </div>
        )}

        {errorMessage && (
          <div className="rounded-2xl border border-red-500/40 bg-red-950/40 p-6 text-red-200">
            Unable to load validation status: {errorMessage}
          </div>
        )}

        {!loading && !errorMessage && (
          <>
            <section className="grid gap-6 lg:grid-cols-3">
              <div className="rounded-3xl border border-slate-800 bg-slate-900 p-6">
                <h2 className="text-xl font-bold">Audit Activity</h2>
                <p className="mt-2 text-sm text-slate-400">
                  Production evidence demonstrates active governance visibility
                  and high-value event tracking.
                </p>

                <div className="mt-6 grid gap-4">
                  <MetricCard
                    label="Audit Events"
                    value={auditEvents}
                    helper="Visible in command center"
                  />
                  <MetricCard
                    label="High-Value Events"
                    value={highValueEvents}
                    helper="Priority governance signals"
                  />
                </div>
              </div>

              <div className="rounded-3xl border border-slate-800 bg-slate-900 p-6 lg:col-span-2">
                <h2 className="text-xl font-bold">Validated Capabilities</h2>
                <p className="mt-2 text-sm text-slate-400">
                  Each capability below is represented in the health endpoint and
                  final validation evidence package.
                </p>

                <div className="mt-6 grid gap-3 md:grid-cols-2">
                  {Object.entries(health?.capabilities || {}).map(
                    ([key, value]) => (
                      <div
                        key={key}
                        className="flex items-center justify-between rounded-2xl border border-slate-800 bg-slate-950 px-4 py-3"
                      >
                        <span className="text-sm capitalize text-slate-300">
                          {key.replaceAll("_", " ")}
                        </span>
                        <span className="rounded-full bg-emerald-400/10 px-3 py-1 text-xs font-semibold text-emerald-300">
                          {String(value).toUpperCase()}
                        </span>
                      </div>
                    )
                  )}
                </div>
              </div>
            </section>

            <section className="mt-8 rounded-3xl border border-slate-800 bg-slate-900 p-6">
              <h2 className="text-xl font-bold">Production Export Evidence</h2>
              <p className="mt-2 text-sm text-slate-400">
                These endpoints were validated with HTTP 200 responses and
                committed as evidence in GitHub.
              </p>

              <div className="mt-6 grid gap-4 md:grid-cols-2 lg:grid-cols-5">
                {evidenceLinks.map((item) => (
                  <a
                    key={item.path}
                    href={`${API_BASE}${item.path}`}
                    className="rounded-2xl border border-slate-800 bg-slate-950 p-4 transition hover:border-emerald-400/60 hover:bg-slate-900"
                  >
                    <div className="text-sm font-semibold text-white">
                      {item.label}
                    </div>
                    <div className="mt-2 text-xs text-slate-400">
                      {item.type}
                    </div>
                    <div className="mt-4 text-xs font-semibold text-emerald-300">
                      Download Evidence →
                    </div>
                  </a>
                ))}
              </div>
            </section>

            <section className="mt-8 grid gap-6 lg:grid-cols-2">
              <div className="rounded-3xl border border-slate-800 bg-slate-900 p-6">
                <h2 className="text-xl font-bold">Executive Readiness</h2>
                <ul className="mt-4 space-y-3 text-sm text-slate-300">
                  <li>✓ Centralized audit command visibility</li>
                  <li>✓ Governance health status</li>
                  <li>✓ Exportable audit evidence</li>
                  <li>✓ Power BI-ready dataset</li>
                  <li>✓ Data dictionary for analytics governance</li>
                  <li>✓ Packaged toolkit for review and validation</li>
                </ul>
              </div>

              <div className="rounded-3xl border border-slate-800 bg-slate-900 p-6">
                <h2 className="text-xl font-bold">Portfolio Statement</h2>
                <p className="mt-4 text-sm leading-6 text-slate-300">
                  Built and validated a production-ready Enterprise Audit Command
                  Center for LumenAI, including health monitoring, audit event
                  visibility, high-value event tracking, executive reporting
                  exports, Power BI CSV output, data dictionary documentation,
                  and a downloadable toolkit ZIP. Final validation evidence was
                  captured, committed, and pushed to GitHub.
                </p>
              </div>
            </section>
          </>
        )}
      </div>
    </div>
  );
}

function MetricCard({ label, value, helper }) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-950 p-5">
      <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
        {label}
      </div>
      <div className="mt-2 text-3xl font-bold text-white">{value}</div>
      {helper && <div className="mt-2 text-xs text-slate-400">{helper}</div>}
    </div>
  );
}

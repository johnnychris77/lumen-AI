from __future__ import annotations

from fastapi import APIRouter, Depends, Header
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db import session as db_session
from app.executive_briefing_dashboard import get_executive_briefing_dashboard_summary


def get_db():
    if hasattr(db_session, "get_db"):
        yield from db_session.get_db()
        return

    if hasattr(db_session, "get_session"):
        yield from db_session.get_session()
        return

    if hasattr(db_session, "SessionLocal"):
        db = db_session.SessionLocal()
        try:
            yield db
        finally:
            db.close()
        return

    raise RuntimeError("No database session provider found in app.db.session")


router = APIRouter(
    prefix="/executive-briefing-dashboard",
    tags=["executive-briefing-dashboard"],
)


@router.get("/summary")
def executive_dashboard_summary(
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_db),
):
    get_current_user(authorization)
    return get_executive_briefing_dashboard_summary(db)


@router.get("/view", response_class=HTMLResponse)
def executive_dashboard_view():
    return """
<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>LumenAI Executive Briefing Dashboard</title>
  <style>
    body { font-family: Arial, sans-serif; background: #f6f7fb; margin: 0; color: #1f2937; }
    header { background: #111827; color: white; padding: 24px 32px; }
    h1 { margin: 0; font-size: 26px; }
    .subtitle { margin-top: 8px; color: #d1d5db; }
    main { padding: 24px 32px; }
    .grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 16px; margin-bottom: 24px; }
    .card { background: white; border-radius: 14px; padding: 18px; box-shadow: 0 8px 18px rgba(15,23,42,0.08); }
    .metric { font-size: 30px; font-weight: 700; margin-top: 8px; }
    .label { color: #6b7280; font-size: 13px; text-transform: uppercase; letter-spacing: 0.05em; }
    section { margin-bottom: 24px; }
    table { width: 100%; border-collapse: collapse; background: white; border-radius: 14px; overflow: hidden; box-shadow: 0 8px 18px rgba(15,23,42,0.08); }
    th, td { padding: 12px 14px; border-bottom: 1px solid #e5e7eb; text-align: left; font-size: 14px; vertical-align: top; }
    th { background: #f3f4f6; color: #374151; }
    .status-sent { color: #047857; font-weight: 700; }
    .status-retry_pending { color: #b45309; font-weight: 700; }
    .status-failed { color: #b91c1c; font-weight: 700; }
    button { background: #111827; color: white; border: 0; padding: 10px 14px; border-radius: 10px; cursor: pointer; }
    button:hover { background: #374151; }
    .toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 18px; }
    .muted { color: #6b7280; font-size: 13px; }
    a { color: #2563eb; text-decoration: none; }
    .error { background: #fff1f2; color: #991b1b; padding: 14px; border-radius: 12px; margin-bottom: 16px; display: none; }
    @media (max-width: 1000px) { .grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
    @media (max-width: 640px) { .grid { grid-template-columns: 1fr; } main { padding: 18px; } }
  </style>
</head>
<body>
  <header>
    <h1>LumenAI Executive Briefing Dashboard</h1>
    <div class="subtitle">Board briefing schedules, generated packages, exports, and delivery status</div>
  </header>

  <main>
    <div class="toolbar">
      <div>
        <strong>Environment:</strong> local API
        <div class="muted">Using Authorization: Bearer dev-token</div>
      </div>
      <button onclick="loadDashboard()">Refresh Dashboard</button>
    </div>

    <div id="error" class="error"></div>

    <div class="grid" id="metrics"></div>

    <section>
      <h2>Recent Deliveries</h2>
      <div id="deliveries"></div>
    </section>

    <section>
      <h2>Retry Pending Deliveries</h2>
      <div id="retryPending"></div>
    </section>

    <section>
      <h2>Recent Exports</h2>
      <div id="exports"></div>
    </section>

    <section>
      <h2>Recent Schedules</h2>
      <div id="schedules"></div>
    </section>

    <section>
      <h2>Recent Briefings</h2>
      <div id="briefings"></div>
    </section>

    <section>
      <h2>Generated Artifacts</h2>
      <div id="artifacts"></div>
    </section>
  </main>

<script>
const token = localStorage.getItem("lumenai_token") || "dev-token";

function esc(value) {
  if (value === null || value === undefined) return "";
  return String(value).replace(/[&<>"']/g, s => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;"
  }[s]));
}

function metricCard(label, value) {
  return `<div class="card"><div class="label">${esc(label)}</div><div class="metric">${esc(value)}</div></div>`;
}

function table(rows, columns) {
  if (!rows || rows.length === 0) return `<div class="card muted">No records found.</div>`;

  return `
    <table>
      <thead>
        <tr>${columns.map(c => `<th>${esc(c.label)}</th>`).join("")}</tr>
      </thead>
      <tbody>
        ${rows.map(row => `
          <tr>
            ${columns.map(c => {
              let value = c.render ? c.render(row) : row[c.key];
              return `<td>${value}</td>`;
            }).join("")}
          </tr>
        `).join("")}
      </tbody>
    </table>
  `;
}

function artifactLinks(row) {
  const id = row.id;
  return `
    <a href="/api/portfolio-briefings/exports/${id}/docx" target="_blank">DOCX</a> |
    <a href="/api/portfolio-briefings/exports/${id}/pptx" target="_blank">PPTX</a> |
    <a href="/api/portfolio-briefings/exports/${id}/pdf" target="_blank">PDF</a>
  `;
}

async function retryDelivery(id) {
  const response = await fetch(`/api/portfolio-briefing-deliveries/${id}/retry`, {
    method: "POST",
    headers: { "Authorization": `Bearer ${token}` }
  });

  if (!response.ok) {
    alert(`Retry failed: ${response.status}`);
    return;
  }

  await loadDashboard();
}

async function loadDashboard() {
  const errorBox = document.getElementById("error");
  errorBox.style.display = "none";
  errorBox.textContent = "";

  try {
    const response = await fetch("/api/executive-briefing-dashboard/summary", {
      headers: { "Authorization": `Bearer ${token}` }
    });

    if (!response.ok) throw new Error(`HTTP ${response.status}`);

    const data = await response.json();
    const counts = data.counts || {};

    document.getElementById("metrics").innerHTML = [
      metricCard("Schedules", counts.schedules || 0),
      metricCard("Enabled", counts.enabled_schedules || 0),
      metricCard("Briefings", counts.briefings || 0),
      metricCard("Exports", counts.exports || 0),
      metricCard("Deliveries", counts.deliveries || 0),
      metricCard("Sent", counts.sent_deliveries || 0),
      metricCard("Retry Pending", counts.retry_pending_deliveries || 0),
      metricCard("Artifacts", data.artifacts?.file_count || 0),
    ].join("");

    document.getElementById("deliveries").innerHTML = table(data.recent_deliveries, [
      { key: "id", label: "ID" },
      { key: "briefing_id", label: "Briefing" },
      { key: "export_id", label: "Export" },
      { key: "delivery_channel", label: "Channel" },
      { key: "delivery_target", label: "Target", render: r => esc(r.delivery_target).slice(0, 70) },
      { key: "status", label: "Status", render: r => `<span class="status-${esc(r.status)}">${esc(r.status)}</span>` },
      { key: "attempt_count", label: "Attempts" },
      { key: "last_attempt_at", label: "Last Attempt" },
      { key: "id", label: "Action", render: r => `<button onclick="retryDelivery(${r.id})">Retry</button>` },
    ]);

    document.getElementById("retryPending").innerHTML = table(data.retry_pending_deliveries, [
      { key: "id", label: "ID" },
      { key: "briefing_id", label: "Briefing" },
      { key: "delivery_channel", label: "Channel" },
      { key: "delivery_target", label: "Target", render: r => esc(r.delivery_target).slice(0, 80) },
      { key: "error_message", label: "Error", render: r => esc(r.error_message).slice(0, 120) },
      { key: "id", label: "Action", render: r => `<button onclick="retryDelivery(${r.id})">Retry</button>` },
    ]);

    document.getElementById("exports").innerHTML = table(data.recent_exports, [
      { key: "id", label: "Export ID" },
      { key: "briefing_id", label: "Briefing" },
      { key: "export_title", label: "Title" },
      { key: "id", label: "Downloads", render: artifactLinks },
      { key: "created_at", label: "Created" },
    ]);

    document.getElementById("schedules").innerHTML = table(data.recent_schedules, [
      { key: "id", label: "ID" },
      { key: "schedule_name", label: "Name" },
      { key: "period_label", label: "Period" },
      { key: "is_enabled", label: "Enabled" },
      { key: "run_count", label: "Runs" },
      { key: "last_run_at", label: "Last Run" },
    ]);

    document.getElementById("briefings").innerHTML = table(data.recent_briefings, [
      { key: "id", label: "ID" },
      { key: "briefing_type", label: "Type" },
      { key: "audience", label: "Audience" },
      { key: "period_label", label: "Period" },
      { key: "title", label: "Title" },
      { key: "created_at", label: "Created" },
    ]);

    const files = data.artifacts?.recent_files || [];
    document.getElementById("artifacts").innerHTML = files.length
      ? `<div class="card">${files.map(f => `<div>${esc(f)}</div>`).join("")}</div>`
      : `<div class="card muted">No artifact files found.</div>`;

  } catch (err) {
    errorBox.textContent = `Dashboard load failed: ${err.message}`;
    errorBox.style.display = "block";
  }
}

loadDashboard();
</script>
</body>
</html>
    """

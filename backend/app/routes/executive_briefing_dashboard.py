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
    * { box-sizing: border-box; }
    body { font-family: Arial, sans-serif; background: #f6f7fb; margin: 0; color: #0f172a; }
    header { background: #111827; color: white; padding: 24px 32px; }
    h1 { margin: 0; font-size: 28px; font-weight: 800; }
    h2 { margin-top: 0; font-size: 22px; }
    h3 { margin: 0 0 12px 0; font-size: 18px; }
    .subtitle { margin-top: 8px; color: #d1d5db; font-size: 16px; }
    main { padding: 24px 32px 48px 32px; max-width: 1900px; margin: 0 auto; }
    .toolbar { display: flex; justify-content: space-between; align-items: center; gap: 16px; margin-bottom: 20px; }
    .toolbar-actions { display: flex; gap: 10px; flex-wrap: wrap; }
    button, .button-link {
      background: #111827; color: white; border: 0; padding: 10px 14px;
      border-radius: 10px; cursor: pointer; font-weight: 700; text-decoration: none;
      display: inline-block; font-size: 14px;
    }
    button:hover, .button-link:hover { background: #374151; }
    .secondary { background: #2563eb; }
    .secondary:hover { background: #1d4ed8; }
    .danger { background: #b45309; }
    .danger:hover { background: #92400e; }
    .green { background: #047857; }
    .green:hover { background: #065f46; }
    .grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 16px; margin-bottom: 24px; }
    .form-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14px; }
    .card { background: white; border-radius: 14px; padding: 18px; box-shadow: 0 8px 18px rgba(15,23,42,0.08); }
    .metric { font-size: 32px; font-weight: 800; margin-top: 8px; }
    .label { color: #64748b; font-size: 13px; text-transform: uppercase; letter-spacing: 0.05em; }
    section { margin-bottom: 28px; }
    table { width: 100%; border-collapse: collapse; background: white; border-radius: 14px; overflow: hidden; box-shadow: 0 8px 18px rgba(15,23,42,0.08); }
    th, td { padding: 12px 14px; border-bottom: 1px solid #e5e7eb; text-align: left; font-size: 14px; vertical-align: top; }
    th { background: #f3f4f6; color: #374151; font-weight: 800; }
    tr:hover td { background: #fafafa; }
    input, select, textarea {
      width: 100%; border: 1px solid #d1d5db; border-radius: 10px;
      padding: 10px 12px; font-size: 14px; background: white;
    }
    textarea { min-height: 72px; resize: vertical; }
    .field label { display: block; font-weight: 700; font-size: 13px; margin-bottom: 6px; color: #374151; }
    .muted { color: #64748b; font-size: 13px; }
    .status { display: inline-block; padding: 5px 9px; border-radius: 999px; font-weight: 800; font-size: 12px; }
    .status-sent, .status-healthy, .status-enabled, .status-no { background: #dcfce7; color: #047857; }
    .status-watch, .status-retry_pending { background: #fef3c7; color: #b45309; }
    .status-at_risk { background: #ffedd5; color: #c2410c; }
    .status-critical, .status-failed, .status-disabled, .status-yes { background: #fee2e2; color: #b91c1c; }
    a { color: #2563eb; text-decoration: none; font-weight: 700; }
    .download-links { display: flex; gap: 10px; flex-wrap: wrap; }
    .download-links a { background: #eff6ff; padding: 6px 9px; border-radius: 8px; }
    .error { background: #fff1f2; color: #991b1b; padding: 14px; border-radius: 12px; margin-bottom: 16px; display: none; }
    .success { background: #ecfdf5; color: #047857; padding: 14px; border-radius: 12px; margin-bottom: 16px; display: none; }
    .small-button { padding: 8px 11px; font-size: 13px; }
    .tenant-panel { border-left: 6px solid #2563eb; }
    .risk-panel { border-left: 6px solid #b45309; }
    .form-actions { display: flex; gap: 10px; margin-top: 14px; flex-wrap: wrap; }
    .wide { grid-column: span 2; }
    .full { grid-column: 1 / -1; }
    @media (max-width: 1200px) {
      .grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      .form-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    }
    @media (max-width: 640px) {
      .grid, .form-grid { grid-template-columns: 1fr; }
      .wide { grid-column: span 1; }
      main { padding: 18px; }
      header { padding: 20px; }
      .toolbar { flex-direction: column; align-items: flex-start; }
    }
  </style>
</head>
<body>
  <header>
    <h1>LumenAI Executive Briefing Dashboard</h1>
    <div class="subtitle">Portfolio intelligence, board briefing automation, exports, schedules, delivery status, and tenant management</div>
  </header>

  <main>
    <div class="toolbar">
      <div>
        <strong>Environment:</strong> local API
        <div class="muted">Using Authorization: Bearer dev-token</div>
        <div class="muted" id="lastRefreshed">Last refreshed: not loaded</div>
      </div>
      <div class="toolbar-actions">
        <button onclick="loadDashboard()">Refresh Dashboard</button>
        <button class="secondary" onclick="runDueNow()">Run Due Now</button>
        <button class="secondary" onclick="startScheduler()">Start Scheduler</button>
        <button class="green" onclick="generateTenantBoardBriefing()">Generate Tenant Board Briefing</button>
      </div>
    </div>

    <div id="error" class="error"></div>
    <div id="success" class="success"></div>

    <section>
      <h2>Portfolio Intelligence Summary</h2>
      <div class="grid" id="tenantMetrics"></div>
    </section>

    <section>
      <h2>Tenant Management</h2>
      <div class="card">
        <h3 id="tenantFormTitle">Create Tenant</h3>
        <input type="hidden" id="tenant_id" />
        <div class="form-grid">
          <div class="field wide">
            <label>Tenant Name</label>
            <input id="tenant_name" placeholder="Example: Riverside Health" />
          </div>
          <div class="field">
            <label>Industry</label>
            <input id="industry" value="healthcare" />
          </div>
          <div class="field">
            <label>Go-Live Status</label>
            <select id="go_live_status">
              <option value="not_started">not_started</option>
              <option value="implementation">implementation</option>
              <option value="live">live</option>
              <option value="go_live_complete">go_live_complete</option>
              <option value="active">active</option>
            </select>
          </div>
          <div class="field">
            <label>Renewal Risk</label>
            <select id="renewal_risk">
              <option value="false">No</option>
              <option value="true">Yes</option>
            </select>
          </div>
          <div class="field">
            <label>Implementation Risk</label>
            <select id="implementation_risk">
              <option value="false">No</option>
              <option value="true">Yes</option>
            </select>
          </div>
          <div class="field">
            <label>Governance Exceptions</label>
            <input id="governance_exception_count" type="number" min="0" value="0" />
          </div>
          <div class="field">
            <label>Last QBR Date</label>
            <input id="last_qbr_date" type="date" />
          </div>
          <div class="field">
            <label>Next QBR Date</label>
            <input id="next_qbr_date" type="date" />
          </div>
          <div class="field">
            <label>Executive Owner</label>
            <input id="executive_owner" placeholder="Executive owner" />
          </div>
          <div class="field">
            <label>Customer Success Owner</label>
            <input id="customer_success_owner" placeholder="CSM owner" />
          </div>
          <div class="field full">
            <label>Notes</label>
            <textarea id="notes" placeholder="Key risk, implementation, QBR, or governance notes"></textarea>
          </div>
        </div>

        <div class="form-actions">
          <button class="green" onclick="saveTenant()">Save Tenant</button>
          <button onclick="clearTenantForm()">Clear Form</button>
          <button class="secondary" onclick="rescoreTenants()">Rescore All Tenants</button>
        </div>
      </div>
    </section>

    <section>
      <h2>Tenant Portfolio</h2>
      <div id="tenantTable"></div>
    </section>

    <section>
      <h2>Top-Risk Tenants</h2>
      <div id="topRiskTenants"></div>
    </section>

    <section>
      <h2>Tenant Executive Insights</h2>
      <div id="tenantInsights"></div>
    </section>

    <section>
      <h2>Automated KPI Snapshot Scheduler + Board Trend Narrative</h2>
      <div class="toolbar-actions" style="margin-bottom: 16px;">
        <button class="secondary" onclick="startKpiScheduler()">Start KPI Scheduler</button>
        <button class="green" onclick="runKpiSchedulerNow()">Run KPI Snapshot Now</button>
        <button onclick="loadKpiNarrative()">Refresh Trend Narrative</button>
      </div>
      <div id="kpiSchedulerStatus" class="card muted">Loading KPI scheduler status...</div>
      <div id="kpiTrendNarrative" style="margin-top: 16px;"></div>
    </section>

    <section>
      <h2>Executive Operating Metrics + KPI Trends</h2>
      <div class="toolbar-actions" style="margin-bottom: 16px;">
        <button class="green" onclick="captureKpiSnapshot()">Capture KPI Snapshot</button>
      </div>
      <div class="grid" id="kpiTrendMetrics"></div>
      <div id="kpiMovement" style="margin-top: 16px;"></div>
      <div id="kpiSnapshotHistory" style="margin-top: 16px;"></div>
    </section>

    <section>
      <h2>Enterprise Audit Trail + Access Governance</h2>
      <div class="grid" id="enterpriseAuditMetrics"></div>
      <div id="enterpriseAuditNarrative" style="margin-top: 16px;"></div>
      <div id="recentAuditEvents" style="margin-top: 16px;"></div>
    </section>

    <section>
      <h2>Executive Decision Log + Governance Action Register</h2>
      <div class="grid" id="executiveDecisionMetrics"></div>
      <div id="executiveDecisionNarrative" style="margin-top: 16px;"></div>
      <div id="openExecutiveDecisions" style="margin-top: 16px;"></div>
      <div id="overdueExecutiveDecisions" style="margin-top: 16px;"></div>
    </section>

    <section>
      <h2>Governance Packet Exports & Board Delivery</h2>
      <div class="toolbar-actions" style="margin-bottom: 16px;">
        <button class="green" onclick="generateGovernancePacketArtifact()">Generate + Export + Deliver Governance Packet</button>
      </div>
      <div class="grid" id="governancePacketMetrics"></div>
      <div id="recentGovernancePackets" style="margin-top: 16px;"></div>
      <div id="recentGovernancePacketExports" style="margin-top: 16px;"></div>
    </section>

    <section>
      <h2>Executive Escalation & Governance Cadence</h2>
      <div class="toolbar-actions" style="margin-bottom: 16px;">
        <button class="danger" onclick="runExecutiveEscalationScan()">Run Escalation Scan</button>
        <button class="green" onclick="generateGovernancePacket()">Generate Governance Packet</button>
      </div>
      <div class="grid" id="executiveEscalationMetrics"></div>
      <div id="openExecutiveEscalations" style="margin-top: 16px;"></div>
      <div id="governancePacket" style="margin-top: 16px;"></div>
    </section>

    <section>
      <h2>Tenant Remediation Workflow</h2>
      <div class="grid" id="remediationMetrics"></div>
      <div style="margin-top: 16px;" id="openRemediations"></div>
      <div style="margin-top: 16px;" id="overdueRemediations"></div>
    </section>

    <section>
      <h2>Executive Automation Summary</h2>
      <div class="grid" id="metrics"></div>
    </section>

    <section>
      <h2>Scheduler Status</h2>
      <div id="schedulerStatus" class="card muted">Loading scheduler status...</div>
    </section>

    <section>
      <h2>Retry Pending Deliveries</h2>
      <div id="retryPending"></div>
    </section>

    <section>
      <h2>Recent Deliveries</h2>
      <div id="deliveries"></div>
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
let tenantCache = [];

function esc(value) {
  if (value === null || value === undefined) return "";
  return String(value).replace(/[&<>"']/g, s => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;"
  }[s]));
}

function formatDate(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return esc(value);
  return date.toLocaleString();
}

function clearMessages() {
  document.getElementById("error").style.display = "none";
  document.getElementById("success").style.display = "none";
}

function showError(message) {
  const box = document.getElementById("error");
  box.textContent = message;
  box.style.display = "block";
}

function showSuccess(message) {
  const box = document.getElementById("success");
  box.textContent = message;
  box.style.display = "block";
  setTimeout(() => { box.style.display = "none"; }, 5000);
}

function metricCard(label, value, extraClass = "") {
  return `<div class="card ${extraClass}"><div class="label">${esc(label)}</div><div class="metric">${esc(value)}</div></div>`;
}

function statusBadge(status) {
  return `<span class="status status-${esc(status)}">${esc(status)}</span>`;
}

function boolBadge(value) {
  return value ? statusBadge("yes") : statusBadge("no");
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
              let value = c.render ? c.render(row) : esc(row[c.key]);
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
    <div class="download-links">
      <a href="/api/portfolio-briefings/exports/${id}/docx" target="_blank">DOCX</a>
      <a href="/api/portfolio-briefings/exports/${id}/pptx" target="_blank">PPTX</a>
      <a href="/api/portfolio-briefings/exports/${id}/pdf" target="_blank">PDF</a>
    </div>
  `;
}

async function apiFetch(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: {
      ...(options.headers || {}),
      "Authorization": `Bearer ${token}`,
      "Content-Type": options.body ? "application/json" : ((options.headers || {})["Content-Type"] || "application/json"),
    }
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`HTTP ${response.status}: ${text.slice(0, 300)}`);
  }

  return response.json();
}

function tenantPayload() {
  return {
    tenant_name: document.getElementById("tenant_name").value.trim(),
    industry: document.getElementById("industry").value.trim() || "healthcare",
    go_live_status: document.getElementById("go_live_status").value,
    renewal_risk: document.getElementById("renewal_risk").value === "true",
    implementation_risk: document.getElementById("implementation_risk").value === "true",
    governance_exception_count: Number(document.getElementById("governance_exception_count").value || 0),
    last_qbr_date: document.getElementById("last_qbr_date").value || null,
    next_qbr_date: document.getElementById("next_qbr_date").value || null,
    executive_owner: document.getElementById("executive_owner").value.trim(),
    customer_success_owner: document.getElementById("customer_success_owner").value.trim(),
    notes: document.getElementById("notes").value.trim(),
  };
}

function clearTenantForm() {
  document.getElementById("tenantFormTitle").textContent = "Create Tenant";
  document.getElementById("tenant_id").value = "";
  document.getElementById("tenant_name").value = "";
  document.getElementById("industry").value = "healthcare";
  document.getElementById("go_live_status").value = "not_started";
  document.getElementById("renewal_risk").value = "false";
  document.getElementById("implementation_risk").value = "false";
  document.getElementById("governance_exception_count").value = "0";
  document.getElementById("last_qbr_date").value = "";
  document.getElementById("next_qbr_date").value = "";
  document.getElementById("executive_owner").value = "";
  document.getElementById("customer_success_owner").value = "";
  document.getElementById("notes").value = "";
}

function editTenant(id) {
  const tenant = tenantCache.find(t => Number(t.id) === Number(id));
  if (!tenant) return;

  document.getElementById("tenantFormTitle").textContent = `Edit Tenant #${tenant.id}`;
  document.getElementById("tenant_id").value = tenant.id;
  document.getElementById("tenant_name").value = tenant.tenant_name || "";
  document.getElementById("industry").value = tenant.industry || "healthcare";
  document.getElementById("go_live_status").value = tenant.go_live_status || "not_started";
  document.getElementById("renewal_risk").value = tenant.renewal_risk ? "true" : "false";
  document.getElementById("implementation_risk").value = tenant.implementation_risk ? "true" : "false";
  document.getElementById("governance_exception_count").value = tenant.governance_exception_count || 0;
  document.getElementById("last_qbr_date").value = tenant.last_qbr_date || "";
  document.getElementById("next_qbr_date").value = tenant.next_qbr_date || "";
  document.getElementById("executive_owner").value = tenant.executive_owner || "";
  document.getElementById("customer_success_owner").value = tenant.customer_success_owner || "";
  document.getElementById("notes").value = tenant.notes || "";
  window.scrollTo({ top: 260, behavior: "smooth" });
}

async function saveTenant() {
  clearMessages();

  const payload = tenantPayload();
  if (!payload.tenant_name) {
    showError("Tenant name is required.");
    return;
  }

  const tenantId = document.getElementById("tenant_id").value;

  try {
    if (tenantId) {
      await apiFetch(`/api/portfolio-tenants/${tenantId}`, {
        method: "PATCH",
        body: JSON.stringify(payload)
      });
      showSuccess(`Tenant ${tenantId} updated successfully.`);
    } else {
      await apiFetch("/api/portfolio-tenants", {
        method: "POST",
        body: JSON.stringify(payload)
      });
      showSuccess("Tenant created successfully.");
    }

    clearTenantForm();
    await loadDashboard();
  } catch (err) {
    showError(`Tenant save failed: ${err.message}`);
  }
}

async function rescoreTenants() {
  clearMessages();
  try {
    const result = await apiFetch("/api/portfolio-tenants/rescore", { method: "POST" });
    showSuccess(`Rescored ${result.length || 0} tenants.`);
    await loadDashboard();
  } catch (err) {
    showError(`Rescore failed: ${err.message}`);
  }
}

async function loadTenants() {
  try {
    tenantCache = await apiFetch("/api/portfolio-tenants");
    document.getElementById("tenantTable").innerHTML = table(tenantCache, [
      { key: "id", label: "ID" },
      { key: "tenant_name", label: "Tenant" },
      { key: "health_status", label: "Health", render: r => statusBadge(r.health_status) },
      { key: "health_score", label: "Score" },
      { key: "go_live_status", label: "Go-Live" },
      { key: "renewal_risk", label: "Renewal Risk", render: r => boolBadge(r.renewal_risk) },
      { key: "implementation_risk", label: "Implementation Risk", render: r => boolBadge(r.implementation_risk) },
      { key: "governance_exception_count", label: "Gov Exceptions" },
      { key: "next_qbr_date", label: "Next QBR", render: r => esc(r.next_qbr_date || "") },
      { key: "customer_success_owner", label: "CS Owner" },
      { key: "id", label: "Action", render: r => `<button class="secondary small-button" onclick="editTenant(${r.id})">Edit</button>` },
    ]);
  } catch (err) {
    document.getElementById("tenantTable").innerHTML = `<div class="card" style="color:#b91c1c;">Failed to load tenants: ${esc(err.message)}</div>`;
  }
}


async function createRemediationsFromInsight(tenantId) {
  clearMessages();
  try {
    const result = await apiFetch(`/api/tenant-remediations/from-insight/${tenantId}`, { method: "POST" });
    showSuccess(`Created ${result.length || 0} remediation action(s) from tenant insight.`);
    await loadDashboard();
  } catch (err) {
    showError(`Create remediation from insight failed: ${err.message}`);
  }
}

async function closeRemediation(id) {
  clearMessages();
  try {
    await apiFetch(`/api/tenant-remediations/${id}/close`, { method: "POST" });
    showSuccess(`Remediation ${id} closed.`);
    await loadDashboard();
  } catch (err) {
    showError(`Close remediation failed: ${err.message}`);
  }
}

async function setRemediationStatus(id, status) {
  clearMessages();
  try {
    await apiFetch(`/api/tenant-remediations/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ status })
    });
    showSuccess(`Remediation ${id} updated to ${status}.`);
    await loadDashboard();
  } catch (err) {
    showError(`Update remediation failed: ${err.message}`);
  }
}






async function loadKpiSchedulerStatus() {
  try {
    const status = await apiFetch("/api/executive-kpi-scheduler/status");
    const jobs = status.jobs || [];
    const last = status.last_run_summary || {};
    document.getElementById("kpiSchedulerStatus").innerHTML = `
      <div><strong>Running:</strong> ${status.running ? "Yes" : "No"}</div>
      <div style="margin-top: 8px;"><strong>Jobs:</strong> ${jobs.length}</div>
      <div class="muted" style="margin-top: 8px;">Next run: ${jobs.map(j => formatDate(j.next_run_time)).join(", ") || "None"}</div>
      <div class="muted" style="margin-top: 8px;">Last run: ${formatDate(last.checked_at)}</div>
      <div class="muted">Last snapshot ID: ${last.snapshot_id || "None"}; status: ${last.status || "not_started"}</div>
      ${last.error ? `<div style="color:#b91c1c;margin-top:8px;">Error: ${esc(last.error)}</div>` : ""}
    `;
  } catch (err) {
    document.getElementById("kpiSchedulerStatus").innerHTML = `<span style="color:#b91c1c;">Failed to load KPI scheduler status: ${esc(err.message)}</span>`;
  }
}

async function startKpiScheduler() {
  clearMessages();
  try {
    await apiFetch("/api/executive-kpi-scheduler/start", { method: "POST" });
    showSuccess("KPI scheduler started.");
    await loadKpiSchedulerStatus();
  } catch (err) {
    showError(`Start KPI scheduler failed: ${err.message}`);
  }
}

async function runKpiSchedulerNow() {
  clearMessages();
  try {
    const result = await apiFetch("/api/executive-kpi-scheduler/run-now", { method: "POST" });
    showSuccess(`KPI scheduler run completed. Snapshot ID: ${result.snapshot?.id || "unknown"}`);
    await loadDashboard();
  } catch (err) {
    showError(`Run KPI scheduler now failed: ${err.message}`);
  }
}

async function loadKpiNarrative() {
  try {
    const narrative = await apiFetch("/api/executive-kpi-scheduler/narrative");
    const movements = narrative.movement_narratives || [];
    const actions = narrative.recommended_actions || [];

    document.getElementById("kpiTrendNarrative").innerHTML = `
      <div class="card">
        <h3>Executive Trend Narrative</h3>
        <p><strong>Status:</strong> ${esc(narrative.status)}</p>
        <p><strong>Executive Summary:</strong> ${esc(narrative.executive_summary || "")}</p>
        <h4>Board Narrative</h4>
        <p>${esc(narrative.board_narrative || "")}</p>
        <h4>Recommended Actions</h4>
        <ul>${actions.map(a => `<li>${esc(a)}</li>`).join("")}</ul>
        <h4>Movement Interpretation</h4>
        ${table(movements, [
          { key: "label", label: "Metric" },
          { key: "previous", label: "Previous" },
          { key: "latest", label: "Latest" },
          { key: "delta", label: "Delta", render: r => movementBadge(r.delta) },
          { key: "narrative", label: "Narrative", render: r => esc(r.narrative).slice(0, 240) },
        ])}
      </div>
    `;
  } catch (err) {
    document.getElementById("kpiTrendNarrative").innerHTML = `<div class="card" style="color:#b91c1c;">Failed to load KPI trend narrative: ${esc(err.message)}</div>`;
  }
}


async function captureKpiSnapshot() {
  clearMessages();
  try {
    const snapshot = await apiFetch("/api/executive-kpi-snapshots/capture", {
      method: "POST",
      body: JSON.stringify({
        snapshot_label: "Dashboard Captured Executive KPI Snapshot"
      })
    });
    showSuccess(`KPI snapshot captured. Snapshot ID: ${snapshot.id}`);
    await loadDashboard();
  } catch (err) {
    showError(`KPI snapshot capture failed: ${err.message}`);
  }
}

function movementBadge(delta) {
  const value = Number(delta || 0);
  if (value > 0) return `<span class="status status-at_risk">+${value}</span>`;
  if (value < 0) return `<span class="status status-healthy">${value}</span>`;
  return `<span class="status status-watch">0</span>`;
}


function governanceArtifactLinks(row) {
  const id = row.id;
  return `
    <div class="download-links">
      <a href="/api/governance-packets/exports/${id}/docx" target="_blank">DOCX</a>
      <a href="/api/governance-packets/exports/${id}/pptx" target="_blank">PPTX</a>
      <a href="/api/governance-packets/exports/${id}/pdf" target="_blank">PDF</a>
    </div>
  `;
}

async function generateGovernancePacketArtifact() {
  clearMessages();
  try {
    const packet = await apiFetch("/api/governance-packets", {
      method: "POST",
      body: JSON.stringify({
        packet_title: "Executive Governance Packet - Dashboard Generated"
      })
    });

    const exportRecord = await apiFetch(`/api/governance-packets/${packet.id}/exports`, {
      method: "POST"
    });

    await apiFetch(`/api/governance-packets/${packet.id}/deliver`, {
      method: "POST",
      body: JSON.stringify({
        export_id: exportRecord.id,
        delivery_channel: "internal",
        delivery_target: "executive-governance-council",
        message: "Executive governance packet generated from open escalation cadence."
      })
    });

    showSuccess(`Governance packet generated, exported, and delivered. Packet ID: ${packet.id}`);
    await loadDashboard();
  } catch (err) {
    showError(`Governance packet artifact workflow failed: ${err.message}`);
  }
}



async function createDecisionFromEscalation(escalationId) {
  clearMessages();
  try {
    const decision = await apiFetch(`/api/executive-decisions/from-escalation/${escalationId}`, { method: "POST" });
    showSuccess(`Executive decision created. Decision ID: ${decision.id}`);
    await loadDashboard();
  } catch (err) {
    showError(`Create decision failed: ${err.message}`);
  }
}

async function approveDecision(decisionId) {
  clearMessages();
  try {
    await apiFetch(`/api/executive-decisions/${decisionId}/approve`, { method: "POST" });
    showSuccess(`Decision ${decisionId} approved.`);
    await loadDashboard();
  } catch (err) {
    showError(`Approve decision failed: ${err.message}`);
  }
}

async function completeDecision(decisionId) {
  clearMessages();
  try {
    await apiFetch(`/api/executive-decisions/${decisionId}/complete`, { method: "POST" });
    showSuccess(`Decision ${decisionId} completed.`);
    await loadDashboard();
  } catch (err) {
    showError(`Complete decision failed: ${err.message}`);
  }
}


async function runExecutiveEscalationScan() {
  clearMessages();
  try {
    const result = await apiFetch("/api/executive-escalations/run", { method: "POST" });
    showSuccess(`Escalation scan completed. Created: ${result.created_count || 0}`);
    await loadDashboard();
  } catch (err) {
    showError(`Escalation scan failed: ${err.message}`);
  }
}

async function acknowledgeExecutiveEscalation(id) {
  clearMessages();
  try {
    await apiFetch(`/api/executive-escalations/${id}/acknowledge`, { method: "POST" });
    showSuccess(`Escalation ${id} acknowledged.`);
    await loadDashboard();
  } catch (err) {
    showError(`Acknowledge escalation failed: ${err.message}`);
  }
}

async function closeExecutiveEscalation(id) {
  clearMessages();
  try {
    await apiFetch(`/api/executive-escalations/${id}/close`, { method: "POST" });
    showSuccess(`Escalation ${id} closed.`);
    await loadDashboard();
  } catch (err) {
    showError(`Close escalation failed: ${err.message}`);
  }
}

async function generateGovernancePacket() {
  clearMessages();
  try {
    const packet = await apiFetch("/api/executive-escalations/generate-governance-packet", { method: "POST" });
    showSuccess("Governance packet generated.");

    const items = packet.top_governance_items || [];
    const decisions = packet.recommended_leadership_decisions || [];

    document.getElementById("governancePacket").innerHTML = `
      <div class="card">
        <h3>Governance Packet</h3>
        <p><strong>Executive Summary:</strong> ${esc(packet.executive_summary || "")}</p>
        <h4>Recommended Leadership Decisions</h4>
        <ul>${decisions.map(d => `<li>${esc(d)}</li>`).join("")}</ul>
        <h4>Top Governance Items</h4>
        ${table(items, [
          { key: "tenant", label: "Tenant" },
          { key: "priority", label: "Priority", render: r => statusBadge(r.priority === "critical" ? "critical" : "at_risk") },
          { key: "type", label: "Type" },
          { key: "owner", label: "Owner" },
          { key: "summary", label: "Summary", render: r => esc(r.summary).slice(0, 220) },
          { key: "leadership_decision_required", label: "Decision Required", render: r => boolBadge(r.leadership_decision_required) },
        ])}
      </div>
    `;
  } catch (err) {
    showError(`Governance packet generation failed: ${err.message}`);
  }
}


async function retryDelivery(id) {
  clearMessages();
  try {
    await apiFetch(`/api/portfolio-briefing-deliveries/${id}/retry`, { method: "POST" });
    showSuccess(`Delivery ${id} retried successfully.`);
    await loadDashboard();
  } catch (err) {
    showError(`Retry failed: ${err.message}`);
  }
}

async function runScheduleNow(id) {
  clearMessages();
  try {
    await apiFetch(`/api/portfolio-briefing-schedules/${id}/run-now`, { method: "POST" });
    showSuccess(`Schedule ${id} ran successfully.`);
    await loadDashboard();
  } catch (err) {
    showError(`Run schedule failed: ${err.message}`);
  }
}

async function runDueNow() {
  clearMessages();
  try {
    const result = await apiFetch("/api/portfolio-briefing-scheduler/run-due", { method: "POST" });
    showSuccess(`Run due completed. Due: ${result.due_count || 0}, Ran: ${result.run_count || 0}, Errors: ${(result.errors || []).length}`);
    await loadDashboard();
  } catch (err) {
    showError(`Run due failed: ${err.message}`);
  }
}

async function startScheduler() {
  clearMessages();
  try {
    await apiFetch("/api/portfolio-briefing-scheduler/start", { method: "POST" });
    showSuccess("Scheduler started.");
    await loadDashboard();
  } catch (err) {
    showError(`Start scheduler failed: ${err.message}`);
  }
}

async function generateTenantBoardBriefing() {
  clearMessages();
  try {
    const briefing = await apiFetch("/api/portfolio-tenants/generate-board-briefing", {
      method: "POST",
      body: JSON.stringify({
        period_label: "Customer Portfolio Board Review - Dashboard Generated",
        audience: "board"
      })
    });

    const exportRecord = await apiFetch(`/api/portfolio-briefings/${briefing.id}/exports`, { method: "POST" });

    await apiFetch(`/api/portfolio-briefings/${briefing.id}/distribute`, {
      method: "POST",
      body: JSON.stringify({
        export_id: exportRecord.id,
        delivery_channel: "internal",
        delivery_target: "executive-board",
        message: "Customer portfolio board briefing generated from dashboard tenant rollup."
      })
    });

    showSuccess(`Tenant board briefing generated, exported, and delivered. Briefing ID: ${briefing.id}`);
    await loadDashboard();
  } catch (err) {
    showError(`Tenant board briefing generation failed: ${err.message}`);
  }
}

async function loadSchedulerStatus() {
  try {
    const status = await apiFetch("/api/portfolio-briefing-scheduler/status");
    const jobs = status.jobs || [];
    const last = status.last_run_summary || {};
    document.getElementById("schedulerStatus").innerHTML = `
      <div><strong>Running:</strong> ${status.running ? "Yes" : "No"}</div>
      <div style="margin-top: 8px;"><strong>Jobs:</strong> ${jobs.length}</div>
      <div class="muted" style="margin-top: 8px;">Next run: ${jobs.map(j => formatDate(j.next_run_time)).join(", ") || "None"}</div>
      <div class="muted" style="margin-top: 8px;">Last check: ${formatDate(last.checked_at)}</div>
      <div class="muted">Last due count: ${last.due_count ?? 0}; run count: ${last.run_count ?? 0}; errors: ${(last.errors || []).length}</div>
    `;
  } catch (err) {
    document.getElementById("schedulerStatus").innerHTML = `<span style="color:#b91c1c;">Failed to load scheduler status: ${esc(err.message)}</span>`;
  }
}

async function loadDashboard() {
  clearMessages();

  try {
    const data = await apiFetch("/api/executive-briefing-dashboard/summary");
    const counts = data.counts || {};
    const tenants = data.portfolio_tenants || {};

    document.getElementById("lastRefreshed").textContent = `Last refreshed: ${new Date().toLocaleString()}`;

    document.getElementById("tenantMetrics").innerHTML = [
      metricCard("Total Tenants", tenants.total || 0, "tenant-panel"),
      metricCard("Healthy", tenants.healthy || 0),
      metricCard("Watch", tenants.watch || 0),
      metricCard("At Risk", tenants.at_risk || 0, "risk-panel"),
      metricCard("Critical", tenants.critical || 0, "risk-panel"),
      metricCard("QBR Overdue", tenants.qbr_overdue || 0, "risk-panel"),
      metricCard("Governance Exceptions", tenants.governance_exceptions || 0, "risk-panel"),
      metricCard("Top Risk Tenants", (data.top_risk_tenants || []).length),
    ].join("");

    document.getElementById("topRiskTenants").innerHTML = table(data.top_risk_tenants, [
      { key: "id", label: "ID" },
      { key: "tenant_name", label: "Tenant" },
      { key: "health_status", label: "Health", render: r => statusBadge(r.health_status) },
      { key: "health_score", label: "Score" },
      { key: "renewal_risk", label: "Renewal Risk", render: r => boolBadge(r.renewal_risk) },
      { key: "implementation_risk", label: "Implementation Risk", render: r => boolBadge(r.implementation_risk) },
      { key: "governance_exception_count", label: "Gov Exceptions" },
      { key: "next_qbr_date", label: "Next QBR", render: r => esc(r.next_qbr_date || "") },
      { key: "customer_success_owner", label: "CS Owner" },
    ]);

    const insightRollup = data.tenant_insights || {};
    const insightRows = data.top_tenant_insights || [];

    document.getElementById("tenantInsights").innerHTML = `
      <div class="grid">
        ${metricCard("Board Attention", insightRollup.board_attention_count || 0, "risk-panel")}
        ${metricCard("Critical Insights", insightRollup.critical_count || 0, "risk-panel")}
        ${metricCard("High/Moderate Risk", insightRollup.high_or_moderate_count || 0, "risk-panel")}
        ${metricCard("Insight Count", insightRollup.tenant_insight_count || 0)}
      </div>
      <div class="card" style="margin-bottom: 16px;">
        <strong>Executive Focus:</strong>
        <div style="margin-top:8px;">${esc(insightRollup.executive_focus_summary || "")}</div>
      </div>
      ${table(insightRows, [
        { key: "tenant_name", label: "Tenant" },
        { key: "risk_level", label: "Risk Level", render: r => statusBadge(r.risk_level === "high" ? "at_risk" : r.risk_level) },
        { key: "board_attention_required", label: "Board Attention", render: r => boolBadge(r.board_attention_required) },
        { key: "executive_summary", label: "Executive Summary", render: r => esc(r.executive_summary).slice(0, 220) },
        { key: "recommended_actions", label: "Recommended Actions", render: r => esc((r.recommended_actions || []).join("; ")).slice(0, 260) },
        { key: "tenant_id", label: "Action", render: r => `<button class="secondary small-button" onclick="createRemediationsFromInsight(${r.tenant_id})">Create Actions</button>` },
      ])}
    `;





    const kpi = data.executive_kpi_trends || {};
    const latestKpi = kpi.latest || {};
    const movement = kpi.movement || {};
    const series = kpi.series || [];

    document.getElementById("kpiTrendMetrics").innerHTML = [
      metricCard("Snapshots", kpi.snapshot_count || 0),
      metricCard("Critical Tenants", latestKpi.tenant_critical || 0, "risk-panel"),
      metricCard("Open Remediations", latestKpi.remediation_open || 0, "risk-panel"),
      metricCard("Overdue Remediations", latestKpi.remediation_overdue || 0, "risk-panel"),
      metricCard("Open Escalations", latestKpi.escalation_open || 0, "risk-panel"),
      metricCard("Leadership Decisions", latestKpi.leadership_decisions_required || 0, "risk-panel"),
      metricCard("Retry Deliveries", latestKpi.delivery_retry_pending || 0, "risk-panel"),
      metricCard("Artifacts", latestKpi.artifact_count || 0),
    ].join("");

    document.getElementById("kpiMovement").innerHTML = `
      <h3>Current vs Previous Snapshot Movement</h3>
      ${table(Object.keys(movement).map(key => ({
        metric: key,
        latest: movement[key].latest,
        previous: movement[key].previous,
        delta: movement[key].delta,
      })), [
        { key: "metric", label: "Metric" },
        { key: "previous", label: "Previous" },
        { key: "latest", label: "Latest" },
        { key: "delta", label: "Delta", render: r => movementBadge(r.delta) },
      ])}
    `;

    document.getElementById("kpiSnapshotHistory").innerHTML = `
      <h3>KPI Snapshot History</h3>
      ${table(series, [
        { key: "id", label: "ID" },
        { key: "snapshot_date", label: "Date" },
        { key: "tenant_critical", label: "Critical Tenants" },
        { key: "qbr_overdue", label: "QBR Overdue" },
        { key: "remediation_open", label: "Open Remediations" },
        { key: "remediation_overdue", label: "Overdue Remediations" },
        { key: "escalation_open", label: "Open Escalations" },
        { key: "leadership_decisions_required", label: "Leadership Decisions" },
        { key: "delivery_retry_pending", label: "Retry Deliveries" },
        { key: "artifact_count", label: "Artifacts" },
        { key: "created_at", label: "Captured", render: r => formatDate(r.created_at) },
      ])}
    `;




    const audit = data.enterprise_audit || {};
    const auditNarrative = data.enterprise_audit_narrative || {};

    document.getElementById("enterpriseAuditMetrics").innerHTML = [
      metricCard("Audit Events", audit.total || 0),
      metricCard("Successful", audit.success || 0),
      metricCard("Failed", audit.failed || 0, audit.failed > 0 ? "risk-panel" : ""),
      metricCard("Write/Execute", audit.writes || 0, "risk-panel"),
      metricCard("Reads", audit.reads || 0),
      metricCard("Dashboard Views", audit.dashboard_views || 0),
      metricCard("Decision Events", audit.decision_events || 0),
      metricCard("Governance Events", audit.governance_events || 0),
    ].join("");

    document.getElementById("enterpriseAuditNarrative").innerHTML = `
      <div class="card">
        <h3>Audit Compliance Narrative</h3>
        <p>${esc(auditNarrative.executive_summary || "")}</p>
        <h4>Recommended Actions</h4>
        <ul>${(auditNarrative.recommended_actions || []).map(a => `<li>${esc(a)}</li>`).join("")}</ul>
      </div>
    `;

    document.getElementById("recentAuditEvents").innerHTML = `
      <h3>Recent Audit Events</h3>
      ${table(data.recent_audit_events || [], [
        { key: "id", label: "ID" },
        { key: "actor", label: "Actor" },
        { key: "actor_role", label: "Role" },
        { key: "resource_type", label: "Resource" },
        { key: "action", label: "Action" },
        { key: "method", label: "Method" },
        { key: "path", label: "Path", render: r => esc(r.path).slice(0, 90) },
        { key: "status_code", label: "Status" },
        { key: "success", label: "Success", render: r => boolBadge(r.success) },
        { key: "created_at", label: "Time", render: r => formatDate(r.created_at) },
      ])}
    `;


    const decisions = data.executive_decisions || {};
    const decisionNarrative = data.executive_decision_narrative || {};

    document.getElementById("executiveDecisionMetrics").innerHTML = [
      metricCard("Total Decisions", decisions.total || 0),
      metricCard("Proposed", decisions.proposed || 0, "risk-panel"),
      metricCard("Approved", decisions.approved || 0),
      metricCard("In Progress", decisions.in_progress || 0),
      metricCard("Blocked", decisions.blocked || 0, "risk-panel"),
      metricCard("Overdue", decisions.overdue || 0, "risk-panel"),
      metricCard("Leadership Required", decisions.leadership_required || 0, "risk-panel"),
      metricCard("Completed", decisions.completed || 0),
    ].join("");

    document.getElementById("executiveDecisionNarrative").innerHTML = `
      <div class="card">
        <h3>Decision Register Narrative</h3>
        <p>${esc(decisionNarrative.executive_summary || "")}</p>
        <h4>Recommended Actions</h4>
        <ul>${(decisionNarrative.recommended_actions || []).map(a => `<li>${esc(a)}</li>`).join("")}</ul>
      </div>
    `;

    document.getElementById("openExecutiveDecisions").innerHTML = `
      <h3>Open Executive Decisions</h3>
      ${table(data.open_executive_decisions || [], [
        { key: "id", label: "ID" },
        { key: "tenant_name", label: "Tenant" },
        { key: "decision_title", label: "Decision", render: r => esc(r.decision_title).slice(0, 150) },
        { key: "decision_owner", label: "Owner" },
        { key: "due_date", label: "Due" },
        { key: "priority", label: "Priority", render: r => statusBadge(r.priority === "critical" ? "critical" : (r.priority === "high" ? "at_risk" : "watch")) },
        { key: "status", label: "Status", render: r => statusBadge(r.status === "proposed" ? "watch" : r.status) },
        { key: "id", label: "Actions", render: r => `
          <button class="secondary small-button" onclick="approveDecision(${r.id})">Approve</button>
          <button class="green small-button" onclick="completeDecision(${r.id})">Complete</button>
        ` },
      ])}
    `;

    document.getElementById("overdueExecutiveDecisions").innerHTML = `
      <h3>Overdue Executive Decisions</h3>
      ${table(data.overdue_executive_decisions || [], [
        { key: "id", label: "ID" },
        { key: "tenant_name", label: "Tenant" },
        { key: "decision_title", label: "Decision", render: r => esc(r.decision_title).slice(0, 160) },
        { key: "decision_owner", label: "Owner" },
        { key: "due_date", label: "Due" },
        { key: "priority", label: "Priority" },
        { key: "status", label: "Status" },
      ])}
    `;


    const governancePackets = data.governance_packets || {};
    document.getElementById("governancePacketMetrics").innerHTML = [
      metricCard("Packets", governancePackets.total || 0),
      metricCard("Packet Exports", governancePackets.exports || 0),
      metricCard("Packet Deliveries", governancePackets.deliveries || 0),
      metricCard("Board Artifact Workflow", "Active"),
    ].join("");

    document.getElementById("recentGovernancePackets").innerHTML = `
      <h3>Recent Governance Packets</h3>
      ${table(data.recent_governance_packets || [], [
        { key: "id", label: "Packet ID" },
        { key: "packet_title", label: "Title" },
        { key: "status", label: "Status", render: r => statusBadge(r.status || "sent") },
        { key: "executive_summary", label: "Summary", render: r => esc(r.executive_summary || "").slice(0, 240) },
        { key: "created_at", label: "Created", render: r => formatDate(r.created_at) },
      ])}
    `;

    document.getElementById("recentGovernancePacketExports").innerHTML = `
      <h3>Recent Governance Packet Exports</h3>
      ${table(data.recent_governance_packet_exports || [], [
        { key: "id", label: "Export ID" },
        { key: "packet_id", label: "Packet" },
        { key: "export_title", label: "Title" },
        { key: "id", label: "Downloads", render: governanceArtifactLinks },
        { key: "created_at", label: "Created", render: r => formatDate(r.created_at) },
      ])}
    `;


    const escalation = data.executive_escalations || {};
    document.getElementById("executiveEscalationMetrics").innerHTML = [
      metricCard("Total Escalations", escalation.total || 0),
      metricCard("Open", escalation.open || 0, "risk-panel"),
      metricCard("Acknowledged", escalation.acknowledged || 0),
      metricCard("Closed", escalation.closed || 0),
      metricCard("Critical", escalation.critical || 0, "risk-panel"),
      metricCard("High", escalation.high || 0, "risk-panel"),
      metricCard("Leadership Decisions", escalation.leadership_decision_required || 0, "risk-panel"),
      metricCard("Governance Cadence", "Active"),
    ].join("");

    document.getElementById("openExecutiveEscalations").innerHTML = `
      <h3>Open Executive Escalations</h3>
      ${table(data.open_executive_escalations || [], [
        { key: "id", label: "ID" },
        { key: "tenant_name", label: "Tenant" },
        { key: "escalation_type", label: "Type" },
        { key: "priority", label: "Priority", render: r => statusBadge(r.priority === "critical" ? "critical" : "at_risk") },
        { key: "owner", label: "Owner" },
        { key: "escalation_summary", label: "Summary", render: r => esc(r.escalation_summary).slice(0, 220) },
        { key: "leadership_decision_required", label: "Decision", render: r => boolBadge(r.leadership_decision_required) },
        { key: "id", label: "Actions", render: r => `
          <button class="secondary small-button" onclick="acknowledgeExecutiveEscalation(${r.id})">Acknowledge</button>
          <button class="green small-button" onclick="closeExecutiveEscalation(${r.id})">Close</button>
          <button class="danger small-button" onclick="createDecisionFromEscalation(${r.id})">Create Decision</button>
        ` },
      ])}
    `;


    const remediation = data.tenant_remediations || {};
    document.getElementById("remediationMetrics").innerHTML = [
      metricCard("Total Actions", remediation.total || 0),
      metricCard("Open", remediation.open || 0, "risk-panel"),
      metricCard("In Progress", remediation.in_progress || 0),
      metricCard("Blocked", remediation.blocked || 0, "risk-panel"),
      metricCard("Escalated", remediation.escalated || 0, "risk-panel"),
      metricCard("Overdue", remediation.overdue || 0, "risk-panel"),
      metricCard("Critical Priority", remediation.critical_priority || 0, "risk-panel"),
      metricCard("Closed", remediation.closed || 0),
    ].join("");

    document.getElementById("openRemediations").innerHTML = `
      <h3>Open Remediation Actions</h3>
      ${table(data.open_remediations || [], [
        { key: "id", label: "ID" },
        { key: "tenant_name", label: "Tenant" },
        { key: "action_title", label: "Action", render: r => esc(r.action_title).slice(0, 120) },
        { key: "owner", label: "Owner" },
        { key: "due_date", label: "Due" },
        { key: "priority", label: "Priority", render: r => statusBadge(r.priority === "critical" ? "critical" : (r.priority === "high" ? "at_risk" : "watch")) },
        { key: "status", label: "Status", render: r => statusBadge(r.status === "open" ? "watch" : r.status) },
        { key: "id", label: "Actions", render: r => `
          <button class="small-button" onclick="setRemediationStatus(${r.id}, 'in_progress')">Start</button>
          <button class="danger small-button" onclick="setRemediationStatus(${r.id}, 'escalated')">Escalate</button>
          <button class="green small-button" onclick="closeRemediation(${r.id})">Close</button>
        ` },
      ])}
    `;

    document.getElementById("overdueRemediations").innerHTML = `
      <h3>Overdue Remediation Actions</h3>
      ${table(data.overdue_remediations || [], [
        { key: "id", label: "ID" },
        { key: "tenant_name", label: "Tenant" },
        { key: "action_title", label: "Action", render: r => esc(r.action_title).slice(0, 140) },
        { key: "owner", label: "Owner" },
        { key: "due_date", label: "Due" },
        { key: "priority", label: "Priority" },
        { key: "status", label: "Status" },
      ])}
    `;


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

    document.getElementById("retryPending").innerHTML = table(data.retry_pending_deliveries, [
      { key: "id", label: "ID" },
      { key: "briefing_id", label: "Briefing" },
      { key: "export_id", label: "Export" },
      { key: "delivery_channel", label: "Channel" },
      { key: "delivery_target", label: "Target", render: r => esc(r.delivery_target).slice(0, 90) },
      { key: "error_message", label: "Error", render: r => esc(r.error_message).slice(0, 160) },
      { key: "attempt_count", label: "Attempts" },
      { key: "id", label: "Action", render: r => `<button class="danger small-button" onclick="retryDelivery(${r.id})">Retry</button>` },
    ]);

    document.getElementById("deliveries").innerHTML = table(data.recent_deliveries, [
      { key: "id", label: "ID" },
      { key: "briefing_id", label: "Briefing" },
      { key: "export_id", label: "Export" },
      { key: "delivery_channel", label: "Channel" },
      { key: "delivery_target", label: "Target", render: r => esc(r.delivery_target).slice(0, 80) },
      { key: "status", label: "Status", render: r => statusBadge(r.status) },
      { key: "attempt_count", label: "Attempts" },
      { key: "last_attempt_at", label: "Last Attempt", render: r => formatDate(r.last_attempt_at) },
      { key: "id", label: "Action", render: r => `<button class="small-button" onclick="retryDelivery(${r.id})">${r.status === "sent" ? "Resend" : "Retry"}</button>` },
    ]);

    document.getElementById("exports").innerHTML = table(data.recent_exports, [
      { key: "id", label: "Export ID" },
      { key: "briefing_id", label: "Briefing" },
      { key: "export_title", label: "Title" },
      { key: "id", label: "Downloads", render: artifactLinks },
      { key: "created_at", label: "Created", render: r => formatDate(r.created_at) },
    ]);

    document.getElementById("schedules").innerHTML = table(data.recent_schedules, [
      { key: "id", label: "ID" },
      { key: "schedule_name", label: "Name" },
      { key: "period_label", label: "Period" },
      { key: "is_enabled", label: "Enabled", render: r => r.is_enabled ? statusBadge("enabled") : statusBadge("disabled") },
      { key: "run_count", label: "Runs" },
      { key: "last_run_at", label: "Last Run", render: r => formatDate(r.last_run_at) },
      { key: "id", label: "Action", render: r => `<button class="secondary small-button" onclick="runScheduleNow(${r.id})">Run Now</button>` },
    ]);

    document.getElementById("briefings").innerHTML = table(data.recent_briefings, [
      { key: "id", label: "ID" },
      { key: "briefing_type", label: "Type" },
      { key: "audience", label: "Audience" },
      { key: "period_label", label: "Period" },
      { key: "title", label: "Title" },
      { key: "created_at", label: "Created", render: r => formatDate(r.created_at) },
    ]);

    const files = data.artifacts?.recent_files || [];
    document.getElementById("artifacts").innerHTML = files.length
      ? `<div class="card">${files.map(f => `<div>${esc(f)}</div>`).join("")}</div>`
      : `<div class="card muted">No artifact files found.</div>`;

    await loadTenants();
    await loadSchedulerStatus();

  } catch (err) {
    showError(`Dashboard load failed: ${err.message}`);
  }
}

loadDashboard();
</script>
</body>
</html>
    """


import { useEffect, useState } from "react";
import type { CSSProperties } from "react";
import { apiFetch } from "@/lib/api";

type CapaItem = {
  capa_id: number;
  finding_id?: number | null;
  vendor_id?: number | null;
  capa_number: string;
  title: string;
  description: string;
  status: string;
  due_date?: string;
  closed_at?: string;
  created_at?: string;
};

const AUTH_TOKEN = localStorage.getItem("token") || import.meta.env.VITE_AUTH_TOKEN || "";


async function updateCapaStatus(capaId: number, status: string, note: string) {
  const response = await apiFetch(`/api/enterprise/capas/${capaId}/status`, { raw: true,
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${AUTH_TOKEN}`,
      "X-LumenAI-Role": "operator",
      "X-LumenAI-Actor": "john-demo",
      "X-Tenant-Id": "bonsecours",
      "X-Tenant-Name": "Bon Secours",
    },
    body: JSON.stringify({
      status,
      note,
    }),
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data?.detail || `CAPA status update failed (${response.status})`);
  }

  return data;
}


export default function EnterpriseCapaPanel() {
  const [items, setItems] = useState<CapaItem[]>([]);
  const [selected, setSelected] = useState<CapaItem | null>(null);
  const [loading, setLoading] = useState(false);
  const [updatingStatus, setUpdatingStatus] = useState("");
  const [statusSuccess, setStatusSuccess] = useState("");
  const [error, setError] = useState("");

  async function loadCapas() {
    setLoading(true);
    setError("");

    try {
      const response = await apiFetch(`/api/enterprise/capas?limit=10`, { raw: true,
        headers: {
          Authorization: `Bearer ${AUTH_TOKEN}`,
          "X-LumenAI-Role": "viewer",
          "X-LumenAI-Actor": "john-demo",
          "X-Tenant-Id": "bonsecours",
          "X-Tenant-Name": "Bon Secours",
        },
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data?.detail || `CAPA request failed (${response.status})`);
      }

      const nextItems = Array.isArray(data.items) ? data.items : [];
      setItems(nextItems);

      if (!selected && nextItems.length > 0) {
        setSelected(nextItems[0]);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown CAPA error");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadCapas();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleStatusUpdate(capa: CapaItem, status: string, note: string) {
    setUpdatingStatus(status);
    setStatusSuccess("");
    setError("");

    try {
      const result = await updateCapaStatus(capa.capa_id, status, note);
      setStatusSuccess(
        `CAPA status updated: ${result.capa_number} → ${result.capa_status}`
      );
      await loadCapas();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown CAPA status update error");
    } finally {
      setUpdatingStatus("");
    }
  }

  return (
    <section style={panelStyle}>
      <div style={eyebrowStyle}>Enterprise CAPA Workflow</div>

      <div style={headerRowStyle}>
        <div>
          <h2 style={{ margin: "8px 0 8px", color: "#0f172a" }}>
            Corrective & Preventive Action Queue
          </h2>
          <p style={{ margin: 0, color: "#475569", lineHeight: 1.6 }}>
            Displays CAPA records opened from enterprise findings, including linked finding,
            vendor context, due date, status, and corrective-action summary.
          </p>
        </div>

        <button
          type="button"
          onClick={loadCapas}
          disabled={loading}
          style={refreshButtonStyle(loading)}
        >
          {loading ? "Refreshing..." : "Refresh CAPAs"}
        </button>
      </div>

      {error ? <div style={errorStyle}>{error}</div> : null}

      {statusSuccess ? <div style={successStyle}>{statusSuccess}</div> : null}

      {!error && items.length === 0 ? (
        <div style={emptyStyle}>
          No CAPA records found yet. Open a CAPA from the Governance Packet Preview, then refresh this panel.
        </div>
      ) : null}

      {items.length > 0 ? (
        <div style={{ overflowX: "auto", marginTop: "16px" }}>
          <table style={tableStyle}>
            <thead>
              <tr style={{ background: "#f3e8ff", color: "#581c87" }}>
                <th style={th}>CAPA</th>
                <th style={th}>Finding</th>
                <th style={th}>Vendor</th>
                <th style={th}>Title</th>
                <th style={th}>Status</th>
                <th style={th}>Due Date</th>
                <th style={th}>Created</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => {
                const isSelected = selected?.capa_id === item.capa_id;

                return (
                  <tr
                    key={item.capa_id}
                    onClick={() => setSelected(item)}
                    style={{
                      borderTop: "1px solid #e5e7eb",
                      cursor: "pointer",
                      background: isSelected ? "#faf5ff" : "#ffffff",
                    }}
                  >
                    <td style={td}>
                      <strong>{item.capa_number}</strong>
                    </td>
                    <td style={td}>#{item.finding_id ?? "—"}</td>
                    <td style={td}>{item.vendor_id ?? "—"}</td>
                    <td style={td}>{item.title || "—"}</td>
                    <td style={td}>
                      <strong style={{ color: statusColor(item.status) }}>
                        {item.status || "—"}
                      </strong>
                    </td>
                    <td style={td}>{formatDateOnly(item.due_date)}</td>
                    <td style={td}>{formatDate(item.created_at)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : null}

      {selected ? <CapaDetail item={selected} onStatusUpdate={handleStatusUpdate} updatingStatus={updatingStatus} /> : null}
    </section>
  );
}

function CapaDetail({
  item,
  onStatusUpdate,
  updatingStatus,
}: {
  item: CapaItem;
  onStatusUpdate: (item: CapaItem, status: string, note: string) => void;
  updatingStatus: string;
}) {
  return (
    <div style={detailPanelStyle}>
      <div style={eyebrowStyle}>CAPA Detail</div>

      <h3 style={{ margin: "6px 0 12px", color: "#0f172a" }}>
        {item.capa_number}: {item.title}
      </h3>

      <div style={detailGridStyle}>
        <InfoCard label="CAPA ID" value={`#${item.capa_id}`} />
        <InfoCard label="CAPA Number" value={item.capa_number || "—"} />
        <InfoCard label="Linked Finding" value={`#${item.finding_id ?? "—"}`} />
        <InfoCard label="Vendor ID" value={String(item.vendor_id ?? "—")} />
        <InfoCard label="Status" value={item.status || "—"} />
        <InfoCard label="Due Date" value={formatDateOnly(item.due_date)} />
        <InfoCard label="Created" value={formatDate(item.created_at)} />
        <InfoCard label="Closed" value={formatDate(item.closed_at)} />
      </div>

      <div style={detailSectionStyle}>
        <h4 style={{ margin: "0 0 8px", color: "#111827" }}>CAPA Description</h4>
        <p style={{ margin: 0, color: "#475569", lineHeight: 1.65 }}>
          {item.description || "No CAPA description provided."}
        </p>
      </div>

      <div style={detailSectionStyle}>
        <h4 style={{ margin: "0 0 8px", color: "#111827" }}>CAPA Status Actions</h4>
        <p style={{ margin: "0 0 12px", color: "#475569", lineHeight: 1.65 }}>
          Update the CAPA lifecycle status and create an auditable status-change event.
        </p>

        <div style={actionRowStyle}>
          <button
            type="button"
            onClick={() =>
              onStatusUpdate(item, "in_progress", "CAPA owner review started.")
            }
            disabled={Boolean(updatingStatus)}
            style={statusButtonStyle("#1d4ed8", updatingStatus === "in_progress")}
          >
            {updatingStatus === "in_progress" ? "Updating..." : "Start Progress"}
          </button>

          <button
            type="button"
            onClick={() =>
              onStatusUpdate(item, "pending_review", "CAPA ready for leadership or quality review.")
            }
            disabled={Boolean(updatingStatus)}
            style={statusButtonStyle("#a16207", updatingStatus === "pending_review")}
          >
            {updatingStatus === "pending_review" ? "Updating..." : "Mark Pending Review"}
          </button>

          <button
            type="button"
            onClick={() =>
              onStatusUpdate(item, "closed", "CAPA reviewed and closed after corrective action documentation.")
            }
            disabled={Boolean(updatingStatus)}
            style={statusButtonStyle("#166534", updatingStatus === "closed")}
          >
            {updatingStatus === "closed" ? "Updating..." : "Close CAPA"}
          </button>

          <button
            type="button"
            onClick={() =>
              onStatusUpdate(item, "overdue", "CAPA marked overdue for escalation.")
            }
            disabled={Boolean(updatingStatus)}
            style={statusButtonStyle("#991b1b", updatingStatus === "overdue")}
          >
            {updatingStatus === "overdue" ? "Updating..." : "Mark Overdue"}
          </button>
        </div>
      </div>

      <div style={footerStyle}>
        CAPA is linked to the enterprise finding and can be used for quality review,
        vendor escalation, and executive governance reporting.
      </div>
    </div>
  );
}

function InfoCard({ label, value }: { label: string; value: string }) {
  return (
    <div style={infoCardStyle}>
      <div style={infoLabelStyle}>{label}</div>
      <div style={infoValueStyle}>{value}</div>
    </div>
  );
}

function formatDate(value?: string) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

function formatDateOnly(value?: string) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString();
}

function statusColor(status?: string) {
  const s = (status || "").toLowerCase();
  if (s === "open") return "#7e22ce";
  if (s === "overdue") return "#991b1b";
  if (s === "closed") return "#166534";
  return "#334155";
}

const panelStyle: CSSProperties = {
  margin: "20px 0",
  padding: "20px",
  borderRadius: "18px",
  border: "1px solid #e9d5ff",
  background: "linear-gradient(135deg, #faf5ff 0%, #ffffff 100%)",
  boxShadow: "0 12px 28px rgba(15, 23, 42, 0.08)",
};

const eyebrowStyle: CSSProperties = {
  fontSize: "13px",
  fontWeight: 800,
  color: "#7e22ce",
  letterSpacing: "0.08em",
  textTransform: "uppercase",
};

const headerRowStyle: CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  gap: "12px",
  alignItems: "center",
  flexWrap: "wrap",
};

function refreshButtonStyle(loading: boolean): CSSProperties {
  return {
    border: "0",
    borderRadius: "12px",
    padding: "10px 14px",
    fontWeight: 800,
    cursor: loading ? "not-allowed" : "pointer",
    background: loading ? "#94a3b8" : "#7e22ce",
    color: "#ffffff",
  };
}


const successStyle: CSSProperties = {
  marginTop: "14px",
  padding: "12px",
  borderRadius: "12px",
  background: "#dcfce7",
  border: "1px solid #bbf7d0",
  color: "#166534",
  fontWeight: 800,
};

const actionRowStyle: CSSProperties = {
  display: "flex",
  gap: "10px",
  flexWrap: "wrap",
  marginTop: "10px",
};

function statusButtonStyle(background: string, active: boolean): CSSProperties {
  return {
    border: "0",
    borderRadius: "12px",
    padding: "10px 13px",
    background: active ? "#94a3b8" : background,
    color: "#ffffff",
    fontWeight: 900,
    cursor: active ? "not-allowed" : "pointer",
    boxShadow: "0 10px 18px rgba(15, 23, 42, 0.12)",
  };
}

const errorStyle: CSSProperties = {
  marginTop: "14px",
  padding: "12px",
  borderRadius: "12px",
  background: "#fef2f2",
  border: "1px solid #fecaca",
  color: "#991b1b",
  fontWeight: 700,
};

const emptyStyle: CSSProperties = {
  marginTop: "14px",
  padding: "12px",
  borderRadius: "12px",
  background: "#ffffff",
  border: "1px solid #e9d5ff",
  color: "#475569",
};

const tableStyle: CSSProperties = {
  width: "100%",
  borderCollapse: "collapse",
  background: "#ffffff",
  borderRadius: "14px",
  overflow: "hidden",
  fontSize: "14px",
};

const th: CSSProperties = {
  textAlign: "left",
  padding: "12px",
  fontWeight: 900,
  whiteSpace: "nowrap",
};

const td: CSSProperties = {
  padding: "12px",
  color: "#334155",
  verticalAlign: "top",
};

const detailPanelStyle: CSSProperties = {
  marginTop: "18px",
  padding: "18px",
  borderRadius: "18px",
  border: "1px solid #d8b4fe",
  background: "#ffffff",
  boxShadow: "0 16px 32px rgba(126, 34, 206, 0.12)",
};

const detailGridStyle: CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(170px, 1fr))",
  gap: "10px",
};

const infoCardStyle: CSSProperties = {
  padding: "12px",
  borderRadius: "14px",
  background: "#f8fafc",
  border: "1px solid #e2e8f0",
};

const infoLabelStyle: CSSProperties = {
  fontSize: "12px",
  color: "#64748b",
  fontWeight: 800,
};

const infoValueStyle: CSSProperties = {
  marginTop: "3px",
  fontWeight: 900,
  color: "#0f172a",
};

const detailSectionStyle: CSSProperties = {
  marginTop: "16px",
  paddingTop: "12px",
  borderTop: "1px solid #e5e7eb",
};

const footerStyle: CSSProperties = {
  marginTop: "16px",
  padding: "12px",
  borderRadius: "14px",
  background: "#faf5ff",
  color: "#581c87",
  fontWeight: 800,
  border: "1px solid #e9d5ff",
};

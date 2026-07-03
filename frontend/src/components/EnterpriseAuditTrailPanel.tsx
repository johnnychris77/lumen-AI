import { useEffect, useState } from "react";
import type { CSSProperties } from "react";

type AuditTrailItem = {
  id: number;
  tenant_id: string;
  actor_email: string;
  actor_role: string;
  action_type: string;
  resource_type: string;
  resource_id: string;
  status: string;
  request_method: string;
  request_path: string;
  details: string;
  compliance_flag: boolean;
  created_at: string;
};

import { api } from "@/lib/api";

export default function EnterpriseAuditTrailPanel() {
  const [items, setItems] = useState<AuditTrailItem[]>([]);
  const [selected, setSelected] = useState<AuditTrailItem | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function loadAuditTrail() {
    setLoading(true);
    setError("");

    try {
      const data = await api.get<{ items?: AuditTrailItem[] }>(
        "/api/enterprise/audit-trail?limit=10",
        {
          // Tenant scoping headers are specific to this panel; role/actor/token
          // are attached centrally by apiFetch.
          headers: {
            "X-Tenant-Id": "bonsecours",
            "X-Tenant-Name": "Bon Secours",
          },
        }
      );

      const nextItems = Array.isArray(data.items) ? data.items : [];
      setItems(nextItems);

      if (!selected && nextItems.length > 0) {
        setSelected(nextItems[0]);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown audit trail error");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadAuditTrail();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <section style={panelStyle}>
      <div style={eyebrowStyle}>Enterprise Audit Trail</div>

      <div style={headerRowStyle}>
        <div>
          <h2 style={{ margin: "8px 0 8px", color: "#0f172a" }}>
            Governance Activity Log
          </h2>
          <p style={{ margin: 0, color: "#475569", lineHeight: 1.6 }}>
            Shows recent enterprise workflow actions, actors, affected records,
            compliance relevance, and traceability for survey readiness.
          </p>
        </div>

        <button
          type="button"
          onClick={loadAuditTrail}
          disabled={loading}
          style={refreshButtonStyle(loading)}
        >
          {loading ? "Refreshing..." : "Refresh Audit Trail"}
        </button>
      </div>

      {error ? <div style={errorStyle}>{error}</div> : null}

      {!error && items.length === 0 ? (
        <div style={emptyStyle}>
          No enterprise audit events found yet. Create an intake or export a governance packet, then refresh this panel.
        </div>
      ) : null}

      {items.length > 0 ? (
        <div style={{ overflowX: "auto", marginTop: "16px" }}>
          <table style={tableStyle}>
            <thead>
              <tr style={{ background: "#fef3c7", color: "#78350f" }}>
                <th style={th}>Event</th>
                <th style={th}>Actor</th>
                <th style={th}>Role</th>
                <th style={th}>Resource</th>
                <th style={th}>Status</th>
                <th style={th}>Compliance</th>
                <th style={th}>Created</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => {
                const isSelected = selected?.id === item.id;

                return (
                  <tr
                    key={item.id}
                    onClick={() => setSelected(item)}
                    style={{
                      borderTop: "1px solid #e5e7eb",
                      cursor: "pointer",
                      background: isSelected ? "#fffbeb" : "#ffffff",
                    }}
                  >
                    <td style={td}>
                      <strong>{formatAction(item.action_type)}</strong>
                    </td>
                    <td style={td}>{item.actor_email || "unknown"}</td>
                    <td style={td}>{item.actor_role || "unknown"}</td>
                    <td style={td}>
                      {item.resource_type || "—"} #{item.resource_id || "—"}
                    </td>
                    <td style={td}>
                      <strong style={{ color: item.status === "success" ? "#166534" : "#991b1b" }}>
                        {item.status}
                      </strong>
                    </td>
                    <td style={td}>
                      {item.compliance_flag ? "Yes" : "No"}
                    </td>
                    <td style={td}>{formatDate(item.created_at)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : null}

      {selected ? <AuditDetail item={selected} /> : null}
    </section>
  );
}

function AuditDetail({ item }: { item: AuditTrailItem }) {
  return (
    <div style={detailPanelStyle}>
      <div style={eyebrowStyle}>Audit Event Detail</div>

      <h3 style={{ margin: "6px 0 12px", color: "#0f172a" }}>
        {formatAction(item.action_type)}
      </h3>

      <div style={detailGridStyle}>
        <InfoCard label="Audit ID" value={`#${item.id}`} />
        <InfoCard label="Tenant" value={item.tenant_id || "—"} />
        <InfoCard label="Actor" value={item.actor_email || "unknown"} />
        <InfoCard label="Role" value={item.actor_role || "unknown"} />
        <InfoCard label="Resource Type" value={item.resource_type || "—"} />
        <InfoCard label="Resource ID" value={item.resource_id || "—"} />
        <InfoCard label="Method" value={item.request_method || "—"} />
        <InfoCard label="Status" value={item.status || "—"} />
        <InfoCard label="Compliance Flag" value={item.compliance_flag ? "Yes" : "No"} />
        <InfoCard label="Created" value={formatDate(item.created_at)} />
      </div>

      <div style={detailSectionStyle}>
        <h4 style={{ margin: "0 0 8px", color: "#111827" }}>Request Path</h4>
        <div style={monoBlockStyle}>{item.request_path || "—"}</div>
      </div>

      <div style={detailSectionStyle}>
        <h4 style={{ margin: "0 0 8px", color: "#111827" }}>Event Details</h4>
        <pre style={preStyle}>{formatDetails(item.details)}</pre>
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

function formatAction(action?: string) {
  if (!action) return "Unknown Action";
  return action
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function formatDate(value?: string) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

function formatDetails(value?: string) {
  if (!value) return "{}";

  try {
    return JSON.stringify(JSON.parse(value), null, 2);
  } catch {
    return value;
  }
}

const panelStyle: CSSProperties = {
  margin: "20px 0",
  padding: "20px",
  borderRadius: "18px",
  border: "1px solid #fde68a",
  background: "linear-gradient(135deg, #fffbeb 0%, #ffffff 100%)",
  boxShadow: "0 12px 28px rgba(15, 23, 42, 0.08)",
};

const eyebrowStyle: CSSProperties = {
  fontSize: "13px",
  fontWeight: 800,
  color: "#b45309",
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
    background: loading ? "#94a3b8" : "#d97706",
    color: "#ffffff",
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
  border: "1px solid #fde68a",
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
  border: "1px solid #fcd34d",
  background: "#ffffff",
  boxShadow: "0 16px 32px rgba(217, 119, 6, 0.12)",
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

const monoBlockStyle: CSSProperties = {
  padding: "10px",
  borderRadius: "12px",
  background: "#f8fafc",
  border: "1px solid #e2e8f0",
  color: "#334155",
  fontFamily: "monospace",
  overflowX: "auto",
};

const preStyle: CSSProperties = {
  margin: 0,
  padding: "12px",
  borderRadius: "12px",
  background: "#0f172a",
  color: "#e2e8f0",
  fontSize: "13px",
  overflowX: "auto",
};

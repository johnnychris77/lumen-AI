import { useEffect, useState } from "react";

type IntakeHistoryItem = {
  finding_id: number;
  vendor_id?: number | null;
  instrument_id?: number | null;
  risk_score_id?: number | null;
  disposition_id?: number | null;
  vendor_name?: string;
  instrument_name?: string;
  instrument_category?: string;
  finding_category?: string;
  finding_description?: string;
  severity?: string;
  confidence_score?: number;
  risk_tier?: string;
  overall_score?: number;
  recommended_action?: string;
  final_action?: string;
  disposition_status?: string;
  workflow_status?: string;
  created_at?: string;
};

const API_BASE =
  import.meta.env.VITE_API_BASE_URL || "https://lumen-ai-53u4.onrender.com";

const AUTH_TOKEN = import.meta.env.VITE_AUTH_TOKEN || "dev-token";

export default function EnterpriseIntakeHistoryPanel() {
  const [items, setItems] = useState<IntakeHistoryItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function loadHistory() {
    setLoading(true);
    setError("");

    try {
      const response = await fetch(
        `${API_BASE}/api/enterprise/intake/history?limit=10`,
        {
          headers: {
            Authorization: `Bearer ${AUTH_TOKEN}`,
            "X-LumenAI-Role": "viewer",
            "X-LumenAI-Actor": "john-demo",
            "X-Tenant-Id": "bonsecours",
            "X-Tenant-Name": "Bon Secours",
          },
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data?.detail || `History request failed (${response.status})`);
      }

      setItems(Array.isArray(data.items) ? data.items : []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown history error");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadHistory();
  }, []);

  return (
    <section
      style={{
        margin: "20px 0",
        padding: "20px",
        borderRadius: "18px",
        border: "1px solid #c7d2fe",
        background: "linear-gradient(135deg, #eef2ff 0%, #ffffff 100%)",
        boxShadow: "0 12px 28px rgba(15, 23, 42, 0.08)",
      }}
    >
      <div
        style={{
          fontSize: "13px",
          fontWeight: 800,
          color: "#4338ca",
          letterSpacing: "0.08em",
          textTransform: "uppercase",
        }}
      >
        Enterprise Workflow Trace
      </div>

      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          gap: "12px",
          alignItems: "center",
          flexWrap: "wrap",
        }}
      >
        <div>
          <h2 style={{ margin: "8px 0 8px", color: "#0f172a" }}>
            Recent Enterprise Intake Records
          </h2>
          <p style={{ margin: 0, color: "#475569", lineHeight: 1.6 }}>
            Displays recent enterprise records created through the intake workflow.
          </p>
        </div>

        <button
          type="button"
          onClick={loadHistory}
          disabled={loading}
          style={{
            border: "0",
            borderRadius: "12px",
            padding: "10px 14px",
            fontWeight: 800,
            cursor: loading ? "not-allowed" : "pointer",
            background: loading ? "#94a3b8" : "#4f46e5",
            color: "#ffffff",
          }}
        >
          {loading ? "Refreshing..." : "Refresh History"}
        </button>
      </div>

      {error ? (
        <div
          style={{
            marginTop: "14px",
            padding: "12px",
            borderRadius: "12px",
            background: "#fef2f2",
            border: "1px solid #fecaca",
            color: "#991b1b",
            fontWeight: 700,
          }}
        >
          {error}
        </div>
      ) : null}

      {!error && items.length === 0 ? (
        <div
          style={{
            marginTop: "14px",
            padding: "12px",
            borderRadius: "12px",
            background: "#ffffff",
            border: "1px solid #e0e7ff",
            color: "#475569",
          }}
        >
          No enterprise intake records found yet. Use the Create Enterprise Intake button above, then refresh this panel.
        </div>
      ) : null}

      {items.length > 0 ? (
        <div style={{ overflowX: "auto", marginTop: "16px" }}>
          <table
            style={{
              width: "100%",
              borderCollapse: "collapse",
              background: "#ffffff",
              borderRadius: "14px",
              overflow: "hidden",
              fontSize: "14px",
            }}
          >
            <thead>
              <tr style={{ background: "#eef2ff", color: "#312e81" }}>
                <th style={th}>Finding</th>
                <th style={th}>Vendor</th>
                <th style={th}>Instrument</th>
                <th style={th}>Issue</th>
                <th style={th}>Severity</th>
                <th style={th}>Risk</th>
                <th style={th}>Action</th>
                <th style={th}>Workflow</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.finding_id} style={{ borderTop: "1px solid #e5e7eb" }}>
                  <td style={td}>#{item.finding_id}</td>
                  <td style={td}>{item.vendor_name || "—"}</td>
                  <td style={td}>{item.instrument_name || "—"}</td>
                  <td style={td}>{item.finding_category || "—"}</td>
                  <td style={td}>
                    <strong style={{ color: severityColor(item.severity) }}>
                      {item.severity || "—"}
                    </strong>
                  </td>
                  <td style={td}>
                    {item.risk_tier || "—"} / {item.overall_score ?? 0}
                  </td>
                  <td style={td}>{item.recommended_action || "—"}</td>
                  <td style={td}>{item.workflow_status || "pending"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </section>
  );
}

const th: React.CSSProperties = {
  textAlign: "left",
  padding: "12px",
  fontWeight: 900,
  whiteSpace: "nowrap",
};

const td: React.CSSProperties = {
  padding: "12px",
  color: "#334155",
  verticalAlign: "top",
};

function severityColor(severity?: string) {
  const s = (severity || "").toLowerCase();
  if (s === "critical") return "#991b1b";
  if (s === "high") return "#b45309";
  if (s === "moderate") return "#a16207";
  return "#166534";
}

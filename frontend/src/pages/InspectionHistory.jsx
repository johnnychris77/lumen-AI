import { useEffect, useMemo, useState } from "react";

const API_BASE =
  (import.meta.env.VITE_API_BASE_URL || "/api").replace(/\/$/, "");

function formatDate(value) {
  if (!value) return "—";
  try {
    return new Date(value).toLocaleString();
  } catch {
    return value;
  }
}

function statusBadge(status) {
  const base = {
    display: "inline-block",
    padding: "4px 10px",
    borderRadius: "999px",
    fontSize: "12px",
    fontWeight: 600,
  };

  switch ((status || "").toLowerCase()) {
    case "completed":
      return { ...base, background: "#dcfce7", color: "#166534" };
    case "queued":
      return { ...base, background: "#fef3c7", color: "#92400e" };
    case "running":
      return { ...base, background: "#dbeafe", color: "#1d4ed8" };
    case "failed":
      return { ...base, background: "#fee2e2", color: "#991b1b" };
    default:
      return { ...base, background: "#e5e7eb", color: "#374151" };
  }
}

function reportActions(item) {
  const reportUrl = `${API_BASE}/reports/${item.id}.pdf`;
  const isCompleted = String(item.status).toLowerCase() === "completed";

  if (!isCompleted) {
    return <span style={{ color: "#6b7280" }}>Report pending</span>;
  }

  return (
    <div style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
      <a
        href={reportUrl}
        target="_blank"
        rel="noreferrer"
        style={actionLinkPrimary}
        title={`Open report for inspection #${item.id}`}
      >
        Open Report
      </a>

      <a
        href={reportUrl}
        download
        style={actionLinkSecondary}
        title={`Download PDF for inspection #${item.id}`}
      >
        Download PDF
      </a>
    </div>
  );
}

export default function InspectionHistory() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const token = useMemo(() => localStorage.getItem("token") || "", []);

  useEffect(() => {
    let ignore = false;

    async function load() {
      setLoading(true);
      setError("");

      try {
        const res = await fetch(`${API_BASE}/history?limit=50`, {
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        });

        if (!res.ok) {
          const text = await res.text();
          throw new Error(`History request failed (${res.status}): ${text}`);
        }

        const data = await res.json();
        const normalized = Array.isArray(data) ? data : data.items || [];

        if (!ignore) {
          setItems(normalized);
        }
      } catch (err) {
        if (!ignore) {
          setError(err.message || "Failed to load history.");
        }
      } finally {
        if (!ignore) {
          setLoading(false);
        }
      }
    }

    load();
    return () => {
      ignore = true;
    };
  }, [token]);

  return (
    <div style={{ padding: "24px", maxWidth: "1400px", margin: "0 auto" }}>
      <div style={{ marginBottom: "16px" }}>
        <h1 style={{ margin: 0 }}>Inspection History</h1>
        <p style={{ color: "#4b5563" }}>
          Review completed and in-progress LumenAI inspections, model metadata,
          and PDF reports.
        </p>
      </div>

      {loading && <p>Loading inspection history...</p>}

      {!loading && error && (
        <div
          style={{
            background: "#fee2e2",
            color: "#991b1b",
            padding: "12px 16px",
            borderRadius: "8px",
          }}
        >
          {error}
        </div>
      )}

      {!loading && !error && items.length === 0 && (
        <div
          style={{
            background: "#f9fafb",
            border: "1px solid #e5e7eb",
            padding: "16px",
            borderRadius: "8px",
          }}
        >
          No inspections found yet.
        </div>
      )}

      {!loading && !error && items.length > 0 && (
        <div style={{ overflowX: "auto" }}>
          <table
            style={{
              width: "100%",
              borderCollapse: "collapse",
              background: "#fff",
              border: "1px solid #e5e7eb",
              borderRadius: "12px",
              overflow: "hidden",
            }}
          >
            <thead style={{ background: "#f9fafb" }}>
              <tr>
                <th style={th}>ID</th>
                <th style={th}>File</th>
                <th style={th}>Created</th>
                <th style={th}>Status</th>
                <th style={th}>Stain</th>
                <th style={th}>Confidence</th>
                <th style={th}>Material</th>
                <th style={th}>Model</th>
                <th style={th}>Inference Time</th>
                <th style={th}>Report</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.id} style={{ borderTop: "1px solid #e5e7eb" }}>
                  <td style={td}>{item.id}</td>
                  <td style={td}>{item.file_name || "—"}</td>
                  <td style={td}>{formatDate(item.created_at)}</td>
                  <td style={td}>
                    <span style={statusBadge(item.status)}>
                      {item.status || "unknown"}
                    </span>
                  </td>
                  <td style={td}>
                    {item.stain_detected === true
                      ? "Yes"
                      : item.stain_detected === false
                      ? "No"
                      : "—"}
                  </td>
                  <td style={td}>
                    {typeof item.confidence === "number"
                      ? item.confidence.toFixed(2)
                      : "—"}
                  </td>
                  <td style={td}>{item.material_type || "—"}</td>
                  <td style={td}>
                    <div>{item.model_name || "—"}</div>
                    <div style={{ color: "#6b7280", fontSize: "12px" }}>
                      v{item.model_version || "—"}
                    </div>
                  </td>
                  <td style={td}>{formatDate(item.inference_timestamp)}</td>
                  <td style={td}>{reportActions(item)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

const th = {
  textAlign: "left",
  padding: "12px",
  fontSize: "13px",
  color: "#374151",
  whiteSpace: "nowrap",
};

const td = {
  padding: "12px",
  fontSize: "14px",
  color: "#111827",
  verticalAlign: "top",
};

const actionLinkPrimary = {
  display: "inline-block",
  padding: "6px 10px",
  borderRadius: "8px",
  background: "#111827",
  color: "#ffffff",
  textDecoration: "none",
  fontSize: "13px",
  fontWeight: 600,
};

const actionLinkSecondary = {
  display: "inline-block",
  padding: "6px 10px",
  borderRadius: "8px",
  background: "#f3f4f6",
  color: "#111827",
  textDecoration: "none",
  fontSize: "13px",
  fontWeight: 600,
  border: "1px solid #d1d5db",
};

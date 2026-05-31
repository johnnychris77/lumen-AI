import React, { useEffect, useState } from "react";

const API_BASE =
  import.meta.env.VITE_API_BASE_URL || "https://lumen-ai-53u4.onrender.com";

export default function VendorGovernancePanel() {
  const [summary, setSummary] = useState(null);
  const [events, setEvents] = useState([]);
  const [linkageSummary, setLinkageSummary] = useState(null);
  const [errorMessage, setErrorMessage] = useState("");
  const [creating, setCreating] = useState(false);

  async function loadVendorGovernance() {
    try {
      setErrorMessage("");

      const [summaryResponse, eventsResponse, linkageResponse] = await Promise.all([
        fetch(`${API_BASE}/api/enterprise/vendor-governance/summary`),
        fetch(`${API_BASE}/api/enterprise/vendor-governance/events?limit=10`),
        fetch(`${API_BASE}/api/enterprise/vendor-governance/capa-linkage-summary`),
      ]);

      if (!summaryResponse.ok) {
        throw new Error(`Vendor summary returned ${summaryResponse.status}`);
      }

      if (!eventsResponse.ok) {
        throw new Error(`Vendor events returned ${eventsResponse.status}`);
      }

      if (!linkageResponse.ok) {
        throw new Error(`Vendor CAPA linkage returned ${linkageResponse.status}`);
      }

      const summaryJson = await summaryResponse.json();
      const eventsJson = await eventsResponse.json();
      const linkageJson = await linkageResponse.json();

      setSummary(summaryJson.summary || {});
      setEvents(eventsJson.items || []);
      setLinkageSummary(linkageJson.summary || {});
    } catch (error) {
      setErrorMessage(
        error.message || "Unable to load Vendor Governance data."
      );
    }
  }



  function downloadVendorPowerBiCsv() {
    window.open(
      `${API_BASE}/api/enterprise/vendor-governance/powerbi-csv?limit=500`,
      "_blank"
    );
  }

  async function createCapaFromVendorEvent(eventId) {
    try {
      setErrorMessage("");

      const response = await fetch(
        `${API_BASE}/api/enterprise/vendor-governance/events/${eventId}/create-capa`,
        {
          method: "POST",
        }
      );

      if (!response.ok) {
        throw new Error(`Create CAPA from vendor event returned ${response.status}`);
      }

      await loadVendorGovernance();
    } catch (error) {
      setErrorMessage(
        error.message || "Unable to create CAPA from vendor event."
      );
    }
  }

  async function createSampleVendorEvent() {
    try {
      setCreating(true);
      setErrorMessage("");

      const response = await fetch(
        `${API_BASE}/api/enterprise/vendor-governance/events`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            vendor_name: "Stryker",
            event_type: "Vendor Tray Quality Signal",
            event_summary:
              "Vendor tray quality signal identified and routed for governance review.",
            risk_level: "high",
            site: "ORC",
            device_or_tray: "Orthopedic vendor tray",
            owner: "Quality / Operations",
          }),
        }
      );

      if (!response.ok) {
        throw new Error(`Create vendor event returned ${response.status}`);
      }

      await loadVendorGovernance();
    } catch (error) {
      setErrorMessage(
        error.message || "Unable to create Vendor Governance event."
      );
    } finally {
      setCreating(false);
    }
  }

  useEffect(() => {
    loadVendorGovernance();
  }, []);

  const safeSummary = summary || {
    total_vendor_events: 0,
    open_vendor_events: 0,
    high_risk_vendor_events: 0,
    vendor_events_linked_to_capa: 0,
    top_vendors: [],
  };

  const safeLinkageSummary = linkageSummary || {
    total_vendor_events: 0,
    vendor_events_linked_to_capa: 0,
    vendor_events_without_capa: 0,
    high_risk_vendor_events_without_capa: 0,
  };

  return (
    <section
      style={{
        marginTop: "24px",
        border: "1px solid #bae6fd",
        borderRadius: "24px",
        background: "#ffffff",
        boxShadow: "0 12px 32px rgba(15, 23, 42, 0.08)",
        padding: "24px",
      }}
    >
      <div
        style={{
          display: "inline-flex",
          borderRadius: "999px",
          background: "#f0f9ff",
          color: "#0369a1",
          padding: "6px 12px",
          fontSize: "12px",
          fontWeight: 800,
          border: "1px solid #bae6fd",
          marginBottom: "10px",
        }}
      >
        Vendor Governance · Quality Accountability
      </div>

      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          gap: "16px",
          flexWrap: "wrap",
          alignItems: "flex-start",
        }}
      >
        <div>
          <h2 style={{ margin: 0, fontSize: "24px", color: "#0f172a" }}>
            Vendor Governance Panel
          </h2>

          <p style={{ marginTop: "8px", color: "#475569", lineHeight: 1.6 }}>
            Tracks vendor quality signals, high-risk vendor events, vendor trend
            concentration, and vendor events linked to CAPA governance review.
          </p>
        </div>

        <div
          style={{
            display: "flex",
            gap: "10px",
            flexWrap: "wrap",
            justifyContent: "flex-end",
          }}
        >
          <button
            onClick={downloadVendorPowerBiCsv}
            style={{
              border: "1px solid #bae6fd",
              borderRadius: "999px",
              background: "#f0f9ff",
              color: "#0369a1",
              padding: "12px 18px",
              fontWeight: 800,
              cursor: "pointer",
              boxShadow: "0 8px 20px rgba(3, 105, 161, 0.12)",
            }}
          >
            Download Vendor Power BI CSV
          </button>

          <button
            onClick={createSampleVendorEvent}
            disabled={creating}
            style={{
              border: "none",
              borderRadius: "999px",
              background: creating ? "#94a3b8" : "#0369a1",
              color: "#ffffff",
              padding: "12px 18px",
              fontWeight: 800,
              cursor: creating ? "not-allowed" : "pointer",
              boxShadow: "0 8px 20px rgba(3, 105, 161, 0.22)",
            }}
          >
            {creating ? "Creating Event..." : "Create Vendor Event"}
          </button>
        </div>
      </div>

      {errorMessage && (
        <div
          style={{
            marginTop: "16px",
            borderRadius: "16px",
            border: "1px solid #fecaca",
            background: "#fef2f2",
            color: "#991b1b",
            padding: "14px",
            fontWeight: 700,
          }}
        >
          {errorMessage}
        </div>
      )}

      {!errorMessage && (
        <>
          <div
            style={{
              marginTop: "20px",
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(170px, 1fr))",
              gap: "14px",
            }}
          >
            <MetricCard
              label="Total Vendor Events"
              value={safeSummary.total_vendor_events}
              tone="neutral"
            />
            <MetricCard
              label="Open Vendor Events"
              value={safeSummary.open_vendor_events}
              tone={safeSummary.open_vendor_events > 0 ? "warning" : "neutral"}
            />
            <MetricCard
              label="High-Risk Vendor Events"
              value={safeSummary.high_risk_vendor_events}
              tone={
                safeSummary.high_risk_vendor_events > 0 ? "danger" : "neutral"
              }
            />
            <MetricCard
              label="Linked to CAPA"
              value={safeSummary.vendor_events_linked_to_capa}
              tone="good"
            />
            <MetricCard
              label="Without CAPA"
              value={safeLinkageSummary.vendor_events_without_capa}
              tone={safeLinkageSummary.vendor_events_without_capa > 0 ? "warning" : "good"}
            />
            <MetricCard
              label="High-Risk Without CAPA"
              value={safeLinkageSummary.high_risk_vendor_events_without_capa}
              tone={safeLinkageSummary.high_risk_vendor_events_without_capa > 0 ? "danger" : "good"}
            />
          </div>

          <div
            style={{
              marginTop: "22px",
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
              gap: "14px",
            }}
          >
            <TopVendors vendors={safeSummary.top_vendors || []} />
            <VendorEvents events={events} onCreateCapa={createCapaFromVendorEvent} />
          </div>
        </>
      )}
    </section>
  );
}

function MetricCard({ label, value, tone }) {
  const styles = {
    neutral: {
      border: "#e2e8f0",
      background: "#f8fafc",
      value: "#0f172a",
    },
    good: {
      border: "#bbf7d0",
      background: "#f0fdf4",
      value: "#15803d",
    },
    warning: {
      border: "#fde68a",
      background: "#fffbeb",
      value: "#b45309",
    },
    danger: {
      border: "#fecaca",
      background: "#fef2f2",
      value: "#b91c1c",
    },
  };

  const selected = styles[tone] || styles.neutral;

  return (
    <div
      style={{
        borderRadius: "18px",
        border: `1px solid ${selected.border}`,
        background: selected.background,
        padding: "16px",
      }}
    >
      <div
        style={{
          color: "#64748b",
          fontSize: "12px",
          textTransform: "uppercase",
          letterSpacing: "0.08em",
          fontWeight: 800,
        }}
      >
        {label}
      </div>
      <div
        style={{
          marginTop: "6px",
          color: selected.value,
          fontSize: "28px",
          fontWeight: 900,
        }}
      >
        {value ?? 0}
      </div>
    </div>
  );
}

function TopVendors({ vendors }) {
  return (
    <div
      style={{
        borderRadius: "18px",
        border: "1px solid #e2e8f0",
        background: "#f8fafc",
        padding: "16px",
      }}
    >
      <h3 style={{ margin: 0, color: "#0f172a", fontSize: "17px" }}>
        Top Vendors
      </h3>

      {vendors.length === 0 ? (
        <p style={{ marginTop: "10px", color: "#64748b" }}>
          No vendor trend data available.
        </p>
      ) : (
        <div style={{ marginTop: "12px", display: "grid", gap: "10px" }}>
          {vendors.slice(0, 5).map((vendor) => (
            <div
              key={vendor.vendor_name}
              style={{
                display: "flex",
                justifyContent: "space-between",
                gap: "12px",
                borderRadius: "14px",
                background: "#ffffff",
                border: "1px solid #e2e8f0",
                padding: "12px",
              }}
            >
              <strong style={{ color: "#0f172a" }}>
                {vendor.vendor_name}
              </strong>
              <span style={{ color: "#0369a1", fontWeight: 900 }}>
                {vendor.event_count}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function VendorEvents({ events, onCreateCapa }) {
  return (
    <div
      style={{
        borderRadius: "18px",
        border: "1px solid #e2e8f0",
        background: "#f8fafc",
        padding: "16px",
      }}
    >
      <h3 style={{ margin: 0, color: "#0f172a", fontSize: "17px" }}>
        Recent Vendor Quality Signals
      </h3>

      {events.length === 0 ? (
        <p style={{ marginTop: "10px", color: "#64748b" }}>
          No vendor events available.
        </p>
      ) : (
        <div style={{ marginTop: "12px", display: "grid", gap: "10px" }}>
          {events.slice(0, 5).map((event) => (
            <div
              key={event.id}
              style={{
                borderRadius: "14px",
                background: "#ffffff",
                border: "1px solid #e2e8f0",
                padding: "12px",
              }}
            >
              <div style={{ fontWeight: 900, color: "#0f172a" }}>
                {event.vendor_name} · {event.event_type}
              </div>
              <div style={{ marginTop: "6px", color: "#475569" }}>
                {event.event_summary}
              </div>
              <div style={{ marginTop: "6px", color: "#64748b" }}>
                Site: {event.site || "Not specified"} · Risk:{" "}
                {event.risk_level || "medium"} · Owner:{" "}
                {event.owner || "Quality / Operations"}
              </div>

              {event.capa_id ? (
                <div
                  style={{
                    marginTop: "10px",
                    color: "#15803d",
                    fontWeight: 800,
                    fontSize: "13px",
                  }}
                >
                  Linked CAPA: {event.capa_id}
                </div>
              ) : (
                <button
                  onClick={() => onCreateCapa(event.id)}
                  style={{
                    marginTop: "10px",
                    border: "1px solid #bbf7d0",
                    borderRadius: "999px",
                    background: "#f0fdf4",
                    color: "#15803d",
                    padding: "8px 12px",
                    fontWeight: 800,
                    cursor: "pointer",
                  }}
                >
                  Create CAPA
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

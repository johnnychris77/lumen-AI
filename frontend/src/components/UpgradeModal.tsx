import React, { useState } from "react";
import { apiFetch } from "@/lib/api";

interface UpgradeModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentTier: string;
  requiredTier: string;
  feature: string;
  tenantId: string;
}

const TIER_DISPLAY = {
  standard: { label: "Standard", price: "Free", color: "#6b7280" },
  professional: { label: "Professional", price: "$1,200/mo per hospital", color: "#2563eb" },
  enterprise: { label: "Enterprise", price: "Custom pricing", color: "#7c3aed" },
};

export function UpgradeModal({ isOpen, onClose, currentTier, requiredTier, feature, tenantId }: UpgradeModalProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const API = import.meta.env.VITE_API_BASE_URL ?? "";
  const token = localStorage.getItem("token") || "";

  if (!isOpen) return null;

  const handleUpgrade = async () => {
    setLoading(true);
    setError("");
    try {
      const r = await apiFetch(`/api/billing/checkout`, { raw: true,
        method: "POST",
        headers: { "Authorization": `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({
          tenant_id: tenantId,
          target_tier: requiredTier,
          success_url: `${window.location.origin}/billing/success`,
          cancel_url: `${window.location.origin}/billing/upgrade`,
        }),
      });
      const data = await r.json();
      if (data.checkout_url) {
        window.location.href = data.checkout_url;
      } else if (data.status === "sandbox") {
        setError("Stripe not configured — set STRIPE_SECRET_KEY to enable live checkout.");
      } else {
        setError(data.message || "Unable to start checkout");
      }
    } catch {
      setError("Network error — please try again");
    } finally {
      setLoading(false);
    }
  };

  const tier = TIER_DISPLAY[requiredTier as keyof typeof TIER_DISPLAY] || TIER_DISPLAY.enterprise;

  return (
    <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)", zIndex: 1000, display: "flex", alignItems: "center", justifyContent: "center" }}>
      <div style={{ background: "#fff", borderRadius: 12, padding: 32, maxWidth: 460, width: "100%", boxShadow: "0 20px 60px rgba(0,0,0,0.3)" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 20 }}>
          <div>
            <div style={{ fontSize: 11, fontWeight: 700, color: tier.color, textTransform: "uppercase", letterSpacing: 1, marginBottom: 4 }}>Upgrade Required</div>
            <h2 style={{ margin: 0, fontSize: 20, color: "#111" }}>Unlock {feature.replace(/_/g, " ")}</h2>
          </div>
          <button onClick={onClose} style={{ background: "none", border: "none", cursor: "pointer", fontSize: 20, color: "#6b7280" }}>✕</button>
        </div>

        <div style={{ background: "#f8fafc", borderRadius: 8, padding: 16, marginBottom: 20, borderLeft: `4px solid ${tier.color}` }}>
          <div style={{ fontSize: 13, color: "#6b7280", marginBottom: 4 }}>You are on <strong>{currentTier}</strong> tier</div>
          <div style={{ fontSize: 15, color: "#111" }}>This feature requires <strong style={{ color: tier.color }}>{tier.label}</strong> tier</div>
          <div style={{ fontSize: 13, color: "#6b7280", marginTop: 4 }}>{tier.price}</div>
        </div>

        {/* Feature comparison */}
        <div style={{ marginBottom: 20 }}>
          {[
            { tier: "standard", features: ["Shared defect signals", "Instrument risk patterns"] },
            { tier: "professional", features: ["+ FDA Recall intelligence", "+ CAPA effectiveness"] },
            { tier: "enterprise", features: ["+ Executive dashboard", "+ Trend analytics", "+ Manufacturer portal"] },
          ].map(row => (
            <div key={row.tier} style={{ display: "flex", alignItems: "flex-start", gap: 10, padding: "6px 0", opacity: row.tier === currentTier || row.tier === requiredTier ? 1 : 0.4 }}>
              <span style={{ color: row.tier === requiredTier ? tier.color : "#22c55e", fontWeight: 700, minWidth: 16 }}>{row.tier === requiredTier ? "★" : "✓"}</span>
              <div>
                <div style={{ fontSize: 12, fontWeight: 600, color: "#374151", textTransform: "capitalize" }}>{row.tier}</div>
                <div style={{ fontSize: 12, color: "#6b7280" }}>{row.features.join(" · ")}</div>
              </div>
            </div>
          ))}
        </div>

        {error && <div style={{ background: "#fef2f2", color: "#dc2626", padding: "8px 12px", borderRadius: 6, fontSize: 13, marginBottom: 16 }}>{error}</div>}

        <div style={{ display: "flex", gap: 10 }}>
          {requiredTier === "enterprise" ? (
            <a href="mailto:sales@lumenai.com" style={{ flex: 1, textAlign: "center", padding: "12px 0", background: tier.color, color: "#fff", borderRadius: 8, fontWeight: 600, fontSize: 14, textDecoration: "none" }}>
              Contact Sales
            </a>
          ) : (
            <button onClick={handleUpgrade} disabled={loading} style={{ flex: 1, padding: "12px 0", background: tier.color, color: "#fff", border: "none", borderRadius: 8, fontWeight: 600, fontSize: 14, cursor: loading ? "not-allowed" : "pointer", opacity: loading ? 0.7 : 1 }}>
              {loading ? "Redirecting to Stripe…" : `Upgrade to ${tier.label}`}
            </button>
          )}
          <button onClick={onClose} style={{ padding: "12px 20px", background: "#f3f4f6", color: "#374151", border: "none", borderRadius: 8, fontWeight: 600, fontSize: 14, cursor: "pointer" }}>
            Maybe later
          </button>
        </div>
      </div>
    </div>
  );
}

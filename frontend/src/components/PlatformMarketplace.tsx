/**
 * v5.0 — LumenAI OS: Project Infinity — AI Skills Marketplace &
 * Application Marketplace.
 *
 * Frontend route `/marketplace`, API prefix `/api/infinity`. A listing
 * can only be published once every Certification Program gate (Section
 * 7) has passed — installing an unpublished listing is rejected.
 */
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

const TABS = ["Browse Listings", "My Installations", "Certification"] as const;
type Tab = (typeof TABS)[number];

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <h3 className="mb-3 text-sm font-semibold text-slate-700">{title}</h3>
      {children}
    </div>
  );
}

export default function PlatformMarketplace() {
  const [activeTab, setActiveTab] = useState<Tab>("Browse Listings");
  const [listingType, setListingType] = useState("");
  const [listings, setListings] = useState<Record<string, unknown>[] | null>(null);
  const [installations, setInstallations] = useState<Record<string, unknown>[] | null>(null);
  const [certListingId, setCertListingId] = useState("");
  const [certStatus, setCertStatus] = useState<Record<string, unknown> | null>(null);

  useEffect(() => {
    if (activeTab === "Browse Listings") {
      const q = listingType ? `?listing_type=${listingType}` : "";
      api.get(`/api/infinity/marketplace/listings${q}`).then((r: Record<string, unknown>) => setListings(r.listings as Record<string, unknown>[])).catch(() => {});
    }
    if (activeTab === "My Installations") {
      api.get("/api/infinity/marketplace/installations").then((r: Record<string, unknown>) => setInstallations(r.installations as Record<string, unknown>[])).catch(() => {});
    }
  }, [activeTab, listingType]);

  async function install(listingId: number) {
    await api.post("/api/infinity/marketplace/installations", { listing_id: listingId });
    api.get("/api/infinity/marketplace/installations").then((r: Record<string, unknown>) => setInstallations(r.installations as Record<string, unknown>[])).catch(() => {});
  }

  async function checkCertification() {
    if (!certListingId.trim()) return;
    const res = await api.get<Record<string, unknown>>(`/api/infinity/certification/listings/${certListingId}`);
    setCertStatus(res);
  }

  return (
    <div className="space-y-4 p-4">
      <h1 className="text-xl font-bold text-slate-800">Marketplace</h1>
      <p className="text-xs text-slate-400">
        AI Skills and Applications from Hospital, Manufacturer, Repair Vendor, Academic, Research, Enterprise,
        and Consulting developers — every listing is versioned and certified before publication.
      </p>

      <div className="flex flex-wrap gap-1">
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => setActiveTab(t)}
            className={`rounded px-3 py-1 text-sm ${activeTab === t ? "bg-indigo-600 text-white" : "bg-slate-100 text-slate-600"}`}
          >
            {t}
          </button>
        ))}
      </div>

      {activeTab === "Browse Listings" && (
        <Section title="Published Listings">
          <select className="mb-3 rounded border border-slate-300 p-1 text-sm" value={listingType} onChange={(e) => setListingType(e.target.value)}>
            <option value="">All types</option>
            <option value="ai_skill">AI Skills</option>
            <option value="application">Applications</option>
          </select>
          {listings?.map((l) => (
            <div key={String(l.id)} className="mb-2 flex items-center justify-between border-b border-slate-100 pb-2 text-sm">
              <div>
                <span className="font-medium">{String(l.name)}</span> — {String(l.listing_type)} / {String(l.category)}
                {" "}(v{String(l.version)}, {String(l.status)})
              </div>
              <button className="rounded bg-indigo-600 px-3 py-1 text-xs text-white" onClick={() => install(Number(l.id))}>Install</button>
            </div>
          ))}
        </Section>
      )}

      {activeTab === "My Installations" && (
        <Section title="Installed Listings">
          {installations?.map((i) => (
            <div key={String(i.id)} className="mb-2 border-b border-slate-100 pb-2 text-sm">
              Listing #{String(i.listing_id)} — v{String(i.installed_version)} ({String(i.status)})
            </div>
          ))}
        </Section>
      )}

      {activeTab === "Certification" && (
        <Section title="Check Certification Status">
          <div className="mb-3 flex gap-2">
            <input className="flex-1 rounded border border-slate-300 p-2 text-sm" placeholder="Listing ID" value={certListingId}
              onChange={(e) => setCertListingId(e.target.value)} />
            <button className="rounded bg-indigo-600 px-4 py-1 text-sm text-white" onClick={checkCertification}>Check</button>
          </div>
          {certStatus && (
            <div className="text-sm">
              <p>Status: <span className="font-medium">{String(certStatus.certification_status)}</span></p>
              <p className="mt-2 text-xs text-slate-400">Gates: {(certStatus.gates as string[])?.join(" → ")}</p>
            </div>
          )}
        </Section>
      )}
    </div>
  );
}

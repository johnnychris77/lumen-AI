const API_HOST = window.location.hostname;
const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || `http://${API_HOST}:18122`;

async function handleResponse(response, label) {
  if (!response.ok) {
    const details = await response.text();
    throw new Error(`${label}: ${response.status} ${details}`);
  }

  return response.json();
}

export async function fetchCapaDashboardSummary() {
  const response = await fetch(`${API_BASE_URL}/api/capa/dashboard/summary`, {
    headers: {
      Authorization: "Bearer dev-token",
      "X-Tenant-Id": "bonsecours",
      "X-Tenant-Name": "Bon Secours",
    },
  });

  return handleResponse(response, "Failed to fetch CAPA dashboard summary");
}

export async function updateCapaStatus(capaId, status, note = "") {
  const response = await fetch(`${API_BASE_URL}/api/capa/${capaId}/status`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      Authorization: "Bearer dev-token",
      "X-Tenant-Id": "bonsecours",
      "X-Tenant-Name": "Bon Secours",
    },
    body: JSON.stringify({ status, note }),
  });

  return handleResponse(response, "Failed to update CAPA status");
}

export async function addCapaUpdate(
  capaId,
  updateType,
  content,
  author = "Dashboard User"
) {
  const response = await fetch(`${API_BASE_URL}/api/capa/${capaId}/update`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      Authorization: "Bearer dev-token",
      "X-Tenant-Id": "bonsecours",
      "X-Tenant-Name": "Bon Secours",
    },
    body: JSON.stringify({
      update_type: updateType,
      content,
      author,
    }),
  });

  return handleResponse(response, "Failed to add CAPA update");
}

export async function addCapaEvidence(
  capaId,
  evidenceName,
  evidenceType,
  evidenceUrl,
  addedBy = "Dashboard User"
) {
  const response = await fetch(`${API_BASE_URL}/api/capa/${capaId}/evidence`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: "Bearer dev-token",
      "X-Tenant-Id": "bonsecours",
      "X-Tenant-Name": "Bon Secours",
    },
    body: JSON.stringify({
      evidence_name: evidenceName,
      evidence_type: evidenceType,
      evidence_url: evidenceUrl,
      added_by: addedBy,
    }),
  });

  return handleResponse(response, "Failed to add CAPA evidence");
}

export async function fetchCapaById(capaId) {
  const response = await fetch(`${API_BASE_URL}/api/capa/${capaId}`, {
    headers: {
      Authorization: "Bearer dev-token",
      "X-Tenant-Id": "bonsecours",
      "X-Tenant-Name": "Bon Secours",
    },
  });

  return handleResponse(response, "Failed to fetch CAPA details");
}

export async function fetchCapaReport(capaId) {
  const response = await fetch(`${API_BASE_URL}/api/capa/${capaId}/report`, {
    headers: {
      Authorization: "Bearer dev-token",
      "X-Tenant-Id": "bonsecours",
      "X-Tenant-Name": "Bon Secours",
    },
  });

  return handleResponse(response, "Failed to fetch CAPA report");
}

export async function closeCapaWithVerification(capaId, note = "") {
  const response = await fetch(`${API_BASE_URL}/api/capa/${capaId}/close-with-verification`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: "Bearer dev-token",
      "X-Tenant-Id": "bonsecours",
      "X-Tenant-Name": "Bon Secours",
    },
    body: JSON.stringify({
      note,
    }),
  });

  return handleResponse(response, "Failed to close CAPA with verification");
}

export async function fetchCapaAnalytics(filters = {}) {
  const params = new URLSearchParams();

  if (filters.status) params.append("status", filters.status);
  if (filters.facility) params.append("facility", filters.facility);
  if (filters.vendor) params.append("vendor", filters.vendor);
  if (filters.risk_level) params.append("risk_level", filters.risk_level);

  const query = params.toString();
  const url = query
    ? `${API_BASE_URL}/api/capa/analytics/trends?${query}`
    : `${API_BASE_URL}/api/capa/analytics/trends`;

  const response = await fetch(url, {
    headers: {
      Authorization: "Bearer dev-token",
      "X-Tenant-Id": "bonsecours",
      "X-Tenant-Name": "Bon Secours",
    },
  });

  return handleResponse(response, "Failed to fetch CAPA analytics");
}

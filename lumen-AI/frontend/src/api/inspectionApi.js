const API_HOST = window.location.hostname;
const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || `http://${API_HOST}:18121`;

async function handleResponse(response, label) {
  if (!response.ok) {
    const details = await response.text();
    throw new Error(`${label}: ${response.status} ${details}`);
  }

  return response.json();
}

export async function createInspectionIntake(payload) {
  const response = await fetch(`${API_BASE_URL}/api/inspections/intake`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: "Bearer dev-token",
      "X-Tenant-Id": "bonsecours",
      "X-Tenant-Name": "Bon Secours",
    },
    body: JSON.stringify(payload),
  });

  return handleResponse(response, "Failed to create inspection intake");
}

export async function fetchInspections(filters = {}) {
  const params = new URLSearchParams();

  if (filters.facility) params.append("facility", filters.facility);
  if (filters.vendor) params.append("vendor", filters.vendor);
  if (filters.risk_level) params.append("risk_level", filters.risk_level);
  if (filters.capa_required !== undefined && filters.capa_required !== "") {
    params.append("capa_required", filters.capa_required);
  }

  const query = params.toString();
  const url = query
    ? `${API_BASE_URL}/api/inspections/?${query}`
    : `${API_BASE_URL}/api/inspections/`;

  const response = await fetch(url, {
    headers: {
      Authorization: "Bearer dev-token",
      "X-Tenant-Id": "bonsecours",
      "X-Tenant-Name": "Bon Secours",
    },
  });

  return handleResponse(response, "Failed to fetch inspections");
}

export async function fetchInspectionById(inspectionId) {
  const response = await fetch(`${API_BASE_URL}/api/inspections/${inspectionId}`, {
    headers: {
      Authorization: "Bearer dev-token",
      "X-Tenant-Id": "bonsecours",
      "X-Tenant-Name": "Bon Secours",
    },
  });

  return handleResponse(response, "Failed to fetch inspection");
}

export async function createCapaFromInspection(inspectionId, payload = {}) {
  const response = await fetch(
    `${API_BASE_URL}/api/inspections/${inspectionId}/create-capa`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: "Bearer dev-token",
        "X-Tenant-Id": "bonsecours",
        "X-Tenant-Name": "Bon Secours",
      },
      body: JSON.stringify(payload),
    }
  );

  return handleResponse(response, "Failed to create CAPA from inspection");
}

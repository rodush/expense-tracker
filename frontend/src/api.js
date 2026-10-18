export async function uploadFile(file) {
  const formData = new FormData();
  formData.append("file", file);
  const response = await fetch("/upload", { method: "POST", body: formData });
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.detail || "Upload failed.");
  }
  return payload;
}

function buildFilterParams(filters = {}, { paging = false } = {}) {
  const params = new URLSearchParams();
  (filters.categories ?? []).forEach((value) =>
    params.append("category", value),
  );
  (filters.who ?? []).forEach((value) => params.append("who", value));
  if (filters.dateFrom) params.set("date_from", filters.dateFrom);
  if (filters.dateTo) params.set("date_to", filters.dateTo);
  if (filters.year) params.set("year", filters.year);
  if (filters.month) params.set("month", filters.month);
  if (paging) {
    params.set("limit", filters.limit ?? 25);
    params.set("offset", filters.offset ?? 0);
  }
  return params;
}

async function getJson(url, fallbackMessage, signal) {
  const response = await fetch(url, { signal });
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.detail || fallbackMessage);
  }
  return payload;
}

export function fetchExpenses(filters, signal) {
  return getJson(
    `/expenses?${buildFilterParams(filters, { paging: true })}`,
    "Unable to load expenses.",
    signal,
  );
}

export function fetchSummary(filters, signal) {
  return getJson(
    `/expenses/summary?${buildFilterParams(filters)}`,
    "Unable to load summary.",
    signal,
  );
}

export function fetchFilterOptions(signal) {
  return getJson(
    "/expenses/filter-options",
    "Unable to load expense filters.",
    signal,
  );
}

export function buildExportUrl(filters) {
  return `/expenses/export?${buildFilterParams(filters)}`;
}

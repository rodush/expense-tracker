export async function uploadFile(file) {
  const formData = new FormData();
  formData.append('file', file);
  const response = await fetch('/upload', { method: 'POST', body: formData });
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.detail || 'Upload failed.');
  }
  return payload;
}

export async function fetchSummary(datasetId, selectedCategories, selectedPeople, signal) {
  const params = new URLSearchParams();
  selectedCategories.forEach((value) => params.append('category', value));
  selectedPeople.forEach((value) => params.append('who', value));
  const response = await fetch(
    `/datasets/${encodeURIComponent(datasetId)}/summary?${params}`,
    { signal },
  );
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.detail || 'Unable to load summary.');
  }
  return payload;
}

export function buildExportUrl(datasetId, categories, people) {
  const params = new URLSearchParams();
  categories.forEach((value) => params.append('category', value));
  people.forEach((value) => params.append('who', value));
  return `/datasets/${encodeURIComponent(datasetId)}/export?${params}`;
}

<script>
  import { onDestroy } from 'svelte';
  import { fetchSummary, uploadFile, buildExportUrl } from './api';
  import DashboardPanel from './components/DashboardPanel.svelte';
  import PreviewPanel from './components/PreviewPanel.svelte';
  import UploadPanel from './components/UploadPanel.svelte';

  let isUploading = $state(false);
  let uploadError = $state('');
  let datasetId = $state(null);
  let downloadId = $state(null);
  let previewRows = $state([]);
  let categoryOptions = $state([]);
  let whoOptions = $state([]);
  let selectedCategories = $state([]);
  let selectedPeople = $state([]);
  let summary = $state(null);
  let isDashboardLoading = $state(false);
  let dashboardError = $state('');
  let summaryController;

  const filteredRows = $derived(previewRows.filter((row) =>
    (!selectedCategories.length || selectedCategories.includes(row.category))
    && (!selectedPeople.length || selectedPeople.includes(row.who))
  ));
  const filteredDownloadUrl = $derived(datasetId
    ? buildExportUrl(datasetId, selectedCategories, selectedPeople)
    : '');

  async function handleUpload(file, fileInput) {
    if (!file) {
      uploadError = 'Please choose a file first.';
      fileInput?.setAttribute('aria-describedby', 'error');
      fileInput?.setAttribute('aria-invalid', 'true');
      return;
    }

    fileInput.setAttribute('aria-invalid', 'false');
    isUploading = true;
    uploadError = '';
    downloadId = null;

    try {
      const payload = await uploadFile(file);
      datasetId = payload.dataset_id;
      downloadId = payload.download_id;
      previewRows = payload.preview;
      categoryOptions = [...new Set(previewRows.map((row) => row.category).filter(Boolean))].sort();
      whoOptions = [...new Set(previewRows.map((row) => row.who).filter(Boolean))].sort();
      selectedCategories = [];
      selectedPeople = [];
      summary = null;
      await loadSummary(payload.dataset_id, [], []);
    } catch (err) {
      uploadError = err instanceof Error ? err.message : 'Something went wrong.';
    } finally {
      isUploading = false;
    }
  }

  async function loadSummary(
    targetDatasetId = datasetId,
    categories = selectedCategories,
    people = selectedPeople,
  ) {
    if (!targetDatasetId) return;
    summaryController?.abort();
    const requestController = new AbortController();
    summaryController = requestController;
    isDashboardLoading = true;
    dashboardError = '';

    try {
      const payload = await fetchSummary(
        targetDatasetId,
        categories,
        people,
        requestController.signal,
      );
      if (requestController.signal.aborted) return;
      summary = payload;
    } catch (err) {
      if (err instanceof Error && err.name !== 'AbortError') {
        dashboardError = err.message;
      }
    } finally {
      if (!requestController.signal.aborted) isDashboardLoading = false;
    }
  }

  function clearFilters() {
    selectedCategories = [];
    selectedPeople = [];
    loadSummary();
  }

  onDestroy(() => summaryController?.abort());
</script>

<main class="container">
  <UploadPanel {isUploading} {uploadError} onupload={handleUpload} />
  <PreviewPanel
    rows={filteredRows}
    {downloadId}
    {datasetId}
    {filteredDownloadUrl}
  />
  {#if datasetId}
    <DashboardPanel
      {categoryOptions}
      {whoOptions}
      bind:selectedCategories
      bind:selectedPeople
      {summary}
      isLoading={isDashboardLoading}
      error={dashboardError}
      onfilterschange={() => loadSummary()}
      onclearfilters={clearFilters}
    />
  {/if}
</main>

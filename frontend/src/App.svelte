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

  async function handleUpload(file) {
    if (!file) {
      uploadError = 'Please choose a file first.';
      return;
    }

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

<main class="container app-shell">
  {#if !datasetId}
    <section class="welcome" aria-labelledby="welcomeHeading">
      <div class="welcome-copy">
        <p class="eyebrow">A clearer view of your spending</p>
        <h1 id="welcomeHeading">Make sense of your spending.</h1>
        <p class="welcome-lede">
          Turn a bank statement into a simple picture of where your money goes.
          Start with a CSV or Excel file.
        </p>
        <ul class="welcome-steps" aria-label="What you can do">
          <li>
            <span class="step-number" aria-hidden="true">01</span>
            <span><strong>Upload a statement</strong><small>CSV, XLS, and XLSX files</small></span>
          </li>
          <li>
            <span class="step-number" aria-hidden="true">02</span>
            <span><strong>See the big picture</strong><small>Totals and category breakdowns</small></span>
          </li>
          <li>
            <span class="step-number" aria-hidden="true">03</span>
            <span><strong>Explore the details</strong><small>Filter transactions and export them</small></span>
          </li>
        </ul>
      </div>
      <UploadPanel {isUploading} {uploadError} onupload={handleUpload} />
    </section>
  {:else}
    <section class="results" aria-labelledby="resultsHeading">
      <header class="results-heading">
        <div>
          <p class="eyebrow">Your statement is ready</p>
          <h1 id="resultsHeading">Your spending, at a glance.</h1>
          <p>Use the filters to focus on the expenses you want to review.</p>
        </div>
        <span class="ready-badge"><span aria-hidden="true">✓</span> Analysis complete</span>
      </header>
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
      <PreviewPanel
        rows={filteredRows}
        {downloadId}
        {datasetId}
        {filteredDownloadUrl}
      />
      <details class="upload-another">
        <summary>Analyze another statement</summary>
        <UploadPanel {isUploading} {uploadError} onupload={handleUpload} />
      </details>
    </section>
  {/if}
</main>

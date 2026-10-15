<script>
  import { uploadFile, buildExportUrl } from './api';
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
  const filteredRows = $derived(previewRows.filter((row) =>
    (!selectedCategories.length || selectedCategories.includes(row.category))
    && (!selectedPeople.length || selectedPeople.includes(row.who))
  ));
  const filteredDownloadUrl = $derived(datasetId
    ? buildExportUrl(datasetId, selectedCategories, selectedPeople)
    : '');
  const summary = $derived.by(() => {
    const totalCents = filteredRows.reduce((sum, row) => sum + Math.round(Number(row.amount ?? 0) * 100), 0);
    const aggregate = (field) => {
      const groups = new Map();
      for (const row of filteredRows) {
        const name = String(row[field] ?? '');
        const group = groups.get(name) ?? { name, cents: 0, count: 0 };
        group.cents += Math.round(Number(row.amount ?? 0) * 100);
        group.count += 1;
        groups.set(name, group);
      }
      return [...groups.values()].map(({ name, cents, count }) => ({ name, amount: cents / 100, count }));
    };
    const categories = aggregate('category').map((item) => ({
      ...item,
      percentage: totalCents ? Math.round(item.amount * 10000 / totalCents) / 100 : 0,
    }));
    return {
      expense_count: filteredRows.length,
      total_amount: totalCents / 100,
      categories,
      who: aggregate('who'),
    };
  });

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
    } catch (err) {
      uploadError = err instanceof Error ? err.message : 'Something went wrong.';
    } finally {
      isUploading = false;
    }
  }

  function clearFilters() {
    selectedCategories = [];
    selectedPeople = [];
  }
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

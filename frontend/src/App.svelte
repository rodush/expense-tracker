<script>
  import { onMount } from "svelte";
  import {
    uploadFile,
    fetchExpenses,
    fetchFilterOptions,
    fetchSummary,
    buildExportUrl,
  } from "./api";
  import DashboardPanel from "./components/DashboardPanel.svelte";
  import PreviewPanel from "./components/PreviewPanel.svelte";
  import UploadPanel from "./components/UploadPanel.svelte";

  const pageSize = 25;
  let isUploading = $state(false);
  let uploadError = $state("");
  let uploadMessage = $state("");
  let hasUploaded = $state(false);
  let historyError = $state("");
  let isLoadingHistory = $state(false);
  let rows = $state([]);
  let totalCount = $state(0);
  let summary = $state(null);
  let categoryOptions = $state([]);
  let whoOptions = $state([]);
  let years = $state([]);
  let selectedCategories = $state([]);
  let selectedPeople = $state([]);
  let dateFrom = $state("");
  let dateTo = $state("");
  let selectedYear = $state("");
  let selectedMonth = $state("");
  let offset = $state(0);
  let activeRequest = 0;

  function currentFilters(paging = false) {
    return {
      categories: [...selectedCategories],
      who: [...selectedPeople],
      dateFrom,
      dateTo,
      year: selectedYear,
      month: selectedMonth,
      ...(paging ? { limit: pageSize, offset } : {}),
    };
  }

  const filteredDownloadUrl = $derived(buildExportUrl(currentFilters()));

  async function refreshFilterOptions() {
    try {
      const options = await fetchFilterOptions();
      categoryOptions = options.categories ?? [];
      whoOptions = options.who ?? [];
      years = options.years ?? [];
    } catch (error) {
      historyError =
        error instanceof Error
          ? error.message
          : "Unable to load expense filters.";
    }
  }

  async function loadHistory() {
    const requestId = ++activeRequest;
    isLoadingHistory = true;
    historyError = "";
    const filters = currentFilters(true);
    try {
      const [page, totals] = await Promise.all([
        fetchExpenses(filters),
        fetchSummary(filters),
      ]);
      if (requestId !== activeRequest) return;
      rows = page.items ?? [];
      totalCount = page.total_count ?? 0;
      summary = totals;
    } catch (error) {
      if (requestId !== activeRequest) return;
      historyError =
        error instanceof Error
          ? error.message
          : "Unable to load saved expenses.";
    } finally {
      if (requestId === activeRequest) isLoadingHistory = false;
    }
  }

  function handleFilterChange(kind = "categories") {
    offset = 0;
    if (kind === "range") {
      selectedYear = "";
      selectedMonth = "";
    } else if (kind === "quick") {
      dateFrom = "";
      dateTo = "";
      if (!selectedYear) selectedMonth = "";
    }
    loadHistory();
  }

  function clearFilters() {
    selectedCategories = [];
    selectedPeople = [];
    dateFrom = "";
    dateTo = "";
    selectedYear = "";
    selectedMonth = "";
    offset = 0;
    loadHistory();
  }

  async function handleUpload(file) {
    if (!file) {
      uploadError = "Please choose a file first.";
      return;
    }

    isUploading = true;
    uploadError = "";
    uploadMessage = "";
    try {
      const result = await uploadFile(file);
      hasUploaded = true;
      uploadMessage = `${result.new_transaction_count ?? 0} new expenses added; ${result.duplicate_count ?? 0} duplicates skipped.`;
      await refreshFilterOptions();
      offset = 0;
      await loadHistory();
    } catch (error) {
      uploadError =
        error instanceof Error ? error.message : "Something went wrong.";
    } finally {
      isUploading = false;
    }
  }

  function previousPage() {
    offset = Math.max(0, offset - pageSize);
    loadHistory();
  }

  function nextPage() {
    if (offset + pageSize < totalCount) {
      offset += pageSize;
      loadHistory();
    }
  }

  onMount(() => {
    refreshFilterOptions();
    loadHistory();
  });
</script>

<main class="container app-shell">
  <section
    class="welcome"
    class:welcome-after-upload={hasUploaded}
    aria-labelledby="welcomeHeading"
  >
    {#if !hasUploaded}
      <div class="welcome-copy">
        <p class="eyebrow">Your household spending ledger</p>
        <h1 id="welcomeHeading">Make sense of your spending.</h1>
        <p class="welcome-lede">
          Import a bank statement to add new expenses. Your saved history stays
          here so you can browse spending over time.
        </p>
      </div>
    {/if}
    <UploadPanel {isUploading} {uploadError} onupload={handleUpload} />
  </section>

  {#if uploadMessage}
    <p class="success-message" role="status">{uploadMessage}</p>
  {/if}

  <section
    class="results"
    aria-labelledby="resultsHeading"
    aria-busy={isLoadingHistory}
  >
    <header class="results-heading">
      <div>
        <p class="eyebrow">All imported transactions</p>
        <h2 id="resultsHeading">Expense history</h2>
        <p>Filter expenses by category, person, and transaction date.</p>
      </div>
    </header>
    {#if historyError}
      <p class="error-message" role="alert">{historyError}</p>
    {/if}
    <DashboardPanel
      {categoryOptions}
      {whoOptions}
      {years}
      bind:selectedCategories
      bind:selectedPeople
      bind:dateFrom
      bind:dateTo
      bind:selectedYear
      bind:selectedMonth
      {summary}
      onclearfilters={clearFilters}
      onfilterchange={handleFilterChange}
    />
    <PreviewPanel
      {rows}
      {totalCount}
      {offset}
      limit={pageSize}
      loading={isLoadingHistory}
      {filteredDownloadUrl}
      onprevious={previousPage}
      onnext={nextPage}
    />
  </section>
</main>

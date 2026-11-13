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
  let uploadAccordion = $state();
  let historyError = $state("");
  let filterError = $state("");
  let ledgerHasExpenses = $state(false);
  let initialLoadComplete = $state(false);
  let sortBy = $state("date");
  let sortDirection = $state("desc");
  const hasFilters = $derived(
    selectedCategories.length ||
      selectedPeople.length ||
      dateFrom ||
      dateTo ||
      selectedYear ||
      selectedMonth,
  );
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
      ...(paging ? { limit: pageSize, offset, sortBy, sortDirection } : {}),
    };
  }

  const filteredDownloadUrl = $derived(buildExportUrl(currentFilters()));

  async function refreshFilterOptions() {
    try {
      filterError = "";
      const options = await fetchFilterOptions();
      categoryOptions = options.categories ?? [];
      whoOptions = options.who ?? [];
      years = options.years ?? [];
      ledgerHasExpenses =
        years.length > 0 || categoryOptions.length > 0 || whoOptions.length > 0;
    } catch (error) {
      filterError =
        error instanceof Error
          ? error.message
          : "Unable to load expense filters.";
    }
  }

  async function loadHistory() {
    const requestId = ++activeRequest;
    isLoadingHistory = true;
    historyError = "";
    rows = [];
    summary = null;
    if (dateFrom && dateTo && dateFrom > dateTo) {
      historyError = "The start date must not be after the end date.";
      isLoadingHistory = false;
      return;
    }
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
      if (page.total_count > 0) ledgerHasExpenses = true;
      if (!initialLoadComplete) {
        initialLoadComplete = true;
        if (!ledgerHasExpenses && !hasFilters && uploadAccordion)
          uploadAccordion.open = true;
      }
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
      if (uploadAccordion) uploadAccordion.open = false;
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

  function changeSort(key) {
    sortDirection = sortBy === key && sortDirection === "asc" ? "desc" : "asc";
    sortBy = key;
    offset = 0;
    loadHistory();
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
    class:returning={ledgerHasExpenses}
    aria-labelledby={hasUploaded || ledgerHasExpenses
      ? undefined
      : "welcomeHeading"}
  >
    {#if !hasUploaded && !ledgerHasExpenses}
      <div class="welcome-copy">
        <p class="eyebrow">Your household spending ledger</p>
        <h1 id="welcomeHeading">Make sense of your spending.</h1>
        <p class="welcome-lede">
          Import a bank statement to add new expenses. Your saved history stays
          here so you can browse spending over time.
        </p>
      </div>
    {/if}
    <details bind:this={uploadAccordion} class="upload-accordion">
      <summary class="upload-accordion-summary">
        <span class="upload-icon" aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="none">
            <path d="M12 16V4m0 0L7.5 8.5M12 4l4.5 4.5M5 14v5h14v-5" />
          </svg>
        </span>
        <span class="upload-accordion-title">
          <span class="eyebrow">Start here</span>
          <span id="uploadHeading">Upload an expense statement</span>
        </span>
      </summary>
      <UploadPanel
        embedded
        {isUploading}
        {uploadError}
        onupload={handleUpload}
      />
    </details>
  </section>

  {#if uploadMessage}
    <p class="success-message" role="status">
      {uploadMessage}
      <a href="#transactionsHeading">
        Review transaction categories and people
      </a>
    </p>
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
    {#if filterError}
      <p class="error-message" role="alert">{filterError}</p>
      <button type="button" onclick={refreshFilterOptions}>
        Retry filters
      </button>
    {/if}
    {#if historyError}
      <p id="reportError" class="error-message" role="alert">{historyError}</p>
      <button type="button" onclick={loadHistory}>Retry report</button>
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
    {#if isLoadingHistory}
      <p class="empty-state" role="status">Loading report…</p>
    {:else if !historyError && summary?.expense_count === 0}
      <p class="empty-state" role="status">
        {hasFilters
          ? "No expenses match these filters. Clear filters to see everything."
          : "Your ledger is empty. Import a statement to get started."}
      </p>
    {:else if !historyError && summary}
      <PreviewPanel
        {rows}
        {totalCount}
        {offset}
        limit={pageSize}
        {sortBy}
        {sortDirection}
        onsort={changeSort}
        {filteredDownloadUrl}
        onprevious={previousPage}
        onnext={nextPage}
      />
    {/if}
  </section>
</main>

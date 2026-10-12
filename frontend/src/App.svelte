<script>
  import { onDestroy, tick } from 'svelte';
  import { uploadFile, fetchSummary, buildExportUrl } from './api';
  import { createOrUpdateCategoryChart, destroyCategoryChart } from './chart';
  import {
    tooltipText,
    tooltipRowIndex,
    tooltipLeft,
    tooltipTop,
    descriptionTooltipElement,
    showDescriptionTooltip,
    positionDescriptionTooltip,
    hideDescriptionTooltip,
  } from './tooltip';

  let fileInput;
  let isUploading = false;
  let uploadError = '';
  let datasetId = null;
  let downloadId = null;
  let previewRows = [];
  let categoryOptions = [];
  let whoOptions = [];
  let selectedCategories = [];
  let selectedPeople = [];
  let summary = null;
  let isDashboardLoading = false;
  let dashboardError = '';
  let summaryController;
  let categoryChartCanvas;
  let categoryChartAmounts = [];

  $: filteredRows = previewRows.filter((row) =>
    (!selectedCategories.length || selectedCategories.includes(row.category))
    && (!selectedPeople.length || selectedPeople.includes(row.who))
  );
  $: activeFilters = [
    ...selectedCategories.map((value) => `category: ${value}`),
    ...selectedPeople.map((value) => `who: ${value}`),
  ];
  let filteredDownloadUrl;
  $: {
    if (datasetId) {
      filteredDownloadUrl = buildExportUrl(datasetId, selectedCategories, selectedPeople);
    }
  }

  async function handleUpload() {
    const file = fileInput?.files?.[0];
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

      destroyCategoryChart();
      datasetId = payload.dataset_id;
      downloadId = payload.download_id;
      previewRows = payload.preview;
      categoryOptions = [...new Set(previewRows.map((row) => row.category).filter(Boolean))].sort();
      whoOptions = [...new Set(previewRows.map((row) => row.who).filter(Boolean))].sort();
      selectedCategories = [];
      selectedPeople = [];
      summary = null;
      await loadSummary();
    } catch (err) {
      uploadError = err instanceof Error ? err.message : 'Something went wrong.';
    } finally {
      isUploading = false;
    }
  }

  async function loadSummary() {
    if (!datasetId) return;
    summaryController?.abort();
    const requestController = new AbortController();
    summaryController = requestController;
    isDashboardLoading = true;
    dashboardError = '';

    try {
      const payload = await fetchSummary(
        datasetId,
        selectedCategories,
        selectedPeople,
        requestController.signal,
      );
      if (requestController.signal.aborted) return;
      summary = payload;
      await renderCategoryChart(payload.categories);
    } catch (err) {
      if (err instanceof Error && err.name !== 'AbortError') {
        showDashboardError(err.message);
      }
    } finally {
      if (!requestController.signal.aborted) isDashboardLoading = false;
    }
  }

  async function renderCategoryChart(items) {
    categoryChartAmounts = categories.map((item) => item.amount);
    await tick();

    createOrUpdateCategoryChart(categoryChartCanvas, items, categoryChartAmounts);
  }


  function formatAmount(amount) {
    return Number(amount).toFixed(2);
  }

  function showDashboardError(message) {
    dashboardError = message;
  }


  onDestroy(() => {
    summaryController?.abort();
    destroyCategoryChart();
  });
</script>

<main class="container">
  <div class="panel">
    <p>Upload a CSV, XLS, or XLSX expense file to categorize descriptions with Gemini.</p>
    <input
      bind:this={fileInput}
      id="fileInput"
      type="file"
      accept=".csv,.xls,.xlsx"
      aria-errormessage="error"
    />
    <button id="uploadButton" onclick={handleUpload} disabled={isUploading}>
      {isUploading ? 'Processing...' : 'Upload & Categorize'}
    </button>
    {#if isUploading}<div id="loading" role="status">Processing...</div>{/if}
    {#if uploadError}<div id="error" class="error" role="alert">{uploadError}</div>{/if}
  </div>

  <article>
    <h2>Preview</h2>
    <details>
      <summary>Categorized expenses (preview)</summary>
      <table id="resultsTable">
        <colgroup>
          <col />
          <col />
          <col />
          <col />
          <col class="description-column" />
        </colgroup>
        <thead>
          <tr>
            <th>Date</th>
            <th>Amount</th>
            <th>Who</th>
            <th>Category</th>
            <th>Description</th>
          </tr>
        </thead>
        <tbody>
          {#each filteredRows as row, index}
            <tr>
              <td>{row.date ?? ''}</td>
              <td>{row.amount ?? ''}</td>
              <td>{row.who ?? ''}</td>
              <td>{row.category ?? ''}</td>
              <td
                class="description-cell"
                tabindex="0"
                aria-describedby={tooltipRowIndex === index ? 'descriptionTooltip' : undefined}
                onmouseover={(event) =>
                  showDescriptionTooltip(index, row.description, event.clientX, event.clientY)}
                onmousemove={(event) => {
                  if (tooltipRowIndex === index) {
                    positionDescriptionTooltip(event.clientX, event.clientY);
                  }
                }}
                onmouseout={(event) => hideDescriptionTooltip(event, index)}
                onfocus={(event) => {
                  const bounds = event.currentTarget.getBoundingClientRect();
                  showDescriptionTooltip(
                    index,
                    row.description,
                    bounds.left + bounds.width / 2,
                    bounds.top + bounds.height / 2,
                  );
                }}
                onblur={(event) => hideDescriptionTooltip(event, index)}
              >{row.description ?? ''}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    </details>
    <p>
      {#if downloadId}
        <a id="downloadLink" href={`/download/${encodeURIComponent(downloadId)}`}>
          Download full categorized CSV
        </a>
      {/if}
      {#if datasetId}
        <a id="filteredDownloadLink" href={filteredDownloadUrl}>
          Download current filtered CSV
        </a>
      {/if}
    </p>
  </article>

  {#if datasetId}
    <section id="dashboard" aria-labelledby="dashboardHeading">
      <h2 id="dashboardHeading">Spending dashboard</h2>
      <form id="filterForm" onsubmit={(event) => event.preventDefault()}>
        <div class="grid">
          <label for="categoryFilter">Categories
            <select
              bind:value={selectedCategories}
              id="categoryFilter"
              multiple
              size="5"
              aria-describedby="filterHelp"
              onchange={loadSummary}
            >
              {#each categoryOptions as category}
                <option value={category}>{category}</option>
              {/each}
            </select>
          </label>
          <label for="whoFilter">Who
            <select
              bind:value={selectedPeople}
              id="whoFilter"
              multiple
              size="5"
              aria-describedby="filterHelp"
              onchange={loadSummary}
            >
              {#each whoOptions as person}
                <option value={person}>{person}</option>
              {/each}
            </select>
          </label>
        </div>
        <small id="filterHelp">Use Ctrl or Command while selecting multiple values.</small>
        <button
          id="clearFilters"
          type="button"
          class="secondary"
          disabled={!selectedCategories.length && !selectedPeople.length}
          onclick={() => {
            selectedCategories = [];
            selectedPeople = [];
            loadSummary();
          }}
        >Clear filters</button>
        <p id="activeFilters" aria-live="polite">
          {activeFilters.length ? `Active filters: ${activeFilters.join(', ')}` : 'No filters active.'}
        </p>
      </form>

      {#if isDashboardLoading}<div id="dashboardLoading" role="status">Loading summary...</div>{/if}
      {#if dashboardError}<div id="dashboardError" class="error" role="alert">{dashboardError}</div>{/if}
      {#if summary?.expense_count === 0}
        <div id="dashboardEmpty" role="status">No expenses match the selected filters.</div>
      {/if}
      {#if summary}
        <div id="dashboardContent">
          <div class="dashboard-grid">
            <article><strong>Total</strong><p id="totalAmount">{formatAmount(summary.total_amount)}</p></article>
            <article><strong>Expenses</strong><p id="expenseCount">{summary.expense_count}</p></article>
          </div>
          <article>
            <header><strong>Spending by category</strong></header>
            <div class="chart-container">
              <canvas
                bind:this={categoryChartCanvas}
                id="categoryChart"
                role="img"
                aria-label="Doughnut chart showing spending by category"
              ></canvas>
            </div>
            <table id="categoryTable">
              <caption>Category totals</caption>
              <thead><tr><th>Category</th><th>Amount</th><th>Count</th></tr></thead>
              <tbody>
                {#each summary.categories as item}
                  <tr><td>{item.name}</td><td>{formatAmount(item.amount)}</td><td>{item.count}</td></tr>
                {/each}
              </tbody>
            </table>
          </article>
          <article>
            <header><strong>Spending by person</strong></header>
            <table id="whoTable">
              <caption>Person totals</caption>
              <thead><tr><th>Person</th><th>Amount</th><th>Count</th></tr></thead>
              <tbody>
                {#each summary.who as item}
                  <tr><td>{item.name}</td><td>{formatAmount(item.amount)}</td><td>{item.count}</td></tr>
                {/each}
              </tbody>
            </table>
          </article>
        </div>
      {/if}
    </section>
  {/if}
</main>

{#if tooltipRowIndex !== null}
  <div
    bind:this={descriptionTooltipElement}
    id="descriptionTooltip"
    class="description-tooltip"
    role="tooltip"
    style={`left: ${tooltipLeft}px; top: ${tooltipTop}px;`}
  >{tooltipText}</div>
{/if}

<style>
  .dashboard-grid {
    display: grid;
    gap: 1rem;
    grid-template-columns: repeat(auto-fit, minmax(12rem, 1fr));
  }

  .chart-container {
    height: 22rem;
    position: relative;
  }

  #resultsTable {
    table-layout: fixed;
    width: 100%;
  }

  #resultsTable col.description-column {
    width: 300px;
  }

  #resultsTable .description-cell {
    max-width: 300px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .description-tooltip {
    background: var(--pico-color);
    border-radius: var(--pico-border-radius);
    color: var(--pico-background-color);
    max-width: min(24rem, calc(100vw - 1.5rem));
    max-height: calc(100vh - 1rem);
    overflow-wrap: anywhere;
    overflow-y: auto;
    padding: 0.5rem 0.75rem;
    pointer-events: none;
    position: fixed;
    white-space: normal;
    z-index: 1000;
  }
</style>

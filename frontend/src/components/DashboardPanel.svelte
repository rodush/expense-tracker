<script>
  import { onDestroy } from 'svelte';
  import { createOrUpdateCategoryChart, destroyCategoryChart } from '../chart';

  let {
    categoryOptions,
    whoOptions,
    selectedCategories = $bindable([]),
    selectedPeople = $bindable([]),
    summary,
    isLoading,
    error,
    onfilterschange,
    onclearfilters,
  } = $props();
  let categoryChartCanvas = $state();

  const activeFilters = $derived([
    ...selectedCategories.map((value) => `category: ${value}`),
    ...selectedPeople.map((value) => `who: ${value}`),
  ]);

  $effect(() => {
    const categories = summary?.categories;
    if (categories && categoryChartCanvas) {
      createOrUpdateCategoryChart(
        categoryChartCanvas,
        categories,
        categories.map((item) => item.amount),
      );
    } else if (!summary) {
      destroyCategoryChart();
    }
  });

  function formatAmount(amount) {
    return new Intl.NumberFormat(undefined, {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(Number(amount));
  }

  onDestroy(destroyCategoryChart);
</script>

<section id="dashboard" class="dashboard" aria-labelledby="dashboardHeading" aria-busy={isLoading}>
  <header class="section-heading">
    <div>
      <p class="eyebrow">Overview</p>
      <h2 id="dashboardHeading">Spending overview</h2>
    </div>
    {#if isLoading}<span class="loading-note" role="status">Updating…</span>{/if}
  </header>

  <section class="filter-card" aria-labelledby="filterHeading">
    <div class="filter-card-heading">
      <div>
        <h3 id="filterHeading">Filter your expenses</h3>
        <p>Choose one or more options to narrow this report.</p>
      </div>
      <button
        id="clearFilters"
        type="button"
        class="clear-filter-button"
        disabled={!selectedCategories.length && !selectedPeople.length}
        onclick={onclearfilters}
      >Clear filters</button>
    </div>
    <div id="filterForm" class="filter-groups">
      <fieldset class="filter-group">
        <legend>Category</legend>
        <div class="filter-options">
          {#each categoryOptions as category}
            <label>
              <input
                bind:group={selectedCategories}
                type="checkbox"
                value={category}
                onchange={onfilterschange}
              />
              {category}
            </label>
          {/each}
        </div>
      </fieldset>
      <fieldset class="filter-group">
        <legend>Person</legend>
        <div class="filter-options">
          {#each whoOptions as person}
            <label>
              <input
                bind:group={selectedPeople}
                type="checkbox"
                value={person}
                onchange={onfilterschange}
              />
              {person}
            </label>
          {/each}
        </div>
      </fieldset>
    </div>
    <p id="activeFilters" class="active-filters" aria-live="polite">
      {activeFilters.length ? `Showing ${activeFilters.join(' · ')}` : 'Showing all expenses'}
    </p>
  </section>

  {#if error}<p id="dashboardError" class="error-message" role="alert">{error}</p>{/if}
  {#if summary?.expense_count === 0}
    <p id="dashboardEmpty" class="empty-state" role="status">
      <strong>No expenses match these filters.</strong>
      <span>Try choosing different options or clear the filters to see everything.</span>
    </p>
  {/if}
  {#if summary}
    <div id="dashboardContent" class="report-grid">
      <section class="summary-cards" aria-label="Spending totals">
        <article class="summary-card summary-card-primary">
          <span class="metric-icon" aria-hidden="true">↗</span>
          <p class="metric-label">Total spend</p>
          <p id="totalAmount" class="metric-value">{formatAmount(summary.total_amount)}</p>
        </article>
        <article class="summary-card">
          <span class="metric-icon metric-icon-muted" aria-hidden="true">#</span>
          <p class="metric-label">Transactions</p>
          <p id="expenseCount" class="metric-value">{summary.expense_count}</p>
        </article>
      </section>

      <div class="breakdown-grid">
        <section class="breakdown-card" aria-labelledby="categoryHeading">
          <header class="breakdown-heading">
            <div><p class="eyebrow">Where it goes</p><h3 id="categoryHeading">By category</h3></div>
          </header>
          <div class="chart-container">
            <canvas
              bind:this={categoryChartCanvas}
              id="categoryChart"
              aria-label="Doughnut chart showing spending by category"
            ></canvas>
          </div>
          <div class="table-scroll">
            <table id="categoryTable">
              <caption>Spending totals by category</caption>
              <thead><tr><th scope="col">Category</th><th scope="col">Amount</th><th scope="col">Count</th></tr></thead>
              <tbody>
                {#each summary.categories as item}
                  <tr><th scope="row">{item.name}</th><td>{formatAmount(item.amount)}</td><td>{item.count}</td></tr>
                {/each}
              </tbody>
            </table>
          </div>
        </section>

        <section class="breakdown-card" aria-labelledby="personHeading">
          <header class="breakdown-heading">
            <div><p class="eyebrow">Who spent it</p><h3 id="personHeading">By person</h3></div>
          </header>
          <div class="table-scroll people-table-scroll">
            <table id="whoTable">
              <caption>Spending totals by person</caption>
              <thead><tr><th scope="col">Person</th><th scope="col">Amount</th><th scope="col">Count</th></tr></thead>
              <tbody>
                {#each summary.who as item}
                  <tr><th scope="row">{item.name}</th><td>{formatAmount(item.amount)}</td><td>{item.count}</td></tr>
                {/each}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </div>
  {/if}
</section>

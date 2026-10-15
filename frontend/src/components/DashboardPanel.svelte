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
    return Number(amount).toFixed(2);
  }

  onDestroy(destroyCategoryChart);
</script>

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
          onchange={onfilterschange}
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
          onchange={onfilterschange}
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
      onclick={onclearfilters}
    >Clear filters</button>
    <p id="activeFilters" aria-live="polite">
      {activeFilters.length ? `Active filters: ${activeFilters.join(', ')}` : 'No filters active.'}
    </p>
  </form>

  {#if isLoading}<div id="dashboardLoading" role="status">Loading summary...</div>{/if}
  {#if error}<div id="dashboardError" class="error" role="alert">{error}</div>{/if}
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
</style>

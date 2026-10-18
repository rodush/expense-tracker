<script>
  import { onDestroy } from "svelte";
  import { createOrUpdateCategoryChart, destroyCategoryChart } from "../chart";

  let {
    categoryOptions,
    whoOptions,
    selectedCategories = $bindable([]),
    selectedPeople = $bindable([]),
    dateFrom = $bindable(""),
    dateTo = $bindable(""),
    selectedYear = $bindable(""),
    selectedMonth = $bindable(""),
    years = [],
    summary,
    onclearfilters,
    onfilterchange,
  } = $props();
  let categoryChartCanvas = $state();
  let categorySort = $state({ key: "amount", direction: "desc" });
  let whoSort = $state({ key: "amount", direction: "desc" });

  const sortedCategories = $derived(
    sortItems(summary?.categories ?? [], categorySort),
  );
  const sortedPeople = $derived(sortItems(summary?.who ?? [], whoSort));

  const activeFilters = $derived([
    ...selectedCategories.map((value) => `category: ${value}`),
    ...selectedPeople.map((value) => `who: ${value}`),
    ...(dateFrom ? [`from ${dateFrom}`] : []),
    ...(dateTo ? [`through ${dateTo}`] : []),
    ...(selectedMonth && selectedYear
      ? [
          `${new Date(Number(selectedYear), Number(selectedMonth) - 1).toLocaleString(undefined, { month: "long" })} ${selectedYear}`,
        ]
      : []),
    ...(!selectedMonth && selectedYear ? [String(selectedYear)] : []),
  ]);

  function changed() {
    onfilterchange?.();
  }

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

  function sortItems(items, sort) {
    return [...items].sort((left, right) => {
      const a = left[sort.key];
      const b = right[sort.key];
      const comparison =
        typeof a === "number" && typeof b === "number"
          ? a - b
          : String(a ?? "").localeCompare(String(b ?? ""), undefined, {
              numeric: true,
            });
      return comparison * (sort.direction === "asc" ? 1 : -1);
    });
  }

  function toggleSort(state, key) {
    state = {
      key,
      direction:
        state.key === key && state.direction === "asc" ? "desc" : "asc",
    };
    return state;
  }

  onDestroy(destroyCategoryChart);
</script>

<section id="dashboard" class="dashboard" aria-labelledby="dashboardHeading">
  <header class="section-heading">
    <div>
      <p class="eyebrow">Overview</p>
      <h2 id="dashboardHeading">Spending overview</h2>
    </div>
  </header>

  <details class="filter-card" aria-labelledby="filterHeading" open>
    <summary class="filter-card-summary">
      <span id="filterHeading" class="filter-card-title">
        Filter your expenses
      </span>
      <span class="selected-filter-count" aria-live="polite">
        {activeFilters.length} selected {activeFilters.length === 1
          ? "filter"
          : "filters"}
      </span>
    </summary>
    <div class="filter-card-content">
      <div class="filter-card-heading">
        <div>
          <p>Choose one or more options to narrow this report.</p>
        </div>
        <button
          id="clearFilters"
          type="button"
          class="clear-filter-button"
          disabled={!selectedCategories.length &&
            !selectedPeople.length &&
            !dateFrom &&
            !dateTo &&
            !selectedYear &&
            !selectedMonth}
          onclick={onclearfilters}
        >
          Clear filters
        </button>
      </div>
      <div id="filterForm" class="filter-groups">
        <fieldset class="filter-group">
          <legend>Category</legend>
          <div class="filter-options">
            {#each categoryOptions as category (category)}
              <label>
                <input
                  bind:group={selectedCategories}
                  type="checkbox"
                  value={category}
                  onchange={changed}
                />
                {category}
              </label>
            {/each}
          </div>
        </fieldset>
        <fieldset class="filter-group">
          <legend>Person</legend>
          <div class="filter-options">
            {#each whoOptions as person (person)}
              <label>
                <input
                  bind:group={selectedPeople}
                  type="checkbox"
                  value={person}
                  onchange={changed}
                />
                {person}
              </label>
            {/each}
          </div>
        </fieldset>
      </div>
      <div class="date-filters">
        <fieldset class="filter-group date-range-group">
          <legend>Date range</legend>
          <label>
            From date
            <input
              aria-label="From date"
              type="date"
              bind:value={dateFrom}
              oninput={() => onfilterchange?.("range")}
            />
          </label>
          <label>
            To date
            <input
              aria-label="To date"
              type="date"
              bind:value={dateTo}
              oninput={() => onfilterchange?.("range")}
            />
          </label>
        </fieldset>
        <fieldset class="filter-group quick-date-group">
          <legend>Quick month and year</legend>
          <label>
            Year
            <select
              aria-label="Year"
              bind:value={selectedYear}
              onchange={() => onfilterchange?.("quick")}
            >
              <option value="">All years</option>
              {#each years as year (year)}
                <option value={String(year)}>{year}</option>
              {/each}
            </select>
          </label>
          <label>
            Month
            <select
              aria-label="Month"
              bind:value={selectedMonth}
              onchange={() => onfilterchange?.("quick")}
              disabled={!selectedYear}
            >
              <option value="">All months</option>
              {#each Array.from({ length: 12 }, (_, index) => index + 1) as month (month)}
                <option value={String(month)}>
                  {new Date(
                    new Date().getFullYear(),
                    month - 1,
                    1,
                  ).toLocaleString(undefined, { month: "long" })}
                </option>
              {/each}
            </select>
          </label>
        </fieldset>
      </div>
      <p id="activeFilters" class="active-filters" aria-live="polite">
        {activeFilters.length
          ? `Showing ${activeFilters.join(" · ")}`
          : "Showing all expenses"}
      </p>
    </div>
  </details>

  {#if summary?.expense_count === 0}
    <p id="dashboardEmpty" class="empty-state" role="status">
      <strong>No expenses match these filters.</strong>
      <span>
        Try choosing different options or clear the filters to see everything.
      </span>
    </p>
  {/if}
  {#if summary}
    <div id="dashboardContent" class="report-grid">
      <div class="breakdown-grid">
        <section class="breakdown-card" aria-labelledby="categoryHeading">
          <header class="breakdown-heading">
            <div>
              <p class="eyebrow">Where it goes</p>
              <h3 id="categoryHeading">By category</h3>
            </div>
          </header>
          <div class="chart-container">
            <canvas
              bind:this={categoryChartCanvas}
              id="categoryChart"
              aria-label="Doughnut chart showing spending by category"
            ></canvas>
          </div>
          <details class="category-totals">
            <summary>Spending totals by category</summary>
            <div class="table-scroll">
              <table id="categoryTable">
                <caption class="visually-hidden">
                  Spending totals by category
                </caption>
                <thead>
                  <tr>
                    {#each [["name", "Category"], ["amount", "Amount"], ["count", "Count"]] as [key, label] (key)}
                      <th scope="col">
                        <button
                          class="sort-button"
                          aria-label={`Sort by ${label}`}
                          onclick={() => {
                            categorySort = toggleSort(categorySort, key);
                          }}
                        >
                          {label}
                          <span aria-hidden="true">
                            {categorySort.key === key
                              ? categorySort.direction === "asc"
                                ? "↑"
                                : "↓"
                              : "↕"}
                          </span>
                        </button>
                      </th>
                    {/each}
                  </tr>
                </thead>
                <tbody>
                  {#each sortedCategories as item (item.name)}
                    <tr>
                      <th scope="row">{item.name}</th>
                      <td>{formatAmount(item.amount)}</td>
                      <td>{item.count}</td>
                    </tr>
                  {/each}
                </tbody>
              </table>
            </div>
          </details>
        </section>

        <div class="people-column">
          <section class="breakdown-card" aria-labelledby="personHeading">
            <header class="breakdown-heading">
              <div>
                <p class="eyebrow">Who spent it</p>
                <h3 id="personHeading">By person</h3>
              </div>
            </header>
            <div class="table-scroll people-table-scroll">
              <table id="whoTable">
                <caption>Spending totals by person</caption>
                <thead>
                  <tr>
                    {#each [["name", "Person"], ["amount", "Amount"], ["count", "Count"]] as [key, label] (key)}
                      <th scope="col">
                        <button
                          class="sort-button"
                          aria-label={`Sort by ${label}`}
                          onclick={() => {
                            whoSort = toggleSort(whoSort, key);
                          }}
                        >
                          {label}
                          <span aria-hidden="true">
                            {whoSort.key === key
                              ? whoSort.direction === "asc"
                                ? "↑"
                                : "↓"
                              : "↕"}
                          </span>
                        </button>
                      </th>
                    {/each}
                  </tr>
                </thead>
                <tbody>
                  {#each sortedPeople as item (item.name)}
                    <tr>
                      <th scope="row">{item.name}</th>
                      <td>{formatAmount(item.amount)}</td>
                      <td>{item.count}</td>
                    </tr>
                  {/each}
                </tbody>
              </table>
            </div>
          </section>
          <article
            class="summary-card summary-card-primary total-spend-card"
            aria-label="Total spend"
          >
            <span class="metric-icon" aria-hidden="true">↗</span>
            <p class="metric-label">Total spend</p>
            <p id="totalAmount" class="metric-value">
              {formatAmount(summary.total_amount)}
            </p>
          </article>
        </div>
      </div>
    </div>
  {/if}
</section>

<script>
  import { formatTransactionDate } from "../date-format";
  import { formatAmount } from "../money";
  let {
    rows,
    filteredDownloadUrl,
    totalCount = 0,
    offset = 0,
    limit = 25,
    sortBy = "date",
    sortDirection = "desc",
    onsort,
    onprevious,
    onnext,
  } = $props();
</script>

<section class="transactions" aria-labelledby="transactionsHeading">
  <header class="section-heading transactions-heading">
    <h2 id="transactionsHeading">Transactions</h2>
    <span class="row-count">
      {totalCount}
      {totalCount === 1 ? "expense" : "expenses"}
    </span>
  </header>
  <nav class="download-actions" aria-label="Export expenses">
    <a
      id="filteredDownloadLink"
      class="download-primary"
      href={filteredDownloadUrl}
    >
      Download filtered CSV <span aria-hidden="true">↓</span>
    </a>
    <small>Amounts in EUR</small>
  </nav>
  <p class="table-help" id="tableHelp">
    Scroll the table horizontally on small screens. Sort applies to all matching
    expenses.
  </p>
  <div class="table-scroll">
    <table id="resultsTable">
      <caption>Expenses included in the current report</caption>
      <thead>
        <tr>
          {#each [["date", "Date"], ["amount", "Amount"], ["who", "Person"], ["category", "Category"], ["description", "Description"]] as [key, label] (key)}
            <th
              scope="col"
              aria-sort={sortBy === key
                ? sortDirection === "asc"
                  ? "ascending"
                  : "descending"
                : "none"}
            >
              <button
                class="sort-button"
                aria-label={`Sort by ${label}`}
                onclick={() => onsort(key)}
              >
                {label}
                <span aria-hidden="true">
                  {sortBy === key ? (sortDirection === "asc" ? "↑" : "↓") : "↕"}
                </span>
              </button>
            </th>
          {/each}
        </tr>
      </thead>
      <tbody>
        {#each rows as row, index (index)}
          <tr>
            <td>{formatTransactionDate(row.date)}</td>
            <td>{formatAmount(row.amount ?? 0)}</td>
            <td>{row.who ?? ""}</td>
            <td>{row.category ?? ""}</td>
            <td class="description-cell">{row.description ?? ""}</td>
          </tr>
        {/each}
      </tbody>
    </table>
  </div>
  <nav class="history-pagination" aria-label="Expense history pages">
    <button
      type="button"
      class="clear-filter-button"
      onclick={onprevious}
      disabled={offset === 0}
    >
      Previous
    </button>
    <span>
      Showing {offset + 1}–{Math.min(offset + limit, totalCount)} of {totalCount}
    </span>
    <button
      type="button"
      class="clear-filter-button"
      onclick={onnext}
      disabled={offset + limit >= totalCount}
    >
      Next page
    </button>
  </nav>
</section>

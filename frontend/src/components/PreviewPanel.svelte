<script>
  import { tick } from 'svelte';
  import { calculateTooltipPosition } from '../tooltip-position';

  let { rows, downloadId, datasetId, filteredDownloadUrl } = $props();
  let tooltipElement = $state();
  let tooltip = $state({ text: '', rowIndex: null, left: 0, top: 0 });
  let sort = $state({ key: 'date', direction: 'desc' });
  const sortedRows = $derived([...rows].sort((left, right) => {
    const a = left[sort.key];
    const b = right[sort.key];
    const comparison = sort.key === 'amount'
      ? Number(a ?? 0) - Number(b ?? 0)
      : String(a ?? '').localeCompare(String(b ?? ''), undefined, { numeric: true });
    return comparison * (sort.direction === 'asc' ? 1 : -1);
  }));

  function toggleSort(key) {
    sort = { key, direction: sort.key === key && sort.direction === 'asc' ? 'desc' : 'asc' };
  }

  async function showTooltip(index, description, x, y) {
    tooltip.rowIndex = index;
    tooltip.text = String(description ?? '');
    await tick();
    positionTooltip(x, y);
  }

  function positionTooltip(x, y) {
    if (!tooltipElement) return;
    const { width, height } = tooltipElement.getBoundingClientRect();
    Object.assign(tooltip, calculateTooltipPosition(
      x,
      y,
      width,
      height,
      window.innerWidth,
      window.innerHeight,
    ));
  }

  function hideTooltip(event, index) {
    if (event.currentTarget.contains(event.relatedTarget)) return;
    if (tooltip.rowIndex === index) tooltip.rowIndex = null;
  }

  function formatAmount(amount) {
    return new Intl.NumberFormat(undefined, {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(Number(amount));
  }
</script>

<section class="transactions" aria-labelledby="transactionsHeading">
  <header class="section-heading transactions-heading">
    <div>
      <p class="eyebrow">Transaction detail</p>
      <h2 id="transactionsHeading">Recent expenses</h2>
    </div>
    <span class="row-count">{rows.length} {rows.length === 1 ? 'expense' : 'expenses'}</span>
  </header>
  <nav class="download-actions" aria-label="Export expenses">
    {#if datasetId}
      <a id="filteredDownloadLink" class="download-primary" href={filteredDownloadUrl}>
        Download filtered CSV <span aria-hidden="true">↓</span>
      </a>
    {/if}
    {#if downloadId}
      <a id="downloadLink" class="download-secondary" href={`/download/${encodeURIComponent(downloadId)}`}>
        Download full statement
      </a>
    {/if}
  </nav>
  <details class="transaction-details">
    <summary><span>Review transactions</span><span class="summary-count">{rows.length} rows</span></summary>
    <div class="table-scroll">
      <table id="resultsTable">
        <caption>Expenses included in the current report</caption>
        <colgroup>
          <col />
          <col />
          <col />
          <col />
          <col class="description-column" />
        </colgroup>
        <thead>
          <tr>
          {#each [['date', 'Date'], ['amount', 'Amount'], ['who', 'Person'], ['category', 'Category'], ['description', 'Description']] as [key, label]}
            <th scope="col"><button class="sort-button" aria-label={`Sort by ${label}`} onclick={() => toggleSort(key)}>{label} <span aria-hidden="true">{sort.key === key ? (sort.direction === 'asc' ? '↑' : '↓') : '↕'}</span></button></th>
          {/each}
          </tr>
        </thead>
        <tbody>
          {#each sortedRows as row, index}
            <tr>
              <td>{row.date ?? ''}</td>
              <td>{formatAmount(row.amount ?? 0)}</td>
              <td>{row.who ?? ''}</td>
              <td>{row.category ?? ''}</td>
              <td
                class="description-cell"
                tabindex="0"
                aria-describedby={tooltip.rowIndex === index ? 'descriptionTooltip' : undefined}
                onmouseover={(event) => showTooltip(index, row.description, event.clientX, event.clientY)}
                onmousemove={(event) => {
                  if (tooltip.rowIndex === index) positionTooltip(event.clientX, event.clientY);
                }}
                onmouseout={(event) => hideTooltip(event, index)}
                onfocus={(event) => {
                  const bounds = event.currentTarget.getBoundingClientRect();
                  showTooltip(
                    index,
                    row.description,
                    bounds.left + bounds.width / 2,
                    bounds.top + bounds.height / 2,
                  );
                }}
                onblur={(event) => hideTooltip(event, index)}
              >{row.description ?? ''}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  </details>
</section>

{#if tooltip.rowIndex !== null}
  <div
    bind:this={tooltipElement}
    id="descriptionTooltip"
    class="description-tooltip"
    role="tooltip"
    style={`left: ${tooltip.left}px; top: ${tooltip.top}px;`}
  >{tooltip.text}</div>
{/if}

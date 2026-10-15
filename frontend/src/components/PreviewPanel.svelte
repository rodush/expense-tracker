<script>
  import { tick } from 'svelte';
  import { calculateTooltipPosition } from '../tooltip-position';

  let { rows, downloadId, datasetId, filteredDownloadUrl } = $props();
  let tooltipElement = $state();
  let tooltip = $state({ text: '', rowIndex: null, left: 0, top: 0 });

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
</script>

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
        {#each rows as row, index}
          <tr>
            <td>{row.date ?? ''}</td>
            <td>{row.amount ?? ''}</td>
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

<style>
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

{#if tooltip.rowIndex !== null}
  <div
    bind:this={tooltipElement}
    id="descriptionTooltip"
    class="description-tooltip"
    role="tooltip"
    style={`left: ${tooltip.left}px; top: ${tooltip.top}px;`}
  >{tooltip.text}</div>
{/if}

const fileInput = document.getElementById('fileInput');
const uploadButton = document.getElementById('uploadButton');
const loading = document.getElementById('loading');
const errorBox = document.getElementById('error');
const resultsTable = document.getElementById('resultsTable');
const downloadLink = document.getElementById('downloadLink');
const filteredDownloadLink = document.getElementById('filteredDownloadLink');
const dashboard = document.getElementById('dashboard');
const categoryFilter = document.getElementById('categoryFilter');
const whoFilter = document.getElementById('whoFilter');
const clearFilters = document.getElementById('clearFilters');
const activeFilters = document.getElementById('activeFilters');
const dashboardLoading = document.getElementById('dashboardLoading');
const dashboardError = document.getElementById('dashboardError');
const dashboardEmpty = document.getElementById('dashboardEmpty');
const dashboardContent = document.getElementById('dashboardContent');
const totalAmount = document.getElementById('totalAmount');
const expenseCount = document.getElementById('expenseCount');
const categoryChartCanvas = document.getElementById('categoryChart');
const categoryTable = document.getElementById('categoryTable');
const whoTable = document.getElementById('whoTable');

let datasetId = null;
let previewRows = [];
let summaryRequest = null;
let categoryChart = null;
let categoryChartAmounts = [];

uploadButton.addEventListener('click', async () => {
  const file = fileInput.files[0];
  if (!file) {
    showError('Please choose a file first.');
    fileInput.setAttribute('aria-describedby', "error");
    fileInput.setAttribute('aria-invalid', true);
    return;
  }

  fileInput.setAttribute('aria-invalid', false);
  loading.classList.remove('hidden');
  errorBox.classList.add('hidden');
  downloadLink.classList.add('hidden');
  filteredDownloadLink.classList.add('hidden');

  try {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch('/upload', {
      method: 'POST',
      body: formData,
    });

    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail || 'Upload failed.');
    }

    datasetId = payload.dataset_id;
    previewRows = payload.preview;
    populateFilters(previewRows);
    renderRows(previewRows);
    downloadLink.href = `/download/${payload.download_id}`;
    downloadLink.classList.remove('hidden');
    filteredDownloadLink.classList.remove('hidden');
    dashboard.classList.remove('hidden');
    await loadSummary();
  } catch (err) {
    showError(err.message || 'Something went wrong.');
  } finally {
    loading.classList.add('hidden');
  }
});

function renderRows(rows) {
  const body = resultsTable.querySelector('tbody');
  body.innerHTML = '';

  for (const row of rows) {
    const tr = document.createElement('tr');
    for (const value of [row.date, row.amount, row.description, row.who, row.category]) {
      const cell = document.createElement('td');
      cell.textContent = value ?? '';
      tr.appendChild(cell);
    }
    body.appendChild(tr);
  }
}

function populateFilters(rows) {
  populateSelect(categoryFilter, rows.map((row) => row.category));
  populateSelect(whoFilter, rows.map((row) => row.who));
  categoryFilter.disabled = false;
  whoFilter.disabled = false;
  clearFilters.disabled = false;
}

function populateSelect(select, values) {
  select.replaceChildren();
  [...new Set(values.filter(Boolean))].sort().forEach((value) => {
    const option = document.createElement('option');
    option.value = value;
    option.textContent = value;
    select.appendChild(option);
  });
}

function selectedValues(select) {
  return [...select.selectedOptions].map((option) => option.value);
}

async function loadSummary() {
  if (!datasetId) return;
  summaryRequest?.abort();
  const requestController = new AbortController();
  summaryRequest = requestController;
  const params = new URLSearchParams();
  selectedValues(categoryFilter).forEach((value) => params.append('category', value));
  selectedValues(whoFilter).forEach((value) => params.append('who', value));
  updateFilterLabel();
  dashboardLoading.classList.remove('hidden');
  dashboardError.classList.add('hidden');
  dashboardEmpty.classList.add('hidden');
  dashboardContent.classList.add('hidden');

  try {
    const response = await fetch(`/datasets/${encodeURIComponent(datasetId)}/summary?${params}`, {
      signal: requestController.signal,
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || 'Unable to load summary.');
    renderSummary(payload);
  } catch (err) {
    if (err.name !== 'AbortError') showDashboardError(err.message);
  } finally {
    if (!requestController.signal.aborted) dashboardLoading.classList.add('hidden');
  }
}

function renderSummary(summary) {
  totalAmount.textContent = formatAmount(summary.total_amount);
  expenseCount.textContent = String(summary.expense_count);
  renderBreakdown(categoryTable, summary.categories);
  renderBreakdown(whoTable, summary.who);
  renderCategoryChart(summary.categories);
  dashboardContent.classList.remove('hidden');
  if (summary.expense_count === 0) dashboardEmpty.classList.remove('hidden');
}

function renderBreakdown(table, items) {
  const body = table.querySelector('tbody');
  body.replaceChildren();
  items.forEach((item) => {
    const row = document.createElement('tr');
    [item.name, formatAmount(item.amount), String(item.count)].forEach((value) => {
      const cell = document.createElement('td');
      cell.textContent = value;
      row.appendChild(cell);
    });
    body.appendChild(row);
  });
}

function renderCategoryChart(items) {
  const visibleItems = items.filter((item) => item.count > 0);
  const labels = visibleItems.map((item) => item.name);
  const values = visibleItems.map((item) => Math.abs(item.amount));
  categoryChartAmounts = visibleItems.map((item) => item.amount);

  if (categoryChart) {
    categoryChart.data.labels = labels;
    categoryChart.data.datasets[0].data = values;
    categoryChart.update();
    return;
  }

  categoryChart = new Chart(categoryChartCanvas, {
    type: 'doughnut',
    data: {
      labels,
      datasets: [{
        data: values,
        borderWidth: 2,
        hoverOffset: 8,
      }],
    },
    options: {
      cutout: '62%',
      maintainAspectRatio: true,
      responsive: true,
      plugins: {
        legend: { position: 'bottom' },
        tooltip: {
          callbacks: {
            label: (context) =>
              `${context.label}: ${formatAmount(categoryChartAmounts[context.dataIndex])}`,
          },
        },
      },
    },
  });
}

function formatAmount(amount) {
  return Number(amount).toFixed(2);
}

function updateFilterLabel() {
  const categories = selectedValues(categoryFilter);
  const people = selectedValues(whoFilter);
  const labels = [
    ...categories.map((value) => `category: ${value}`),
    ...people.map((value) => `who: ${value}`),
  ];
  activeFilters.textContent = labels.length ? `Active filters: ${labels.join(', ')}` : 'No filters active.';
  const params = new URLSearchParams();
  categories.forEach((value) => params.append('category', value));
  people.forEach((value) => params.append('who', value));
  filteredDownloadLink.href = `/datasets/${encodeURIComponent(datasetId)}/export?${params}`;
  renderRows(previewRows.filter((row) =>
    (!categories.length || categories.includes(row.category))
    && (!people.length || people.includes(row.who))
  ));
}

categoryFilter.addEventListener('change', loadSummary);
whoFilter.addEventListener('change', loadSummary);
clearFilters.addEventListener('click', () => {
  categoryFilter.selectedIndex = -1;
  whoFilter.selectedIndex = -1;
  loadSummary();
});

function showDashboardError(message) {
  dashboardError.textContent = message;
  dashboardError.classList.remove('hidden');
}

function showError(message) {
  errorBox.textContent = message;
  errorBox.classList.remove('hidden');
}

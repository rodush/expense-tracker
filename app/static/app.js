const fileInput = document.getElementById('fileInput');
const uploadButton = document.getElementById('uploadButton');
const loading = document.getElementById('loading');
const errorBox = document.getElementById('error');
const resultsTable = document.getElementById('resultsTable');
const downloadLink = document.getElementById('downloadLink');

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

    renderRows(payload.preview);
    downloadLink.href = `/download/${payload.download_id}`;
    downloadLink.classList.remove('hidden');
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
    tr.innerHTML = `
      <td>${row.date ?? ''}</td>
      <td>${row.amount ?? ''}</td>
      <td>${row.description ?? ''}</td>
      <td>${row.who ?? ''}</td>
      <td>${row.category ?? ''}</td>
    `;
    body.appendChild(tr);
  }
}

function showError(message) {
  errorBox.textContent = message;
  errorBox.classList.remove('hidden');
}

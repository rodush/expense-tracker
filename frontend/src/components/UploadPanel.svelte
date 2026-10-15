<script>
  let { isUploading, uploadError, onupload } = $props();
  let fileInput = $state();

  function submitUpload() {
    onupload(fileInput?.files?.[0] ?? null, fileInput);
  }
</script>

<div class="panel">
  <p>Upload a CSV, XLS, or XLSX expense file to categorize descriptions with Gemini.</p>
  <input
    bind:this={fileInput}
    id="fileInput"
    type="file"
    accept=".csv,.xls,.xlsx"
    aria-errormessage="error"
  />
  <button id="uploadButton" onclick={submitUpload} disabled={isUploading}>
    {isUploading ? 'Processing...' : 'Upload & Categorize'}
  </button>
  {#if isUploading}<div id="loading" role="status">Processing...</div>{/if}
  {#if uploadError}<div id="error" class="error" role="alert">{uploadError}</div>{/if}
</div>

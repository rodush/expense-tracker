<script>
  let { isUploading, uploadError, onupload } = $props();
  let fileInput = $state();
  let selectedFile = $state(null);

  function submitUpload(event) {
    event.preventDefault();
    onupload(selectedFile);
  }

  function handleFileChange() {
    selectedFile = fileInput?.files?.[0] ?? null;
  }
</script>

<section class="upload-card" aria-labelledby="uploadHeading">
  <div class="upload-card-heading">
    <span class="upload-icon" aria-hidden="true">
      <svg viewBox="0 0 24 24" fill="none">
        <path d="M12 16V4m0 0L7.5 8.5M12 4l4.5 4.5M5 14v5h14v-5" />
      </svg>
    </span>
    <div>
      <p class="eyebrow">Start here</p>
      <h2 id="uploadHeading">Upload an expense statement</h2>
    </div>
  </div>

  <form onsubmit={submitUpload}>
    <label class="file-picker" for="fileInput">
      <span class="file-picker-title">Select a statement file</span>
      <span class="file-picker-note">CSV, XLS, or XLSX · up to 5 MB</span>
      <input
        bind:this={fileInput}
        id="fileInput"
        type="file"
        accept=".csv,.xls,.xlsx"
        aria-describedby={uploadError ? "uploadError" : "fileHelp"}
        aria-invalid={uploadError ? "true" : undefined}
        onchange={handleFileChange}
      />
    </label>
    <small id="fileHelp" class="file-help"
      >Your statement is used to prepare this report.</small
    >

    {#if selectedFile}
      <p class="selected-file" role="status">
        <span class="selected-file-check" aria-hidden="true">✓</span>
        <span
          ><strong>{selectedFile.name}</strong><small>Ready to analyze</small
          ></span
        >
      </p>
    {/if}

    <button
      id="uploadButton"
      class="primary-action"
      type="submit"
      disabled={isUploading}
    >
      {#if isUploading}
        <span class="button-spinner" aria-hidden="true"></span> Analyzing statement…
      {:else}
        Analyze expenses
        <span aria-hidden="true">→</span>
      {/if}
    </button>
    {#if uploadError}
      <p id="uploadError" class="error-message" role="alert">{uploadError}</p>
    {/if}
  </form>
</section>

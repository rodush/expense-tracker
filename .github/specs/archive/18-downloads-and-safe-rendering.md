# Issue 18: Preserve safe rendering and flexible export behavior

## Title
Keep the dashboard safe, consistent, and export-friendly for filtered reporting

## Description
The dashboard will render uploaded values and exported data in several places. This issue ensures user-generated content is rendered safely, download behavior is explicit, and the same normalized data powers both the table and chart output.

## Scope
- Replace unsafe HTML rendering with text-safe DOM methods or escaped output
- Decide whether full exports and filtered exports are separate actions or a single toggle
- Preserve the existing full CSV export while defining filtered export requirements
- Keep table, chart, and CSV output aligned with the same normalized row set
- Document the safe rendering and download semantics for users and maintainers

## Acceptance Criteria
- Uploaded text is rendered as text, not executable HTML or script content
- CSV export behavior is explicit for full versus filtered datasets
- The table and chart output remain consistent with the selected filters
- The dashboard avoids unsafe string interpolation in DOM rendering paths
- The chosen export semantics are documented in the app workflow

## Decisions

- Preview cells are created with `textContent` and appended as DOM nodes. Uploaded
  values are displayed as text even when they contain HTML or script-like content;
  no uploaded value is interpolated into `innerHTML`.
- The existing `/download/{download_id}` endpoint remains the full categorized
  upload export and continues to serve the original CSV artifact.
- Filtered exports are explicit and separate: `GET
  /datasets/{dataset_id}/export` accepts repeated `category` and `who` query
  parameters using the same AND semantics and validation as summary requests.
  Without filters it exports the complete normalized dataset; with filters it
  exports only matching normalized rows.
- The UI exposes both links. The full link preserves the uploaded CSV exactly,
  while the filtered link follows the current dashboard selections and uses the
  normalized dataset shared by summary aggregation.

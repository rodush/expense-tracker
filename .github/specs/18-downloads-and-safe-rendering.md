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

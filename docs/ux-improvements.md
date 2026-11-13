# UX review implementation

Implements the findings in PR #87.

- Transaction sorting applies to the complete filtered ledger before pagination,
  with stable ordering for ties. Table headers expose their sort direction.
- Refreshing clears previous totals and transactions. Export becomes available
  only after a successful report response. Report and filter-option failures have
  separate retry actions, and older responses cannot replace current results.
- Monetary values and chart tooltips use EUR. Import explains the single-currency
  assumption, persistence, duplicate handling, and possible external AI processing.
- Empty ledgers open import automatically. Format requirements are available
  before submission, and successful imports link to transaction review.
- Date controls explain their mutually exclusive modes, commit on change rather
  than every input event, and reject reversed ranges with associated feedback.
- Responsive containers constrain wide tables to horizontal scroll areas.
  Descriptions wrap in full rather than requiring hover or individual tab stops.
- Loading and empty states apply to the complete report. Empty charts and tables
  are omitted, and filtered emptiness differs from first use.
- Returning visitors see a compact introduction and the total before filters and
  breakdowns. Category values are available in an initially open table.

## Validation

Python: 81 tests passed; Ruff formatting, lint and ty checks passed.
Frontend: 21 tests passed; ESLint, Prettier verification, Svelte diagnostics and
production build passed.

Chrome used an isolated SQLite database, synthetic CSV and local categorization
(no external AI key) to verify first use, import of 30 expenses, amount sorting
across pages, year/month filtering, and a CSV download containing the 15 matching
expenses. Screenshots were inspected at 1440, 390 and 320 pixels; the page width
matched the viewport at each size and total spend appeared in the initial view.
This does not constitute screen-reader testing or testing on physical phones.

[Desktop](screenshots/ux-improvements/desktop.png) ·
[Mobile](screenshots/ux-improvements/mobile.png)

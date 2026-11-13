## Monthly import and expense history

The workflow is:

1. **Upload**: send a CSV, XLS, or XLSX file to `POST /upload`. It must contain
   date, amount, and description columns. ABN AMRO headers `Transactiedatum`,
   `Transactiebedrag`, and `Omschrijving` map to those fields.
2. **Import once**: the server normalizes expenses, resolves who made each
   expense, categorizes only records not already in the ledger, and stores the
   result in the configured database. Identical files are recognized by their
   content hash; overlapping exports are checked record by record.
3. **Browse history**: the dashboard combines records from every import. Filter
   by category, person, date range, or quick month/year selection. Export the
   filtered results or the full history.

Uploads are limited to 5 MiB. The route reads at most 5 MiB plus one byte before
service validation rejects oversized files with HTTP 413. Multipart parsing may
spool incoming files to temporary storage; private deployments should also set
a request body limit at their proxy to bound temporary disk usage.

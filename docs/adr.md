- Amounts are parsed as numeric values during upload. Positive values are
  treated as card credits, and SEPA transfers whose description names
  `Savings Account` are excluded before categorization. Retained negative debit
  values are stored and reported as their absolute values. Thus the ledger
  contains expenses only, and `total_amount` is a gross spending total.
- The ledger currently assumes one currency (EUR). Currency metadata and mixed
  currency handling need to be defined before importing accounts with multiple
  currencies.
- The category list is read from `CATEGORIES` and the fallback from `FALLBACK_CATEGORY`;
  the fallback must be one of the configured categories.
  `TRANSACTION_DATE_FORMAT` uses Python `strptime` directives and defaults to `%Y%m%d`,
  matching the ABN AMRO export's `YYYYMMDD` date values.
  For another bank format, configure its corresponding format (for example `%d-%m-%Y`).
- A valid filter that matches no rows is not an error. It returns
  `total_amount: 0`, `expense_count: 0`, and empty breakdowns.
- `/expenses/export` exports the filtered ledger. `/download/{download_id}`
  remains available for a full categorized CSV associated with one import.
- Without a stable bank transaction reference, record fingerprints cannot distinguish
  truly identical transactions across different exports.\
  Currently, hash is made of a transaction row to be used as identifier for the transaction (expense).
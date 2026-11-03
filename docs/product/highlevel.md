# Main idea

Expense Categorizer web application turns monthly bank (ABN Amro) transaction exports (as XLS file) into a persistent household expense ledger.
Backend logic assigns each expense a category and a person (who), skips records already imported, and lets you browse spending history across all uploads.

## Technical aspects

Application uses integration with LLM (Gemini in its first iteration; Jev is potentially a much better -- faster and cheaper -- candidate),
as well as local heuristics model as a fallback in cases when remote API call fails.

## Flow

User uploads XLS file and presses "Analyze expenses" button.
Once file is processed, the categorized data is returned via API.
Using filters in frontend application (dropdowns, checkboxes) user can dive deeper into particular facets.
User can select date range to analyze expenses within.

More details are in [workflow.md](./workflow.md) file.

## Features

User can define categories and who made the purchase manually, in the account settings.
Manually configured rules are then used to override the default settings.

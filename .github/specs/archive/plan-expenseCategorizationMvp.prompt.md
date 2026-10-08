## Plan: Expense Categorization App

This is the aligned MVP plan for the expense categorization application.

### Goal
Build a lightweight Python web app that lets a user upload an XLS or CSV expense file, parses the rows, and categorizes each expense description using Gemini.

### MVP Scope
- Minimal browser UI with upload, processing, preview, and download
- Support CSV and XLS/XLSX input files
- Backend implemented in Python
- Gemini used to categorize expenses by description
- Categories driven from a config file
- Start with a small default category list that can be expanded later

### Required input fields
The uploaded expense file should contain, or at least be interpreted as having:
- date
- transaction amount
- description
- who made the purchase based on debit card details

### Behavior
- Use the description field as the primary signal for categorization
- If a category column does not already exist, add one in the output
- Use a strict category list from config so Gemini only returns approved categories
- If uncertain, fall back to a default category such as “Other” or “Unclassified”

### Recommended initial categories
Start with a short config-based list such as:
- Food
- Transport
- Utilities
- Shopping
- Other

### Implementation approach
- Backend: FastAPI
- File parsing: pandas
- Gemini integration: Google Generative AI client
- Frontend: unless a stronger preference is stated, default to a lightweight server-rendered HTML/CSS/JS UI for the MVP to keep the stack simple and fast to ship

### Refined assumptions and open questions
- Frontend technology is not yet strongly specified. For the first version, the safest default is a minimal server-rendered page rather than a React/Vue frontend.
- Category taxonomy is intentionally small for the MVP and should come from a config file, not hardcoded in the UI.
- Output behavior should preserve the original sheet structure and append or create a category column rather than inventing a new report format.
- The app should validate required fields and show a clear error if the expected columns are missing.
- Gemini API credentials should live in environment configuration, not in source code.
- The first version is expected to process a single uploaded file at a time, not a live streaming pipeline.

### Prompting strategy
Tell Gemini to:
- choose exactly one category from the configured list
- return only valid category names
- not invent new categories
- use “Other” when the description is too vague

### Output
- Show categorized results in the browser
- Allow the user to download the updated categorized file

### Next step
Proceed with implementation using the MVP structure above, then refine the category list and prompt behavior after the first working version is confirmed.

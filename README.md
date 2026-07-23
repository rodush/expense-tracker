# Expense Categorizer MVP

This project is a small FastAPI-based expense categorization app that reads uploaded CSV/XLS/XLSX files and assigns categories using a configurable category list with Gemini support.

## Run locally

```bash
cd /home/rodush/Work/expense-tracker
/home/rodush/.local/bin/uv run uvicorn app.main:app --reload
```

Then open:

```text
http://127.0.0.1:8000
```

## Environment variables

Create a `.env` file or export the following variable:

```bash
export GEMINI_API_KEY=YOUR_GEMINI_API_KEY
export CATEGORIES=Food,Transport,Utilities,Shopping,Other
```

## Category config

The starter category list is read from the `CATEGORIES` environment variable. If the variable is not set, the app falls back to:

- Food
- Transport
- Utilities
- Shopping
- Other

## Testing

```bash
cd /home/rodush/Work/expense-tracker
/home/rodush/.local/bin/uv run pytest
```

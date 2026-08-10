# Issue 3: Validate required columns and add missing category column

## Title
Validate expense input columns and ensure category column exists

## Description
Before calling Gemini, validate the required expense columns and ensure the output includes a `category` field if the uploaded file does not already contain one.

## Acceptance Criteria
- Missing required columns raise a clear validation error
- A `category` column is added to the output dataset when absent
- Validation errors are surfaced to the user in the UI

# Issue 5: Integrate Gemini with strict category enforcement

## Title
Add Gemini categorization prompt with controlled category output

## Description
Create a Gemini service that sends expense descriptions to the model with a prompt that:
- allows only the configured categories
- returns exactly one category per record
- falls back to “Other” when input is unclear

## Acceptance Criteria
- Gemini response is parsed into a valid category
- Invalid or invented categories are rejected or normalized
- A fallback category is used when necessary

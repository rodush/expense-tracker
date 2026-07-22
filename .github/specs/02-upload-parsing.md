# Issue 2: Add CSV/XLS/XLSX upload and parsing flow

## Title
Implement file upload and spreadsheet parsing support

## Description
Add backend support for uploading a single expense file and parsing CSV/XLS/XLSX data. The system should normalize the input so later processing can rely on a predictable shape.

## Acceptance Criteria
- Upload endpoint accepts CSV/XLS/XLSX files
- File content is parsed into rows
- Required fields are accessible for downstream categorization
- The app handles unsupported file types clearly

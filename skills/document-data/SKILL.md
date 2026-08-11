---
name: document-data
description: Document creation, spreadsheet processing, CSV, data extraction, reporting.
version: 1.0.0
---

# Document & Data Processing

## Activation
When task involves: creating documents, processing tables, CSV work, spreadsheet manipulation, data extraction, report generation.

## Workflow
1. Validate input data
2. Normalize schema
3. Process data (clean, transform, aggregate)
4. Check for missing values and duplicates
5. Export to target format
6. Re-open and verify readability
7. Cross-check record counts
8. Deliver with path

## Rules
- Never fabricate unknown data
- Mark missing values explicitly
- Don't modify source data unnecessarily
- Keep original copy
- Document cleaning/transformation steps
- Verify record count before and after
- Check for duplicate entries
- Verify data types

## Completion Criteria
- File exported at target path
- Re-opened and verified readable
- Record counts reconciled
- Format/structure consistent

## Common Failures
- Wrong encoding → check before export
- Truncated data → verify row counts
- Formula errors in spreadsheets → test with sample

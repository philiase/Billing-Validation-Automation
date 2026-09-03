# RPA Orchestration Notes

## Purpose

This project can be run directly with Python, but it is also suitable for RPA orchestration.

The recommended design is to let Python do the data validation and let the RPA tool manage the surrounding workflow.

## Suggested RPA Flow

```text
Start
  |
  v
Check input workbook exists
  |
  v
Run Python automation
  |
  v
Check process exit status
  |
  v
Confirm Excel report was created
  |
  v
Read AI summary text
  |
  v
Notify business users
  |
  v
Log result and end
```

## Why Not Put All Rules In RPA?

RPA tools are strong at:

- opening applications
- clicking screens
- moving files
- scheduling jobs
- sending emails
- integrating with business systems

Python is stronger for:

- working with large datasets
- applying validation rules
- grouping exception summaries
- creating reports
- writing audit records

Keeping the validation engine in Python makes the logic easier to test, version, and reuse.

## UiPath Example

A UiPath workflow can:

1. Use a file check activity for `input/sample_billing_data.xlsx`.
2. Use `Start Process` to run `run_automation.cmd`.
3. Wait for the process to complete.
4. Check `reports/` for a new `billing_exception_report_*.xlsx`.
5. Check `ai_outputs/` for a new `exception_summary_for_ai_*.txt`.
6. Use a log message or email activity to share the outcome.

## Error Handling

The RPA workflow should handle:

- missing input files
- Python process failures
- report not created
- locked Excel files
- unavailable network folders
- email or notification failures

The workflow should not fail silently. It should log the error, notify the support owner, and stop safely.

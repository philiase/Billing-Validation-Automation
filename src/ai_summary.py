from __future__ import annotations

from pathlib import Path
from typing import Union

import pandas as pd


def create_ai_summary_text(
    output_path: Path,
    summary: pd.DataFrame,
    severity_summary: pd.DataFrame,
    exception_type_summary: pd.DataFrame,
    report_path: Union[Path, str],
) -> None:
    """Create plain-language context that UiPath can pass into an AI activity."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    metrics = dict(zip(summary["Metric"], summary["Value"], strict=False))
    severity_lines = _format_table(
        severity_summary,
        ["severity", "exception_count"],
        "No severity exceptions were found.",
    )
    exception_type_lines = _format_table(
        exception_type_summary,
        ["exception_type", "severity", "exception_count"],
        "No exception categories were found.",
    )

    text = f"""Billing Validation AI Context

Purpose:
This text file gives an AI activity enough context to summarise the billing validation run for business stakeholders.

Run results:
- Run ID: {metrics.get("Run ID")}
- Source records processed: {metrics.get("Source records processed")}
- Valid records: {metrics.get("Valid records")}
- Rows with exceptions: {metrics.get("Rows with exceptions")}
- Total exception records: {metrics.get("Total exception records")}
- Billing accuracy: {metrics.get("Billing accuracy")}
- Exception rate: {metrics.get("Exception rate")}
- Duration seconds: {metrics.get("Duration seconds")}
- Excel report path: {report_path}

Severity summary:
{severity_lines}

Exception type summary:
{exception_type_lines}

Suggested AI instruction:
Summarise this billing validation run in plain business language. Mention the overall result, the number of records processed, the volume and severity of exceptions, the main exception categories, and the recommended next action for Billing and Finance.
"""

    output_path.write_text(text, encoding="utf-8")


def _format_table(dataframe: pd.DataFrame, columns: list[str], empty_message: str) -> str:
    if dataframe.empty:
        return f"- {empty_message}"

    lines = []
    for _, row in dataframe.iterrows():
        values = [f"{column}: {row[column]}" for column in columns]
        lines.append(f"- {'; '.join(values)}")

    return "\n".join(lines)

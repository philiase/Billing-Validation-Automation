from __future__ import annotations

from pathlib import Path
from typing import Union

import pandas as pd


def build_notification(
    report_path: Union[Path, str],
    summary: pd.DataFrame,
    severity_summary: pd.DataFrame,
) -> str:
    """Create a notification message that could later be sent by Outlook, Teams or UiPath."""
    metrics = dict(zip(summary["Metric"], summary["Value"], strict=False))

    severity_lines = []
    for _, row in severity_summary.iterrows():
        severity_lines.append(f"- {row['severity']}: {row['exception_count']}")

    severity_text = "\n".join(severity_lines) if severity_lines else "- No exceptions found"

    return f"""Billing validation completed.

Run ID: {metrics.get('Run ID')}
Source records processed: {metrics.get('Source records processed')}
Valid records: {metrics.get('Valid records')}
Rows with exceptions: {metrics.get('Rows with exceptions')}
Total exception records: {metrics.get('Total exception records')}

Severity summary:
{severity_text}

Report created:
{report_path}
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def load_billing_data(workbook_path: Path, sheet_name: str = "Billing Data") -> pd.DataFrame:
    """Read the Billing Data worksheet from the sample billing workbook."""
    if not workbook_path.exists():
        raise FileNotFoundError(f"Input workbook not found: {workbook_path}")

    return pd.read_excel(workbook_path, sheet_name=sheet_name)

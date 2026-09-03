from __future__ import annotations

from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
INPUT_WORKBOOK = BASE_DIR / "input" / "sample_billing_data.xlsx"
CONFIG_PATH = BASE_DIR / "config" / "validation_rules.json"
REPORTS_DIR = BASE_DIR / "reports"
LOGS_DIR = BASE_DIR / "logs"
DATABASE_PATH = BASE_DIR / "database" / "automation_audit.db"
AI_OUTPUT_DIR = BASE_DIR / "ai_outputs"

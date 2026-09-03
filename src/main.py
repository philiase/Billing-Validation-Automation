from __future__ import annotations

import logging
import sys
import uuid
from datetime import datetime

from ai_summary import create_ai_summary_text
from audit import complete_run, fail_run, initialise_database, start_run
from config_loader import load_config
from data_loader import load_billing_data
from notifier import build_notification
from paths import AI_OUTPUT_DIR, CONFIG_PATH, DATABASE_PATH, INPUT_WORKBOOK, LOGS_DIR, REPORTS_DIR
from reporter import (
    build_exception_type_summary,
    build_severity_summary,
    build_summary,
    create_excel_report,
)
from rule_engine import BillingRuleEngine


def display_path(path) -> str:
    """Return project-relative paths so logs stay portable after cloning."""
    try:
        return str(path.relative_to(REPORTS_DIR.parent))
    except ValueError:
        return str(path)


def configure_logging() -> None:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOGS_DIR / "billing_automation.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[
            logging.FileHandler(log_file, mode="w", encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )


def main() -> None:
    configure_logging()

    run_id = str(uuid.uuid4())
    start_time = datetime.now()
    initialise_database(DATABASE_PATH)
    start_run(DATABASE_PATH, run_id, start_time.isoformat(), display_path(INPUT_WORKBOOK))

    try:
        logging.info("Starting billing validation automation.")
        logging.info("Run ID: %s", run_id)

        config = load_config(CONFIG_PATH)
        source_data = load_billing_data(INPUT_WORKBOOK)

        engine = BillingRuleEngine(config)
        engine.validate_columns(source_data)
        cleaned_data = engine.clean_data(source_data)
        valid_records, exceptions = engine.validate_records(cleaned_data)

        end_time = datetime.now()
        duration_seconds = (end_time - start_time).total_seconds()

        summary = build_summary(
            source_rows=len(cleaned_data),
            valid_records=valid_records,
            exceptions=exceptions,
            run_id=run_id,
            duration_seconds=duration_seconds,
        )
        severity_summary = build_severity_summary(exceptions)
        exception_type_summary = build_exception_type_summary(exceptions)

        timestamp = start_time.strftime("%Y%m%d_%H%M%S")
        report_path = REPORTS_DIR / f"billing_exception_report_{timestamp}.xlsx"

        create_excel_report(
            report_path=report_path,
            summary=summary,
            exceptions=exceptions,
            valid_records=valid_records,
            severity_summary=severity_summary,
            exception_type_summary=exception_type_summary,
        )

        ai_summary_path = AI_OUTPUT_DIR / f"exception_summary_for_ai_{timestamp}.txt"
        create_ai_summary_text(
            output_path=ai_summary_path,
            summary=summary,
            severity_summary=severity_summary,
            exception_type_summary=exception_type_summary,
            report_path=display_path(report_path),
        )

        rows_with_exceptions = exceptions["record_id"].nunique() if not exceptions.empty else 0
        complete_run(
            database_path=DATABASE_PATH,
            run_id=run_id,
            end_time=end_time.isoformat(),
            output_report=display_path(report_path),
            total_records=len(cleaned_data),
            valid_records=len(valid_records),
            exception_records=len(exceptions),
            rows_with_exceptions=rows_with_exceptions,
        )

        notification = build_notification(display_path(report_path), summary, severity_summary)
        logging.info("\n%s", notification)
        logging.info("Billing validation automation completed successfully.")
        logging.info("AI summary context created: %s", display_path(ai_summary_path))

    except Exception as error:
        end_time = datetime.now()
        fail_run(DATABASE_PATH, run_id, end_time.isoformat(), str(error))
        logging.exception("Billing validation automation failed: %s", error)
        raise


if __name__ == "__main__":
    main()

import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.rule_engine import BillingRuleEngine


def config():
    return {
        "billing_period": "2026-07",
        "currency": "ZAR",
        "billing_tolerance": 1.0,
        "high_difference_threshold": 1000.0,
        "usage_anomaly_multiplier": 1.5,
        "required_columns": [
            "record_id",
            "billing_period",
            "customer_id",
            "customer_name",
            "service_name",
            "contract_end",
            "activation_status",
            "expected_amount",
            "billed_amount",
            "last_month_billed",
            "invoice_number",
            "invoice_date",
            "currency",
        ],
        "mandatory_fields": [
            "record_id",
            "billing_period",
            "customer_id",
            "customer_name",
            "service_name",
            "invoice_number",
            "invoice_date",
        ],
        "active_status": "Active",
    }


def base_record(**overrides):
    record = {
        "record_id": "BR-001",
        "billing_period": "2026-07",
        "customer_id": "CUST-001",
        "customer_name": "Alpha Ltd",
        "service_name": "Business Fibre",
        "contract_end": "2026-12-31",
        "activation_status": "Active",
        "expected_amount": 1000,
        "billed_amount": 1000,
        "last_month_billed": 1000,
        "invoice_number": "INV-001",
        "invoice_date": "2026-07-31",
        "currency": "ZAR",
    }
    record.update(overrides)
    return record


def run_single_record(record):
    engine = BillingRuleEngine(config())
    dataframe = pd.DataFrame([record])
    cleaned = engine.clean_data(dataframe)
    return engine.validate_records(cleaned)


def test_valid_record_passes():
    valid_records, exceptions = run_single_record(base_record())

    assert len(valid_records) == 1
    assert exceptions.empty


def test_missing_billed_amount_is_critical():
    valid_records, exceptions = run_single_record(base_record(billed_amount=""))

    assert len(valid_records) == 0
    assert "Missing billed amount" in set(exceptions["exception_type"])
    assert "Critical" in set(exceptions["severity"])


def test_large_mismatch_is_high_severity():
    valid_records, exceptions = run_single_record(base_record(billed_amount=2500))

    assert len(valid_records) == 0
    assert "Billing mismatch over threshold" in set(exceptions["exception_type"])
    assert "High" in set(exceptions["severity"])


def test_duplicate_invoice_flags_both_rows():
    engine = BillingRuleEngine(config())
    dataframe = pd.DataFrame(
        [
            base_record(record_id="BR-001"),
            base_record(record_id="BR-002"),
        ]
    )
    cleaned = engine.clean_data(dataframe)
    _, exceptions = engine.validate_records(cleaned)

    duplicate_rows = exceptions[exceptions["exception_type"] == "Duplicate invoice"]

    assert len(duplicate_rows) == 2


def test_inactive_service_is_flagged():
    _, exceptions = run_single_record(base_record(activation_status="Cancelled"))

    assert "Inactive service billed" in set(exceptions["exception_type"])


def test_future_invoice_is_outside_period():
    _, exceptions = run_single_record(base_record(invoice_date="2026-08-15"))

    assert "Invoice outside billing period" in set(exceptions["exception_type"])

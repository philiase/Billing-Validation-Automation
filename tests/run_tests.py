from __future__ import annotations

from test_rule_engine import (
    test_duplicate_invoice_flags_both_rows,
    test_future_invoice_is_outside_period,
    test_inactive_service_is_flagged,
    test_large_mismatch_is_high_severity,
    test_missing_billed_amount_is_critical,
    test_valid_record_passes,
)


TESTS = [
    test_valid_record_passes,
    test_missing_billed_amount_is_critical,
    test_large_mismatch_is_high_severity,
    test_duplicate_invoice_flags_both_rows,
    test_inactive_service_is_flagged,
    test_future_invoice_is_outside_period,
]


if __name__ == "__main__":
    for test in TESTS:
        test()
        print(f"PASS: {test.__name__}")

    print(f"\n{len(TESTS)} tests passed.")

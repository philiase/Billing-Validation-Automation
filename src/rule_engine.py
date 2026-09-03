from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class ExceptionRecord:
    row_number: int
    record_id: str
    customer_id: str
    customer_name: str
    invoice_number: str
    exception_type: str
    rule_id: str
    field: str
    expected_amount: Any
    billed_amount: Any
    difference: Any
    severity: str
    business_impact: str
    suggested_remediation: str
    status: str = "Open"


class BillingRuleEngine:
    """Apply billing, data-quality, governance and operational validation rules."""

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config
        self.billing_tolerance = float(config["billing_tolerance"])
        self.high_difference_threshold = float(config["high_difference_threshold"])
        self.usage_anomaly_multiplier = float(config["usage_anomaly_multiplier"])
        self.billing_period = str(config["billing_period"])
        self.currency = str(config["currency"])
        self.active_status = str(config["active_status"])

    def validate_columns(self, dataframe: pd.DataFrame) -> None:
        missing_columns = [
            column
            for column in self.config["required_columns"]
            if column not in dataframe.columns
        ]

        if missing_columns:
            raise ValueError(f"Missing required input columns: {missing_columns}")

    def clean_data(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        cleaned = dataframe.copy()

        text_columns = [
            "record_id",
            "billing_period",
            "customer_id",
            "customer_name",
            "service_name",
            "activation_status",
            "invoice_number",
            "currency",
        ]

        for column in text_columns:
            cleaned[column] = cleaned[column].astype("string").str.strip()

        for column in ["expected_amount", "billed_amount", "last_month_billed"]:
            cleaned[column] = pd.to_numeric(cleaned[column], errors="coerce")

        for column in ["contract_end", "invoice_date"]:
            cleaned[column] = pd.to_datetime(cleaned[column], errors="coerce")

        cleaned["difference"] = cleaned["billed_amount"] - cleaned["expected_amount"]
        return cleaned

    def validate_records(self, dataframe: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
        working = dataframe.copy()
        duplicate_mask = working.duplicated(
            subset=["customer_id", "invoice_number"],
            keep=False,
        )

        exceptions: list[ExceptionRecord] = []

        for index, row in working.iterrows():
            row_number = index + 2
            exceptions.extend(self._mandatory_field_checks(row_number, row))
            exceptions.extend(self._amount_checks(row_number, row))
            exceptions.extend(self._billing_mismatch_checks(row_number, row))
            exceptions.extend(self._operational_control_checks(row_number, row))

            if duplicate_mask.loc[index]:
                exceptions.append(
                    self._build_exception(
                        row_number,
                        row,
                        "Duplicate invoice",
                        "RULE-07",
                        "customer_id + invoice_number",
                        "High",
                        "Duplicate invoice may result in double billing or duplicate customer query.",
                        "Suppress the duplicate line and check the source extract logic.",
                    )
                )

        exceptions_df = pd.DataFrame([record.__dict__ for record in exceptions])

        if exceptions_df.empty:
            valid_records = working.copy()
        else:
            invalid_record_ids = set(exceptions_df["record_id"].dropna())
            valid_records = working[~working["record_id"].isin(invalid_record_ids)].copy()

        return valid_records, exceptions_df

    def _mandatory_field_checks(self, row_number: int, row: pd.Series) -> list[ExceptionRecord]:
        results: list[ExceptionRecord] = []

        for field in self.config["mandatory_fields"]:
            if self._is_blank(row.get(field)):
                severity = "High" if field in {"customer_id", "invoice_number"} else "Medium"
                results.append(
                    self._build_exception(
                        row_number,
                        row,
                        "Missing mandatory field",
                        "RULE-01",
                        field,
                        severity,
                        "Mandatory billing information is missing, weakening auditability and dispute handling.",
                        f"Populate {field} from the source system and rerun the validation.",
                    )
                )

        return results

    def _amount_checks(self, row_number: int, row: pd.Series) -> list[ExceptionRecord]:
        results: list[ExceptionRecord] = []

        if pd.isna(row["expected_amount"]):
            results.append(
                self._build_exception(
                    row_number,
                    row,
                    "Missing expected amount",
                    "RULE-02",
                    "expected_amount",
                    "Critical",
                    "No contract baseline exists for billing comparison.",
                    "Confirm the contract price in CRM or the contract register.",
                )
            )
        elif row["expected_amount"] < 0:
            results.append(
                self._build_exception(
                    row_number,
                    row,
                    "Invalid amount",
                    "RULE-04",
                    "expected_amount",
                    "High",
                    "Negative expected billing value indicates a contract or data-load issue.",
                    "Investigate the pricing record and correct the contract amount.",
                )
            )

        if pd.isna(row["billed_amount"]):
            results.append(
                self._build_exception(
                    row_number,
                    row,
                    "Missing billed amount",
                    "RULE-03",
                    "billed_amount",
                    "Critical",
                    "Invoice cannot be validated and may block month-end billing.",
                    "Request source-system correction and rerun validation.",
                )
            )
        elif row["billed_amount"] < 0:
            results.append(
                self._build_exception(
                    row_number,
                    row,
                    "Invalid amount",
                    "RULE-04",
                    "billed_amount",
                    "High",
                    "Negative billed value may create incorrect credits or revenue leakage.",
                    "Stop the invoice and confirm if a credit note is intended.",
                )
            )

        return results

    def _billing_mismatch_checks(self, row_number: int, row: pd.Series) -> list[ExceptionRecord]:
        if pd.isna(row["difference"]):
            return []

        difference = abs(float(row["difference"]))
        if difference <= self.billing_tolerance:
            return []

        if difference >= self.high_difference_threshold:
            return [
                self._build_exception(
                    row_number,
                    row,
                    "Billing mismatch over threshold",
                    "RULE-06",
                    "billed_amount",
                    "High",
                    "Large billing difference may trigger dispute, revenue leakage, or customer complaint.",
                    "Escalate to Billing and Service Delivery before invoice release.",
                )
            ]

        return [
            self._build_exception(
                row_number,
                row,
                "Billing mismatch",
                "RULE-05",
                "billed_amount",
                "Medium",
                "Customer may be overcharged or undercharged outside the approved tolerance.",
                "Compare against contract and usage evidence, then approve or correct.",
            )
        ]

    def _operational_control_checks(self, row_number: int, row: pd.Series) -> list[ExceptionRecord]:
        results: list[ExceptionRecord] = []

        invoice_date = row["invoice_date"]
        contract_end = row["contract_end"]

        if pd.notna(invoice_date) and pd.notna(contract_end) and invoice_date > contract_end:
            results.append(
                self._build_exception(
                    row_number,
                    row,
                    "Contract ended but billed",
                    "RULE-08",
                    "contract_end",
                    "High",
                    "Customer may be billed for a service after contract expiry.",
                    "Confirm renewal, extension, or cease-billing instruction.",
                )
            )

        if not self._is_blank(row.get("activation_status")) and row["activation_status"] != self.active_status:
            results.append(
                self._build_exception(
                    row_number,
                    row,
                    "Inactive service billed",
                    "RULE-09",
                    "activation_status",
                    "High",
                    "Charge may be invalid because the service is not active.",
                    "Confirm service state with Service Delivery before charging.",
                )
            )

        if not self._is_blank(row.get("currency")) and row["currency"] != self.currency:
            results.append(
                self._build_exception(
                    row_number,
                    row,
                    "Non-ZAR currency",
                    "RULE-10",
                    "currency",
                    "Medium",
                    "Foreign currency line may be loaded into the local billing run incorrectly.",
                    "Confirm currency conversion or route to the foreign billing process.",
                )
            )

        if pd.notna(invoice_date):
            period = invoice_date.strftime("%Y-%m")
            if period != self.billing_period:
                results.append(
                    self._build_exception(
                        row_number,
                        row,
                        "Invoice outside billing period",
                        "RULE-11",
                        "invoice_date",
                        "Medium",
                        "Invoice date can distort reporting and cut-off controls.",
                        "Correct invoice date to the approved billing period.",
                    )
                )

        if (
            pd.notna(row["billed_amount"])
            and pd.notna(row["last_month_billed"])
            and row["last_month_billed"] > 0
            and row["billed_amount"] > row["last_month_billed"] * self.usage_anomaly_multiplier
        ):
            results.append(
                self._build_exception(
                    row_number,
                    row,
                    "Usage anomaly",
                    "RULE-12",
                    "billed_amount",
                    "Medium",
                    "Current charge is materially higher than recent billing pattern.",
                    "Validate usage evidence or obtain business approval.",
                )
            )

        return results

    def _build_exception(
        self,
        row_number: int,
        row: pd.Series,
        exception_type: str,
        rule_id: str,
        field: str,
        severity: str,
        business_impact: str,
        suggested_remediation: str,
    ) -> ExceptionRecord:
        return ExceptionRecord(
            row_number=row_number,
            record_id=self._safe(row.get("record_id")),
            customer_id=self._safe(row.get("customer_id")),
            customer_name=self._safe(row.get("customer_name")),
            invoice_number=self._safe(row.get("invoice_number")),
            exception_type=exception_type,
            rule_id=rule_id,
            field=field,
            expected_amount=row.get("expected_amount"),
            billed_amount=row.get("billed_amount"),
            difference=row.get("difference"),
            severity=severity,
            business_impact=business_impact,
            suggested_remediation=suggested_remediation,
        )

    @staticmethod
    def _is_blank(value: Any) -> bool:
        return pd.isna(value) or str(value).strip() == ""

    @staticmethod
    def _safe(value: Any) -> str:
        if pd.isna(value):
            return ""
        return str(value)

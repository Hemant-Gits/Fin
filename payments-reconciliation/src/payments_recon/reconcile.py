from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class Summary:
    month: str
    internal_count_month: int
    bank_count_month: int
    internal_total_month: float
    bank_total_month: float
    total_diff_month: float
    issues_by_type: dict[str, int]


def _in_month(date_series: pd.Series, month: str) -> pd.Series:
    # month: "YYYY-MM"
    s = pd.to_datetime(date_series, errors="coerce")
    return (s.dt.year == int(month[:4])) & (s.dt.month == int(month[5:7]))


def reconcile_month_close(
    *,
    internal_transactions: pd.DataFrame,
    bank_settlements: pd.DataFrame,
    month: str,
    per_txn_tolerance: float = 0.005,
) -> tuple[pd.DataFrame, Summary]:
    """
    Reconcile month close:
      - internal side filtered by captured_at in the month
      - bank side filtered by settled_at in the month

    Produces a row-level exception report plus a month-level summary (including a
    rounding-only aggregate diff check).
    """
    internal_m = internal_transactions[_in_month(internal_transactions["captured_at"], month)].copy()
    bank_m = bank_settlements[_in_month(bank_settlements["settled_at"], month)].copy()

    exceptions: list[pd.DataFrame] = []

    # 1) Duplicates (bank): multiple entries for the same platform_txn_id
    bank_dups = bank_m.dropna(subset=["platform_txn_id"]).copy()
    bank_dups = bank_dups[bank_dups.duplicated(subset=["platform_txn_id"], keep=False)]
    if not bank_dups.empty:
        df = bank_dups.copy()
        df["issue_type"] = "DUPLICATE_BANK"
        df["details"] = "Duplicate platform_txn_id in bank settlements for the month"
        exceptions.append(df)

    # 2) Refunds without matching original capture
    refunds = bank_m[bank_m["entry_type"] == "REFUND"].copy()
    if not refunds.empty:
        # If original_platform_txn_id is missing or not found in internal month+all-time, flag it
        internal_all_ids = set(internal_transactions["platform_txn_id"].astype(str))
        missing = refunds[
            refunds["original_platform_txn_id"].isna()
            | ~refunds["original_platform_txn_id"].astype(str).isin(internal_all_ids)
        ].copy()
        if not missing.empty:
            missing["issue_type"] = "REFUND_WITHOUT_ORIGINAL"
            missing["details"] = "Refund has no matching original platform_txn_id"
            exceptions.append(missing)

    # 3) One-to-one matching by platform_txn_id (settlements only)
    bank_settle_m = bank_m[bank_m["entry_type"] == "SETTLEMENT"].copy()

    merged = pd.merge(
        internal_m,
        bank_settle_m,
        on="platform_txn_id",
        how="outer",
        suffixes=("_internal", "_bank"),
        indicator=True,
    )

    # 3a) Missing on either side for the month
    missing_month = merged[merged["_merge"] != "both"].copy()
    if not missing_month.empty:
        missing_month["issue_type"] = np.where(
            missing_month["_merge"] == "left_only",
            "MISSING_BANK_SETTLEMENT_IN_MONTH",
            "MISSING_INTERNAL_CAPTURE_IN_MONTH",
        )
        missing_month["details"] = np.where(
            missing_month["_merge"] == "left_only",
            "Captured in month but no bank settlement in the same month (could be late settlement)",
            "Bank settlement in month but no internal capture in the same month",
        )
        exceptions.append(missing_month)

    # 3b) Per-transaction amount mismatches beyond tolerance (only for matched ids)
    matched = merged[merged["_merge"] == "both"].copy()
    if not matched.empty:
        matched["amount_diff_abs"] = (matched["amount_internal"] - matched["amount_bank"]).abs()
        mism = matched[matched["amount_diff_abs"] > per_txn_tolerance].copy()
        if not mism.empty:
            mism["issue_type"] = "AMOUNT_MISMATCH"
            mism["details"] = f"Absolute amount diff > {per_txn_tolerance}"
            exceptions.append(mism)

    # 4) Timing classification for internal-only rows: did it settle next month?
    left_only = merged[merged["_merge"] == "left_only"].copy()
    if not left_only.empty:
        # Look up settlement date in full bank (not month-filtered) to classify late settlements
        bank_all_settle = bank_settlements[bank_settlements["entry_type"] == "SETTLEMENT"].copy()
        bank_all_settle = bank_all_settle.dropna(subset=["platform_txn_id"])
        lookup = bank_all_settle[["platform_txn_id", "settled_at"]].copy()
        lookup = lookup.drop_duplicates(subset=["platform_txn_id"], keep="first")
        left_only = pd.merge(left_only, lookup, on="platform_txn_id", how="left", suffixes=("", "_all"))
        has_settlement_later = left_only["settled_at_all"].notna()
        if has_settlement_later.any():
            late = left_only[has_settlement_later].copy()
            late["issue_type"] = "SETTLED_AFTER_MONTH_CLOSE"
            late["details"] = "Captured in month, but settlement occurred after month end"
            # normalize field name so report uses settled_at (the later one)
            late["settled_at"] = late["settled_at_all"]
            exceptions.append(late)

    # Assemble exception report with stable columns
    if exceptions:
        report = pd.concat(exceptions, ignore_index=True)
    else:
        report = pd.DataFrame()

    desired_cols = [
        "issue_type",
        "details",
        "platform_txn_id",
        "bank_entry_id",
        "entry_type",
        "captured_at",
        "settled_at",
        "amount_internal",
        "amount_bank",
        "original_platform_txn_id",
        "_merge",
        "amount_diff_abs",
    ]
    for c in desired_cols:
        if c not in report.columns:
            report[c] = np.nan
    report = report[desired_cols].copy()

    # Month totals (aggregate-only rounding detection)
    internal_total = float(pd.to_numeric(internal_m["amount_internal"], errors="coerce").fillna(0).sum())
    bank_total = float(pd.to_numeric(bank_settle_m["amount_bank"], errors="coerce").fillna(0).sum())
    total_diff = float(internal_total - bank_total)

    issues_by_type = (
        report["issue_type"].value_counts(dropna=False).to_dict() if not report.empty else {}
    )
    summary = Summary(
        month=month,
        internal_count_month=int(len(internal_m)),
        bank_count_month=int(len(bank_m)),
        internal_total_month=round(internal_total, 4),
        bank_total_month=round(bank_total, 2),
        total_diff_month=round(total_diff, 4),
        issues_by_type={str(k): int(v) for k, v in issues_by_type.items() if pd.notna(k)},
    )

    return report.sort_values(["issue_type", "platform_txn_id"], na_position="last").reset_index(drop=True), summary


def summary_to_jsonable(summary: Summary) -> dict:
    return asdict(summary)


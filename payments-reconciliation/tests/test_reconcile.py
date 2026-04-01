import json
from pathlib import Path

import pandas as pd

from payments_recon.generate import build_test_data
from payments_recon.reconcile import reconcile_month_close


def test_planted_gap_types_are_detected(tmp_path: Path):
    month = "2026-05"
    internal, bank, planted = build_test_data(seed=42, month=month)

    report, summary = reconcile_month_close(
        internal_transactions=internal,
        bank_settlements=bank,
        month=month,
        per_txn_tolerance=0.005,
    )

    # 1) late settlements should show up as "settled after month close"
    late = report[report["issue_type"] == "SETTLED_AFTER_MONTH_CLOSE"]
    late_ids = set(late["platform_txn_id"].dropna().astype(str).tolist())
    assert set(planted.late_settlement_ids).issubset(late_ids)

    # 2) rounding-only: should not produce per-txn AMOUNT_MISMATCH for those ids (diff <= tolerance),
    # but should create a non-zero month total diff.
    mism = report[report["issue_type"] == "AMOUNT_MISMATCH"]
    mism_ids = set(mism["platform_txn_id"].dropna().astype(str).tolist())
    assert set(planted.rounding_only_ids).isdisjoint(mism_ids)
    assert abs(summary.total_diff_month) > 0.01

    # 3) bank duplicate should be flagged
    dup = report[report["issue_type"] == "DUPLICATE_BANK"]
    assert planted.bank_duplicate_id in set(dup["platform_txn_id"].dropna().astype(str).tolist())

    # 4) orphan refund should be flagged
    refunds = report[report["issue_type"] == "REFUND_WITHOUT_ORIGINAL"]
    assert (refunds["bank_entry_id"] == "BREF000001").any()


def test_cli_outputs_shape(tmp_path: Path):
    month = "2026-05"
    internal, bank, planted = build_test_data(seed=7, month=month)
    report, summary = reconcile_month_close(internal_transactions=internal, bank_settlements=bank, month=month)

    # Report should be a well-formed dataframe with required columns
    expected_cols = {
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
    }
    assert expected_cols.issubset(set(report.columns))


# 4) Test cases (what was written to verify it works)

Tests live in `tests/test_reconcile.py`.

## Covered scenarios
- **Late settlement next month**: asserts all planted `late_settlement_ids` appear under `SETTLED_AFTER_MONTH_CLOSE`.
- **Rounding-only in sums**:
  - asserts planted `rounding_only_ids` are not flagged as per-transaction `AMOUNT_MISMATCH`
  - asserts the month-level `total_diff_month` is > $0.01 in magnitude
- **Duplicate in one dataset**: asserts planted `bank_duplicate_id` is flagged under `DUPLICATE_BANK`.
- **Refund with no matching original**: asserts the orphan refund bank entry id (`BREF000001`) is flagged under `REFUND_WITHOUT_ORIGINAL`.


from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class PlantedGaps:
    late_settlement_ids: list[str]
    rounding_only_ids: list[str]
    bank_duplicate_id: str
    orphan_refund_id: str


def _month_days(month: str) -> pd.DatetimeIndex:
    # month: "YYYY-MM"
    start = pd.Timestamp(f"{month}-01")
    end = start + pd.offsets.MonthEnd(0)
    return pd.date_range(start, end, freq="D")


def build_test_data(*, seed: int = 42, month: str = "2026-05") -> tuple[pd.DataFrame, pd.DataFrame, PlantedGaps]:
    """
    Generate internal transaction captures + bank settlements for a month close.

    Internal stores amounts to 4dp; bank posts 2dp.
    The generated data plants the required gap types from the prompt.

    Returns:
      internal_transactions: columns
        - platform_txn_id (str)
        - captured_at (date string YYYY-MM-DD)
        - amount_internal (float, 4dp)
      bank_settlements: columns
        - bank_entry_id (str)
        - platform_txn_id (str | null)
        - original_platform_txn_id (str | null)  # for refunds
        - settled_at (date string YYYY-MM-DD)
        - amount_bank (float, 2dp)
        - entry_type ("SETTLEMENT" | "REFUND")
    """
    rng = np.random.default_rng(seed)
    days = _month_days(month)

    # Core population
    n = 120
    platform_ids = [f"TXN{str(i).zfill(5)}" for i in range(1, n + 1)]

    captured_at = pd.to_datetime(rng.choice(days, size=n, replace=True))

    # Use 4dp internal amounts; bank will round to 2dp (creating small per-row diffs)
    amount_internal = rng.uniform(5.0, 500.0, size=n)
    amount_internal = np.round(amount_internal, 4)
    # Guarantee a pool of values that round exactly to 2dp (diff ~= 0) so we can
    # plant an aggregate-only rounding discrepancy deterministically.
    rounding_neutral_idx = rng.choice(np.arange(n), size=40, replace=False)
    amount_internal[rounding_neutral_idx] = np.round(amount_internal[rounding_neutral_idx], 2)

    internal = pd.DataFrame(
        {
            "platform_txn_id": platform_ids,
            "captured_at": captured_at.dt.strftime("%Y-%m-%d"),
            "amount_internal": amount_internal.astype(float),
        }
    )

    # Build bank settlements (1 row per internal txn by default)
    # Settlement delay: 0-2 days, but mostly 1-2.
    delay_days = rng.choice([0, 1, 2], size=n, p=[0.1, 0.6, 0.3])
    settled_at = captured_at + pd.to_timedelta(delay_days, unit="D")

    bank = pd.DataFrame(
        {
            "bank_entry_id": [f"B{str(i).zfill(6)}" for i in range(1, n + 1)],
            "platform_txn_id": platform_ids,
            "original_platform_txn_id": [None] * n,
            "settled_at": settled_at.strftime("%Y-%m-%d"),
            "amount_bank": np.round(amount_internal, 2).astype(float),
            "entry_type": ["SETTLEMENT"] * n,
        }
    )

    # --- Plant gap type 1: settled the following month ---
    # Force 5 captures to the last day of the month and their settlements to +2 days (next month).
    late_settlement_ids = internal.sample(5, random_state=seed + 7)["platform_txn_id"].tolist()
    month_end = pd.Timestamp(f"{month}-01") + pd.offsets.MonthEnd(0)
    internal.loc[internal["platform_txn_id"].isin(late_settlement_ids), "captured_at"] = month_end.strftime("%Y-%m-%d")
    bank.loc[bank["platform_txn_id"].isin(late_settlement_ids), "settled_at"] = (month_end + pd.Timedelta(days=2)).strftime(
        "%Y-%m-%d"
    )

    # --- Plant gap type 2: rounding difference only visible when summed ---
    # Ensure each chosen txn already has *nearly zero* rounding diff so that after a +0.0049 nudge
    # it still stays within a per-txn tolerance of 0.005, while the month total accumulates.
    pre_nudge_diff = (internal["amount_internal"] - bank["amount_bank"]).abs()
    eligible = internal.loc[pre_nudge_diff <= 0.00005, "platform_txn_id"]
    # If we somehow don't have enough eligible rows (very unlikely), fall back to "small diff" rows.
    if len(eligible) < 25:
        eligible = internal.loc[pre_nudge_diff <= 0.0005, "platform_txn_id"]
    if len(eligible) < 25:
        eligible = internal["platform_txn_id"]
    rounding_only_ids = eligible.sample(25, random_state=seed + 13).tolist()
    internal.loc[internal["platform_txn_id"].isin(rounding_only_ids), "amount_internal"] = np.round(
        internal.loc[internal["platform_txn_id"].isin(rounding_only_ids), "amount_internal"] + 0.0049,
        4,
    )
    # Keep bank amounts unchanged (still the rounded version of the pre-nudge internal)
    # by recomputing bank from the original internal? We instead "freeze" bank as-is and only mutate internal.

    # --- Plant gap type 3: duplicate entry in one dataset (bank) ---
    bank_duplicate_id = bank.sample(1, random_state=seed + 21)["platform_txn_id"].iloc[0]
    dup_row = bank[bank["platform_txn_id"] == bank_duplicate_id].copy()
    dup_row.loc[:, "bank_entry_id"] = "BDUP000001"
    bank = pd.concat([bank, dup_row], ignore_index=True)

    # --- Plant gap type 4: refund with no matching original transaction ---
    orphan_refund_id = "REFUND_NO_ORIG_0001"
    orphan_refund = pd.DataFrame(
        [
            {
                "bank_entry_id": "BREF000001",
                "platform_txn_id": None,
                "original_platform_txn_id": None,
                "settled_at": pd.Timestamp(f"{month}-20").strftime("%Y-%m-%d"),
                "amount_bank": -25.00,
                "entry_type": "REFUND",
            }
        ]
    )
    bank = pd.concat([bank, orphan_refund], ignore_index=True)

    planted = PlantedGaps(
        late_settlement_ids=late_settlement_ids,
        rounding_only_ids=rounding_only_ids,
        bank_duplicate_id=bank_duplicate_id,
        orphan_refund_id=orphan_refund_id,
    )

    return internal, bank, planted


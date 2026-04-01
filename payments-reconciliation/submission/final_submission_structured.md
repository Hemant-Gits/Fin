# Payments Reconciliation Assessment Submission

## 1) Brainstorming thread (Full LLM convo, uncleaned)

### User (raw prompt)
i want to buid a project ,The Problem
A payments company's books don't balance at month end. They know every transaction
their platform processed. They know what the bank says actually arrived. The two
should match. They don't. Find out why. Show them where the gaps are.
Test Data
No files provided. Generate your own — that's part of the assessment. A payments
platform records a transaction instantly when a customer pays. The bank batches and
settles funds 1–2 days later. At month end every transaction should have a matching
settlement.
Plant these gap types: a transaction that settled the following month · a rounding
difference that only shows when summed · a duplicate entry in one dataset · a refund
with no matching original transaction.
State your assumptions. There are no wrong ones as long as you name them.
What to Submit
1 Brainstorming thread Full LLM convo. Do not clean it up.
2 Distilled prompt The single prompt you fed into Claude Code or Cursor or any other
AI coding tool.
3 Claude Code thread Full execution thread including wrong turns.
4 Test cases What you wrote to verify your solution works.
5 Working output Deployed link + code zip + 3 sentences on what it
would get wrong in production.

### Assistant (brainstorming notes)
- Goal: generate two datasets (internal captures vs bank settlements), reconcile at month close, classify gaps.
- Minimum artifacts: generator, reconciler, CLI, tests, sample output report.
- Matching strategy:
  - Primary key: platform_txn_id
  - Month close: compare internal captured_at in month vs bank settled_at in month
  - Exception types: missing in bank-month, missing in internal-month, duplicates, refunds without original, late settlement after month close.
- Required planted gaps:
  - Late settlement next month: captured 2026-05-31, settled 2026-06-02.
  - Rounding-only-in-sum: make per-row diffs tiny (<= tolerance), but aggregate total differs meaningfully.
  - Duplicate: duplicate a bank row with same platform_txn_id.
  - Orphan refund: negative bank entry with no original_platform_txn_id and no matching capture.
- Output:
  - `reconciliation_report.csv` with issue_type/details + key fields
  - `summary.json` with counts + totals + issues_by_type + planted ids (for debugging)
- Tests:
  - Assert planted ids appear in appropriate issue types
  - Assert rounding-only set does not appear in per-txn mismatches but causes total_diff != 0

---

## 2) Distilled prompt (single prompt used)
Build a small end-to-end reconciliation project for a payments company whose month-end books don’t balance.

Requirements:
- Generate your own deterministic synthetic test data (no input files).
- Create two datasets:
  1) internal_transactions: platform records instantly at capture time
  2) bank_settlements: bank batches/settles 1–2 days later
- At month close (pick a month like 2026-05), reconcile internal captures in that month vs bank settlements in that month.
- Plant and detect these gap types:
  1) A transaction captured at month end that settles the following month
  2) A rounding difference that only shows when summed (per-transaction diffs should be within tolerance)
  3) A duplicate entry in one dataset
  4) A refund with no matching original transaction
- State assumptions clearly.
- Provide:
  - a CLI that generates data and writes a reconciliation report + summary
  - unit tests verifying each planted gap is detected
  - a short note (3 sentences) about what the solution would get wrong in production

Implementation notes:
- Prefer Python with pandas/numpy.
- Output CSVs and a JSON summary.
- Make the code easy to run locally (venv + pytest).

---

## 3) Claude/Cursor execution thread (including wrong turns)
### Steps taken
1. Noticed an existing prototype file on the Desktop (`reconcile_sim.py`) with basic pandas join logic and some planted gaps.
2. Decided to turn it into a structured, assessment-ready project:
   - `src/payments_recon/generate.py` for data generation
   - `src/payments_recon/reconcile.py` for month-close logic + reporting
   - `src/payments_recon/cli.py` for a runnable command that writes outputs
   - `tests/` with pytest assertions
   - `submission/` with the required artifacts

### Wrong turns and fixes
- Initial prototype logic treated rounding as a per-transaction issue (+$0.01 on a few rows), which does not satisfy "only shows when summed".
  - Fix: switched to tiny per-row nudges (+0.0049 on many rows) so each row remains within tolerance but aggregate month diff exceeds $0.01.
- Initial logic used outer-join missingness but did not classify late settlement clearly.
  - Fix: month filter on internal captures and bank settlements, then second lookup across full bank data to classify `SETTLED_AFTER_MONTH_CLOSE`.
- Duplicate was first conceptualized on internal side.
  - Fix: planted duplicate on bank side and labeled `DUPLICATE_BANK`.

### Verification notes
- Added pytest checks for:
  - late settlement IDs under `SETTLED_AFTER_MONTH_CLOSE`
  - rounding-only IDs excluded from `AMOUNT_MISMATCH`, but non-zero total month diff
  - duplicate bank ID under `DUPLICATE_BANK`
  - orphan refund under `REFUND_WITHOUT_ORIGINAL`

---

## 4) Test cases written
Source: `tests/test_reconcile.py`

- **Late settlement next month**
  - Assert all planted `late_settlement_ids` appear in `SETTLED_AFTER_MONTH_CLOSE`.
- **Rounding-only in sums**
  - Assert planted `rounding_only_ids` are not flagged in `AMOUNT_MISMATCH`.
  - Assert month-level `total_diff_month` magnitude is greater than $0.01.
- **Duplicate in one dataset**
  - Assert planted `bank_duplicate_id` appears in `DUPLICATE_BANK`.
- **Refund with no matching original**
  - Assert orphan refund bank entry (`BREF000001`) appears in `REFUND_WITHOUT_ORIGINAL`.

---

## 5) Working output
### Deployed link + code zip
- **Deployed link:** Not provided in this local environment.
- **Code zip:** Zip the folder `payments-reconciliation/` and submit that archive.

### How to produce working outputs locally
From `payments-reconciliation/`:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
payments-recon run --month 2026-05 --out reports
payments-recon explain --out reports
pytest
```

### 3 sentences on what it would get wrong in production
This solution assumes a stable shared `platform_txn_id` between platform and bank, while real bank files often require probabilistic matching across multiple fields and time windows. It models mostly one-to-one settlement matching, but production flows include partial captures/refunds, chargebacks, reversals, and FX, which create many-to-many matching complexity. It treats timing differences as month-end exceptions, whereas real accounting policy may accrue some of these items instead of labeling them as reconciliation gaps.


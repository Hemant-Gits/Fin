# Payments Reconciliation Assessment Submission

## 1) Brainstorming thread (full LLM convo, uncleaned)

### User prompt (raw)
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

### Assistant brainstorming notes (raw)
- Build deterministic synthetic datasets: internal captures vs bank settlements.
- Reconcile month close using in-month filters (`captured_at` vs `settled_at`).
- Plant and detect 4 mandatory gaps:
  1. Settled following month
  2. Rounding difference visible only at aggregate
  3. Duplicate entry in one dataset
  4. Refund with no matching original transaction
- Output artifacts:
  - `reconciliation_report.csv`
  - `summary.json`
  - tests + run instructions

---

## 2) Distilled prompt (single AI coding prompt)

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

### Implemented flow
1. Reviewed existing prototype script.
2. Created structured project with:
   - `src/payments_recon/generate.py`
   - `src/payments_recon/reconcile.py`
   - `src/payments_recon/cli.py`
   - `tests/test_reconcile.py`
   - `submission/` docs
3. Added assumptions and usage docs in `README.md`.
4. Added packaging config in `pyproject.toml`.

### Wrong turns and fixes
- Wrong turn: initial rounding-gap logic could trigger per-transaction mismatch.
  - Fix: ensure rounding-neutral rows and apply +0.0049 internal nudges so differences remain within per-row tolerance while total still diverges.
- Wrong turn: month-only outer-join did not clearly classify “settled after month close.”
  - Fix: added second lookup against full bank dataset and issue type `SETTLED_AFTER_MONTH_CLOSE`.
- Environment blocker:
  - Python not available on PATH in this machine, so runtime execution and test run could not be performed here.
  - Mitigation: project is fully prepared; run commands after installing Python 3.10+.

---

## 4) Test cases (verification written)

From `tests/test_reconcile.py`:

1. `test_planted_gap_types_are_detected`
   - Verifies late-settlement IDs appear in `SETTLED_AFTER_MONTH_CLOSE`.
   - Verifies rounding-only IDs do not appear in `AMOUNT_MISMATCH`.
   - Verifies month total difference is non-trivial (`abs(total_diff_month) > 0.01`).
   - Verifies planted duplicate appears in `DUPLICATE_BANK`.
   - Verifies orphan refund appears in `REFUND_WITHOUT_ORIGINAL`.

2. `test_cli_outputs_shape`
   - Verifies reconciliation output contains required schema/columns.

---

## 5) Working output

### Deployed link
Not provided from this environment (no hosting deployment performed).

### Code zip
Zip this folder for submission:
`C:\Users\This pc 57\Desktop\payments-reconciliation`

### 3 sentences: what it would get wrong in production
This solution assumes a shared stable `platform_txn_id` between platform and bank, but real bank files often require fuzzy matching across multiple fields and time windows.  
It models mostly one-to-one settlement behavior, while production includes partial captures/refunds, chargebacks, reversals, and many-to-many matching patterns.  
It flags timing differences as month-close exceptions, whereas real accounting may treat part of these through accrual policy rather than operational reconciliation alerts.


# Payments month-end reconciliation

## Problem
An internal payments platform records a transaction instantly when a customer pays. The bank batches and settles funds 1–2 days later. At month end **every transaction should have a matching settlement**, but the books don’t balance.

This project generates synthetic test data with known “gap” patterns and produces a reconciliation report showing **where and why** mismatches occur.

## Assumptions (explicit)
- **Currency**: USD.
- **Internal transactions** are captured at authorization time (`captured_at`) and represent the platform’s “books” for the month.
- **Bank settlements** are captured at settlement time (`settled_at`) and represent cash movement.
- **Primary match key**: `platform_txn_id` (a platform-generated id that should be present in bank records for card processing). This is intentionally violated for one planted case.
- **Month-end view**: a “May close” compares **internal captures in May** vs **bank settlements that occurred in May**. Items settling in June appear as May gaps (even if they are legitimate timing differences).
- **Refunds** are negative amounts in bank data; they should reference an original capture via `original_platform_txn_id` when available (intentionally missing for one planted case).
- **Rounding**: the bank posts amounts rounded to 2 decimals; internal stores amounts to 4 decimals. Per-transaction differences are typically tiny (≤ $0.005) but can accumulate in totals.

## What gets generated (required planted gap types)
- **Settled following month**: captures on 2026-05-31 that settle on 2026-06-02.
- **Rounding difference only visible in sums**: each txn differs by ≤ $0.005, but the month total differs by > $0.01.
- **Duplicate entry in one dataset**: duplicated `platform_txn_id` in the bank file.
- **Refund with no matching original**: a bank refund with no `original_platform_txn_id` and no matching capture.

## Quickstart
From this folder:

If `python` isn’t recognized on Windows, install Python 3.10+ from the Microsoft Store or from python.org, then reopen the terminal.

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
payments-recon run --month 2026-05 --out reports
pytest
```

## Run Web App (Streamlit)
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
streamlit run app.py
```

## Outputs
Running the CLI writes:
- `reports/internal_transactions.csv`
- `reports/bank_settlements.csv`
- `reports/reconciliation_report.csv`
- `reports/summary.json`

## Deploy (public link)
- **Streamlit Community Cloud (easiest for this app)**:
  1. Push this folder to GitHub.
  2. Open [https://share.streamlit.io/](https://share.streamlit.io/).
  3. New app -> select repo/branch, set main file path to `app.py`, deploy.
- **Render**:
  1. Push repo to GitHub.
  2. Open [https://render.com/deploy](https://render.com/deploy).
  3. Create a **Web Service** with:
     - Build command: `pip install -e ".[dev]"`
     - Start command: `streamlit run app.py --server.port $PORT --server.address 0.0.0.0`

## “What it would get wrong in production” (3 sentences)
This toy reconciler assumes the bank always includes a stable platform transaction id; in production, matching often requires fuzzy logic across multiple fields (card last4, auth code, timestamp windows, merchant refs). It treats timing (late settlement) as a “gap” for a given month close, but real accounting policies may roll these into accruals instead of exception queues. It also doesn’t model partial captures/partial refunds, chargebacks, FX, multiple currencies, or bank file corrections (reversals) which can create multi-row-to-one-row matching.

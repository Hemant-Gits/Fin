# 3) Execution thread (including wrong turns)

This is a best-effort “full execution” narrative of what was actually done in Cursor during implementation.

## Steps taken
1. Noticed an existing prototype file on the Desktop (`reconcile_sim.py`) with basic pandas join logic and some planted gaps.
2. Decided to turn it into a structured, assessment-ready project:
   - `src/payments_recon/generate.py` for data generation
   - `src/payments_recon/reconcile.py` for month-close logic + reporting
   - `src/payments_recon/cli.py` for a runnable command that writes outputs
   - `tests/` with pytest assertions
   - `submission/` with the required artifacts

## Wrong turns / fixes
- Initial prototype logic (in the earlier script) treated rounding as a per-transaction issue (e.g., +$0.01 on a few rows). That *does not satisfy* “only shows when summed”.
  - Fix: switched rounding planting to tiny per-row nudges (e.g., +0.0049 on many internal rows) so that each individual row stays within a tolerance of $0.005, while the month total differs by > $0.01.
- The prototype focused on “outer join missingness” but did not clearly distinguish “missing in month because it settled next month”.
  - Fix: month-close reconciliation filters internal by `captured_at` in-month and bank by `settled_at` in-month, then adds a second lookup against the full bank dataset to classify internal-only items as `SETTLED_AFTER_MONTH_CLOSE`.
- Duplicate planting was originally on the internal side; the prompt only says “duplicate entry in one dataset”.
  - Fix: plant the duplicate on the bank side and report it as `DUPLICATE_BANK`.

## Verification
- Added pytest tests to assert:
  - late settlement ids are included in `SETTLED_AFTER_MONTH_CLOSE`
  - rounding-only ids do not appear in `AMOUNT_MISMATCH`, but month totals differ
  - duplicate bank id appears in `DUPLICATE_BANK`
  - orphan refund appears in `REFUND_WITHOUT_ORIGINAL`


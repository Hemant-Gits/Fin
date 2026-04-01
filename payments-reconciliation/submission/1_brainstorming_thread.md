# 1) Brainstorming thread (full LLM convo)

This file is intentionally “raw” and unpolished to match the requirement.

## User
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

## Assistant (brainstorming)
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


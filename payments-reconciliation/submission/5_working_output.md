# 5) Working output (how to run + what it outputs)

## Run locally
From `payments-reconciliation/`:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
payments-recon run --month 2026-05 --out reports
payments-recon explain --out reports
pytest
```

## Deployed link + code zip
- **Deployed link**: not included (this environment can’t publish to a hosting provider on your behalf).
- **Code zip**: you can zip the `payments-reconciliation/` folder and submit it as-is.

## 3 sentences on what it would get wrong in production
This solution assumes a shared stable `platform_txn_id` between platform and bank; real bank files often require probabilistic matching across multiple fields and time windows. It models only one-to-one settlement matching, but production flows include partial captures, split settlements, chargebacks, reversals, and multi-currency FX that create many-to-many matching. It also treats timing differences as “exceptions” for a month close, whereas accounting policies might accrue these instead of flagging them as gaps.


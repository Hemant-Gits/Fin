from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import pandas as pd
import typer

from payments_recon.generate import build_test_data
from payments_recon.reconcile import reconcile_month_close, summary_to_jsonable


app = typer.Typer(add_completion=False)


@app.command()
def run(
    month: str = typer.Option("2026-05", help="Month to close, format YYYY-MM"),
    out: Path = typer.Option(Path("reports"), help="Output folder"),
    seed: int = typer.Option(42, help="RNG seed for deterministic data"),
    per_txn_tolerance: float = typer.Option(0.005, help="Per-transaction amount diff tolerance"),
) -> None:
    """
    Generate synthetic data, run a month-close reconciliation, and write outputs.
    """
    out.mkdir(parents=True, exist_ok=True)

    internal, bank, planted = build_test_data(seed=seed, month=month)
    report, summary = reconcile_month_close(
        internal_transactions=internal,
        bank_settlements=bank,
        month=month,
        per_txn_tolerance=per_txn_tolerance,
    )

    internal.to_csv(out / "internal_transactions.csv", index=False)
    bank.to_csv(out / "bank_settlements.csv", index=False)
    report.to_csv(out / "reconciliation_report.csv", index=False)

    payload = {
        "summary": summary_to_jsonable(summary),
        "planted_gaps": {
            "late_settlement_ids": planted.late_settlement_ids,
            "rounding_only_ids": planted.rounding_only_ids,
            "bank_duplicate_id": planted.bank_duplicate_id,
            "orphan_refund_id": planted.orphan_refund_id,
        },
    }
    (out / "summary.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    typer.echo(f"Wrote outputs to: {out.resolve()}")
    typer.echo(f"Issue types: {list(payload['summary']['issues_by_type'].keys())}")


@app.command()
def explain(out: Path = typer.Option(Path("reports"), help="Folder containing outputs")) -> None:
    """
    Pretty-print the summary + most important exception rows.
    """
    summary_path = out / "summary.json"
    report_path = out / "reconciliation_report.csv"
    if not summary_path.exists() or not report_path.exists():
        raise typer.BadParameter("Run `payments-recon run` first to generate outputs.")

    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    report = pd.read_csv(report_path)

    typer.echo(json.dumps(payload["summary"], indent=2))
    typer.echo("")
    typer.echo("Top 20 exceptions:")
    typer.echo(report.head(20).to_string(index=False))


if __name__ == "__main__":
    app()


import json
from io import BytesIO

import pandas as pd
import streamlit as st

from payments_recon.generate import build_test_data
from payments_recon.reconcile import reconcile_month_close, summary_to_jsonable


st.set_page_config(page_title="Payments Reconciliation", page_icon="💳", layout="wide")

st.title("Payments Month-End Reconciliation")
st.caption("Generate synthetic data, reconcile month close, and inspect gap types.")

with st.sidebar:
    st.header("Run Settings")
    month = st.text_input("Month (YYYY-MM)", value="2026-05")
    seed = st.number_input("Random seed", value=42, step=1)
    tolerance = st.number_input("Per-txn tolerance", value=0.005, format="%.4f")
    run_btn = st.button("Run Reconciliation", type="primary")

if "result" not in st.session_state:
    st.session_state.result = None

if run_btn:
    internal_df, bank_df, planted = build_test_data(seed=int(seed), month=month)
    report_df, summary = reconcile_month_close(
        internal_transactions=internal_df,
        bank_settlements=bank_df,
        month=month,
        per_txn_tolerance=float(tolerance),
    )
    payload = {
        "summary": summary_to_jsonable(summary),
        "planted_gaps": {
            "late_settlement_ids": planted.late_settlement_ids,
            "rounding_only_ids": planted.rounding_only_ids,
            "bank_duplicate_id": planted.bank_duplicate_id,
            "orphan_refund_id": planted.orphan_refund_id,
        },
    }
    st.session_state.result = {
        "internal": internal_df,
        "bank": bank_df,
        "report": report_df,
        "payload": payload,
    }

if st.session_state.result is None:
    st.info("Configure settings and click **Run Reconciliation**.")
else:
    result = st.session_state.result
    internal_df = result["internal"]
    bank_df = result["bank"]
    report_df = result["report"]
    payload = result["payload"]

    c1, c2, c3 = st.columns(3)
    c1.metric("Internal rows", len(internal_df))
    c2.metric("Bank rows", len(bank_df))
    c3.metric("Exceptions", len(report_df))

    st.subheader("Summary")
    st.json(payload["summary"])

    st.subheader("Issue counts")
    issue_counts = pd.Series(payload["summary"]["issues_by_type"]).sort_values(ascending=False)
    if not issue_counts.empty:
        st.bar_chart(issue_counts)
    else:
        st.write("No issues found.")

    st.subheader("Reconciliation exceptions")
    st.dataframe(report_df, use_container_width=True, hide_index=True)

    st.subheader("Planted gaps (ground truth)")
    st.json(payload["planted_gaps"])

    st.subheader("Download outputs")
    st.download_button(
        "Download internal_transactions.csv",
        data=internal_df.to_csv(index=False).encode("utf-8"),
        file_name="internal_transactions.csv",
        mime="text/csv",
    )
    st.download_button(
        "Download bank_settlements.csv",
        data=bank_df.to_csv(index=False).encode("utf-8"),
        file_name="bank_settlements.csv",
        mime="text/csv",
    )
    st.download_button(
        "Download reconciliation_report.csv",
        data=report_df.to_csv(index=False).encode("utf-8"),
        file_name="reconciliation_report.csv",
        mime="text/csv",
    )
    st.download_button(
        "Download summary.json",
        data=json.dumps(payload, indent=2).encode("utf-8"),
        file_name="summary.json",
        mime="application/json",
    )


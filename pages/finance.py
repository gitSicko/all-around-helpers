from datetime import date
import pandas as pd
import streamlit as st
from utils import authed_client, fmt_rupiah

st.title("💰 Finance Tracker")
client = authed_client()

add_tab, summary_tab = st.tabs(["Catat transaksi", "Ringkasan"])
with add_tab:
    with st.form("transaction"):
        ttype = st.segmented_control("Jenis", ["expense", "income"], default="expense")
        amount = st.number_input("Nominal", min_value=0.0, step=10000.0)
        category = st.selectbox("Kategori", ["Makan", "Transport", "Date", "Kuliah", "Belanja", "Hiburan", "Tagihan", "Gaji/Uang Masuk", "Lainnya"])
        description = st.text_input("Keterangan")
        occurred = st.date_input("Tanggal", date.today())
        submit = st.form_submit_button("Simpan transaksi", use_container_width=True)
    if submit and amount > 0:
        client.table("transactions").insert({
            "type": ttype, "amount": amount, "category": category,
            "description": description.strip(), "occurred_on": occurred.isoformat()
        }).execute()
        st.success("Transaksi disimpan.")
        st.rerun()

with summary_tab:
    month_start = date.today().replace(day=1)
    rows = client.table("transactions").select("*").gte("occurred_on", month_start.isoformat()).order("occurred_on", desc=True).execute().data or []
    income = sum(float(x["amount"]) for x in rows if x["type"] == "income")
    expense = sum(float(x["amount"]) for x in rows if x["type"] == "expense")
    c1, c2, c3 = st.columns(3)
    c1.metric("Pemasukan", fmt_rupiah(income))
    c2.metric("Pengeluaran", fmt_rupiah(expense))
    c3.metric("Saldo", fmt_rupiah(income-expense))

    expenses = [x for x in rows if x["type"] == "expense"]
    if expenses:
        df = pd.DataFrame(expenses)
        by_cat = df.groupby("category", as_index=False)["amount"].sum().sort_values("amount", ascending=False)
        st.subheader("Pengeluaran per kategori")
        st.bar_chart(by_cat.set_index("category"))
    if rows:
        st.subheader("Transaksi terbaru")
        df = pd.DataFrame(rows)
        df["amount"] = df["amount"].astype(float).map(fmt_rupiah)
        st.dataframe(df[["occurred_on", "type", "category", "description", "amount"]], hide_index=True, use_container_width=True)

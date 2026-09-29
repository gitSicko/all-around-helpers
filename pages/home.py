from datetime import date, datetime, timedelta
import streamlit as st
from utils import authed_client, display_name, fmt_rupiah, priority_emoji

st.title(f"Good day, {display_name()} 👋")
st.caption(date.today().strftime("%A, %d %B %Y"))

client = authed_client()
today = date.today().isoformat()
next_week = (date.today() + timedelta(days=7)).isoformat()

try:
    events = client.table("events").select("*").gte("start_at", f"{today}T00:00:00").lt("start_at", f"{today}T23:59:59").order("start_at").execute().data or []
    deadlines = client.table("deadlines").select("*").eq("is_done", False).gte("due_date", today).lte("due_date", next_week).order("due_date").limit(5).execute().data or []
    tx = client.table("transactions").select("amount,type").gte("occurred_on", date.today().replace(day=1).isoformat()).execute().data or []
    tasks = client.table("tasks").select("*").eq("task_date", today).order("created_at").execute().data or []
except Exception as exc:
    st.error(f"Tidak bisa mengambil data dashboard: {exc}")
    st.stop()

income = sum(float(x["amount"]) for x in tx if x["type"] == "income")
expense = sum(float(x["amount"]) for x in tx if x["type"] == "expense")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Agenda hari ini", len(events))
c2.metric("Tugas hari ini", len([t for t in tasks if not t["is_done"]]))
c3.metric("Deadline ≤ 7 hari", len(deadlines))
c4.metric("Saldo bulan ini", fmt_rupiah(income - expense))

left, right = st.columns([1.35, 1])
with left:
    st.subheader("📅 Today")
    if not events:
        st.info("Belum ada jadwal hari ini.")
    for event in events:
        dt = datetime.fromisoformat(event["start_at"])
        icon = "❤️" if event.get("scope") == "couple" else "•"
        st.write(f"**{dt.strftime('%H:%M')}** {icon} {event['title']}")

    st.subheader("✅ To-do")
    if not tasks:
        st.info("Belum ada to-do untuk hari ini.")
    for task in tasks:
        label = f"~~{task['title']}~~" if task["is_done"] else task["title"]
        st.markdown(f"- {label}")

with right:
    st.subheader("📚 Upcoming deadlines")
    if not deadlines:
        st.success("Tidak ada deadline dalam 7 hari ke depan 🎉")
    for item in deadlines:
        due = date.fromisoformat(item["due_date"])
        days = (due - date.today()).days
        st.write(f"{priority_emoji(item.get('priority'))} **{item['title']}**")
        st.caption(f"{item.get('course') or 'General'} • {days} hari lagi")

    st.subheader("💰 This month")
    st.write(f"Pemasukan: **{fmt_rupiah(income)}**")
    st.write(f"Pengeluaran: **{fmt_rupiah(expense)}**")

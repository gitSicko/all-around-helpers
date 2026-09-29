from datetime import date, datetime, time, timedelta
import pandas as pd
import streamlit as st
from utils import authed_client

st.title("📅 Planner")
client = authed_client()

add_tab, calendar_tab, todo_tab = st.tabs(["Tambah jadwal", "Agenda", "To-do"])

with add_tab:
    with st.form("add_event"):
        title = st.text_input("Judul kegiatan")
        d = st.date_input("Tanggal", value=date.today())
        c1, c2 = st.columns(2)
        start_t = c1.time_input("Mulai", value=time(9, 0))
        end_t = c2.time_input("Selesai", value=time(10, 0))
        category = st.selectbox("Kategori", ["Kuliah", "Belajar", "Organisasi", "Personal", "Kesehatan", "Lainnya"])
        note = st.text_area("Catatan", height=90)
        submitted = st.form_submit_button("Simpan jadwal", use_container_width=True)
    if submitted:
        if not title.strip():
            st.error("Judul kegiatan wajib diisi.")
        else:
            start = datetime.combine(d, start_t)
            end = datetime.combine(d, end_t)
            if end <= start:
                st.error("Waktu selesai harus setelah waktu mulai.")
            else:
                client.table("events").insert({
                    "title": title.strip(), "start_at": start.isoformat(), "end_at": end.isoformat(),
                    "category": category, "notes": note.strip(), "scope": "private"
                }).execute()
                st.success("Jadwal ditambahkan.")
                st.rerun()

with calendar_tab:
    c1, c2 = st.columns(2)
    start_d = c1.date_input("Dari", date.today(), key="planner_from")
    end_d = c2.date_input("Sampai", date.today() + timedelta(days=7), key="planner_to")
    data = client.table("events").select("id,title,start_at,end_at,category,scope").gte("start_at", f"{start_d}T00:00:00").lte("start_at", f"{end_d}T23:59:59").order("start_at").execute().data or []
    if data:
        df = pd.DataFrame(data)
        df["start_at"] = pd.to_datetime(df["start_at"])
        df["end_at"] = pd.to_datetime(df["end_at"])
        df["Date"] = df["start_at"].dt.strftime("%d %b %Y")
        df["Time"] = df["start_at"].dt.strftime("%H:%M") + "–" + df["end_at"].dt.strftime("%H:%M")
        st.dataframe(df[["Date", "Time", "title", "category", "scope"]], use_container_width=True, hide_index=True)
        options = {f"{r['Date']} {r['Time']} — {r['title']}": r["id"] for _, r in df.iterrows()}
        selected = st.selectbox("Hapus agenda", ["—"] + list(options.keys()))
        if selected != "—" and st.button("Hapus agenda terpilih"):
            client.table("events").delete().eq("id", options[selected]).execute()
            st.rerun()
    else:
        st.info("Belum ada agenda pada rentang ini.")

with todo_tab:
    with st.form("todo_add", clear_on_submit=True):
        c1, c2 = st.columns([2, 1])
        task_title = c1.text_input("To-do")
        task_date = c2.date_input("Tanggal", date.today(), key="todo_date")
        add = st.form_submit_button("Tambah")
    if add and task_title.strip():
        client.table("tasks").insert({"title": task_title.strip(), "task_date": task_date.isoformat()}).execute()
        st.rerun()

    todos = client.table("tasks").select("*").gte("task_date", (date.today() - timedelta(days=2)).isoformat()).order("task_date").execute().data or []
    for item in todos:
        c1, c2, c3 = st.columns([0.6, 5, 1])
        new_done = c1.checkbox("", value=item["is_done"], key=f"todo_{item['id']}")
        c2.write(f"{item['task_date']} — {item['title']}")
        if new_done != item["is_done"]:
            client.table("tasks").update({"is_done": new_done}).eq("id", item["id"]).execute()
            st.rerun()
        if c3.button("🗑️", key=f"del_task_{item['id']}"):
            client.table("tasks").delete().eq("id", item["id"]).execute()
            st.rerun()

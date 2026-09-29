from datetime import date
import streamlit as st
from utils import authed_client, priority_emoji

st.title("📚 Assignment & Deadline Tracker")
client = authed_client()

with st.expander("➕ Tambah deadline", expanded=True):
    with st.form("deadline_form"):
        title = st.text_input("Tugas / deadline")
        course = st.text_input("Mata kuliah / kategori")
        c1, c2 = st.columns(2)
        due = c1.date_input("Deadline", date.today())
        priority = c2.selectbox("Prioritas", ["High", "Medium", "Low"])
        progress = st.slider("Progress", 0, 100, 0, step=5)
        notes = st.text_area("Catatan")
        submit = st.form_submit_button("Simpan", use_container_width=True)
    if submit and title.strip():
        client.table("deadlines").insert({
            "title": title.strip(), "course": course.strip(), "due_date": due.isoformat(),
            "priority": priority, "progress": progress, "notes": notes.strip()
        }).execute()
        st.rerun()

status = st.radio("Tampilkan", ["Belum selesai", "Semua"], horizontal=True)
q = client.table("deadlines").select("*").order("due_date")
if status == "Belum selesai":
    q = q.eq("is_done", False)
rows = q.execute().data or []

if not rows:
    st.info("Belum ada deadline.")
for item in rows:
    due = date.fromisoformat(item["due_date"])
    days = (due - date.today()).days
    with st.container(border=True):
        c1, c2 = st.columns([4, 1])
        c1.markdown(f"### {priority_emoji(item['priority'])} {item['title']}")
        c1.caption(f"{item.get('course') or 'General'} • {item['due_date']} • {days} hari")
        new_progress = c1.slider("Progress", 0, 100, int(item["progress"]), 5, key=f"prog_{item['id']}")
        done = c2.checkbox("Selesai", value=item["is_done"], key=f"done_{item['id']}")
        if new_progress != item["progress"] or done != item["is_done"]:
            client.table("deadlines").update({"progress": new_progress, "is_done": done}).eq("id", item["id"]).execute()
            st.rerun()
        if c2.button("Hapus", key=f"del_dead_{item['id']}"):
            client.table("deadlines").delete().eq("id", item["id"]).execute()
            st.rerun()

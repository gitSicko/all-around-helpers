import streamlit as st
from utils import authed_client

st.title("📝 Notes")
client = authed_client()

with st.form("new_note", clear_on_submit=True):
    title = st.text_input("Judul")
    content = st.text_area("Isi catatan", height=160)
    category = st.selectbox("Kategori", ["Personal", "Kuliah", "Wishlist", "Shopping", "Idea", "Lainnya"])
    submit = st.form_submit_button("Simpan catatan", use_container_width=True)
if submit and (title.strip() or content.strip()):
    client.table("notes").insert({"title": title.strip() or "Untitled", "content": content.strip(), "category": category}).execute()
    st.rerun()

rows = client.table("notes").select("*").order("updated_at", desc=True).execute().data or []
if not rows:
    st.info("Belum ada catatan.")
for note in rows:
    with st.expander(f"{note['category']} • {note['title']}"):
        edited = st.text_area("Isi", value=note.get("content") or "", key=f"note_{note['id']}")
        c1, c2 = st.columns(2)
        if c1.button("Simpan perubahan", key=f"save_{note['id']}"):
            client.table("notes").update({"content": edited}).eq("id", note["id"]).execute()
            st.success("Tersimpan.")
        if c2.button("Hapus", key=f"delete_{note['id']}"):
            client.table("notes").delete().eq("id", note["id"]).execute()
            st.rerun()

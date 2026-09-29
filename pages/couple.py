from datetime import date, datetime, time, timedelta
import streamlit as st
from utils import authed_client, get_profile

st.title("❤️ Couple Calendar")
client = authed_client()
profile = get_profile()

if not profile.get("couple_id"):
    st.info("Hubungkan akun kalian dulu. Salah satu membuat kode, yang lain bergabung memakai kode tersebut.")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Buat ruang bersama")
        if st.button("Buat Couple Code", use_container_width=True):
            result = client.rpc("create_couple").execute()
            st.success(f"Kode kalian: **{result.data}**")
            st.info("Kirim kode ini ke pasanganmu. Setelah pasangan bergabung, refresh halaman.")
    with c2:
        st.subheader("Gabung ruang pasangan")
        code = st.text_input("Couple Code").strip().upper()
        if st.button("Gabung", use_container_width=True) and code:
            try:
                client.rpc("join_couple", {"p_code": code}).execute()
                st.success("Berhasil terhubung ❤️")
                st.rerun()
            except Exception as exc:
                st.error(f"Gagal bergabung: {exc}")
    st.stop()

st.success("Akunmu sudah terhubung ke couple space ❤️")
try:
    couple = client.table("couples").select("join_code").eq("id", profile["couple_id"]).single().execute().data
    if couple and couple.get("join_code"):
        st.caption(f"Couple Code: `{couple['join_code']}`")
except Exception:
    pass

add_tab, schedule_tab = st.tabs(["Tambah jadwal bersama", "Jadwal bersama"])
with add_tab:
    with st.form("couple_event"):
        title = st.text_input("Agenda bersama")
        d = st.date_input("Tanggal", date.today())
        c1, c2 = st.columns(2)
        start_t = c1.time_input("Mulai", time(19, 0))
        end_t = c2.time_input("Selesai", time(21, 0))
        notes = st.text_area("Catatan")
        submit = st.form_submit_button("Tambah ❤️", use_container_width=True)
    if submit and title.strip():
        client.table("events").insert({
            "title": title.strip(), "start_at": datetime.combine(d, start_t).isoformat(),
            "end_at": datetime.combine(d, end_t).isoformat(), "category": "Couple",
            "notes": notes.strip(), "scope": "couple", "couple_id": profile["couple_id"]
        }).execute()
        st.success("Agenda bersama ditambahkan.")
        st.rerun()

with schedule_tab:
    start = date.today()
    end = date.today() + timedelta(days=30)
    events = client.table("events").select("*").eq("scope", "couple").gte("start_at", f"{start}T00:00:00").lte("start_at", f"{end}T23:59:59").order("start_at").execute().data or []
    if not events:
        st.info("Belum ada jadwal bersama 30 hari ke depan.")
    for event in events:
        dt = datetime.fromisoformat(event["start_at"])
        st.markdown(f"### ❤️ {event['title']}")
        st.write(dt.strftime("%A, %d %B %Y • %H:%M"))
        if event.get("notes"):
            st.caption(event["notes"])
        st.divider()

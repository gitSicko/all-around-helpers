from datetime import date, datetime, time, timedelta

import streamlit as st
from streamlit_calendar import calendar

from utils import authed_client, get_profile


st.title("❤️ Couple Calendar")
client = authed_client()
profile = get_profile()


def _parse_dt(value: str) -> datetime:
    dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return dt.replace(tzinfo=None)


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
    couple = (
        client.table("couples")
        .select("join_code")
        .eq("id", profile["couple_id"])
        .single()
        .execute()
        .data
    )
    if couple and couple.get("join_code"):
        st.caption(f"Couple Code: `{couple['join_code']}`")
except Exception:
    pass

next_mode = st.session_state.pop("couple_next_mode", None)
if next_mode:
    st.session_state["couple_mode"] = next_mode

mode = st.radio(
    "Couple calendar mode",
    ["Kalender", "Tambah agenda bersama"],
    horizontal=True,
    label_visibility="collapsed",
    key="couple_mode",
)


if mode == "Kalender":
    st.caption("Klik tanggal untuk membuat agenda bersama. Klik agenda untuk melihat, mengedit, atau menghapusnya.")

    rows = (
        client.table("events")
        .select("id,title,start_at,end_at,notes,user_id,category")
        .eq("scope", "couple")
        .eq("couple_id", profile["couple_id"])
        .order("start_at")
        .execute()
        .data
        or []
    )

    by_id = {str(row["id"]): row for row in rows}
    calendar_events = [
        {
            "id": str(row["id"]),
            "title": f"❤️ {row['title']}",
            "start": row["start_at"],
            "end": row["end_at"],
            "extendedProps": {"notes": row.get("notes") or ""},
        }
        for row in rows
    ]

    state = calendar(
        events=calendar_events,
        options={
            "initialView": "dayGridMonth",
            "firstDay": 1,
            "nowIndicator": True,
            "selectable": True,
            "editable": False,
            "height": 650,
            "slotMinTime": "06:00:00",
            "slotMaxTime": "24:00:00",
            "headerToolbar": {
                "left": "prev,next today",
                "center": "title",
                "right": "dayGridMonth,timeGridWeek,timeGridDay,listWeek",
            },
        },
        callbacks=["eventClick", "dateClick"],
        custom_css="""
            .fc .fc-toolbar-title { font-size: 1.25rem; font-weight: 700; }
            .fc .fc-button { border-radius: 8px; }
            .fc-event-title { font-weight: 650; }
            .fc-event { cursor: pointer; }
        """,
        key="couple_calendar_widget",
    )

    if state.get("callback") == "dateClick":
        raw = state.get("dateClick", {}).get("date")
        if raw:
            clicked = _parse_dt(raw)
            st.session_state["couple_prefill_datetime"] = clicked
            st.session_state["couple_next_mode"] = "Tambah agenda bersama"
            st.rerun()

    if state.get("callback") == "eventClick":
        clicked_event = state.get("eventClick", {}).get("event", {})
        if clicked_event.get("id"):
            st.session_state["couple_selected_event"] = str(clicked_event["id"])

    selected_id = st.session_state.get("couple_selected_event")
    selected = by_id.get(str(selected_id)) if selected_id else None

    if selected:
        start_dt = _parse_dt(selected["start_at"])
        end_dt = _parse_dt(selected["end_at"])
        st.divider()
        st.subheader(f"❤️ {selected['title']}")
        st.write(
            f"**{start_dt.strftime('%d %B %Y')}** · "
            f"{start_dt.strftime('%H:%M')}–{end_dt.strftime('%H:%M')}"
        )
        if selected.get("notes"):
            st.caption(selected["notes"])

        with st.expander("✏️ Edit agenda bersama"):
            with st.form(f"edit_couple_event_{selected_id}"):
                edit_title = st.text_input("Agenda bersama", value=selected["title"])
                edit_date = st.date_input("Tanggal", value=start_dt.date())
                c1, c2 = st.columns(2)
                edit_start = c1.time_input("Mulai", value=start_dt.time().replace(second=0, microsecond=0))
                edit_end = c2.time_input("Selesai", value=end_dt.time().replace(second=0, microsecond=0))
                edit_notes = st.text_area("Catatan", value=selected.get("notes") or "")
                save = st.form_submit_button("Simpan perubahan", use_container_width=True)

            if save:
                new_start = datetime.combine(edit_date, edit_start)
                new_end = datetime.combine(edit_date, edit_end)
                if not edit_title.strip():
                    st.error("Judul agenda wajib diisi.")
                elif new_end <= new_start:
                    st.error("Waktu selesai harus setelah waktu mulai.")
                else:
                    client.table("events").update(
                        {
                            "title": edit_title.strip(),
                            "start_at": new_start.isoformat(),
                            "end_at": new_end.isoformat(),
                            "notes": edit_notes.strip(),
                        }
                    ).eq("id", selected_id).execute()
                    st.success("Agenda bersama diperbarui.")
                    st.rerun()

        if st.button("🗑️ Hapus agenda bersama", key=f"delete_couple_{selected_id}"):
            client.table("events").delete().eq("id", selected_id).execute()
            st.session_state.pop("couple_selected_event", None)
            st.rerun()

    elif not rows:
        st.info("Belum ada agenda bersama. Klik salah satu tanggal untuk membuat agenda pertama ❤️")


else:
    prefill = st.session_state.get("couple_prefill_datetime")
    default_date = prefill.date() if isinstance(prefill, datetime) else date.today()
    default_start = (
        prefill.time().replace(second=0, microsecond=0)
        if isinstance(prefill, datetime) and prefill.time() != time(0, 0)
        else time(19, 0)
    )
    default_end = (
        datetime.combine(default_date, default_start) + timedelta(hours=2)
    ).time().replace(second=0, microsecond=0)

    with st.form("couple_event", clear_on_submit=True):
        title = st.text_input("Agenda bersama")
        d = st.date_input("Tanggal", default_date)
        c1, c2 = st.columns(2)
        start_t = c1.time_input("Mulai", default_start)
        end_t = c2.time_input("Selesai", default_end)
        notes = st.text_area("Catatan")
        submit = st.form_submit_button("Tambah ❤️", use_container_width=True)

    if submit:
        start_dt = datetime.combine(d, start_t)
        end_dt = datetime.combine(d, end_t)
        if not title.strip():
            st.error("Judul agenda wajib diisi.")
        elif end_dt <= start_dt:
            st.error("Waktu selesai harus setelah waktu mulai.")
        else:
            client.table("events").insert(
                {
                    "title": title.strip(),
                    "start_at": start_dt.isoformat(),
                    "end_at": end_dt.isoformat(),
                    "category": "Couple",
                    "notes": notes.strip(),
                    "scope": "couple",
                    "couple_id": profile["couple_id"],
                }
            ).execute()
            st.session_state.pop("couple_prefill_datetime", None)
            st.success("Agenda bersama ditambahkan.")
            st.session_state["couple_mode"] = "Kalender"
            st.rerun()

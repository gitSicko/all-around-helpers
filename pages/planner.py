from datetime import date, datetime, time, timedelta

import streamlit as st
from streamlit_calendar import calendar

from utils import authed_client, get_profile


st.title("📅 Planner")
client = authed_client()

CATEGORIES = ["Kuliah", "Belajar", "Organisasi", "Personal", "Kesehatan", "Lainnya"]


def _parse_dt(value: str) -> datetime:
    """Parse ISO datetime from Supabase / FullCalendar without changing wall-clock time."""
    dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return dt.replace(tzinfo=None)


# dateClick is handled on the next rerun so we do not modify a widget key
# after the radio widget has already been instantiated.
next_mode = st.session_state.pop("planner_next_mode", None)
if next_mode:
    st.session_state["planner_mode"] = next_mode

mode = st.radio(
    "Planner mode",
    ["Kalender", "Tambah jadwal", "Jadwal kuliah", "To-do"],
    horizontal=True,
    label_visibility="collapsed",
    key="planner_mode",
)


if mode == "Kalender":
    st.caption("Klik tanggal untuk menambah agenda. Klik agenda untuk melihat, mengedit, atau menghapusnya.")

    rows = (
        client.table("events")
        .select("id,title,start_at,end_at,category,notes,scope,couple_id,user_id")
        .order("start_at")
        .execute()
        .data
        or []
    )

    calendar_events = []
    by_id = {}
    for row in rows:
        event_id = str(row["id"])
        by_id[event_id] = row
        prefix = "❤️ " if row.get("scope") == "couple" else ""
        calendar_events.append(
            {
                "id": event_id,
                "title": f"{prefix}{row['title']}",
                "start": row["start_at"],
                "end": row["end_at"],
                "extendedProps": {
                    "category": row.get("category") or "",
                    "notes": row.get("notes") or "",
                    "scope": row.get("scope") or "private",
                },
            }
        )

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
        key="planner_calendar",
    )

    if state.get("callback") == "dateClick":
        raw = state.get("dateClick", {}).get("date")
        if raw:
            clicked = _parse_dt(raw)
            st.session_state["planner_prefill_datetime"] = clicked
            st.session_state["planner_next_mode"] = "Tambah jadwal"
            st.rerun()

    if state.get("callback") == "eventClick":
        clicked_event = state.get("eventClick", {}).get("event", {})
        if clicked_event.get("id"):
            st.session_state["planner_selected_event"] = str(clicked_event["id"])

    selected_id = st.session_state.get("planner_selected_event")
    selected = by_id.get(str(selected_id)) if selected_id else None

    if selected:
        start_dt = _parse_dt(selected["start_at"])
        end_dt = _parse_dt(selected["end_at"])

        st.divider()
        scope_label = "❤️ Bersama" if selected.get("scope") == "couple" else "🔒 Pribadi"
        st.subheader(selected["title"])
        st.write(
            f"**{start_dt.strftime('%d %B %Y')}** · "
            f"{start_dt.strftime('%H:%M')}–{end_dt.strftime('%H:%M')} · "
            f"{selected.get('category') or 'Tanpa kategori'} · {scope_label}"
        )
        if selected.get("notes"):
            st.caption(selected["notes"])

        with st.expander("✏️ Edit agenda"):
            category_options = list(CATEGORIES)
            current_category = selected.get("category") or "Lainnya"
            if current_category not in category_options:
                category_options.append(current_category)

            with st.form(f"edit_event_{selected_id}"):
                edit_title = st.text_input("Judul", value=selected["title"])
                edit_date = st.date_input("Tanggal", value=start_dt.date())
                c1, c2 = st.columns(2)
                edit_start = c1.time_input("Mulai", value=start_dt.time().replace(second=0, microsecond=0))
                edit_end = c2.time_input("Selesai", value=end_dt.time().replace(second=0, microsecond=0))
                edit_category = st.selectbox(
                    "Kategori",
                    category_options,
                    index=category_options.index(current_category),
                )
                edit_notes = st.text_area("Catatan", value=selected.get("notes") or "", height=90)
                save_edit = st.form_submit_button("Simpan perubahan", use_container_width=True)

            if save_edit:
                new_start = datetime.combine(edit_date, edit_start)
                new_end = datetime.combine(edit_date, edit_end)
                if not edit_title.strip():
                    st.error("Judul kegiatan wajib diisi.")
                elif new_end <= new_start:
                    st.error("Waktu selesai harus setelah waktu mulai.")
                else:
                    client.table("events").update(
                        {
                            "title": edit_title.strip(),
                            "start_at": new_start.isoformat(),
                            "end_at": new_end.isoformat(),
                            "category": edit_category,
                            "notes": edit_notes.strip(),
                        }
                    ).eq("id", selected_id).execute()
                    st.success("Agenda diperbarui.")
                    st.rerun()

        if st.button("🗑️ Hapus agenda ini", key=f"delete_event_{selected_id}"):
            client.table("events").delete().eq("id", selected_id).execute()
            st.session_state.pop("planner_selected_event", None)
            st.rerun()

    elif not rows:
        st.info("Kalender masih kosong. Klik salah satu tanggal untuk membuat agenda pertama.")


elif mode == "Tambah jadwal":
    prefill = st.session_state.get("planner_prefill_datetime")
    default_date = prefill.date() if isinstance(prefill, datetime) else date.today()
    default_start = (
        prefill.time().replace(second=0, microsecond=0)
        if isinstance(prefill, datetime) and prefill.time() != time(0, 0)
        else time(9, 0)
    )
    default_end_dt = datetime.combine(default_date, default_start) + timedelta(hours=1)
    default_end = default_end_dt.time().replace(second=0, microsecond=0)

    with st.form("add_event", clear_on_submit=True):
        title = st.text_input("Judul kegiatan")
        d = st.date_input("Tanggal", value=default_date)
        c1, c2 = st.columns(2)
        start_t = c1.time_input("Mulai", value=default_start)
        end_t = c2.time_input("Selesai", value=default_end)
        category = st.selectbox("Kategori", CATEGORIES)
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
                client.table("events").insert(
                    {
                        "title": title.strip(),
                        "start_at": start.isoformat(),
                        "end_at": end.isoformat(),
                        "category": category,
                        "notes": note.strip(),
                        "scope": "private",
                    }
                ).execute()
                st.session_state.pop("planner_prefill_datetime", None)
                st.success("Jadwal ditambahkan.")
                st.session_state["planner_mode"] = "Kalender"
                st.rerun()


elif mode == "Jadwal kuliah":
    st.subheader("🎓 Jadwal kuliah mingguan")
    st.caption(
        "Masukkan satu kali jadwal, lalu semua pertemuan mingguan sampai akhir periode akan otomatis muncul di kalender. "
        "Kalau ada libur atau kelas ditiadakan, pertemuan pada tanggal itu bisa dihapus satu-satu dari Kalender."
    )

    DAY_NAMES = [
        "Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"
    ]

    today = date.today()
    default_until = today + timedelta(days=120)

    with st.form("weekly_class_form", clear_on_submit=False):
        course_name = st.text_input("Mata kuliah", placeholder="Contoh: Analisis Log Sumur")
        first_date = st.date_input(
            "Pertemuan pertama",
            value=today,
            help="Hari pada tanggal ini akan menjadi hari kuliah setiap minggu.",
        )
        until_date = st.date_input(
            "Ulangi sampai",
            value=default_until,
            help="Biasanya isi dengan tanggal akhir semester/perkuliahan.",
        )

        c1, c2 = st.columns(2)
        start_t = c1.time_input("Jam mulai", value=time(8, 0), key="class_start")
        end_t = c2.time_input("Jam selesai", value=time(10, 0), key="class_end")

        c3, c4 = st.columns(2)
        room = c3.text_input("Ruangan / lokasi", placeholder="Contoh: Lab 3")
        lecturer = c4.text_input("Dosen (opsional)", placeholder="Nama dosen")

        extra_note = st.text_area("Catatan tambahan", placeholder="Contoh: bawa laptop / modul")

        share_with_partner = False
        try:
            profile = get_profile()
            if profile.get("couple_id"):
                share_with_partner = st.checkbox(
                    "❤️ Tampilkan juga di Couple Calendar",
                    value=False,
                    help="Pasanganmu akan bisa melihat jadwal kuliah ini di kalender bersama.",
                )
        except Exception:
            profile = {}

        add_weekly = st.form_submit_button("Tambahkan jadwal setiap minggu", use_container_width=True)

    weekday_name = DAY_NAMES[first_date.weekday()]
    if until_date >= first_date:
        total_meetings = ((until_date - first_date).days // 7) + 1
        st.info(
            f"📌 Jadwal akan dibuat setiap **{weekday_name}**, "
            f"sebanyak **{total_meetings} pertemuan** dari "
            f"**{first_date.strftime('%d/%m/%Y')}** sampai **{until_date.strftime('%d/%m/%Y')}**."
        )

    if add_weekly:
        if not course_name.strip():
            st.error("Nama mata kuliah wajib diisi.")
        elif until_date < first_date:
            st.error("Tanggal akhir harus sama dengan atau setelah pertemuan pertama.")
        elif end_t <= start_t:
            st.error("Jam selesai harus setelah jam mulai.")
        else:
            dates = []
            current = first_date
            while current <= until_date:
                dates.append(current)
                current += timedelta(days=7)

            if len(dates) > 60:
                st.error("Periode terlalu panjang. Maksimal 60 pertemuan untuk satu jadwal kuliah.")
            else:
                note_parts = []
                if room.strip():
                    note_parts.append(f"Lokasi: {room.strip()}")
                if lecturer.strip():
                    note_parts.append(f"Dosen: {lecturer.strip()}")
                if extra_note.strip():
                    note_parts.append(extra_note.strip())
                note_text = " · ".join(note_parts)

                scope = "couple" if share_with_partner else "private"
                couple_id = profile.get("couple_id") if share_with_partner else None

                payload = []
                for meeting_date in dates:
                    start_dt = datetime.combine(meeting_date, start_t)
                    end_dt = datetime.combine(meeting_date, end_t)
                    row = {
                        "title": course_name.strip(),
                        "start_at": start_dt.isoformat(),
                        "end_at": end_dt.isoformat(),
                        "category": "Kuliah",
                        "notes": note_text,
                        "scope": scope,
                    }
                    if couple_id:
                        row["couple_id"] = couple_id
                    payload.append(row)

                client.table("events").insert(payload).execute()
                st.success(
                    f"Berhasil menambahkan {len(payload)} pertemuan {course_name.strip()} setiap {weekday_name} 🎓"
                )
                st.session_state["planner_mode"] = "Kalender"
                st.rerun()


else:  # To-do
    with st.form("todo_add", clear_on_submit=True):
        c1, c2 = st.columns([2, 1])
        task_title = c1.text_input("To-do")
        task_date = c2.date_input("Tanggal", date.today(), key="todo_date")
        add = st.form_submit_button("Tambah")

    if add and task_title.strip():
        client.table("tasks").insert(
            {"title": task_title.strip(), "task_date": task_date.isoformat()}
        ).execute()
        st.rerun()

    todos = (
        client.table("tasks")
        .select("*")
        .gte("task_date", (date.today() - timedelta(days=2)).isoformat())
        .order("task_date")
        .execute()
        .data
        or []
    )

    if not todos:
        st.info("Belum ada to-do.")

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

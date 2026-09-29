from __future__ import annotations

from datetime import date, datetime
from typing import Any
import streamlit as st
from supabase import create_client, Client


def _secrets_ready() -> bool:
    return "SUPABASE_URL" in st.secrets and "SUPABASE_KEY" in st.secrets


def public_client() -> Client:
    if not _secrets_ready():
        raise RuntimeError("Supabase secrets belum diisi.")
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])


def authed_client() -> Client:
    client = public_client()
    access = st.session_state.get("access_token")
    refresh = st.session_state.get("refresh_token")
    if access and refresh:
        client.auth.set_session(access, refresh)
    return client


def sign_in(email: str, password: str):
    client = public_client()
    result = client.auth.sign_in_with_password({"email": email, "password": password})
    if result.session:
        st.session_state.access_token = result.session.access_token
        st.session_state.refresh_token = result.session.refresh_token
        st.session_state.user_id = result.user.id
        st.session_state.user_email = result.user.email
    return result


def sign_up(email: str, password: str, display_name: str):
    client = public_client()
    result = client.auth.sign_up(
        {
            "email": email,
            "password": password,
            "options": {"data": {"display_name": display_name}},
        }
    )
    return result


def sign_out():
    try:
        authed_client().auth.sign_out()
    except Exception:
        pass
    for key in ["access_token", "refresh_token", "user_id", "user_email"]:
        st.session_state.pop(key, None)


def is_logged_in() -> bool:
    return bool(st.session_state.get("access_token"))


def require_login():
    if not is_logged_in():
        st.warning("Silakan login terlebih dahulu.")
        st.stop()


def get_profile() -> dict[str, Any]:
    require_login()
    uid = st.session_state["user_id"]
    response = authed_client().table("profiles").select("*").eq("id", uid).single().execute()
    return response.data or {}


def display_name() -> str:
    try:
        profile = get_profile()
        return profile.get("display_name") or st.session_state.get("user_email", "Kamu")
    except Exception:
        return st.session_state.get("user_email", "Kamu")


def fmt_rupiah(value: float | int | None) -> str:
    value = float(value or 0)
    return "Rp {:,.0f}".format(value).replace(",", ".")


def today_iso() -> str:
    return date.today().isoformat()


def parse_date(value: str | date | None) -> date | None:
    if value is None:
        return None
    if isinstance(value, date):
        return value
    return datetime.fromisoformat(str(value)).date()


def priority_emoji(priority: str | None) -> str:
    return {"High": "🔴", "Medium": "🟡", "Low": "🟢"}.get(priority or "", "⚪")


def safe_execute(fn, success_message: str | None = None):
    try:
        result = fn()
        if success_message:
            st.success(success_message)
        return result
    except Exception as exc:
        st.error(f"Terjadi error: {exc}")
        return None

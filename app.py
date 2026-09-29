import streamlit as st
from utils import is_logged_in, sign_in, sign_up, sign_out, display_name

st.set_page_config(page_title="All Around Helper", page_icon="✨", layout="wide")

st.markdown("""
<style>
.block-container {padding-top: 1.5rem; padding-bottom: 3rem; max-width: 1200px;}
[data-testid="stMetric"] {border: 1px solid rgba(128,128,128,.2); padding: 14px; border-radius: 16px;}
.hero {padding: 18px 22px; border-radius: 20px; background: rgba(127,127,127,.08); margin-bottom: 14px;}
.small-muted {opacity: .7; font-size: .9rem;}
</style>
""", unsafe_allow_html=True)


def login_page():
    st.title("✨ All Around Helper")
    st.caption("Planner, couple calendar, finance, deadline, dan notes dalam satu tempat.")

    if "SUPABASE_URL" not in st.secrets or "SUPABASE_KEY" not in st.secrets:
        st.error("Supabase belum dikonfigurasi. Ikuti README.md dan isi `.streamlit/secrets.toml`.")
        st.stop()

    tab_login, tab_signup = st.tabs(["Login", "Buat akun"])

    with tab_login:
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Masuk", use_container_width=True)
        if submitted:
            try:
                sign_in(email.strip(), password)
                st.rerun()
            except Exception as exc:
                st.error(f"Login gagal: {exc}")

    with tab_signup:
        with st.form("signup_form"):
            name = st.text_input("Nama panggilan")
            email = st.text_input("Email", key="signup_email")
            password = st.text_input("Password", type="password", key="signup_password")
            submitted = st.form_submit_button("Daftar", use_container_width=True)
        if submitted:
            if len(password) < 6:
                st.error("Password minimal 6 karakter.")
            else:
                try:
                    result = sign_up(email.strip(), password, name.strip() or "User")
                    if result.session:
                        st.session_state.access_token = result.session.access_token
                        st.session_state.refresh_token = result.session.refresh_token
                        st.session_state.user_id = result.user.id
                        st.session_state.user_email = result.user.email
                        st.rerun()
                    st.success("Akun dibuat. Cek email untuk verifikasi jika verifikasi email aktif di Supabase.")
                except Exception as exc:
                    st.error(f"Pendaftaran gagal: {exc}")


def logout_page():
    st.title("Account")
    st.write(f"Login sebagai **{display_name()}**")
    if st.button("Keluar", type="primary"):
        sign_out()
        st.rerun()


if not is_logged_in():
    login_page()
else:
    pages = {
        "My Life": [
            st.Page("pages/home.py", title="Home", icon="🏠", default=True),
            st.Page("pages/planner.py", title="Planner", icon="📅"),
            st.Page("pages/deadlines.py", title="Deadlines", icon="📚"),
            st.Page("pages/finance.py", title="Finance", icon="💰"),
            st.Page("pages/notes.py", title="Notes", icon="📝"),
        ],
        "Us": [st.Page("pages/couple.py", title="Couple Calendar", icon="❤️")],
        "Settings": [st.Page(logout_page, title="Account", icon="⚙️")],
    }
    pg = st.navigation(pages)
    pg.run()

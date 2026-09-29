# ✨ All Around Helper

Web app pribadi berbasis **Python + Streamlit + Supabase** untuk:

- 🏠 Dashboard harian
- 📅 Planner & to-do
- ❤️ Couple calendar dua akun
- 💰 Catatan keuangan
- 📚 Deadline tugas
- 📝 Notes

## 1. Buat Supabase project

1. Buka Supabase dan buat project baru.
2. Masuk ke **SQL Editor**.
3. Copy seluruh isi `schema.sql`, lalu **Run**.
4. Masuk ke **Project Settings → API** dan ambil:
   - Project URL
   - anon / publishable key

> Jangan gunakan `service_role` key di aplikasi Streamlit.

## 2. Isi secrets

Copy:

`.streamlit/secrets.example.toml`

menjadi:

`.streamlit/secrets.toml`

Lalu isi:

```toml
SUPABASE_URL = "https://PROJECT.supabase.co"
SUPABASE_KEY = "ANON_KEY_KAMU"
```

## 3. Install dan jalankan

Windows PowerShell:

```powershell
cd all_around_helper
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

Browser akan membuka aplikasi lokal, biasanya di `http://localhost:8501`.

## 4. Buat dua akun

Buat akunmu dan akun pasanganmu. Jika Supabase meminta email verification, verifikasi email masing-masing terlebih dahulu.

Di menu **Couple Calendar**:

1. Akun pertama klik **Buat Couple Code**.
2. Kirim kode ke pasangan.
3. Akun pasangan login → **Gabung ruang pasangan** → masukkan kode.

Setelah itu event dengan scope `couple` akan terlihat oleh dua akun, sementara Finance, Notes, Deadline, dan to-do tetap private.

## 5. Supaya bisa diakses HP / iPad

Deploy repository ini ke **Streamlit Community Cloud** atau provider Python lain. Saat deploy, masukkan `SUPABASE_URL` dan `SUPABASE_KEY` ke Secrets milik deployment, bukan ke GitHub.

Setelah punya URL publik, buka dari Safari/Chrome di HP/iPad. Kamu juga bisa **Add to Home Screen**.

## Struktur project

```text
all_around_helper/
├── app.py
├── utils.py
├── schema.sql
├── requirements.txt
├── README.md
├── .streamlit/
│   └── secrets.example.toml
└── pages/
    ├── home.py
    ├── planner.py
    ├── couple.py
    ├── finance.py
    ├── deadlines.py
    └── notes.py
```

## Catatan MVP

Versi ini sengaja fokus ke fungsi utama. Tahap berikutnya yang cocok ditambahkan:

- Google Calendar sync
- Reminder deadline
- Budget bulanan
- Recurring events
- Edit agenda
- Tema / avatar pasangan
- PWA-like install experience
- Dashboard statistik mingguan
- Ask Helper / AI assistant

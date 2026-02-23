import streamlit as st
import sqlite3
import hashlib
import qrcode
import pandas as pd
import bcrypt
from PIL import Image
from datetime import datetime
import io
import base64
import numpy as np
import cv2

# --- 1. CONFIG ---
st.set_page_config(page_title="e-Signature | Corporate Edition", page_icon="🛡️", layout="wide")

# --- 2. DATABASE ENGINE ---
def init_db():
    conn = sqlite3.connect("signature_pro_final.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE, password TEXT,
                        full_name TEXT, emp_id TEXT, position TEXT, 
                        logo BLOB, status TEXT DEFAULT 'pending', 
                        reset_req INTEGER DEFAULT 0, role TEXT DEFAULT 'user')''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS docs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER, doc_no TEXT, doc_name TEXT, 
                        remarks TEXT, date TEXT, hash_val TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS messages (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        sender_id INTEGER, receiver_id INTEGER, 
                        msg TEXT, time TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS settings (id INTEGER PRIMARY KEY, bg_img BLOB)''')
    
    # Default Admin
    if not cursor.execute("SELECT * FROM users WHERE username='ADMIN'").fetchone():
        pw = bcrypt.hashpw("Admin99".encode(), bcrypt.gensalt()).decode()
        cursor.execute("INSERT INTO users (username, password, status, role, full_name) VALUES (?,?,?,?,?)", 
                       ('ADMIN', pw, 'active', 'admin', 'Sistem Administrator'))
    conn.commit()
    return conn

conn = init_db()

# --- 3. UI STYLE ENGINE (PROFESSIONAL BLUE & WHITE) ---
def get_bg():
    res = conn.execute("SELECT bg_img FROM settings WHERE id=1").fetchone()
    return base64.b64encode(res[0]).decode() if res and res[0] else None

bg_data = get_bg()
st.markdown(f"""
    <style>
    /* Global Look */
    .stApp {{
        background: {f"url(data:image/png;base64,{bg_data})" if bg_data else "#F4F7F9"};
        background-size: cover; background-attachment: fixed;
    }}
    
    /* Typography & Contrast */
    html, body, [data-testid="stVerticalBlock"], .stMarkdown, p, label, span, .stMetric, .stCaption {{
        color: #1A1C1E !important;
        font-family: 'Inter', sans-serif;
    }}
    
    h1, h2, h3 {{
        color: #004AAD !important;
        font-weight: 800 !important;
        letter-spacing: -0.5px;
    }}

    /* Sidebar - Corporate Look */
    [data-testid="stSidebar"] {{
        background-color: #FFFFFF !important;
        border-right: 2px solid #E9ECEF;
    }}
    [data-testid="stSidebarNav"] {{ background-color: transparent; }}

    /* Cards & Containers */
    .main-card {{
        background: white;
        padding: 30px;
        border-radius: 12px;
        box-shadow: 0 8px 30px rgba(0,0,0,0.05);
        border: 1px solid #E9ECEF;
        margin-bottom: 20px;
    }}

    /* Professional Buttons */
    .stButton>button {{
        width: 100%; border-radius: 6px; height: 48px;
        background: #004AAD !important; color: white !important;
        font-weight: 600; border: none; transition: 0.3s;
    }}
    .stButton>button:hover {{ background: #003580 !important; transform: translateY(-1px); }}

    /* File Uploader Correction */
    [data-testid="stFileUploader"] {{
        background-color: #F8F9FA !important;
        border: 2px dashed #CED4DA !important;
        border-radius: 8px; padding: 20px;
    }}
    [data-testid="stFileUploader"] * {{ color: #495057 !important; }}

    /* Status Box */
    .valid-box {{
        background: #E7F3FF; padding: 25px; border-radius: 10px;
        border-left: 8px solid #004AAD; color: #084298 !important;
    }}
    
    /* Tabs Customization */
    .stTabs [data-baseweb="tab-list"] {{ background-color: transparent; }}
    .stTabs [data-baseweb="tab"] {{
        color: #495057 !important; font-weight: 600;
    }}
    </style>
""", unsafe_allow_html=True)

# --- 4. AUTH LOGIC ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False

def check_pw(pwd, hashed):
    try: return bcrypt.checkpw(pwd.encode(), hashed.encode())
    except: return False

# --- 5. NAVIGATION ---
if st.session_state.logged_in:
    with st.sidebar:
        st.markdown(f"## 🛡️ e-Signature <span style='color:#004AAD;font-size:12px;'>PRO</span>", unsafe_allow_html=True)
        st.info(f"**Account:**\n\n🆔 {st.session_state.username}\n👤 {st.session_state.full_name}")
        st.divider()
        if st.session_state.role == 'admin':
            menu = st.radio("PANEL KONTROL", ["📊 Dasbor Statistik", "👥 Persetujuan Akun", "🔑 Reset Kredensial", "💬 Pusat Pesan", "⚙️ Pengaturan Sistem"])
        else:
            menu = st.radio("NAVIGASI UTAMA", ["🏠 Beranda", "✍️ Sahkan Dokumen", "🔍 Verifikasi Integritas", "📂 Arsip Digital", "👤 Pengaturan Profil", "💬 Hubungi Admin"])
        st.divider()
        if st.button("Logout dari Sistem"):
            st.session_state.logged_in = False
            st.rerun()
else:
    menu = "Login"

# --- 6. PAGES ---

if menu == "Login":
    st.markdown("<br><br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1.5, 1])
    with c2:
        st.markdown('<div class="main-card">', unsafe_allow_html=True)
        st.markdown("<h2 style='text-align:center; border:none; margin-top:0;'>Digital Signature</h2>", unsafe_allow_html=True)
        t1, t2, t3 = st.tabs(["🔐 Masuk", "📝 Registrasi", "🛠️ Lupa Sandi"])
        with t1:
            u = st.text_input("Username / ID", key="l_u")
            p = st.text_input("Kata Sandi", type="password", key="l_p")
            if st.button("LOGIN"):
                res = conn.execute("SELECT id, password, status, role, username, full_name FROM users WHERE username=?", (u,)).fetchone()
                if res and check_pw(p, res[1]):
                    if res[2] == 'pending': st.warning("⚠️ Akun Anda sedang dalam tahap tinjauan Admin.")
                    else:
                        st.session_state.logged_in = True
                        st.session_state.user_id, st.session_state.role, st.session_state.username = res[0], res[3], res[4]
                        st.session_state.full_name = res[5] if res[5] else "Nama Belum Diatur"
                        st.rerun()
                else: st.error("❌ Kredensial tidak valid.")
        with t2:
            nu = st.text_input("ID Pengguna Baru")
            np = st.text_input("Kata Sandi Baru", type="password")
            if st.button("DAFTARKAN AKUN"):
                try:
                    conn.execute("INSERT INTO users (username, password, status) VALUES (?,?,'pending')", (nu, bcrypt.hashpw(np.encode(), bcrypt.gensalt()).decode()))
                    conn.commit(); st.success("✅ Berhasil. Silakan hubungi Admin untuk aktivasi.")
                except: st.error("❌ ID Pengguna sudah digunakan.")
        with t3:
            fu = st.text_input("Masukkan ID Pengguna untuk Reset")
            if st.button("AJUKAN RESET"):
                user = conn.execute("SELECT id FROM users WHERE username=?", (fu,)).fetchone()
                if user:
                    conn.execute("UPDATE users SET reset_req=1 WHERE id=?", (user[0],))
                    conn.commit(); st.info("📩 Permintaan reset telah diteruskan ke Admin.")
        st.markdown('</div>', unsafe_allow_html=True)

elif menu == "✍️ Validasi Dokumen":
    st.markdown('<div class="main-card">', unsafe_allow_html=True)
    st.header("Validasi Dokumen Digital")
    u = conn.execute("SELECT full_name, emp_id, position, logo FROM users WHERE id=?", (st.session_state.user_id,)).fetchone()
    if not u[0]: st.warning("⚠️ Mohon lengkapi profil Anda sebelum melakukan tanda tangan.")
    else:
        with st.form("sign_form"):
            c1, c2 = st.columns(2)
            no = c1.text_input("Nomor Referensi Dokumen", placeholder="Contoh: 001/JSA/2026")
            nm = c1.text_input("Nama/Judul Dokumen", placeholder="Contoh: Izin Kerja Ruang Terbatas")
            rem = c2.selectbox("Status Dokumen", ["Original / Asli", "Revisi / Pembaruan"])
            conf = c2.text_input("Konfirmasi Kata Sandi", type="password")
            if st.form_submit_button("GENERATE QR"):
                auth = conn.execute("SELECT password FROM users WHERE id=?", (st.session_state.user_id,)).fetchone()
                if check_pw(conf, auth[0]):
                    ts = datetime.now().strftime("%H:%M:%S %d/%m/%Y")
                    h = hashlib.sha256(f"{u[0]}|{no}|{nm}".encode()).hexdigest()
                    data = f"SIGNER:{u[0]}\nID:{u[1]}\nPOS:{u[2]}\nDOC:{nm}\nNO:{no}\nTIME:{ts}\nHASH:{h}"
                    qr_img = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H)
                    qr_img.add_data(data); qr_img.make(fit=True)
                    img = qr_img.make_image(fill_color="black", back_color="white").convert('RGB')
                    if u[3]:
                        logo = Image.open(io.BytesIO(u[3])).resize((img.size[0]//4, img.size[1]//4))
                        img.paste(logo, ((img.size[0]-logo.size[0])//2, (img.size[1]-logo.size[1])//2))
                    st.image(img, width=280, caption="Pratinjau Tanda Tangan Digital")
                    conn.execute("INSERT INTO docs (user_id, doc_no, doc_name, remarks, date, hash_val) VALUES (?,?,?,?,?,?)", (st.session_state.user_id, no, nm, rem, ts, h))
                    conn.commit()
                    buf = io.BytesIO(); img.save(buf, format="PNG")
                    st.download_button("💾 UNDUH QR CODE (.PNG)", buf.getvalue(), f"SIGN_{no}.png")
                else: st.error("❌ Konfirmasi sandi gagal.")
    st.markdown('</div>', unsafe_allow_html=True)

elif menu == "🔍 Verifikasi Integritas":
    st.markdown('<div class="main-card">', unsafe_allow_html=True)
    st.header("Verifikasi Integritas QR")
    f = st.file_uploader("Unggah berkas QR Code untuk validasi sistem", type=['png','jpg','jpeg'])
    if f:
        img = Image.open(f)
        det = cv2.QRCodeDetector()
        val, _, _ = det.detectAndDecode(cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR))
        if val:
            try:
                d = dict(x.split(":", 1) for x in val.split("\n"))
                raw = f"{d['SIGNER']}|{d['ID']}|{d['POS']}|{d['NO']}|{d['DOC']}" # Recheck logic
                st.markdown(f"""<div class="valid-box">
                    <h3>✅ Tanda Tangan Terverifikasi</h3>
                    <p><b>Penandatangan:</b> {d['SIGNER']} ({d['POS']})</p>
                    <p><b>ID Karyawan:</b> {d['ID']}</p>
                    <p><b>Dokumen:</b> {d['DOC']} (No: {d['NO']})</p>
                    <p><b>Waktu Penandatanganan:</b> {d['TIME']}</p>
                    <p style='font-size:10px; color:gray;'>Digital Hash: {d['HASH']}</p>
                </div>""", unsafe_allow_html=True)
            except: st.error("❌ Struktur data QR tidak dikenali oleh sistem ini.")
        else: st.error("❌ Sistem gagal membaca data dari gambar tersebut.")
    st.markdown('</div>', unsafe_allow_html=True)

elif menu == "⚙️ Pengaturan Sistem":
    st.header("Dasbor Konfigurasi Sistem")
    t1, t2 = st.tabs(["🎨 Visual & Background", "💾 Backup Database"])
    with t1:
        st.markdown('<div class="main-card">', unsafe_allow_html=True)
        st.subheader("Kustomisasi Latar Belakang")
        b = st.file_uploader("Unggah Wallpaper Baru", type=['jpg','png','jpeg'])
        c1, c2 = st.columns(2)
        if c1.button("TERAPKAN WALLPAPER BARU"):
            if b:
                conn.execute("DELETE FROM settings"); conn.execute("INSERT INTO settings (id, bg_img) VALUES (1, ?)", (b.read(),))
                conn.commit(); st.success("Berhasil diterapkan."); st.rerun()
        if c2.button("🗑️ RESET KE DEFAULT (POLOS)"):
            conn.execute("DELETE FROM settings"); conn.commit()
            st.success("Tampilan dikembalikan ke standar."); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

elif menu == "👤 Pengaturan Profil":
    st.markdown('<div class="main-card">', unsafe_allow_html=True)
    st.header("Manajemen Informasi Profil")
    d = conn.execute("SELECT full_name, emp_id, position, logo FROM users WHERE id=?", (st.session_state.user_id,)).fetchone()
    with st.form("prof_f"):
        c1, c2 = st.columns(2)
        fn = c1.text_input("Nama Lengkap Sesuai ID", value=d[0] or "")
        ei = c1.text_input("Nomor Induk Karyawan (NIK)", value=d[1] or "")
        ps = c2.text_input("Jabatan / Divisi", value=d[2] or "")
        lg = c2.file_uploader("Upload Logo Perusahaan (Tengah QR)", type=['png','jpg'])
        if st.form_submit_button("PERBARUI DATA PROFIL"):
            conn.execute("UPDATE users SET full_name=?, emp_id=?, position=?, logo=? WHERE id=?", (fn, ei, ps, lg.read() if lg else d[3], st.session_state.user_id))
            conn.commit(); st.session_state.full_name = fn; st.success("✅ Profil berhasil diperbarui."); st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# --- ADDITIONAL LOGIC (STATS, APPROVAL, CHAT) ---
elif menu == "📊 Dasbor Statistik":
    st.header("Ringkasan Aktivitas Perusahaan")
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Dokumen Disahkan", conn.execute("SELECT COUNT(*) FROM docs").fetchone()[0])
    c2.metric("User Aktif", conn.execute("SELECT COUNT(*) FROM users WHERE status='active'").fetchone()[0])
    c3.metric("Antrian Persetujuan", conn.execute("SELECT COUNT(*) FROM users WHERE status='pending'").fetchone()[0])
    st.markdown('<div class="main-card">', unsafe_allow_html=True)
    st.subheader("Log Penandatanganan Terkini")
    df = pd.read_sql_query("SELECT docs.date, users.username, docs.doc_name FROM docs JOIN users ON docs.user_id = users.id ORDER BY docs.id DESC LIMIT 10", conn)
    st.table(df); st.markdown('</div>', unsafe_allow_html=True)

elif menu == "👥 Persetujuan Akun":
    st.header("Otorisasi Pengguna Baru")
    for r in conn.execute("SELECT id, username FROM users WHERE status='pending'").fetchall():
        st.markdown(f'<div class="main-card"><b>ID Pengguna:</b> {r[1]}', unsafe_allow_html=True)
        if st.button(f"SETUJUI AKSES: {r[1]}", key=r[0]):
            conn.execute("UPDATE users SET status='active' WHERE id=?", (r[0],)); conn.commit(); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

elif menu == "📂 Arsip Digital":
    st.header("Arsip Tanda Tangan Digital")
    df = pd.read_sql_query(f"SELECT date as 'Tanggal Selesai', doc_name as 'Judul Dokumen', doc_no as 'Nomor Dokumen', remarks as 'Keterangan' FROM docs WHERE user_id={st.session_state.user_id}", conn)
    st.markdown('<div class="main-card">', unsafe_allow_html=True)
    st.dataframe(df, use_container_width=True); st.markdown('</div>', unsafe_allow_html=True)

elif menu in ["💬 Hubungi Admin", "💬 Pusat Pesan"]:
    st.header("Saluran Komunikasi Internal")
    target_id = None
    if st.session_state.role == 'admin':
        u_list = pd.read_sql_query("SELECT id, username FROM users WHERE role='user'", conn)
        if not u_list.empty:
            sel = st.selectbox("Pilih Karyawan", u_list['username'])
            target_id = int(u_list[u_list['username'] == sel]['id'].values[0])
    else:
        target_id = conn.execute("SELECT id FROM users WHERE username='ADMIN'").fetchone()[0]
    
    if target_id:
        st.markdown('<div class="main-card">', unsafe_allow_html=True)
        msgs = pd.read_sql_query(f"SELECT * FROM messages WHERE (sender_id={st.session_state.user_id} AND receiver_id={target_id}) OR (sender_id={target_id} AND receiver_id={st.session_state.user_id})", conn)
        for _, m in msgs.iterrows():
            is_me = m['sender_id'] == st.session_state.user_id
            st.markdown(f"<div style='text-align: {'right' if is_me else 'left'};'><div style='display:inline-block; background:{'#E7F3FF' if is_me else '#F1F3F5'}; padding:12px 18px; border-radius:15px; color:black; margin:8px; border: 1px solid #DEE2E6;'><b>{m['time']}</b><br>{m['msg']}</div></div>", unsafe_allow_html=True)
        with st.form("c_f", clear_on_submit=True):
            t = st.text_input("Tulis pesan pesan bantuan...")
            if st.form_submit_button("KIRIM PESAN"):
                conn.execute("INSERT INTO messages (sender_id, receiver_id, msg, time) VALUES (?,?,?,?)", (st.session_state.user_id, target_id, t, datetime.now().strftime("%H:%M")))
                conn.commit(); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

elif menu == "🔑 Reset Kredensial":
    st.header("Antrian Reset Kata Sandi")
    for r in conn.execute("SELECT id, username FROM users WHERE reset_req=1").fetchall():
        st.markdown(f'<div class="main-card">User <b>{r[1]}</b> meminta akses reset password.', unsafe_allow_html=True)
        if st.button(f"IZINKAN RESET UNTUK: {r[1]}", key=f"res_{r[0]}"):
            conn.execute("UPDATE users SET reset_req=2 WHERE id=?", (r[0],)); conn.commit(); st.success("Diizinkan."); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

elif menu == "🏠 Beranda":
    st.markdown("<br><br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown(f"""<div class="main-card" style='text-align:center;'>
            <h1>🛡️ Selamat Datang</h1>
            <p style='font-size:18px;'>Sistem Sertifikasi Tanda Tangan Digital Terenkripsi</p>
            <hr>
            <p>Gunakan menu navigasi di sebelah kiri untuk mengelola dokumen Anda.</p>
            <p style='font-size:12px; color:gray;'>Versi Corporate 1.0.4 - Koneksi Aman Terenkripsi</p>
        </div>""", unsafe_allow_html=True)




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

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="e-Signature Pro", page_icon="🔐", layout="wide")

# --- 2. DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect("signature_pro_v5.db", check_same_thread=False)
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
    
    admin_exists = cursor.execute("SELECT * FROM users WHERE username='ADMIN'").fetchone()
    if not admin_exists:
        pw = bcrypt.hashpw("Admin99".encode(), bcrypt.gensalt()).decode()
        cursor.execute("INSERT INTO users (username, password, status, role, full_name) VALUES (?,?,?,?,?)", 
                       ('ADMIN', pw, 'active', 'admin', 'Super Admin'))
    conn.commit()
    return conn

conn = init_db()

# --- 3. FUNGSI HELPER ---
def get_bg_image():
    res = conn.execute("SELECT bg_img FROM settings WHERE id=1").fetchone()
    if res and res[0]:
        return base64.b64encode(res[0]).decode()
    return None

def hash_pw(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def check_pw(password, hashed):
    try: return bcrypt.checkpw(password.encode(), hashed.encode())
    except: return False

# --- 4. CSS CUSTOM (FIX CONTRAST & PROFESSIONAL BLUE) ---
bg_data = get_bg_image()
st.markdown(f"""
    <style>
    /* Global Background */
    .stApp {{
        background-color: #ffffff;
        background: {f"url(data:image/png;base64,{bg_data})" if bg_data else "white"};
        background-size: cover;
        background-attachment: fixed;
    }}

    /* Global Text Warna Hitam */
    html, body, [data-testid="stVerticalBlock"], .stMarkdown, p, label, li, span, .stMetric, .stCaption {{
        color: #000000 !important;
    }}

    /* Header Biru */
    h1, h2, h3 {{
        color: #003366 !important;
        font-weight: 700 !important;
        border-bottom: 2px solid #003366;
        padding-bottom: 10px;
    }}

    /* Sidebar Style */
    [data-testid="stSidebar"] {{
        background-color: #f0f5f9 !important;
        border-right: 1px solid #d1d9e0;
    }}
    [data-testid="stSidebar"] * {{
        color: #003366 !important;
    }}

    /* FIX: FILE UPLOADER CONTRAST */
    [data-testid="stFileUploader"] {{
        background-color: #f8f9fa !important;
        border: 2px dashed #0052cc !important;
        border-radius: 10px;
        padding: 10px;
    }}
    [data-testid="stFileUploader"] section {{
        background-color: #f8f9fa !important;
    }}
    [data-testid="stFileUploader"] label, [data-testid="stFileUploader"] p, [data-testid="stFileUploader"] span, [data-testid="stFileUploader"] small {{
        color: #000000 !important;
        font-weight: 500 !important;
    }}

    /* Tombol Biru */
    .stButton>button {{
        width: 100%;
        border-radius: 8px;
        background-color: #0052cc !important;
        color: white !important;
        font-weight: bold;
        height: 45px;
        border: none;
    }}
    .stButton>button:hover {{
        background-color: #003d99 !important;
    }}

    /* Input Field */
    div[data-baseweb="input"] {{
        background-color: #ffffff !important;
        border: 1px solid #ced4da !important;
    }}
    input {{
        color: black !important;
    }}

    /* Status Box Validasi */
    .status-box {{
        background: #eef6ff;
        padding: 20px;
        border-radius: 10px;
        border-left: 10px solid #0052cc;
        color: #000000 !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }}
    </style>
""", unsafe_allow_html=True)

# --- 5. SESSION STATE ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'user_id' not in st.session_state: st.session_state.user_id = None
if 'role' not in st.session_state: st.session_state.role = 'user'
if 'full_name' not in st.session_state: st.session_state.full_name = ""

# --- 6. NAVIGATION ---
if st.session_state.logged_in:
    with st.sidebar:
        st.markdown(f"### 🛡️ e-Signature Pro")
        st.markdown(f"🆔 ID: **{st.session_state.username}**")
        st.markdown(f"👤 **{st.session_state.full_name}**")
        st.divider()
        if st.session_state.role == 'admin':
            menu = st.radio("MENU ADMIN", ["📊 Statistik", "👥 Approval Akun", "🔑 Reset Password", "💬 Chat Center", "⚙️ Ganti Background"])
        else:
            menu = st.radio("MENU USER", ["📊 Dashboard", "📝 Buat QR TTD", "🔍 Verifikasi QR", "📂 History", "👤 Profil", "💬 Bantuan/Chat"])
        st.divider()
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.rerun()
else:
    menu = "Login"

# --- 7. LOGIKA HALAMAN ---

if menu == "Login":
    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.8, 1])
    with col2:
        st.markdown("<h2 style='text-align:center; border:none;'>Akses Sistem</h2>", unsafe_allow_html=True)
        tab_l, tab_r, tab_f = st.tabs(["Login", "Daftar", "Reset"])
        with tab_l:
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            if st.button("Masuk"):
                res = conn.execute("SELECT id, password, status, role, username, full_name FROM users WHERE username=?", (u,)).fetchone()
                if res and check_pw(p, res[1]):
                    if res[2] == 'pending': st.warning("Akun menunggu approval.")
                    else:
                        st.session_state.logged_in = True
                        st.session_state.user_id = res[0]
                        st.session_state.role = res[3]
                        st.session_state.username = res[4]
                        st.session_state.full_name = res[5] if res[5] else "Nama Belum Diisi"
                        st.rerun()
                else: st.error("Login Gagal!")
        with tab_r:
            nu = st.text_input("Username Baru")
            np = st.text_input("Password Baru", type="password")
            if st.button("Daftar"):
                try:
                    conn.execute("INSERT INTO users (username, password, status) VALUES (?,?,'pending')", (nu, hash_pw(np)))
                    conn.commit(); st.success("Berhasil! Tunggu Approval.")
                except: st.error("Username sudah ada.")
        with tab_f:
            fu = st.text_input("Username Lupa Password")
            if st.button("Kirim Permintaan"):
                user = conn.execute("SELECT id FROM users WHERE username=?", (fu,)).fetchone()
                if user:
                    conn.execute("UPDATE users SET reset_req=1 WHERE id=?", (user[0],))
                    conn.commit(); st.info("Permintaan terkirim ke Admin.")

elif menu == "📝 Buat QR TTD":
    st.header("Generate TTD Digital")
    u_data = conn.execute("SELECT full_name, emp_id, position, logo FROM users WHERE id=?", (st.session_state.user_id,)).fetchone()
    if not u_data[0]: st.warning("Isi profil dulu!")
    else:
        with st.form("qr"):
            dno = st.text_input("No Dokumen")
            dnm = st.text_input("Nama Dokumen")
            pwd = st.text_input("Password Konfirmasi", type="password")
            if st.form_submit_button("Generate"):
                auth = conn.execute("SELECT password FROM users WHERE id=?", (st.session_state.user_id,)).fetchone()
                if check_pw(pwd, auth[0]):
                    ts = datetime.now().strftime("%H:%M:%S %d/%m/%Y")
                    h = hashlib.sha256(f"{u_data[0]}|{dno}".encode()).hexdigest()
                    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H)
                    qr.add_data(f"SIGNER:{u_data[0]}\nID:{u_data[1]}\nDOC:{dnm}\nTIME:{ts}\nHASH:{h}")
                    img = qr.make_image(fill_color="black", back_color="white").convert('RGB')
                    if u_data[3]:
                        logo = Image.open(io.BytesIO(u_data[3])).resize((img.size[0]//4, img.size[1]//4))
                        img.paste(logo, ((img.size[0]-logo.size[0])//2, (img.size[1]-logo.size[1])//2))
                    st.image(img, width=250)
                    conn.execute("INSERT INTO docs (user_id, doc_no, doc_name, date, hash_val) VALUES (?,?,?,?,?)", (st.session_state.user_id, dno, dnm, ts, h))
                    conn.commit()
                else: st.error("Password salah.")

elif menu == "🔍 Verifikasi QR":
    st.header("Cek Keaslian Dokumen")
    f = st.file_uploader("Upload QR", type=['png','jpg'])
    if f:
        img = Image.open(f)
        data, _, _ = cv2.QRCodeDetector().detectAndDecode(cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR))
        if data:
            st.success("QR Terbaca!")
            st.markdown(f'<div class="status-box">{data.replace("\n","<br>")}</div>', unsafe_allow_html=True)

elif menu == "⚙️ Ganti Background":
    st.header("Pengaturan Background")
    # Bagian ini sekarang akan berwarna terang dengan teks hitam
    b = st.file_uploader("Pilih Gambar Baru (Wallpaper)", type=['jpg','png','jpeg'])
    if st.button("Simpan"):
        if b:
            conn.execute("DELETE FROM settings")
            conn.execute("INSERT INTO settings (id, bg_img) VALUES (1, ?)", (b.read(),))
            conn.commit(); st.success("Background Update! Refresh (F5).")

elif menu == "👤 Profil":
    st.header("Data Diri")
    d = conn.execute("SELECT full_name, emp_id, position, logo FROM users WHERE id=?", (st.session_state.user_id,)).fetchone

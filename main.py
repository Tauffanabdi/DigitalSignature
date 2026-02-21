import streamlit as st
import sqlite3
import hashlib
import qrcode
import pandas as pd
import bcrypt
from PIL import Image, ImageDraw
from datetime import datetime
import io
import base64
import numpy as np
import cv2

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="e-Signature Pro", page_icon="🔐", layout="wide")

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect("signature_pro_v3.db", check_same_thread=False)
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

# --- FUNGSI HELPER ---
def get_bg_image():
    res = conn.execute("SELECT bg_img FROM settings WHERE id=1").fetchone()
    if res and res[0]:
        return base64.b64encode(res[0]).decode()
    return None

def hash_pw(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def check_pw(password, hashed):
    return bcrypt.checkpw(password.encode(), hashed.encode())

# --- CSS UI MODERN ---
bg_data = get_bg_image()
bg_style = f"""
    <style>
    .stApp {{
        background: {f"url(data:image/png;base64,{bg_data})" if bg_data else "linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%)"};
        background-size: cover;
        background-attachment: fixed;
    }}
    
    /* Login Card Container */
    .login-card {{
        background: rgba(255, 255, 255, 0.95);
        padding: 40px;
        border-radius: 20px;
        box-shadow: 0 15px 35px rgba(0,0,0,0.2);
        max-width: 500px;
        margin: auto;
        color: #1e1e1e !important;
    }}
    
    /* Force All Label & Text to Black */
    .stMarkdown, p, label, .stDataFrame, .stSelectbox, div[data-baseweb="select"] {{
        color: #1e1e1e !important;
    }}
    
    h1, h2, h3 {{
        color: #004085 !important;
        font-weight: 800 !important;
    }}

    .stButton>button {{
        width: 100%;
        border-radius: 10px;
        background: linear-gradient(45deg, #007bff, #0056b3);
        color: white !important;
        font-weight: bold;
        border: none;
        height: 45px;
        transition: 0.3s;
    }}
    
    .stButton>button:hover {{
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(0,123,255,0.4);
    }}

    /* Sidebar Styling */
    section[data-testid="stSidebar"] {{
        background-color: #ffffff !important;
        border-right: 1px solid #e0e0e0;
    }}
    
    .status-box {{
        background: white;
        padding: 20px;
        border-radius: 15px;
        border-left: 8px solid #28a745;
        color: black !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        margin-top: 20px;
    }}
    </style>
"""
st.markdown(bg_style, unsafe_allow_html=True)

# --- SESSION STATE ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'user_id' not in st.session_state: st.session_state.user_id = None
if 'role' not in st.session_state: st.session_state.role = 'user'

# --- NAVIGATION ---
if st.session_state.logged_in:
    with st.sidebar:
        st.markdown(f"### 🛡️ e-Signature Pro\n**{st.session_state.username.upper()}** ({st.session_state.role})")
        st.divider()
        if st.session_state.role == 'admin':
            menu = st.radio("MENU ADMIN", ["Dashboard Stats", "Approve Akun", "Reset Password", "Chat Center", "Ganti Background"])
        else:
            menu = st.radio("MENU USER", ["Dashboard", "Buat QR TTD", "Verifikasi QR", "History Dokumen", "Profil Saya", "Bantuan/Chat"])
        
        st.sidebar.markdown("---")
        if st.sidebar.button("🚪 Logout"):
            st.session_state.logged_in = False
            st.rerun()
else:
    menu = "Login"

# --- LOGIN & REGISTER UI ---
if menu == "Login":
    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.5, 1])
    
    with col2:
        st.markdown('<div class="login-card">', unsafe_allow_html=True)
        st.title("🔐 Access Portal")
        tab_l, tab_r, tab_f = st.tabs(["Masuk", "Daftar", "Lupa Password"])
        
        with tab_l:
            u = st.text_input("Username", placeholder="Masukkan username...")
            p = st.text_input("Password", type="password", placeholder="Masukkan password...")
            if st.button("LOGIN SEKARANG"):
                res = conn.execute("SELECT id, password, status, role, username FROM users WHERE username=?", (u,)).fetchone()
                if res:
                    if res[2] == 'pending':
                        st.warning("⏳ Akun menunggu persetujuan Admin.")
                    elif check_pw(p, res[1]):
                        st.session_state.logged_in = True
                        st.session_state.user_id = res[0]
                        st.session_state.role = res[3]
                        st.session_state.username = res[4]
                        st.rerun()
                    else: st.error("❌ Password salah!")
                else: st.error("❌ Username tidak terdaftar.")
        
        with tab_r:
            new_u = st.text_input("Username Baru", key="reg_u")
            new_p = st.text_input("Password Baru", type="password", key="reg_p")
            if st.button("DAFTAR AKUN"):
                try:
                    conn.execute("INSERT INTO users (username, password, status, role) VALUES (?,?,'pending','user')", 
                                 (new_u, hash_pw(new_p)))
                    conn.commit()
                    st.success("✅ Terdaftar! Menunggu konfirmasi Admin.")
                except: st.error("❌ Username sudah digunakan.")
        
        with tab_f:
            f_u = st.text_input("Username Anda", key="forgot_u")
            if st.button("MINTA RESET PASSWORD"):
                user = conn.execute("SELECT id, reset_req FROM users WHERE username=?", (f_u,)).fetchone()
                if user:
                    if user[1] == 2:
                        new_pass = st.text_input("Password Baru", type="password")
                        if st.button("Update Sekarang"):
                            conn.execute("UPDATE users SET password=?, reset_req=0 WHERE id=?", (hash_pw(new_pass), user[0]))
                            conn.commit()
                            st.success("Berhasil! Silakan Login.")
                    else:
                        conn.execute("UPDATE users SET reset_req=1 WHERE id=?", (user[0],))
                        conn.commit()
                        st.info("📩 Permintaan terkirim ke Admin.")
                else: st.error("User tidak ditemukan.")
        st.markdown('</div>', unsafe_allow_html=True)

# --- ADMIN: APPROVE AKUN ---
elif menu == "Approve Akun":
    st.header("👥 Persetujuan User Baru")
    df_p = pd.read_sql_query("SELECT id, username, status FROM users WHERE status='pending'", conn)
    if df_p.empty:
        st.info("Tidak ada user yang menunggu approval.")
    else:
        for _, r in df_p.iterrows():
            c1, c2 = st.columns([3, 1])
            c1.subheader(f"User: {r['username']}")
            if c2.button("SETUJUI", key=f"app_{r['id']}"):
                conn.execute("UPDATE users SET status='active' WHERE id=?", (r['id'],))
                conn.commit()
                st.rerun()

# --- USER: BUAT QR TTD ---
elif menu == "Buat QR TTD":
    st.header("📝 Generate QR Signature")
    u_data = conn.execute("SELECT full_name, emp_id, position, logo FROM users WHERE id=?", (st.session_state.user_id,)).fetchone()
    
    if not u_data[0]:
        st.warning("Lengkapi profil dulu di menu Profil Saya.")
    else:
        with st.form("qr_form"):
            col1, col2 = st.columns(2)
            d_no = col1.text_input("Nomor Dokumen")
            d_nm = col1.text_input("Nama Dokumen")
            rem = col2.selectbox("Keterangan", ["Original", "Revisi"])
            pwd = col2.text_input("Konfirmasi Password", type="password")
            
            if st.form_submit_button("GENERATE & SIGN"):
                auth = conn.execute("SELECT password FROM users WHERE id=?", (st.session_state.user_id,)).fetchone()
                if check_pw(pwd, auth[0]):
                    ts = datetime.now().strftime("%H:%M:%S %d/%m/%Y")
                    raw = f"{u_data[0]}|{u_data[1]}|{u_data[2]}|{d_no}|{d_nm}"
                    h_val = hashlib.sha256(raw.encode()).hexdigest()
                    
                    qr_data = f"SIGNER:{u_data[0]}\nID:{u_data[1]}\nPOS:{u_data[2]}\nDOC_NO:{d_no}\nDOC_NAME:{d_nm}\nTIME:{ts}\nHASH:{h_val}"
                    
                    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=10, border=4)
                    qr.add_data(qr_data)
                    qr.make(fit=True)
                    img = qr.make_image(fill_color="black", back_color="white").convert('RGB')
                    
                    if u_data[3]:
                        logo = Image.open(io.BytesIO(u_data[3]))
                        logo = logo.resize((img.size[0]//4, img.size[1]//4))
                        img.paste(logo, ((img.size[0]-logo.size[0])//2, (img.size[1]-logo.size[1])//2))
                    
                    st.image(img, caption="QR TTD ANDA", width=300)
                    conn.execute("INSERT INTO docs (user_id, doc_no, doc_name, remarks, date, hash_val) VALUES (?,?,?,?,?,?)",
                                 (st.session_state.user_id, d_no, d_nm, rem, ts, h_val))
                    conn.commit()
                    
                    buf = io.BytesIO()
                    img.save(buf, format="PNG")
                    st.download_button("DOWNLOAD QR (.PNG)", buf.getvalue(), f"TTD_{d_no}.png")
                else: st.error("Password Salah!")

# --- VERIFIKASI QR ---
elif menu == "Verifikasi QR":
    st.header("🔍 Verifikasi Keaslian QR")
    uploaded_file = st.file_uploader("Upload QR Code", type=['png', 'jpg', 'jpeg'])
    if uploaded_file:
        img = Image.open(uploaded_file)
        opencv_img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        data, _, _ = cv2.QRCodeDetector().detectAndDecode(opencv_img)
        if data:
            try:
                d = dict(line.split(":", 1) for line in data.split("\n"))
                raw = f"{d['SIGNER']}|{d['ID']}|{d['POS']}|{d['DOC_NO']}|{d['DOC_NAME']}"
                if hashlib.sha256(raw.encode()).hexdigest() == d['HASH']:
                    st.success("✅ QR CODE VALID & ASLI")
                    st.markdown(f"""<div class="status-box">
                        <p><b>Signed By:</b> {d['SIGNER']} ({d['POS']})</p>
                        <p><b>Employee ID:</b> {d['ID']}</p>
                        <p><b>Document:</b> {d['DOC_NAME']} / {d['DOC_NO']}</p>
                        <p><b>Timestamp:</b> {d['TIME']}</p>
                    </div>""", unsafe_allow_html=True)
                else: st.error("🚨 QR CODE TELAH DIMANIPULASI / PALSU!")
            except: st.error("Format QR tidak dikenal.")
        else: st.error("QR Code tidak terbaca.")

# --- DASHBOARD STATS (USER & ADMIN) ---
elif menu in ["Dashboard", "Dashboard Stats"]:
    st.header("📊 Dashboard Overview")
    if st.session_state.role == 'admin':
        t_docs = conn.execute("SELECT COUNT(*) FROM docs").fetchone()[0]
        t_users = conn.execute("SELECT COUNT(*) FROM users WHERE role='user'").fetchone()[0]
        c1, c2 = st.columns(2)
        c1.metric("Total Dokumen TTD", t_docs)
        c2.metric("Total User", t_users)
        
        st.subheader("📋 Aktivitas TTD Terbaru")
        df_lat = pd.read_sql_query("""SELECT docs.date, users.username, docs.doc_name 
                                      FROM docs JOIN users ON docs.user_id = users.id 
                                      ORDER BY docs.id DESC LIMIT 5""", conn)
        st.table(df_lat)
    else:
        u_docs = conn.execute("SELECT COUNT(*) FROM docs WHERE user_id=?", (st.session_state.user_id,)).fetchone()[0]
        st.metric("Dokumen Saya", u_docs)
        st.info("Gunakan menu sebelah kiri untuk mengelola tanda tangan digital Anda.")

# --- PROFIL SAYA ---
elif menu == "Profil Saya":
    st.header("👤 Manajemen Profil")
    u_data = conn.execute("SELECT full_name, emp_id, position, logo FROM users WHERE id=?", (st.session_state.user_id,)).fetchone()
    with st.form("prof_form"):
        fn = st.text_input("Nama Lengkap", value=u_data[0] or "")
        ei = st.text_input("Nomor ID Karyawan", value=u_data[1] or "")
        ps = st.text_input("Jabatan", value=u_data[2] or "")
        lg = st.file_uploader("Upload Logo Perusahaan (Tengah QR)", type=['png','jpg'])
        if st.form_submit_button("SIMPAN PROFIL"):
            l_blob = lg.read() if lg else u_data[3]
            conn.execute("UPDATE users SET full_name=?, emp_id=?, position=?, logo=? WHERE id=?", (fn, ei, ps, l_blob, st.session_state.user_id))
            conn.commit()
            st.success("Profil diperbarui!")

# --- CHAT & BANTUAN (PERBAIKAN ERROR INDEX) ---
elif menu in ["Bantuan/Chat", "Chat Center"]:
    st.header("💬 Pusat Bantuan")
    
    # Inisialisasi target_id
    target_id = None
    
    if st.session_state.role == 'admin':
        # Ambil daftar user yang BUKAN admin
        u_list = pd.read_sql_query("SELECT id, username FROM users WHERE role='user'", conn)
        
        if u_list.empty:
            st.info("ℹ️ Belum ada user (karyawan) yang terdaftar di sistem.")
        else:
            sel_u = st.selectbox("Pilih User untuk diajak Chat", u_list['username'])
            # Cari ID user berdasarkan username yang dipilih
            match = u_list[u_list['username'] == sel_u]
            if not match.empty:
                target_id = int(match['id'].values[0])
    else:
        # Jika login sebagai User, otomatis targetnya adalah ADMIN
        admin_data = conn.execute("SELECT id FROM users WHERE username='ADMIN'").fetchone()
        if admin_data:
            target_id = admin_id = admin_data[0]
        else:
            st.error("Sistem Error: Akun ADMIN tidak ditemukan.")

    # Jika target_id ditemukan, tampilkan Chat
    if target_id is not None:
        st.divider()
        
        # Load riwayat pesan
        chat_df = pd.read_sql_query(f"""
            SELECT * FROM messages 
            WHERE (sender_id={st.session_state.user_id} AND receiver_id={target_id}) 
            OR (sender_id={target_id} AND receiver_id={st.session_state.user_id})
            ORDER BY id ASC
        """, conn)

        # Container untuk Chat agar bisa scroll
        chat_container = st.container()
        with chat_container:
            for _, m in chat_df.iterrows():
                is_me = m['sender_id'] == st.session_state.user_id
                align = "right" if is_me else "left"
                bg_color = "#dcf8c6" if is_me else "#ffffff" # Warna Hijau WhatsApp vs Putih
                
                st.markdown(f"""
                    <div style="display: flex; justify-content: {align}; margin-bottom: 10px;">
                        <div style="background-color: {bg_color}; padding: 10px 15px; border-radius: 15px; 
                                    max-width: 70%; box-shadow: 0 1px 2px rgba(0,0,0,0.1); color: black;">
                            <div style="font-size: 0.8em; color: gray;">{m['time']}</div>
                            <div style="font-size: 1em;">{m['msg']}</div>
                        </div>
                    </div>
                """, unsafe_allow_html=True)

        # Form input pesan (selalu di bawah)
        with st.form("chat_form", clear_on_submit=True):
            col_t, col_b = st.columns([4, 1])
            msg_in = col_t.text_input("Ketik pesan...", placeholder="Tulis sesuatu di sini...")
            if col_b.form_submit_button("KIRIM 🚀"):
                if msg_in:
                    now = datetime.now().strftime("%H:%M")
                    conn.execute("INSERT INTO messages (sender_id, receiver_id, msg, time) VALUES (?,?,?,?)", 
                                 (st.session_state.user_id, target_id, msg_in, now))
                    conn.commit()
                    st.rerun()
    else:
        st.warning("⚠️ Chat belum dapat dimulai.")

# --- ADMIN: GANTI BACKGROUND ---
elif menu == "Ganti Background":
    st.header("⚙️ Pengaturan Tampilan")
    f_bg = st.file_uploader("Upload Foto Background Baru", type=['png','jpg','jpeg'])
    if st.button("TERAPKAN BACKGROUND"):
        if f_bg:
            blob = f_bg.read()
            conn.execute("DELETE FROM settings")
            conn.execute("INSERT INTO settings (id, bg_img) VALUES (1, ?)", (blob,))
            conn.commit()
            st.success("Background Berhasil Diganti! Refresh halaman (F5).")

# --- USER: HISTORY ---
elif menu == "History Dokumen":
    st.header("📂 Riwayat Penandatanganan")
    df_h = pd.read_sql_query(f"SELECT date as Tanggal, doc_name as Nama_Dokumen, doc_no as No_Dokumen, remarks as Keterangan FROM docs WHERE user_id={st.session_state.user_id}", conn)
    st.dataframe(df_h, use_container_width=True)


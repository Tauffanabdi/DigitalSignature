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

# --- 4. CSS CUSTOM (PROFESSIONAL BLUE & WHITE) ---
bg_data = get_bg_image()
st.markdown(f"""
    <style>
    /* 1. Background Utama Putih Bersih */
    .stApp {{
        background-color: #ffffff;
        background: {f"url(data:image/png;base64,{bg_data})" if bg_data else "white"};
        background-size: cover;
        background-attachment: fixed;
    }}

    /* 2. Global Text Menjadi Hitam Pekat */
    html, body, [data-testid="stVerticalBlock"], .stMarkdown, p, label, li, span, .stMetric, .stCaption {{
        color: #000000 !important;
        font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    }}

    /* 3. Judul (Headers) Biru Profesional */
    h1, h2, h3 {{
        color: #003366 !important;
        font-weight: 700 !important;
        border-bottom: 2px solid #003366;
        padding-bottom: 10px;
    }}

    /* 4. Sidebar Biru Muda dengan Teks Hitam */
    [data-testid="stSidebar"] {{
        background-color: #f0f5f9 !important;
        border-right: 1px solid #d1d9e0;
    }}
    [data-testid="stSidebar"] .stMarkdown, [data-testid="stSidebar"] label, [data-testid="stSidebar"] p {{
        color: #003366 !important;
        font-weight: 600;
    }}

    /* 5. Login Card Style */
    .login-card {{
        background: #ffffff;
        padding: 40px;
        border-radius: 15px;
        border: 1px solid #d1d9e0;
        box-shadow: 0 10px 25px rgba(0,0,0,0.1);
        max-width: 500px;
        margin: auto;
    }}

    /* 6. Tombol Biru */
    .stButton>button {{
        width: 100%;
        border-radius: 8px;
        background-color: #0052cc !important;
        color: white !important;
        font-weight: bold;
        border: none;
        height: 45px;
        transition: 0.3s;
    }}
    .stButton>button:hover {{
        background-color: #003d99 !important;
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }}

    /* 7. Input Field Style */
    input {{
        color: black !important;
        background-color: #f8f9fa !important;
        border: 1px solid #ced4da !important;
    }}

    /* 8. Status Box (Validasi) */
    .status-box {{
        background: #eef6ff;
        padding: 20px;
        border-radius: 10px;
        border-left: 10px solid #0052cc;
        color: #000000 !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }}
    .status-box p, .status-box b {{
        color: #000000 !important;
    }}

    /* 9. Dataframe / Table */
    .stDataFrame, .stTable {{
        background-color: white !important;
        color: black !important;
        border-radius: 10px;
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
        st.markdown(f"🆔 User ID: **{st.session_state.username}**")
        st.markdown(f"👤 Nama: **{st.session_state.full_name}**")
        st.divider()
        
        if st.session_state.role == 'admin':
            menu = st.radio("MENU UTAMA", ["📊 Statistik", "👥 Approval Akun", "🔑 Reset Password", "💬 Chat Center", "⚙️ Ganti Background"])
        else:
            menu = st.radio("MENU UTAMA", ["📊 Dashboard", "📝 Buat QR TTD", "🔍 Verifikasi QR", "📂 History", "👤 Profil", "💬 Bantuan/Chat"])
        
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
        st.markdown('<div class="login-card">', unsafe_allow_html=True)
        st.markdown("<h2 style='text-align:center; border:none;'>Akses Sistem</h2>", unsafe_allow_html=True)
        tab_l, tab_r, tab_f = st.tabs(["Login", "Daftar Akun", "Reset"])
        
        with tab_l:
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            if st.button("Masuk"):
                res = conn.execute("SELECT id, password, status, role, username, full_name FROM users WHERE username=?", (u,)).fetchone()
                if res:
                    if res[2] == 'pending': st.warning("Akun menunggu persetujuan Admin.")
                    elif check_pw(p, res[1]):
                        st.session_state.logged_in = True
                        st.session_state.user_id = res[0]
                        st.session_state.role = res[3]
                        st.session_state.username = res[4]
                        st.session_state.full_name = res[5] if res[5] else "Belum Diisi"
                        st.rerun()
                    else: st.error("Password Salah!")
                else: st.error("User tidak ditemukan.")
        
        with tab_r:
            new_u = st.text_input("Buat Username")
            new_p = st.text_input("Buat Password", type="password")
            if st.button("Daftar Sekarang"):
                try:
                    conn.execute("INSERT INTO users (username, password, status, role) VALUES (?,?,'pending','user')", (new_u, hash_pw(new_p)))
                    conn.commit(); st.success("Terdaftar! Hubungi Admin untuk aktivasi.")
                except: st.error("Username sudah ada.")
        
        with tab_f:
            f_u = st.text_input("Username Lupa Password")
            if st.button("Ajukan Reset"):
                user = conn.execute("SELECT id, reset_req FROM users WHERE username=?", (f_u,)).fetchone()
                if user:
                    if user[1] == 2:
                        npw = st.text_input("Password Baru", type="password")
                        if st.button("Update"):
                            conn.execute("UPDATE users SET password=?, reset_req=0 WHERE id=?", (hash_pw(npw), user[0]))
                            conn.commit(); st.success("Selesai!")
                    else:
                        conn.execute("UPDATE users SET reset_req=1 WHERE id=?", (user[0],))
                        conn.commit(); st.info("Permintaan terkirim.")
        st.markdown('</div>', unsafe_allow_html=True)

elif menu in ["📊 Dashboard", "📊 Statistik"]:
    st.header("Dashboard Overview")
    if st.session_state.role == 'admin':
        c1, c2 = st.columns(2)
        c1.metric("Total Dokumen", conn.execute("SELECT COUNT(*) FROM docs").fetchone()[0])
        c2.metric("Total User Aktif", conn.execute("SELECT COUNT(*) FROM users WHERE status='active'").fetchone()[0])
        st.subheader("Aktivitas Terbaru")
        df = pd.read_sql_query("SELECT docs.date, users.username, docs.doc_name FROM docs JOIN users ON docs.user_id = users.id ORDER BY docs.id DESC LIMIT 5", conn)
        st.table(df)
    else:
        st.metric("Tanda Tangan Saya", conn.execute("SELECT COUNT(*) FROM docs WHERE user_id=?", (st.session_state.user_id,)).fetchone()[0])
        st.write("Gunakan menu di samping untuk membuat atau memvalidasi TTD.")

elif menu == "📝 Buat QR TTD":
    st.header("Generate Digital Signature")
    u_data = conn.execute("SELECT full_name, emp_id, position, logo FROM users WHERE id=?", (st.session_state.user_id,)).fetchone()
    if not u_data[0]: st.warning("Lengkapi profil Anda terlebih dahulu.")
    else:
        with st.form("qr_f"):
            d_no = st.text_input("Nomor Dokumen")
            d_nm = st.text_input("Nama Dokumen (JSA/BA/Laporan)")
            pwd = st.text_input("Konfirmasi Password", type="password")
            if st.form_submit_button("Generate QR Code"):
                auth = conn.execute("SELECT password FROM users WHERE id=?", (st.session_state.user_id,)).fetchone()
                if check_pw(pwd, auth[0]):
                    ts = datetime.now().strftime("%H:%M:%S %d/%m/%Y")
                    h = hashlib.sha256(f"{u_data[0]}|{u_data[1]}|{u_data[2]}|{d_no}|{d_nm}".encode()).hexdigest()
                    qr_txt = f"SIGNER:{u_data[0]}\nID:{u_data[1]}\nPOS:{u_data[2]}\nDOC_NO:{d_no}\nDOC_NAME:{d_nm}\nTIME:{ts}\nHASH:{h}"
                    
                    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=10, border=4)
                    qr.add_data(qr_txt); qr.make(fit=True)
                    img = qr.make_image(fill_color="black", back_color="white").convert('RGB')
                    if u_data[3]:
                        logo = Image.open(io.BytesIO(u_data[3])).resize((img.size[0]//4, img.size[1]//4))
                        img.paste(logo, ((img.size[0]-logo.size[0])//2, (img.size[1]-logo.size[1])//2))
                    st.image(img, width=250)
                    conn.execute("INSERT INTO docs (user_id, doc_no, doc_name, date, hash_val) VALUES (?,?,?,?,?)", (st.session_state.user_id, d_no, d_nm, ts, h))
                    conn.commit()
                    buf = io.BytesIO(); img.save(buf, format="PNG")
                    st.download_button("Download QR PNG", buf.getvalue(), f"QR_{d_no}.png")
                else: st.error("Password Salah!")

elif menu == "🔍 Verifikasi QR":
    st.header("Verifikasi Keaslian Dokumen")
    f = st.file_uploader("Pilih file QR", type=['png','jpg'])
    if f:
        img = Image.open(f)
        data, _, _ = cv2.QRCodeDetector().detectAndDecode(cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR))
        if data:
            try:
                d = dict(l.split(":", 1) for l in data.split("\n"))
                raw = f"{d['SIGNER']}|{d['ID']}|{d['POS']}|{d['DOC_NO']}|{d['DOC_NAME']}"
                if hashlib.sha256(raw.encode()).hexdigest() == d['HASH']:
                    st.success("QR CODE TERVERIFIKASI")
                    st.markdown(f'<div class="status-box"><p><b>Penandatangan:</b> {d["SIGNER"]} ({d["POS"]})</p><p><b>ID Karyawan:</b> {d["ID"]}</p><p><b>Dokumen:</b> {d["DOC_NAME"]} / {d["DOC_NO"]}</p><p><b>Waktu:</b> {d["TIME"]}</p></div>', unsafe_allow_html=True)
                else: st.error("DATA TELAH DIMANIPULASI")
            except: st.error("Format tidak dikenal.")
        else: st.error("QR tidak terbaca.")

elif menu == "👤 Profil":
    st.header("Manajemen Profil")
    u_data = conn.execute("SELECT full_name, emp_id, position, logo FROM users WHERE id=?", (st.session_state.user_id,)).fetchone()
    with st.form("p"):
        fn = st.text_input("Nama Lengkap", value=u_data[0] or "")
        ei = st.text_input("ID Karyawan", value=u_data[1] or "")
        ps = st.text_input("Jabatan", value=u_data[2] or "")
        lg = st.file_uploader("Logo TTD", type=['png','jpg'])
        if st.form_submit_button("Simpan"):
            conn.execute("UPDATE users SET full_name=?, emp_id=?, position=?, logo=? WHERE id=?", (fn, ei, ps, lg.read() if lg else u_data[3], st.session_state.user_id))
            conn.commit(); st.session_state.full_name = fn; st.success("Profil Disimpan!"); st.rerun()

elif menu == "📂 History":
    st.header("Riwayat Dokumen")
    st.dataframe(pd.read_sql_query(f"SELECT date as Tanggal, doc_name as Nama, doc_no as No FROM docs WHERE user_id={st.session_state.user_id}", conn), use_container_width=True)

elif menu in ["💬 Bantuan/Chat", "💬 Chat Center"]:
    st.header("Pusat Bantuan")
    target_id = None
    if st.session_state.role == 'admin':
        u_list = pd.read_sql_query("SELECT id, username FROM users WHERE role='user'", conn)
        if not u_list.empty:
            sel = st.selectbox("Chat dengan user", u_list['username'])
            target_id = int(u_list[u_list['username'] == sel]['id'].values[0])
    else:
        target_id = conn.execute("SELECT id FROM users WHERE username='ADMIN'").fetchone()[0]
    
    if target_id:
        msgs = pd.read_sql_query(f"SELECT * FROM messages WHERE (sender_id={st.session_state.user_id} AND receiver_id={target_id}) OR (sender_id={target_id} AND receiver_id={st.session_state.user_id})", conn)
        for _, m in msgs.iterrows():
            is_me = m['sender_id'] == st.session_state.user_id
            st.markdown(f"<div style='text-align: {'right' if is_me else 'left'};'><div style='display:inline-block; background:{'#e1f5fe' if is_me else '#f1f1f1'}; padding:8px 15px; border-radius:10px; color:black; margin:5px;'>{m['msg']}</div></div>", unsafe_allow_html=True)
        with st.form("c", clear_on_submit=True):
            t = st.text_input("Ketik...")
            if st.form_submit_button("Kirim"):
                conn.execute("INSERT INTO messages (sender_id, receiver_id, msg, time) VALUES (?,?,?,?)", (st.session_state.user_id, target_id, t, datetime.now().strftime("%H:%M")))
                conn.commit(); st.rerun()

elif menu == "👥 Approval Akun":
    st.header("Approval User Baru")
    for _, r in pd.read_sql_query("SELECT id, username FROM users WHERE status='pending'", conn).iterrows():
        c1, c2 = st.columns([3,1])
        c1.write(f"Username: {r['username']}")
        if c2.button("Approve", key=r['id']):
            conn.execute("UPDATE users SET status='active' WHERE id=?", (r['id'],)); conn.commit(); st.rerun()

elif menu == "⚙️ Ganti Background":
    st.header("Pengaturan Background")
    b = st.file_uploader("Upload Image", type=['jpg','png'])
    if st.button("Simpan"):
        if b: conn.execute("DELETE FROM settings"); conn.execute("INSERT INTO settings (id, bg_img) VALUES (1, ?)", (b.read(),)); conn.commit(); st.success("Ok!"); st.rerun()

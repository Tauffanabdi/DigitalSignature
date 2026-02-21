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
    conn = sqlite3.connect("signature_pro_v4.db", check_same_thread=False)
    cursor = conn.cursor()
    # Tabel Users
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE, password TEXT,
                        full_name TEXT, emp_id TEXT, position TEXT, 
                        logo BLOB, status TEXT DEFAULT 'pending', 
                        reset_req INTEGER DEFAULT 0, role TEXT DEFAULT 'user')''')
    # Tabel Dokumen
    cursor.execute('''CREATE TABLE IF NOT EXISTS docs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER, doc_no TEXT, doc_name TEXT, 
                        remarks TEXT, date TEXT, hash_val TEXT)''')
    # Tabel Pesan (Chat)
    cursor.execute('''CREATE TABLE IF NOT EXISTS messages (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        sender_id INTEGER, receiver_id INTEGER, 
                        msg TEXT, time TEXT)''')
    # Tabel Settings
    cursor.execute('''CREATE TABLE IF NOT EXISTS settings (id INTEGER PRIMARY KEY, bg_img BLOB)''')
    
    # Akun Admin Default
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

# --- 4. CSS CUSTOM (UI PREMIUM) ---
bg_data = get_bg_image()
st.markdown(f"""
    <style>
    .stApp {{
        background: {f"url(data:image/png;base64,{bg_data})" if bg_data else "linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%)"};
        background-size: cover;
        background-attachment: fixed;
    }}
    .login-card {{
        background: rgba(255, 255, 255, 0.95);
        padding: 40px; border-radius: 20px; box-shadow: 0 15px 35px rgba(0,0,0,0.2);
        max-width: 500px; margin: auto; color: #1e1e1e !important;
    }}
    /* Paksa teks hitam di area putih */
    .stMarkdown, p, label, .stDataFrame, .stSelectbox, div[data-baseweb="select"], .stCaption {{
        color: #1e1e1e !important;
    }}
    .status-box {{
        background: white; padding: 20px; border-radius: 15px; border-left: 8px solid #28a745;
        color: black !important; box-shadow: 0 4px 12px rgba(0,0,0,0.1); margin-top: 20px;
    }}
    .status-box b, .status-box p {{ color: black !important; }}
    .stButton>button {{
        width: 100%; border-radius: 10px; background: linear-gradient(45deg, #007bff, #0056b3);
        color: white !important; font-weight: bold; height: 45px; border: none;
    }}
    </style>
""", unsafe_allow_html=True)

# --- 5. SESSION STATE ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'user_id' not in st.session_state: st.session_state.user_id = None
if 'role' not in st.session_state: st.session_state.role = 'user'
if 'full_name' not in st.session_state: st.session_state.full_name = ""

# --- 6. NAVIGATION & SIDEBAR ---
if st.session_state.logged_in:
    with st.sidebar:
        st.markdown(f"### 🛡️ e-Signature Pro")
        st.markdown(f"🆔 **{st.session_state.username}**")
        st.markdown(f"👤 *{st.session_state.full_name}*")
        st.caption(f"Status: {st.session_state.role.upper()}")
        st.divider()
        
        if st.session_state.role == 'admin':
            menu = st.radio("MENU ADMIN", ["Dashboard Stats", "Approve Akun", "Reset Password", "Chat Center", "Ganti Background"])
        else:
            menu = st.radio("MENU USER", ["Dashboard", "Buat QR TTD", "Verifikasi QR", "History Dokumen", "Profil Saya", "Bantuan/Chat"])
        
        st.divider()
        if st.button("🚪 Logout"):
            st.session_state.logged_in = False
            st.rerun()
else:
    menu = "Login"

# --- 7. LOGIKA HALAMAN ---

# --- LOGIN / REGISTER ---
if menu == "Login":
    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown('<div class="login-card">', unsafe_allow_html=True)
        st.title("🔐 Access Portal")
        tab_l, tab_r, tab_f = st.tabs(["Masuk", "Daftar", "Lupa Password"])
        
        with tab_l:
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            if st.button("LOGIN SEKARANG"):
                res = conn.execute("SELECT id, password, status, role, username, full_name FROM users WHERE username=?", (u,)).fetchone()
                if res:
                    if res[2] == 'pending':
                        st.warning("⏳ Akun menunggu persetujuan Admin.")
                    elif check_pw(p, res[1]):
                        st.session_state.logged_in = True
                        st.session_state.user_id = res[0]
                        st.session_state.role = res[3]
                        st.session_state.username = res[4]
                        st.session_state.full_name = res[5] if res[5] else "Nama Belum Diisi"
                        st.rerun()
                    else: st.error("❌ Password salah!")
                else: st.error("❌ Akun tidak ditemukan.")
        
        with tab_r:
            new_u = st.text_input("Username Baru")
            new_p = st.text_input("Password Baru", type="password")
            if st.button("DAFTAR AKUN"):
                try:
                    conn.execute("INSERT INTO users (username, password, status, role) VALUES (?,?,'pending','user')", 
                                 (new_u, hash_pw(new_p)))
                    conn.commit()
                    st.info("✅ Registrasi Berhasil! Menunggu konfirmasi Admin.")
                except: st.error("❌ Username sudah terdaftar.")
        
        with tab_f:
            f_u = st.text_input("Masukkan Username Anda")
            if st.button("AJUKAN RESET"):
                user = conn.execute("SELECT id, reset_req FROM users WHERE username=?", (f_u,)).fetchone()
                if user:
                    if user[1] == 2:
                        new_pass = st.text_input("Password Baru", type="password")
                        if st.button("UPDATE PASSWORD"):
                            conn.execute("UPDATE users SET password=?, reset_req=0 WHERE id=?", (hash_pw(new_pass), user[0]))
                            conn.commit()
                            st.success("Berhasil! Silakan Login.")
                    else:
                        conn.execute("UPDATE users SET reset_req=1 WHERE id=?", (user[0],))
                        conn.commit()
                        st.info("📩 Permintaan terkirim. Hubungi Admin.")
                else: st.error("User tidak ditemukan.")
        st.markdown('</div>', unsafe_allow_html=True)

# --- DASHBOARD & STATS ---
elif menu in ["Dashboard", "Dashboard Stats"]:
    st.header("📊 Dashboard Overview")
    if st.session_state.role == 'admin':
        c1, c2 = st.columns(2)
        c1.metric("Total Dokumen TTD", conn.execute("SELECT COUNT(*) FROM docs").fetchone()[0])
        c2.metric("Total User", conn.execute("SELECT COUNT(*) FROM users WHERE role='user'").fetchone()[0])
        st.subheader("📋 Aktivitas Terbaru")
        df_lat = pd.read_sql_query("SELECT docs.date, users.username, docs.doc_name FROM docs JOIN users ON docs.user_id = users.id ORDER BY docs.id DESC LIMIT 5", conn)
        st.table(df_lat)
    else:
        st.metric("Dokumen Saya", conn.execute("SELECT COUNT(*) FROM docs WHERE user_id=?", (st.session_state.user_id,)).fetchone()[0])
        st.info("Selamat bekerja! Gunakan menu di kiri untuk mengelola TTD Digital.")

# --- PROFIL SAYA ---
elif menu == "Profil Saya":
    st.header("👤 Manajemen Profil")
    u_data = conn.execute("SELECT full_name, emp_id, position, logo FROM users WHERE id=?", (st.session_state.user_id,)).fetchone()
    with st.form("prof_form"):
        fn = st.text_input("Nama Lengkap", value=u_data[0] or "")
        ei = st.text_input("Nomor ID Karyawan", value=u_data[1] or "")
        ps = st.text_input("Jabatan", value=u_data[2] or "")
        lg = st.file_uploader("Upload Logo Perusahaan", type=['png','jpg'])
        if st.form_submit_button("SIMPAN PROFIL"):
            l_blob = lg.read() if lg else u_data[3]
            conn.execute("UPDATE users SET full_name=?, emp_id=?, position=?, logo=? WHERE id=?", (fn, ei, ps, l_blob, st.session_state.user_id))
            conn.commit()
            st.session_state.full_name = fn
            st.success("Profil diperbarui!")
            st.rerun()

# --- GENERATOR QR ---
elif menu == "Buat QR TTD":
    st.header("📝 Buat Tanda Tangan QR")
    u_data = conn.execute("SELECT full_name, emp_id, position, logo FROM users WHERE id=?", (st.session_state.user_id,)).fetchone()
    if not u_data[0]: st.warning("Lengkapi profil dulu.")
    else:
        with st.form("qr_f"):
            d_no = st.text_input("Nomor Dokumen")
            d_nm = st.text_input("Nama Dokumen")
            rem = st.selectbox("Keterangan", ["Original", "Revisi"])
            pwd = st.text_input("Konfirmasi Password", type="password")
            if st.form_submit_button("GENERATE"):
                auth = conn.execute("SELECT password FROM users WHERE id=?", (st.session_state.user_id,)).fetchone()
                if check_pw(pwd, auth[0]):
                    ts = datetime.now().strftime("%H:%M:%S %d/%m/%Y")
                    h_val = hashlib.sha256(f"{u_data[0]}|{u_data[1]}|{u_data[2]}|{d_no}|{d_nm}".encode()).hexdigest()
                    qr_txt = f"SIGNER:{u_data[0]}\nID:{u_data[1]}\nPOS:{u_data[2]}\nDOC_NO:{d_no}\nDOC_NAME:{d_nm}\nTIME:{ts}\nHASH:{h_val}"
                    
                    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=10, border=4)
                    qr.add_data(qr_txt); qr.make(fit=True)
                    img = qr.make_image(fill_color="black", back_color="white").convert('RGB')
                    if u_data[3]:
                        logo = Image.open(io.BytesIO(u_data[3])).resize((img.size[0]//4, img.size[1]//4))
                        img.paste(logo, ((img.size[0]-logo.size[0])//2, (img.size[1]-logo.size[1])//2))
                    
                    st.image(img, width=250)
                    conn.execute("INSERT INTO docs (user_id, doc_no, doc_name, remarks, date, hash_val) VALUES (?,?,?,?,?,?)", (st.session_state.user_id, d_no, d_nm, rem, ts, h_val))
                    conn.commit()
                    buf = io.BytesIO(); img.save(buf, format="PNG")
                    st.download_button("Download QR", buf.getvalue(), f"TTD_{d_no}.png")
                else: st.error("Password Salah!")

# --- VERIFIKASI QR ---
elif menu == "Verifikasi QR":
    st.header("🔍 Validasi Dokumen")
    f = st.file_uploader("Upload QR", type=['png','jpg','jpeg'])
    if f:
        img = Image.open(f)
        data, _, _ = cv2.QRCodeDetector().detectAndDecode(cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR))
        if data:
            try:
                d = dict(l.split(":", 1) for l in data.split("\n"))
                if hashlib.sha256(f"{d['SIGNER']}|{d['ID']}|{d['POS']}|{d['DOC_NO']}|{d['DOC_NAME']}".encode()).hexdigest() == d['HASH']:
                    st.success("✅ VALID")
                    st.markdown(f'<div class="status-box"><p><b>Signed By:</b> {d["SIGNER"]} ({d["POS"]})</p><p><b>ID:</b> {d["ID"]}</p><p><b>Doc:</b> {d["DOC_NAME"]} / {d["DOC_NO"]}</p><p><b>On:</b> {d["TIME"]}</p></div>', unsafe_allow_html=True)
                else: st.error("🚨 MANIPULATED!")
            except: st.error("Format QR salah.")
        else: st.error("QR tidak terbaca.")

# --- BANTUAN & CHAT (FIX ERROR) ---
elif menu in ["Bantuan/Chat", "Chat Center"]:
    st.header("💬 Chat & Bantuan")
    target_id = None
    if st.session_state.role == 'admin':
        u_list = pd.read_sql_query("SELECT id, username FROM users WHERE role='user'", conn)
        if u_list.empty: st.info("Belum ada user.")
        else:
            sel_u = st.selectbox("Pilih User", u_list['username'])
            target_id = int(u_list[u_list['username'] == sel_u]['id'].values[0])
    else:
        target_id = conn.execute("SELECT id FROM users WHERE username='ADMIN'").fetchone()[0]

    if target_id:
        msgs = pd.read_sql_query(f"SELECT * FROM messages WHERE (sender_id={st.session_state.user_id} AND receiver_id={target_id}) OR (sender_id={target_id} AND receiver_id={st.session_state.user_id}) ORDER BY id ASC", conn)
        for _, m in msgs.iterrows():
            is_me = m['sender_id'] == st.session_state.user_id
            st.markdown(f'<div style="text-align: {"right" if is_me else "left"};"><div style="display: inline-block; background: {"#dcf8c6" if is_me else "#fff"}; padding: 10px; border-radius: 10px; margin: 5px; color: black; box-shadow: 0 1px 2px rgba(0,0,0,0.1);"><b>{m["time"]}</b><br>{m["msg"]}</div></div>', unsafe_allow_html=True)
        
        with st.form("chat_f", clear_on_submit=True):
            col_in, col_bt = st.columns([4, 1])
            txt = col_in.text_input("Pesan...")
            if col_bt.form_submit_button("KIRIM"):
                if txt:
                    conn.execute("INSERT INTO messages (sender_id, receiver_id, msg, time) VALUES (?,?,?,?)", (st.session_state.user_id, target_id, txt, datetime.now().strftime("%H:%M")))
                    conn.commit(); st.rerun()

# --- ADMIN: APPROVE & RESET ---
elif menu == "Approve Akun":
    st.header("👥 Approval")
    for _, r in pd.read_sql_query("SELECT id, username FROM users WHERE status='pending'", conn).iterrows():
        c1, c2 = st.columns([3, 1])
        c1.write(r['username'])
        if c2.button("APPROVE", key=r['id']):
            conn.execute("UPDATE users SET status='active' WHERE id=?", (r['id'],)); conn.commit(); st.rerun()

elif menu == "Reset Password":
    st.header("🔑 Reset Request")
    for _, r in pd.read_sql_query("SELECT id, username FROM users WHERE reset_req=1", conn).iterrows():
        c1, c2 = st.columns([3, 1])
        c1.write(r['username'])
        if c2.button("IZINKAN", key=f"rs_{r['id']}"):
            conn.execute("UPDATE users SET reset_req=2 WHERE id=?", (r['id'],)); conn.commit(); st.rerun()

elif menu == "Ganti Background":
    st.header("⚙️ Settings")
    f_bg = st.file_uploader("Upload Background", type=['jpg','png'])
    if st.button("TERAPKAN"):
        if f_bg:
            conn.execute("DELETE FROM settings"); conn.execute("INSERT INTO settings (id, bg_img) VALUES (1, ?)", (f_bg.read(),)); conn.commit(); st.success("Berhasil!"); st.rerun()

elif menu == "History Dokumen":
    st.header("📂 History")
    st.dataframe(pd.read_sql_query(f"SELECT date as Tanggal, doc_name as Nama, doc_no as No, remarks as Status FROM docs WHERE user_id={st.session_state.user_id}", conn), use_container_width=True)

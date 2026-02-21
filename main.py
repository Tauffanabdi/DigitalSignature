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

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="e-Signature Pro - Admin System", page_icon="🔐", layout="wide")

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect("signature_pro_v2.db", check_same_thread=False)
    cursor = conn.cursor()
    # Tabel User (Update: Status & Reset Request)
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
    
    # Tabel Chat
    cursor.execute('''CREATE TABLE IF NOT EXISTS messages (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        sender_id INTEGER, receiver_id INTEGER, 
                        msg TEXT, time TEXT)''')
    
    # Tabel Settings (Untuk Background Dashboard)
    cursor.execute('''CREATE TABLE IF NOT EXISTS settings (id INTEGER PRIMARY KEY, bg_img BLOB)''')
    
    # Buat Akun ADMIN jika belum ada
    admin_exists = cursor.execute("SELECT * FROM users WHERE username='ADMIN'").fetchone()
    if not admin_exists:
        pw = bcrypt.hashpw("Admin99".encode(), bcrypt.gensalt()).decode()
        cursor.execute("INSERT INTO users (username, password, status, role, full_name) VALUES (?,?,?,?,?)", 
                       ('ADMIN', pw, 'active', 'admin', 'Super Admin'))
    
    conn.commit()
    return conn

conn = init_db()

# --- FUNGSI PEMBANTU ---
def get_bg_image():
    res = conn.execute("SELECT bg_img FROM settings WHERE id=1").fetchone()
    if res and res[0]:
        b64 = base64.b64encode(res[0]).decode()
        return f"data:image/png;base64,{b64}"
    return None

def hash_pw(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def check_pw(password, hashed):
    return bcrypt.checkpw(password.encode(), hashed.encode())

# --- CSS CUSTOM ---
bg_url = get_bg_image()
bg_css = f"""
    <style>
    .stApp {{
        background: {f'url({bg_url})' if bg_url else '#f5f7f9'};
        background-size: cover;
    }}
    .status-box {{ 
        padding: 20px; border-radius: 10px; border-left: 5px solid #28a745; 
        background-color: #ffffff; color: #000000 !important; box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }}
    .status-box b, .status-box p {{ color: #000000 !important; }}
    .chat-user {{ background: #e3f2fd; padding: 10px; border-radius: 10px; margin: 5px 0; color: black; }}
    .chat-admin {{ background: #f1f8e9; padding: 10px; border-radius: 10px; margin: 5px 0; text-align: right; color: black; }}
    </style>
"""
st.markdown(bg_css, unsafe_allow_html=True)

# --- SESSION STATE ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'user_id' not in st.session_state: st.session_state.user_id = None
if 'role' not in st.session_state: st.session_state.role = 'user'

# --- UI: SIDEBAR ---
if st.session_state.logged_in:
    with st.sidebar:
        st.title("🛡️ e-Signature Pro")
        st.write(f"Logged in as: **{st.session_state.username}**")
        
        if st.session_state.role == 'admin':
            menu = st.radio("Admin Panel", ["Dashboard Stats", "Approve Users", "Reset Requests", "Chat Center", "Settings"])
        else:
            menu = st.radio("User Menu", ["Dashboard", "Generator QR", "Validasi QR", "History", "Profil", "Hubungi Admin"])
            
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.rerun()
else:
    menu = "Login"

# --- HALAMAN LOGIN & REGISTER ---
if menu == "Login":
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.title("🔐 Access Portal")
        tab1, tab2, tab3 = st.tabs(["Login", "Register", "Lupa Password"])
        
        with tab1:
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            if st.button("Masuk"):
                res = conn.execute("SELECT id, password, status, role, username FROM users WHERE username=?", (u,)).fetchone()
                if res:
                    if res[2] == 'pending':
                        st.warning("⚠️ Akun Anda belum disetujui oleh Admin. Mohon tunggu.")
                    elif check_pw(p, res[1]):
                        st.session_state.logged_in = True
                        st.session_state.user_id = res[0]
                        st.session_state.role = res[3]
                        st.session_state.username = res[4]
                        st.success("Berhasil Masuk!")
                        st.rerun()
                    else: st.error("Password Salah")
                else: st.error("User tidak ditemukan")

        with tab2:
            new_u = st.text_input("Buat Username")
            new_p = st.text_input("Buat Password", type="password")
            if st.button("Daftar"):
                try:
                    conn.execute("INSERT INTO users (username, password, status, role) VALUES (?,?,'pending','user')", 
                                 (new_u, hash_pw(new_p)))
                    conn.commit()
                    st.info("✅ Registrasi Berhasil! Menunggu konfirmasi Admin untuk aktif.")
                except: st.error("Username sudah ada.")

        with tab3:
            st.subheader("Permintaan Reset Password")
            reset_u = st.text_input("Masukkan Username Anda")
            if st.button("Ajukan Reset"):
                user = conn.execute("SELECT id, reset_req FROM users WHERE username=?", (reset_u,)).fetchone()
                if user:
                    if user[1] == 2: # Status 2 = Disetujui Admin
                        new_pass = st.text_input("Password Baru", type="password", key="newpw")
                        if st.button("Update Password"):
                            conn.execute("UPDATE users SET password=?, reset_req=0 WHERE id=?", (hash_pw(new_pass), user[0]))
                            conn.commit()
                            st.success("Password berhasil diganti! Silakan login.")
                    else:
                        conn.execute("UPDATE users SET reset_req=1 WHERE id=?", (user[0],))
                        conn.commit()
                        st.warning("Permintaan terkirim. Menunggu konfirmasi Admin agar Anda bisa input password baru.")
                else: st.error("User tidak ditemukan.")

# --- HALAMAN ADMIN: APPROVE USERS ---
elif menu == "Approve Users":
    st.title("👥 Persetujuan Akun Baru")
    users = pd.read_sql_query("SELECT id, username, status FROM users WHERE status='pending'", conn)
    if users.empty:
        st.write("Tidak ada antrian persetujuan.")
    else:
        for i, row in users.iterrows():
            col1, col2 = st.columns([3,1])
            col1.write(f"Username: **{row['username']}**")
            if col2.button(f"Approve {row['username']}", key=row['id']):
                conn.execute("UPDATE users SET status='active' WHERE id=?", (row['id'],))
                conn.commit()
                st.success(f"Akun {row['username']} diaktifkan!")
                st.rerun()

# --- HALAMAN ADMIN: RESET REQUESTS ---
elif menu == "Reset Requests":
    st.title("🔑 Permintaan Reset Password")
    reqs = pd.read_sql_query("SELECT id, username FROM users WHERE reset_req=1", conn)
    if reqs.empty:
        st.write("Tidak ada permintaan reset.")
    else:
        for i, row in reqs.iterrows():
            col1, col2 = st.columns([3,1])
            col1.write(f"User **{row['username']}** ingin reset password.")
            if col2.button("Izinkan Reset", key=f"res_{row['id']}"):
                conn.execute("UPDATE users SET reset_req=2 WHERE id=?", (row['id'],))
                conn.commit()
                st.success("User sekarang diizinkan mengganti password di halaman Login.")

# --- HALAMAN ADMIN: STATS ---
elif menu == "Dashboard Stats":
    st.title("📊 Statistik Sistem")
    total_docs = conn.execute("SELECT COUNT(*) FROM docs").fetchone()[0]
    total_users = conn.execute("SELECT COUNT(*) FROM users WHERE role='user'").fetchone()[0]
    
    c1, c2 = st.columns(2)
    c1.metric("Total Dokumen TTD", total_docs)
    c2.metric("Total User Terdaftar", total_users)
    
    st.subheader("Aktivitas Terakhir")
    recent = pd.read_sql_query("""SELECT docs.date, users.username, docs.doc_name 
                                  FROM docs JOIN users ON docs.user_id = users.id 
                                  ORDER BY docs.id DESC LIMIT 10""", conn)
    st.table(recent)

# --- HALAMAN USER: HUBUNGI ADMIN & CHAT CENTER ---
elif menu in ["Hubungi Admin", "Chat Center"]:
    st.title("💬 Pusat Bantuan & Chat")
    
    if st.session_state.role == 'admin':
        # Admin View
        user_list = pd.read_sql_query("SELECT id, username FROM users WHERE role='user'", conn)
        target_user = st.selectbox("Pilih User untuk Chat", user_list['username'])
        target_id = user_list[user_list['username'] == target_user]['id'].values[0]
    else:
        # User View
        target_id = conn.execute("SELECT id FROM users WHERE username='ADMIN'").fetchone()[0]

    # Load Messages
    msgs = pd.read_sql_query(f"""SELECT * FROM messages WHERE 
                                (sender_id={st.session_state.user_id} AND receiver_id={target_id}) OR 
                                (sender_id={target_id} AND receiver_id={st.session_state.user_id}) 
                                ORDER BY id ASC""", conn)
    
    for _, m in msgs.iterrows():
        div_class = "chat-admin" if m['sender_id'] == st.session_state.user_id else "chat-user"
        st.markdown(f'<div class="{div_class}">{m['msg']}<br><small>{m['time']}</small></div>', unsafe_allow_html=True)
    
    with st.form("send_chat"):
        txt = st.text_input("Ketik pesan...")
        if st.form_submit_button("Kirim"):
            now = datetime.now().strftime("%H:%M")
            conn.execute("INSERT INTO messages (sender_id, receiver_id, msg, time) VALUES (?,?,?,?)", 
                         (st.session_state.user_id, target_id, txt, now))
            conn.commit()
            st.rerun()

# --- HALAMAN ADMIN: SETTINGS (BACKGROUND) ---
elif menu == "Settings":
    st.title("⚙️ Pengaturan Aplikasi")
    new_bg = st.file_uploader("Upload Background Dashboard (PNG/JPG)", type=['png','jpg','jpeg'])
    if st.button("Update Background"):
        if new_bg:
            blob = new_bg.read()
            conn.execute("DELETE FROM settings")
            conn.execute("INSERT INTO settings (id, bg_img) VALUES (1, ?)", (blob,))
            conn.commit()
            st.success("Background diperbarui! Refresh halaman.")
            st.rerun()

# --- BAGIAN GENERATOR QR & VALIDASI (LOGIKA LAMA TETAP SAMA) ---
elif menu == "Generator QR":
    st.title("📝 Buat Tanda Tangan Digital")
    u_data = conn.execute("SELECT full_name, emp_id, position, logo FROM users WHERE id=?", (st.session_state.user_id,)).fetchone()
    
    if not u_data[0]:
        st.warning("Mohon lengkapi profil Anda di menu Profil.")
    else:
        with st.container():
            col1, col2 = st.columns(2)
            with col1:
                doc_no = st.text_input("Nomor Dokumen")
                doc_name = st.text_input("Nama Dokumen")
            with col2:
                remarks = st.selectbox("Keterangan", ["Original", "Revisi"])
                confirm_p = st.text_input("Konfirmasi Password", type="password")
            
            if st.button("Generate & Sign QR"):
                auth = conn.execute("SELECT password FROM users WHERE id=?", (st.session_state.user_id,)).fetchone()
                if check_pw(confirm_p, auth[0]):
                    ts = datetime.now().strftime("%H:%M:%S %d/%m/%Y")
                    raw = f"{u_data[0]}|{u_data[1]}|{u_data[2]}|{doc_no}|{doc_name}"
                    h_val = hashlib.sha256(raw.encode()).hexdigest()
                    
                    # LOGIKA GENERATE QR DENGAN LOGO (Sama seperti sebelumnya)
                    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=10, border=4)
                    qr.add_data(f"SIGNER:{u_data[0]}\nID:{u_data[1]}\nPOS:{u_data[2]}\nDOC_NO:{doc_no}\nDOC_NAME:{doc_name}\nTIME:{ts}\nHASH:{h_val}")
                    qr.make(fit=True)
                    img_qr = qr.make_image(fill_color="black", back_color="white").convert('RGB')
                    
                    if u_data[3]: # Jika ada logo
                        logo = Image.open(io.BytesIO(u_data[3]))
                        logo = logo.resize((img_qr.size[0]//4, img_qr.size[1]//4))
                        pos = ((img_qr.size[0]-logo.size[0])//2, (img_qr.size[1]-logo.size[1])//2)
                        img_qr.paste(logo, pos)
                    
                    st.image(img_qr, width=250)
                    conn.execute("INSERT INTO docs (user_id, doc_no, doc_name, remarks, date, hash_val) VALUES (?,?,?,?,?,?)",
                                 (st.session_state.user_id, doc_no, doc_name, remarks, ts, h_val))
                    conn.commit()
                    
                    buf = io.BytesIO()
                    img_qr.save(buf, format="PNG")
                    st.download_button("Download QR Code", buf.getvalue(), f"QR_{doc_no}.png")
                else: st.error("Password Salah")

elif menu == "Validasi QR":
    st.title("🔍 Verifikasi Keaslian QR")
    file = st.file_uploader("Upload QR", type=['png','jpg','jpeg'])
    if file:
        import numpy as np
        import cv2
        img = Image.open(file)
        opencv_img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        data, _, _ = cv2.QRCodeDetector().detectAndDecode(opencv_img)
        if data:
            try:
                d = dict(line.split(":", 1) for line in data.split("\n"))
                raw = f"{d['SIGNER']}|{d['ID']}|{d['POS']}|{d['DOC_NO']}|{d['DOC_NAME']}"
                if hashlib.sha256(raw.encode()).hexdigest() == d['HASH']:
                    st.success("✅ VALID")
                    st.markdown(f"""<div class="status-box">
                        <b>Signed By:</b> {d['SIGNER']} ({d['POS']})<br>
                        <b>Employee ID:</b> {d['ID']}<br>
                        <b>Document:</b> {d['DOC_NAME']} / {d['DOC_NO']}<br>
                        <b>Timestamp:</b> {d['TIME']}</div>""", unsafe_allow_html=True)
                else: st.error("🚨 MANIPULATED")
            except: st.error("Format Salah")

elif menu == "Profil":
    st.title("👤 Profil")
    user_data = conn.execute("SELECT full_name, emp_id, position, logo FROM users WHERE id=?", (st.session_state.user_id,)).fetchone()
    with st.form("p_form"):
        name = st.text_input("Nama", value=user_data[0] or "")
        eid = st.text_input("No. ID", value=user_data[1] or "")
        pos = st.text_input("Jabatan", value=user_data[2] or "")
        uploaded_logo = st.file_uploader("Upload Logo", type=['png','jpg'])
        if st.form_submit_button("Simpan"):
            logo_blob = uploaded_logo.read() if uploaded_logo else user_data[3]
            conn.execute("UPDATE users SET full_name=?, emp_id=?, position=?, logo=? WHERE id=?", (name, eid, pos, logo_blob, st.session_state.user_id))
            conn.commit()
            st.success("Tersimpan!")

elif menu == "History":
    st.title("📂 Riwayat")
    df = pd.read_sql_query(f"SELECT date, doc_name, doc_no, remarks FROM docs WHERE user_id={st.session_state.user_id}", conn)
    st.dataframe(df, use_container_width=True)

elif menu == "Dashboard":
    st.title(f"Selamat Datang, {st.session_state.username}")
    my_docs = conn.execute("SELECT COUNT(*) FROM docs WHERE user_id=?", (st.session_state.user_id,)).fetchone()[0]
    st.metric("Dokumen Saya", my_docs)

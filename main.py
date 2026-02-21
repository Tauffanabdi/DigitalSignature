import streamlit as st
import sqlite3
import hashlib
import qrcode
import pandas as pd
import bcrypt
from PIL import Image, ImageOps, ImageDraw
from datetime import datetime
import io
import os

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="e-Signature Pro", page_icon="🔐", layout="wide")

# Custom CSS untuk UI Premium
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #007bff; color: white; }
    .stTextInput>div>div>input { border-radius: 5px; }
    .status-box { padding: 20px; border-radius: 10px; border-left: 5px solid #007bff; background-color: white; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
    </style>
    """, unsafe_allow_html=True)

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect("signature_pro.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE, password TEXT,
                        full_name TEXT, emp_id TEXT, position TEXT, logo BLOB)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS docs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER, doc_no TEXT, doc_name TEXT, 
                        remarks TEXT, date TEXT, hash_val TEXT)''')
    conn.commit()
    return conn

conn = init_db()

# --- FUNGSI LOGIKA ---
def hash_password(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def check_password(password, hashed):
    return bcrypt.checkpw(password.encode(), hashed.encode())

def generate_qr_with_logo(data, logo_bytes):
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=10, border=4)
    qr.add_data(data)
    qr.make(fit=True)
    img_qr = qr.make_image(fill_color="black", back_color="white").convert('RGB')

    if logo_bytes:
        logo = Image.open(io.BytesIO(logo_bytes))
        # Resize logo
        base_width = img_qr.size[0] // 4
        w_percent = (base_width / float(logo.size[0]))
        h_size = int((float(logo.size[1]) * float(w_percent)))
        logo = logo.resize((base_width, h_size), Image.Resampling.LANCZOS)
        
        # Tempel di tengah
        pos = ((img_qr.size[0] - logo.size[0]) // 2, (img_qr.size[1] - logo.size[1]) // 2)
        img_qr.paste(logo, pos)
    
    return img_qr

# --- SESSION STATE ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_id' not in st.session_state:
    st.session_state.user_id = None

# --- UI: SIDEBAR NAVIGATION ---
if st.session_state.logged_in:
    with st.sidebar:
        st.title("🛡️ e-Signature")
        st.write(f"Welcome back!")
        menu = st.radio("Main Menu", ["Dashboard", "Generator QR", "Validasi QR", "Database Dokumen", "Profil Saya"])
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.rerun()
else:
    menu = "Login"

# --- HALAMAN LOGIN & REGISTER ---
if menu == "Login":
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        tab1, tab2 = st.tabs(["Login", "Register"])
        
        with tab1:
            st.subheader("Login ke Sistem")
            u = st.text_input("Username", key="l_user")
            p = st.text_input("Password", type="password", key="l_pass")
            if st.button("Sign In"):
                res = conn.execute("SELECT id, password FROM users WHERE username=?", (u,)).fetchone()
                if res and check_password(p, res[1]):
                    st.session_state.logged_in = True
                    st.session_state.user_id = res[0]
                    st.success("Login Berhasil!")
                    st.rerun()
                else:
                    st.error("Username/Password Salah")

        with tab2:
            st.subheader("Buat Akun Baru")
            new_u = st.text_input("Username Baru")
            new_p = st.text_input("Password Baru", type="password")
            if st.button("Daftar sekarang"):
                try:
                    conn.execute("INSERT INTO users (username, password) VALUES (?,?)", (new_u, hash_password(new_p)))
                    conn.commit()
                    st.success("Berhasil! Silakan Login.")
                except:
                    st.error("Username sudah terdaftar")

# --- HALAMAN PROFIL ---
elif menu == "Profil Saya":
    st.title("👤 Pengaturan Profil")
    user_data = conn.execute("SELECT full_name, emp_id, position, logo FROM users WHERE id=?", (st.session_state.user_id,)).fetchone()
    
    with st.form("profile_form"):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Nama Lengkap", value=user_data[0] or "")
            eid = st.text_input("No. ID Karyawan", value=user_data[1] or "")
        with col2:
            pos = st.text_input("Jabatan", value=user_data[2] or "")
            uploaded_logo = st.file_uploader("Upload Logo Perusahaan (PNG/JPG)", type=['png', 'jpg', 'jpeg'])
        
        if st.form_submit_button("Simpan Perubahan"):
            logo_blob = uploaded_logo.read() if uploaded_logo else user_data[3]
            conn.execute("UPDATE users SET full_name=?, emp_id=?, position=?, logo=? WHERE id=?", 
                         (name, eid, pos, logo_blob, st.session_state.user_id))
            conn.commit()
            st.success("Profil diperbarui!")
            st.rerun()

# --- HALAMAN GENERATOR ---
elif menu == "Generator QR":
    st.title("📝 Buat Tanda Tangan Digital")
    u_data = conn.execute("SELECT full_name, emp_id, position, logo FROM users WHERE id=?", (st.session_state.user_id,)).fetchone()
    
    if not u_data[0]:
        st.warning("Mohon lengkapi profil Anda terlebih dahulu.")
    else:
        with st.container():
            col1, col2 = st.columns(2)
            with col1:
                doc_no = st.text_input("Nomor Dokumen")
                doc_name = st.text_input("Nama Dokumen (Contoh: JSA)")
            with col2:
                remarks = st.selectbox("Keterangan", ["Original", "Revisi"])
                confirm_p = st.text_input("Konfirmasi Password", type="password")
            
            if st.button("Generate QR Code"):
                auth = conn.execute("SELECT password FROM users WHERE id=?", (st.session_state.user_id,)).fetchone()
                if check_password(confirm_p, auth[0]):
                    ts = datetime.now().strftime("%H:%M:%S %d/%m/%Y")
                    # Logic Hashing
                    raw = f"{u_data[0]}|{u_data[1]}|{u_data[2]}|{doc_no}|{doc_name}"
                    h_val = hashlib.sha256(raw.encode()).hexdigest()
                    
                    qr_text = f"SIGNER:{u_data[0]}\nID:{u_data[1]}\nPOS:{u_data[2]}\nDOC_NO:{doc_no}\nDOC_NAME:{doc_name}\nTIME:{ts}\nHASH:{h_val}"
                    
                    qr_img = generate_qr_with_logo(qr_text, u_data[3])
                    
                    # Tampilkan
                    st.image(qr_img, caption="Preview TTD Digital", width=300)
                    
                    # Simpan ke DB
                    conn.execute("INSERT INTO docs (user_id, doc_no, doc_name, remarks, date, hash_val) VALUES (?,?,?,?,?,?)",
                                 (st.session_state.user_id, doc_no, doc_name, remarks, ts, h_val))
                    conn.commit()
                    
                    # Download button
                    buf = io.BytesIO()
                    qr_img.save(buf, format="PNG")
                    st.download_button("Download QR Code", buf.getvalue(), f"QR_{doc_no}.png", "image/png")
                else:
                    st.error("Password Konfirmasi Salah!")

# --- HALAMAN VALIDASI ---
elif menu == "Validasi QR":
    st.title("🔍 Verifikasi Keaslian QR")
    file = st.file_uploader("Upload QR Code untuk di-scan", type=['png', 'jpg', 'jpeg'])
    
    if file:
        img = Image.open(file)
        import numpy as np
        import cv2
        opencv_img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        detector = cv2.QRCodeDetector()
        data, _, _ = detector.detectAndDecode(opencv_img)
        
        if data:
            try:
                d = dict(line.split(":", 1) for line in data.split("\n"))
                # Re-check Hash
                raw = f"{d['SIGNER']}|{d['ID']}|{d['POS']}|{d['DOC_NO']}|{d['DOC_NAME']}"
                calc_h = hashlib.sha256(raw.encode()).hexdigest()
                
                if calc_h == d['HASH']:
                    st.success("✅ QR CODE VALID & TERVERIFIKASI")
                    st.markdown(f"""
                    <div class="status-box">
                    <b>Signed By:</b> {d['SIGNER']} ({d['POS']})<br>
                    <b>Employee ID:</b> {d['ID']}<br>
                    <b>Document:</b> {d['DOC_NAME']} / {d['DOC_NO']}<br>
                    <b>Timestamp:</b> {d['TIME']}
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.error("🚨 QR CODE MANIPULATED / INVALID")
            except:
                st.error("Format QR tidak dikenali.")
        else:
            st.error("QR Code tidak terbaca.")

# --- HALAMAN DATABASE ---
elif menu == "Database Dokumen":
    st.title("📂 Riwayat Dokumen")
    df = pd.read_sql_query(f"SELECT date, doc_name, doc_no, remarks FROM docs WHERE user_id={st.session_state.user_id}", conn)
    st.dataframe(df, use_container_width=True)
import streamlit as st
import pandas as pd
import requests
import os
import re
import json
from datetime import datetime
from users import USER_DB
from ultralytics import YOLO 
from PIL import Image, ImageOps

# --- KONFIGURASI ---
TOKEN = "8765480491:AAGI8Q8qi5ruWWdHZBSrNdq1j-NkUWa9YJc"
CHAT_ID = "-1003811491120"

st.set_page_config(page_title="QC MBI - Checker Center", layout="wide")

# --- LOAD MODEL AI ---
@st.cache_resource
def load_ai_model():
    if os.path.exists("best.pt"):
        return YOLO("best.pt")
    return None

model_ai = load_ai_model()

# --- INISIALISASI SESSION STATE ---
if 'font_size' not in st.session_state: st.session_state['font_size'] = 16
if 'auth' not in st.session_state:
    params = st.query_params
    if "u" in params and params["u"] in USER_DB:
        st.session_state['auth'], st.session_state['user'] = True, params["u"].capitalize()
    else: st.session_state['auth'] = False

if 'user' not in st.session_state: st.session_state['user'] = ""
if 'page' not in st.session_state: st.session_state['page'] = "search"
if 'selected_so' not in st.session_state: st.session_state['selected_so'] = None
if 'qc_drafts' not in st.session_state: st.session_state['qc_drafts'] = {}

# --- STYLING CSS ---
st.markdown(f"""
    <style>
    footer {{visibility: hidden !important;}}
    .stAppDeployButton {{ display: none !important; }}
    html, body, [data-testid="stWidgetLabel"] p, .stMarkdown p, .stSelectbox label, label {{
        font-size: {st.session_state['font_size']}px !important;
    }}
    div[data-testid="stExpander"] {{ border: 1px solid #ddd; border-radius: 8px; margin-bottom: -15px !important; }}
    .ai-box {{ padding: 15px; border-radius: 8px; border: 2px dashed #007bff; background-color: #f8f9fa; margin-bottom: 15px; }}
    .status-ok {{ background-color: #d4edda !important; border-left: 10px solid #28a745; margin-bottom: -15px !important; }}
    .status-err {{ background-color: #f8d7da !important; border-left: 10px solid #dc3545; margin-bottom: -15px !important; }}
    .status-pending {{ background-color: #ffffff !important; border-left: 10px solid #6c757d; margin-bottom: -15px !important; }}
    </style>
""", unsafe_allow_html=True)

# --- FUNGSI CORE ---
def update_password_db(u, p):
    USER_DB[u.lower()] = p
    with open("users.py", "w") as f: f.write(f"USER_DB = {json.dumps(USER_DB, indent=4)}")

def get_user_photo(u):
    path = f"photos/{u.lower()}.png"
    return path if os.path.exists(path) else None

def simpan_draft_ke_file(so, data):
    if not os.path.exists("drafts"): os.makedirs("drafts")
    with open(f"drafts/draft_{so}.json", "w") as f: json.dump(data, f)

def muat_draft_dari_file(so):
    path = f"drafts/draft_{so}.json"
    if os.path.exists(path):
        try:
            with open(path, "r") as f: return json.load(f)
        except: return {}
    return {}

def hapus_file_draft(so):
    path = f"drafts/draft_{so}.json"
    if os.path.exists(path): os.remove(path)

def ambil_semua_lock():
    locks = {}
    if os.path.exists("locks.txt"):
        try:
            with open("locks.txt", "r") as f:
                for line in f:
                    if "|" in line: s, p = line.strip().split("|"); locks[s] = p
        except: pass
    return locks

def kunci_so(so, p):
    locks = ambil_semua_lock()
    if so not in locks:
        with open("locks.txt", "a") as f: f.write(f"{so}|{p}\n"); f.flush()

def buka_kunci_so(so):
    locks = ambil_semua_lock()
    if so in locks:
        del locks[so]
        with open("locks.txt", "w") as f:
            for s, p in locks.items(): f.write(f"{s}|{p}\n"); f.flush()

def ambil_daftar_selesai():
    if os.path.exists("selesai.txt"):
        with open("selesai.txt", "r") as f: return [line.strip() for line in f.readlines()]
    return []

def simpan_rekap_data(l):
    if not os.path.exists("rekap_qc.csv"): pd.DataFrame(l).to_csv("rekap_qc.csv", index=False)
    else: pd.DataFrame(l).to_csv("rekap_qc.csv", mode='a', header=False, index=False)

def simpan_so_selesai(so):
    with open("selesai.txt", "a" if os.path.exists("selesai.txt") else "w") as f: 
        f.write(so.strip() + "\n"); f.flush()
    buka_kunci_so(so); hapus_file_draft(so)
    if so in st.session_state['qc_drafts']: del st.session_state['qc_drafts'][so]

def kirim_telegram(m):
    try: 
        requests.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={m}", timeout=5)
    except: 
        pass

# --- FUNGSI PREDIKSI AI ---
def prediksi_barang(img_buffer, kode_target):
    if model_ai is None:
        return None, 0, "Model AI (best.pt) tidak ditemukan"
    img = Image.open(img_buffer)
    img = ImageOps.exif_transpose(img) # Memperbaiki rotasi foto HP
    results = model_ai.predict(img)
    top_result = results[0].probs
    class_index = top_result.top1
    confidence = top_result.top1conf.item()
    detected_code = results[0].names[class_index]
    match = str(detected_code) == str(kode_target)
    return match, confidence, detected_code

# --- LOGIN ---
if not st.session_state['auth']:
    st.title("🔐 Login Checker MBI")
    u_in = st.text_input("Username").lower().strip()
    p_in = st.text_input("Password", type="password")
    if st.button("Masuk", use_container_width=True):
        if u_in in USER_DB and USER_DB[u_in] == p_in:
            st.session_state['auth'], st.session_state['user'] = True, u_in.capitalize()
            st.query_params["u"] = u_in; st.rerun()
        else: st.error("Username atau Password salah!")
else:
    is_admin = st.session_state['user'].lower() == "galang"
    with st.sidebar:
        photo = get_user_photo(st.session_state['user'])
        if photo: st.image(photo, width=100)
        st.title(f"👤 {st.session_state['user']}")
        m_list = ["Pemeriksaan QC", "Dashboard Monitoring", "⚙️ Pengaturan"] if is_admin else ["Pemeriksaan QC", "⚙️ Pengaturan"]
        menu = st.radio("Menu Utama", m_list)
        if st.sidebar.button("Log Out"):
            if st.session_state['selected_so']: buka_kunci_so(st.session_state['selected_so'])
            st.session_state['auth'] = False; st.query_params.clear(); st.rerun()

    if os.path.exists("data_so.csv"):
        df_master = pd.read_csv("data_so.csv")
        df_master.columns = df_master.columns.str.strip()
        c_so, c_cust, c_tgl = 'Nomor # Pesanan Penjualan', 'Pelanggan', 'Tanggal Pesanan Penjualan'
        c_qty, c_item, c_kd = 'Kuantitas', 'Nama Barang', 'Kode #'
        c_btch, c_exp = 'No Seri/Produksi', 'Tgl Kadaluarsa'
        df_master[c_so] = df_master[c_so].astype(str).str.strip()
        df_master[[c_so, c_cust, c_tgl]] = df_master[[c_so, c_cust, c_tgl]].ffill()
        df_master = df_master[df_master[c_item].notna()]
        selesai_list = ambil_daftar_selesai()

        if menu == "⚙️ Pengaturan":
            st.header("⚙️ Pengaturan Akun")
            st.session_state['font_size'] = st.slider("Ukuran Font", 12, 24, st.session_state['font_size'])
            st.subheader("🖼️ Update Foto Profil")
            up_f = st.file_uploader("Upload Foto", type=['png', 'jpg'])
            if up_f:
                if not os.path.exists("photos"): os.makedirs("photos")
                with open(f"photos/{st.session_state['user'].lower()}.png", "wb") as f: f.write(up_f.getbuffer())
                st.success("Foto Berhasil!"); st.rerun()

        elif menu == "Pemeriksaan QC":
            if st.session_state['page'] == "search":
                l_all = df_master[c_so].unique()
                l_aktif = sorted([s for s in l_all if s not in selesai_list])
                st.subheader("🎯 Cari Nomor SO")
                so_dipilih = st.selectbox("Pilih No SO:", l_aktif, index=None, placeholder="Ketik nomor SO...")
                if so_dipilih:
                    locks = ambil_semua_lock()
                    if so_dipilih in locks and locks[so_dipilih] != st.session_state['user']: st.error(f"🚫 Sedang dibuka oleh {locks[so_dipilih]}")
                    else:
                        kunci_so(so_dipilih, st.session_state['user'])
                        st.session_state['selected_so'], st.session_state['page'] = so_dipilih, "list_barang"
                        st.session_state['qc_drafts'][so_dipilih] = muat_draft_dari_file(so_dipilih); st.rerun()

            elif st.session_state['page'] == "list_barang":
                so_aktif = st.session_state['selected_so']
                if st.button("⬅️ Kembali"):
                    buka_kunci_so(so_aktif); st.session_state['selected_so'], st.session_state['page'] = None, "search"; st.rerun()
                
                df_f = df_master[df_master[c_so] == so_aktif].copy()
                st.info(f"📄 **SO:** {so_aktif} | 🏢 **Apotek:** {df_f.iloc[0][c_cust]}")

                v_all, l_final, draft = True, [], st.session_state['qc_drafts'].get(so_aktif, {})
                for idx, row in df_f.iterrows():
                    iid = str(row[c_kd]).strip(); target = int(float(row[c_qty]))
                    vq, vn, vt = draft.get(f"q_{iid}", 0), draft.get(f"n_{iid}", ""), draft.get(f"t_{iid}", False)
                    s_clp = "status-ok" if int(vq) == target else ("status-err" if int(vq) > 0 else "status-pending")
                    
                    st.markdown(f'<div class="{s_clp}">', unsafe_allow_html=True)
                    with st.expander(f"💊 {row[c_item]}", expanded=False):
                        # --- MODUL AI SCAN PALING STABIL ---
                        st.markdown('<div class="ai-box">', unsafe_allow_html=True)
                        st.write("🤖 **AI Visual Verification**")
                        # camera_input standar lebih ramah memori server
                        img_file = st.camera_input("Ambil Foto Barang", key=f"cam_{iid}")
                        
                        if img_file:
                            match, conf, d_code = prediksi_barang(img_file, iid)
                            if match: st.success(f"✅ SESUAI ({int(conf*100)}%)")
                            else: st.error(f"❌ SALAH BARANG! (Terdeteksi: {d_code})")
                        st.markdown('</div>', unsafe_allow_html=True)

                        ci, ct = st.columns([4, 1])
                        ci.write(f"**Code:** {iid} | **Qty SO:** {target}")
                        t_ui = ct.checkbox("📝 Note", key=f"t_{iid}", value=vt)
                        u_in = st.text_input("Input Fisik", key=f"q_{iid}", value="" if vq==0 else str(vq), placeholder="0")
                        
                        q_num = int(re.sub("[^0-9]", "", u_in)) if re.sub("[^0-9]", "", u_in) != "" else 0
                        n_ui = st.text_input("Catatan:", key=f"n_{iid}", value=vn) if t_ui else ""
                        
                        if draft.get(f"q_{iid}") != q_num or draft.get(f"n_{iid}") != n_ui:
                            draft.update({f"q_{iid}": q_num, f"n_{iid}": n_ui, f"t_{iid}": t_ui})
                            simpan_draft_ke_file(so_aktif, draft); st.rerun()
                        if q_num != target: v_all = False
                    st.markdown('</div>', unsafe_allow_html=True)
                    l_final.append({"Petugas": st.session_state['user'], "SO": so_aktif, "Kode": iid, "Qty_Fisik": q_num, "Note": n_ui})

                if st.button("✅ SELESAI & KIRIM", use_container_width=True, type="primary"):
                    if v_all:
                        simpan_rekap_data(l_final); simpan_so_selesai(so_aktif)
                        kirim_telegram(f"✅ QC SELESAI: {so_aktif} oleh {st.session_state['user']}")
                        st.session_state['page'] = "search"; st.balloons(); st.rerun()
                    else: st.error("Cek kembali jumlah barang!")
    else: st.error("data_so.csv tidak ditemukan.")

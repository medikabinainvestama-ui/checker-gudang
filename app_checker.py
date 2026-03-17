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

# --- KONFIGURASI TELEGRAM ---
TOKEN = "8765480491:AAGI8Q8qi5ruWWdHZBSrNdq1j-NkUWa9YJc"
CHAT_ID = "-1003811491120"

st.set_page_config(page_title="QC MBI - Checker Center", layout="wide")

# --- LOAD MODEL AI ---
@st.cache_resource
def load_ai_model():
    if os.path.exists("best.pt"):
        try: return YOLO("best.pt")
        except: return None
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
    table, thead, tbody, th, td {{ text-align: center !important; vertical-align: middle !important; }}
    .block-container {{ padding-top: 2rem !important; padding-bottom: 0rem !important; }}
    div[data-testid="stExpander"] {{ border: 1px solid #ddd; border-radius: 8px; margin-bottom: -15px !important; }}
    .metric-card {{
        background-color: #f0f2f6; padding: 15px; border-radius: 10px;
        text-align: center; border: 1px solid #e0e0e0; margin-top: 10px; margin-bottom: 10px;
    }}
    .status-ok {{ background-color: #d4edda !important; border-radius: 8px; border-left: 10px solid #28a745; margin-bottom: -15px !important; }}
    .status-err {{ background-color: #f8d7da !important; border-radius: 8px; border-left: 10px solid #dc3545; margin-bottom: -15px !important; }}
    .status-pending {{ background-color: #ffffff !important; border-radius: 8px; border-left: 10px solid #6c757d; margin-bottom: -15px !important; }}
    .ai-box {{ padding: 10px; border-radius: 5px; margin-bottom: 10px; border: 1px dashed #333; background-color: #f9f9f9; }}
    </style>
""", unsafe_allow_html=True)

# --- FUNGSI CORE ---
def simpan_draft_ke_file(so, data):
    if not os.path.exists("drafts"): os.makedirs("drafts")
    with open(f"drafts/draft_{so}.json", "w") as f: json.dump(data, f)

def muat_draft_dari_file(so):
    path = f"drafts/draft_{so}.json"
    if os.path.exists(path):
        try: with open(path, "r") as f: return json.load(f)
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
    try: requests.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={m}", timeout=5)
    except: pass

def prediksi_barang(img_buffer, kode_target):
    if model_ai is None: return None, 0, "Model AI tidak ditemukan"
    img = Image.open(img_buffer)
    img = ImageOps.exif_transpose(img)
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
            st.rerun()
        else: st.error("Username atau Password salah!")
else:
    is_admin = st.session_state['user'].lower() == "galang"
    with st.sidebar:
        st.title(f"👤 {st.session_state['user']}")
        menu = st.radio("Menu Utama", ["Pemeriksaan QC", "Dashboard Monitoring", "⚙️ Pengaturan"])
        if st.sidebar.button("Log Out"):
            if st.session_state['selected_so']: buka_kunci_so(st.session_state['selected_so'])
            st.session_state['auth'] = False; st.rerun()

    if os.path.exists("data_so.csv"):
        df_master = pd.read_csv("data_so.csv")
        df_master.columns = df_master.columns.str.strip()
        c_so, c_cust, c_tgl = 'Nomor # Pesanan Penjualan', 'Pelanggan', 'Tanggal Pesanan Penjualan'
        c_qty, c_item, c_kd = 'Kuantitas', 'Nama Barang', 'Kode #'
        df_master[c_so] = df_master[c_so].astype(str).str.strip()
        df_master[[c_so, c_cust, c_tgl]] = df_master[[c_so, c_cust, c_tgl]].ffill()
        df_master = df_master[df_master[c_item].notna()]
        selesai_list = ambil_daftar_selesai()

        if menu == "Pemeriksaan QC":
            if st.session_state['page'] == "search":
                l_all = df_master[c_so].unique()
                l_aktif = sorted([s for s in l_all if s not in selesai_list])
                st.subheader("🎯 Cari Nomor SO")
                
                if is_admin:
                    with st.expander("🛠️ ADMIN TOOLS (Galang Only)"):
                        s_adm = st.selectbox("Action SO:", l_aktif)
                        if s_adm:
                            ca, cb = st.columns(2)
                            if ca.button("🔓 Unlock"): buka_kunci_so(s_adm); st.rerun()
                            if cb.button("♻️ Reset"): hapus_file_draft(s_adm); st.rerun()

                so_dipilih = st.selectbox("Pilih No SO:", l_aktif, index=None, placeholder="Ketik nomor SO...")
                st.divider()
                m1, m2, m3 = st.columns(3)
                m1.markdown(f'<div class="metric-card">📦 <b>Total SO</b><br>{len(l_all)}</div>', unsafe_allow_html=True)
                m2.markdown(f'<div class="metric-card">⏳ <b>Belum QC</b><br>{len(l_aktif)}</div>', unsafe_allow_html=True)
                m3.markdown(f'<div class="metric-card">✅ <b>Selesai</b><br>{len(selesai_list)}</div>', unsafe_allow_html=True)
                
                if so_dipilih:
                    kunci_so(so_dipilih, st.session_state['user'])
                    st.session_state['selected_so'], st.session_state['page'] = so_dipilih, "list_barang"
                    st.session_state['qc_drafts'][so_dipilih] = muat_draft_dari_file(so_dipilih); st.rerun()

            elif st.session_state['page'] == "list_barang":
                so_aktif = st.session_state['selected_so']
                if st.button("⬅️ Kembali ke Pencarian"):
                    buka_kunci_so(so_aktif); st.session_state['selected_so'], st.session_state['page'] = None, "search"; st.rerun()
                
                df_f = df_master[df_master[c_so] == so_aktif].copy()
                
                # --- RINCIAN SO (SESUAI PERMINTAAN ANDA) ---
                nama_apotek = df_f.iloc[0][c_cust]
                tgl_so = df_f.iloc[0][c_tgl]
                jml_jenis = len(df_f)
                jml_qty = int(pd.to_numeric(df_f[c_qty]).sum())

                st.markdown(f"""
                ### 📋 Rincian SO: {so_aktif}
                * 🏢 **Nama Apotek:** {nama_apotek}
                * 📅 **Tanggal SO:** {tgl_so}
                * 💊 **Jumlah Jenis Barang:** {jml_jenis} Item
                * 🔢 **Jumlah Qty Total:** {jml_qty} Pcs
                """, unsafe_allow_html=True)
                
                st.divider()

                v_all, l_final, draft = True, [], st.session_state['qc_drafts'].get(so_aktif, {})
                for idx, row in df_f.iterrows():
                    iid = str(row[c_kd]).strip(); target = int(float(row[c_qty]))
                    vq, vn = draft.get(f"q_{iid}", 0), draft.get(f"n_{iid}", "")
                    s_clp = "status-ok" if int(vq) == target else ("status-err" if int(vq) > 0 else "status-pending")
                    
                    st.markdown(f'<div class="{s_clp}">', unsafe_allow_html=True)
                    with st.expander(f"💊 {row[c_item]}", expanded=False):
                        st.markdown('<div class="ai-box"><b>🤖 AI Visual Checker</b>', unsafe_allow_html=True)
                        cam_img = st.file_uploader(f"Scan {iid}", key=f"cam_{iid}", label_visibility="collapsed")
                        if cam_img:
                            match, conf, d_code = prediksi_barang(cam_img, iid)
                            if match is True: st.success(f"✅ SESUAI ({int(conf*100)}%)")
                            elif match is False: st.error(f"❌ SALAH! (Detected: {d_code})")
                        st.markdown('</div>', unsafe_allow_html=True)

                        ci, ct = st.columns([4.5, 1])
                        ci.write(f"**Code:** {row[c_kd]} | **Qty SO:** {target}")
                        u_in = st.text_input("Input Fisik", key=f"q_{iid}", value="" if vq==0 else str(vq), placeholder="0")
                        n_ui = st.text_input("Catatan:", key=f"n_{iid}", value=vn, placeholder="Note...")
                        
                        q_num = int(re.sub("[^0-9]", "", u_in)) if re.sub("[^0-9]", "", u_in) != "" else 0
                        if draft.get(f"q_{iid}") != q_num or draft.get(f"n_{iid}") != n_ui:
                            draft.update({f"q_{iid}": q_num, f"n_{iid}": n_ui})
                            simpan_draft_ke_file(so_aktif, draft); st.rerun()
                        if q_num != target: v_all = False
                    st.markdown('</div>', unsafe_allow_html=True)
                    l_final.append({"Petugas": st.session_state['user'], "SO": so_aktif, "Kode": iid, "Item": row[c_item], "Qty_SO": target, "Qty_Fisik": q_num, "Note": n_ui})

                if st.button("✅ SELESAI & KIRIM LAPORAN", use_container_width=True, type="primary"):
                    if v_all:
                        simpan_rekap_data(l_final); simpan_so_selesai(so_aktif)
                        kirim_telegram(f"✅ QC SELESAI: {so_aktif} oleh {st.session_state['user']}")
                        st.session_state['page'] = "search"; st.balloons(); st.rerun()
                    else: st.error("Lengkapi jumlah barang sesuai SO!")

        elif menu == "Dashboard Monitoring":
            st.title("📊 Monitoring QC")
            if os.path.exists("rekap_qc.csv"):
                rkp = pd.read_csv("rekap_qc.csv")
                st.subheader("📋 Log Pemeriksaan Terakhir")
                st.dataframe(rkp.tail(20), use_container_width=True)
    else: st.error("❌ File data_so.csv tidak ditemukan.")

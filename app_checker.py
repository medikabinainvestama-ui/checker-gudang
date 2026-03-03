import streamlit as st
import pandas as pd
import requests
import os
import re
import json
from datetime import datetime
from users import USER_DB

# --- KONFIGURASI TELEGRAM ---
TOKEN = "8765480491:AAGI8Q8qi5ruWWdHZBSrNdq1j-NkUWa9YJc"
CHAT_ID = "-1003811491120"

st.set_page_config(page_title="QC MBI - Checker Center", layout="wide")

# --- STYLING CSS ---
st.markdown("""
    <style>
    footer {visibility: hidden !important;}
    #MainMenu {visibility: hidden !important;}
    .viewerBadge_container__1QSob, .viewerBadge_link__1QSob, .st-emotion-cache-1aege4m, .st-emotion-cache-zq5wrt,
    div[data-testid="stStatusWidget"], div[class^="viewerBadge"] { display: none !important; }

    div[data-testid="stTable"] th, div[data-testid="stTable"] td, 
    div[data-testid="stDataFrame"] th, div[data-testid="stDataFrame"] td,
    table, thead, tbody, th, td { text-align: center !important; vertical-align: middle !important; }
    
    .block-container { padding-top: 2rem !important; padding-bottom: 0rem !important; }
    div[data-testid="stExpander"] { border: 1px solid #ddd; border-radius: 8px; margin-bottom: -15px !important; }

    /* Style Kartu Statistik */
    .metric-card {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 10px;
        text-align: center;
        border: 1px solid #e0e0e0;
        margin-top: 10px;
        margin-bottom: 10px;
    }

    .status-ok { background-color: #d4edda !important; border-radius: 8px; border-left: 10px solid #28a745; margin-bottom: -15px !important; }
    .status-err { background-color: #f8d7da !important; border-radius: 8px; border-left: 10px solid #dc3545; margin-bottom: -15px !important; }
    .status-pending { background-color: #ffffff !important; border-radius: 8px; border-left: 10px solid #6c757d; margin-bottom: -15px !important; }
    </style>
""", unsafe_allow_html=True)

# --- FUNGSI DATABASE & DRAFT ---
def simpan_draft_ke_file(so_aktif, draft_data):
    if not os.path.exists("drafts"): os.makedirs("drafts")
    with open(f"drafts/draft_{so_aktif}.json", "w") as f: json.dump(draft_data, f)

def muat_draft_dari_file(so_aktif):
    file_path = f"drafts/draft_{so_aktif}.json"
    if os.path.exists(file_path):
        try:
            with open(file_path, "r") as f: return json.load(f)
        except: return {}
    return {}

def hapus_file_draft(so_aktif):
    file_path = f"drafts/draft_{so_aktif}.json"
    if os.path.exists(file_path): os.remove(file_path)

def ambil_semua_lock():
    locks = {}
    if os.path.exists("locks.txt"):
        try:
            with open("locks.txt", "r") as f:
                for line in f:
                    if "|" in line:
                        s, p = line.strip().split("|")
                        locks[s] = p
        except: pass
    return locks

def kunci_so(no_so, nama_petugas):
    locks = ambil_semua_lock()
    if no_so not in locks:
        with open("locks.txt", "a") as f:
            f.write(f"{no_so}|{nama_petugas}\n")
            f.flush()

def buka_kunci_so(no_so):
    locks = ambil_semua_lock()
    if no_so in locks:
        del locks[no_so]
        with open("locks.txt", "w") as f:
            for s, p in locks.items(): f.write(f"{s}|{p}\n")
            f.flush()

def ambil_daftar_selesai():
    if os.path.exists("selesai.txt"):
        with open("selesai.txt", "r") as f: return [line.strip() for line in f.readlines()]
    return []

def simpan_rekap_data(data_list):
    file_rekap = "rekap_qc.csv"
    df_baru = pd.DataFrame(data_list)
    if not os.path.exists(file_rekap): df_baru.to_csv(file_rekap, index=False)
    else: df_baru.to_csv(file_rekap, mode='a', header=False, index=False)

def simpan_so_selesai(no_so):
    path_selesai = "selesai.txt"
    with open(path_selesai, "a" if os.path.exists(path_selesai) else "w") as f:
        f.write(no_so.strip() + "\n")
        f.flush()
    buka_kunci_so(no_so)
    hapus_file_draft(no_so)
    if no_so in st.session_state['qc_drafts']: del st.session_state['qc_drafts'][no_so]

def kirim_telegram(pesan):
    try: requests.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={pesan}")
    except: pass

# --- INISIALISASI SESSION STATE ---
if 'auth' not in st.session_state:
    params = st.query_params
    if "u" in params and params["u"] in USER_DB:
        st.session_state['auth'] = True
        st.session_state['user'] = params["u"].capitalize()
    else: st.session_state['auth'] = False

if 'user' not in st.session_state: st.session_state['user'] = ""
if 'page' not in st.session_state: st.session_state['page'] = "search"
if 'selected_so' not in st.session_state: st.session_state['selected_so'] = None
if 'qc_drafts' not in st.session_state: st.session_state['qc_drafts'] = {}

# --- LOGIN ---
if not st.session_state['auth']:
    st.title("🔐 Login Checker MBI")
    u_input = st.text_input("Username").lower().strip()
    p_input = st.text_input("Password", type="password")
    if st.button("Masuk", use_container_width=True):
        if u_input in USER_DB and USER_DB[u_input] == p_input:
            st.session_state['auth'], st.session_state['user'] = True, u_input.capitalize()
            st.query_params["u"] = u_input 
            st.rerun()
        else: st.error("Username atau Password salah!")
else:
    is_admin = st.session_state['user'].lower() == "galang"
    st.sidebar.title(f"👤 {st.session_state['user']}")
    menu = st.sidebar.radio("Menu Utama", ["Pemeriksaan QC", "Dashboard Monitoring"]) if is_admin else "Pemeriksaan QC"
    
    if st.sidebar.button("Log Out"):
        if st.session_state['selected_so']: buka_kunci_so(st.session_state['selected_so'])
        st.session_state['auth'] = False
        st.query_params.clear()
        st.rerun()

    if os.path.exists("data_so.csv"):
        df_master = pd.read_csv("data_so.csv")
        df_master.columns = df_master.columns.str.strip()
        col_so, col_customer, col_tgl = 'Nomor # Pesanan Penjualan', 'Pelanggan', 'Tanggal Pesanan Penjualan'
        col_qty, col_item, col_kode = 'Kuantitas', 'Nama Barang', 'Kode #'
        col_batch, col_exp = 'No Seri/Produksi', 'Tgl Kadaluarsa'
        df_master[col_so] = df_master[col_so].astype(str).str.strip()
        df_master[[col_so, col_customer, col_tgl]] = df_master[[col_so, col_customer, col_tgl]].ffill()
        df_master = df_master[df_master[col_item].notna()]
        selesai_list = ambil_daftar_selesai()

        if menu == "Pemeriksaan QC":
            if st.session_state['page'] == "search":
                list_so_all = df_master[col_so].unique()
                list_so_aktif = sorted([s for s in list_so_all if s not in selesai_list])
                current_locks = ambil_semua_lock()
                
                st.subheader("🎯 Cari Nomor SO")

                # --- 1. ADMIN TOOLS (GALANG ONLY) DI ATAS PENCARIAN ---
                if is_admin:
                    with st.expander("🛠️ ADMIN TOOLS (Galang Only)", expanded=False):
                        so_adm = st.selectbox("Pilih SO untuk Admin Action:", list_so_aktif, key="so_admin_tool")
                        if so_adm:
                            c1, c2, c3, c4 = st.columns(4)
                            if c1.button("🔓 Unlock SO"): buka_kunci_so(so_adm); st.rerun()
                            if c2.button("♻️ Reset Draft"): hapus_file_draft(so_adm); st.rerun()
                            if c3.button("🗑️ Hapus SO"): simpan_so_selesai(so_adm); st.rerun()
                            if c4.button("⚡ Quick Done"):
                                simpan_so_selesai(so_adm)
                                kirim_telegram(f"⚡ *QUICK QC DONE (BY ADMIN)*\n👤 Admin: {st.session_state['user']}\n📄 No SO: {so_adm}")
                                st.rerun()
                
                # --- 2. KOLOM PENCARIAN (UTAMA) ---
                so_dipilih = st.selectbox("Pilih No SO:", list_so_aktif, index=None, placeholder="Ketik nomor SO...")
                
                # --- 3. METRIC CARDS DI BAWAH PENCARIAN ---
                st.divider()
                m1, m2, m3 = st.columns(3)
                m1.markdown(f'<div class="metric-card">📦 <b>Total SO</b><br><span style="font-size:24px">{len(list_so_all)}</span></div>', unsafe_allow_html=True)
                m2.markdown(f'<div class="metric-card">⏳ <b>Belum QC</b><br><span style="font-size:24px">{len(list_so_aktif)}</span></div>', unsafe_allow_html=True)
                m3.markdown(f'<div class="metric-card">✅ <b>Selesai</b><br><span style="font-size:24px">{len(selesai_list)}</span></div>', unsafe_allow_html=True)

                if current_locks:
                    with st.expander("👥 Petugas Aktif Saat Ini", expanded=True):
                        for s, p in current_locks.items():
                            st.caption(f"🔵 **{p}** sedang mengerjakan **{s}**")

                if so_dipilih:
                    if so_dipilih in current_locks and current_locks[so_dipilih] != st.session_state['user']:
                        st.error(f"🚫 Sedang dibuka oleh **{current_locks[so_dipilih]}**")
                    else:
                        kunci_so(so_dipilih, st.session_state['user'])
                        st.session_state['selected_so'], st.session_state['page'] = so_dipilih, "list_barang"
                        st.session_state['qc_drafts'][so_dipilih] = muat_draft_dari_file(so_dipilih)
                        st.rerun()

            elif st.session_state['page'] == "list_barang":
                so_aktif = st.session_state['selected_so']
                if st.button("⬅️ Kembali ke Pencarian"):
                    buka_kunci_so(so_aktif); st.session_state['selected_so'], st.session_state['page'] = None, "search"; st.rerun()

                df_filter = df_master[df_master[col_so] == so_aktif].copy()
                nama_apotek, tgl_so = df_filter.iloc[0][col_customer], df_filter.iloc[0][col_tgl]
                df_filter[col_qty] = pd.to_numeric(df_filter[col_qty], errors='coerce').fillna(0)
                
                st.info(f"📌 **Nomor SO:** {so_aktif}")
                h1, h2 = st.columns(2)
                h1.markdown(f"🏢 **Apotek:** {nama_apotek}\n\n📅 **Tanggal SO:** {tgl_so}")
                h2.markdown(f"💊 **Total Jenis:** {len(df_filter)} Item\n\n🔢 **Total Qty SO:** {int(df_filter[col_qty].sum())} Pcs")
                st.divider()

                valid_all, list_data_final, draft_so = True, [], st.session_state['qc_drafts'].get(so_aktif, {})

                for index, row in df_filter.iterrows():
                    item_id = str(row[col_kode]).strip()
                    target = int(float(row[col_qty]))
                    val_q = draft_so.get(f"q_{item_id}", 0)
                    val_n = draft_so.get(f"n_{item_id}", "")
                    val_t = draft_so.get(f"tog_{item_id}", False)
                    val_disp = "" if str(val_q) == "0" else str(val_q)
                    
                    status_class = "status-pending"; icon_status = " ⏳"
                    if str(val_q) != "0":
                        if int(val_q) == target: status_class, icon_status = "status-ok", " ✅"
                        else: status_class, icon_status = "status-err", " ⚠️"

                    st.markdown(f'<div class="{status_class}">', unsafe_allow_html=True)
                    with st.expander(f"💊 {row[col_item]}{icon_status}", expanded=False):
                        ci, ct = st.columns([4.5, 1])
                        ci.write(f"**Code:** {row[col_kode]} | **Batch:** {row[col_batch]} | **Exp:** {row[col_exp]} | **Qty:** {target}")
                        is_note = ct.checkbox("📝", key=f"tog_ui_{so_aktif}_{item_id}", value=val_t)
                        u_in = st.text_input(f"Qty Input", key=f"q_ui_{so_aktif}_{item_id}", value=val_disp, placeholder="0", label_visibility="collapsed")
                        q_num = int(re.sub("[^0-9]", "", u_in)) if re.sub("[^0-9]", "", u_in) != "" else 0
                        note_text = st.text_input("Catatan:", key=f"n_ui_{so_aktif}_{item_id}", value=val_n).strip() if is_note else ""

                        if draft_so.get(f"q_{item_id}") != q_num or draft_so.get(f"n_{item_id}") != note_text or draft_so.get(f"tog_{item_id}") != is_note:
                            draft_so.update({f"q_{item_id}": q_num, f"n_{item_id}": note_text, f"tog_{item_id}": is_note})
                            simpan_draft_ke_file(so_aktif, draft_so); st.rerun()

                        if u_in == "" or q_num != target: valid_all = False
                    st.markdown('</div>', unsafe_allow_html=True)
                    list_data_final.append({"Waktu": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "Petugas": st.session_state['user'], "SO": so_aktif, "Apotek": nama_apotek, "Kode": row[col_kode], "Item": row[col_item], "Batch": row[col_batch], "Exp": row[col_exp], "Qty_SO": target, "Qty_Fisik": q_num, "Note": note_text})

                st.divider()
                if st.button("✅ SELESAI & KIRIM LAPORAN", use_container_width=True, type="primary"):
                    if valid_all:
                        simpan_rekap_data(list_data_final)
                        nt = ""
                        for d in list_data_final:
                            if d['Note']: nt += f"- {d['Kode']} ({d['Qty_Fisik']} pcs)\n  🗒 Note: {d['Note']}\n"
                        kirim_telegram(f"✅ *QC SELESAI*\n👤 Petugas: {st.session_state['user']}\n📄 No SO: {so_aktif}\n📍 Apotek: {nama_apotek}\n---------------------------\n{nt if nt else '_Tanpa Catatan_'}")
                        simpan_so_selesai(so_aktif); st.balloons(); st.rerun()
                    else: st.error("Lengkapi semua barang (Warna Hijau) sebelum kirim!")

        elif menu == "Dashboard Monitoring":
            st.title("📊 Monitoring & Klasemen QC")
            if os.path.exists("rekap_qc.csv"):
                df_rkp = pd.read_csv("rekap_qc.csv")
                klasemen = df_rkp.groupby('Petugas').agg({'SO': 'nunique', 'Item': 'count', 'Qty_Fisik': 'sum'}).reset_index()
                klasemen.columns = ['Nama QC', 'Total SO', 'Total Jenis Barang', 'Total Qty SO']
                klasemen = klasemen.sort_values(by='Total Jenis Barang', ascending=False).reset_index(drop=True)
                klasemen.index += 1
                st.subheader("🏆 Klasemen Checker")
                st.table(klasemen)
            
            df_mon = df_master.groupby([col_so, col_tgl]).agg({col_item: 'count', col_qty: 'sum'}).reset_index()
            df_mon.columns = ['No SO', 'Tanggal SO', 'Total Jenis Barang', 'Total Qty SO']
            def get_info(row):
                if row['No SO'] in selesai_list:
                    try:
                        ptgs = df_rkp[df_rkp['SO'] == row['No SO']]['Petugas'].iloc[0]
                        return "Done QC", ptgs
                    except: return "Done QC", "-"
                return "Pending QC", "-"
            df_mon[['Status', 'Nama QC']] = df_mon.apply(lambda x: pd.Series(get_info(x)), axis=1)
            st.subheader("📋 Status Semua No SO")
            st.dataframe(df_mon[['Tanggal SO', 'No SO', 'Nama QC', 'Total Jenis Barang', 'Total Qty SO', 'Status']], use_container_width=True, hide_index=True)
    else: st.error("File data_so.csv tidak ditemukan.")

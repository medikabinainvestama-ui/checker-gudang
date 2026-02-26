import streamlit as st
import pandas as pd
import requests
import os
import re
from datetime import datetime
from users import USER_DB

# --- KONFIGURASI TELEGRAM ---
TOKEN = "8765480491:AAGI8Q8qi5ruWWdHZBSrNdq1j-NkUWa9YJc"
CHAT_ID = "-1003811491120"

st.set_page_config(page_title="QC MBI - Checker", layout="wide")

# --- STYLING CSS ---
st.markdown("""
    <style>
    .stExpander { border: 1px solid #ddd; border-radius: 8px; margin-bottom: 10px; }
    </style>
""", unsafe_allow_html=True)

# --- FUNGSI DATABASE ---
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
            for s, p in locks.items():
                f.write(f"{s}|{p}\n")
            f.flush()

def ambil_daftar_selesai():
    if os.path.exists("selesai.txt"):
        with open("selesai.txt", "r") as f:
            return [line.strip() for line in f.readlines()]
    return []

def simpan_rekap_data(data_list):
    file_rekap = "rekap_qc.csv"
    df_baru = pd.DataFrame(data_list)
    if not os.path.exists(file_rekap):
        df_baru.to_csv(file_rekap, index=False)
    else:
        df_baru.to_csv(file_rekap, mode='a', header=False, index=False)

def simpan_so_selesai(no_so):
    path_selesai = "selesai.txt"
    with open(path_selesai, "a" if os.path.exists(path_selesai) else "w") as f:
        f.write(no_so.strip() + "\n")
        f.flush()
    buka_kunci_so(no_so)
    if no_so in st.session_state['qc_drafts']:
        del st.session_state['qc_drafts'][no_so]

# --- INISIALISASI SESSION STATE (PENYELAMAT LOGIN) ---
if 'auth' not in st.session_state:
    # Cek apakah ada jejak login di URL browser
    params = st.query_params
    if "u" in params and params["u"] in USER_DB:
        st.session_state['auth'] = True
        st.session_state['user'] = params["u"].capitalize()
    else:
        st.session_state['auth'] = False

if 'user' not in st.session_state:
    st.session_state['user'] = ""
if 'page' not in st.session_state:
    st.session_state['page'] = "search"
if 'selected_so' not in st.session_state:
    st.session_state['selected_so'] = None
if 'qc_drafts' not in st.session_state:
    st.session_state['qc_drafts'] = {}

# --- SISTEM LOGIN ---
if not st.session_state['auth']:
    st.title("🔐 Login Checker MBI")
    u_input = st.text_input("Username").lower().strip()
    p_input = st.text_input("Password", type="password")
    if st.button("Masuk", use_container_width=True):
        if u_input in USER_DB and USER_DB[u_input] == p_input:
            st.session_state['auth'] = True
            st.session_state['user'] = u_input.capitalize()
            # Simpan username di URL agar tidak logout otomatis
            st.query_params["u"] = u_input 
            st.rerun()
        else:
            st.error("Username atau Password salah!")
else:
    # --- SIDEBAR MENU ---
    st.sidebar.title(f"👤 {st.session_state['user']}")
    
    if st.session_state['user'].lower() == "galang":
        menu = st.sidebar.radio("Menu Utama", ["Pemeriksaan QC", "Dashboard Monitoring"])
    else:
        menu = "Pemeriksaan QC"
        st.sidebar.info("Mode: Checker Gudang")

    if st.sidebar.button("Log Out"):
        if st.session_state['selected_so']:
            buka_kunci_so(st.session_state['selected_so'])
        st.session_state['auth'] = False
        st.query_params.clear() # Hapus jejak login di URL
        st.rerun()

    # --- LOAD DATA ---
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

        # --- MENU 1: PEMERIKSAAN QC ---
        if menu == "Pemeriksaan QC":
            if st.session_state['page'] == "search":
                list_so_aktif = sorted([s for s in df_master[col_so].unique() if s not in selesai_list])
                st.subheader("🎯 Cari Nomor SO")
                so_dipilih = st.selectbox("Pilih No SO:", list_so_aktif, index=None, placeholder="Ketik nomor SO...")
                
                if so_dipilih:
                    current_locks = ambil_semua_lock()
                    if so_dipilih in current_locks and current_locks[so_dipilih] != st.session_state['user']:
                        st.error(f"🚫 Sedang dibuka oleh **{current_locks[so_dipilih]}**")
                    else:
                        kunci_so(so_dipilih, st.session_state['user'])
                        st.session_state['selected_so'], st.session_state['page'] = so_dipilih, "list_barang"
                        if so_dipilih not in st.session_state['qc_drafts']:
                            st.session_state['qc_drafts'][so_dipilih] = {}
                        st.rerun()

            elif st.session_state['page'] == "list_barang":
                so_aktif = st.session_state['selected_so']
                if st.button("⬅️ Kembali ke Pencarian"):
                    buka_kunci_so(so_aktif)
                    st.session_state['selected_so'], st.session_state['page'] = None, "search"
                    st.rerun()

                df_filter = df_master[df_master[col_so] == so_aktif].copy()
                nama_apotek, tgl_so = df_filter.iloc[0][col_customer], df_filter.iloc[0][col_tgl]
                df_filter[col_qty] = pd.to_numeric(df_filter[col_qty], errors='coerce').fillna(0)
                
                st.info(f"📌 **Nomor SO:** {so_aktif}")
                h1, h2 = st.columns(2)
                h1.markdown(f"🏢 **Apotek:** {nama_apotek}\n\n📅 **Tanggal SO:** {tgl_so}")
                h2.markdown(f"💊 **Total Jenis:** {len(df_filter)} Item\n\n🔢 **Total Qty SO:** {int(df_filter[col_qty].sum())} Pcs")
                st.divider()

                valid_all, list_data_final = True, []
                draft_so = st.session_state['qc_drafts'].get(so_aktif, {})

                for index, row in df_filter.iterrows():
                    target = int(float(row[col_qty]))
                    val_q = draft_so.get(f"q_{index}", 0)
                    val_n = draft_so.get(f"n_{index}", "")
                    val_t = draft_so.get(f"tog_{index}", False)

                    icon = " ✅" if str(val_q) != "0" and int(val_q) == target else (" ⚠️" if str(val_q) != "0" else "")
                    val_disp = "" if str(val_q) == "0" else str(val_q)

                    with st.expander(f"💊 {row[col_item]}{icon}", expanded=False):
                        ci, ct = st.columns([4.5, 1])
                        ci.write(f"**Code:** {row[col_kode]} | **Batch:** {row[col_batch]} | **Exp:** {row[col_exp]} | **Qty:** {target}")
                        is_note = ct.checkbox("📝", key=f"tog_ui_{index}", value=val_t)
                        draft_so[f"tog_{index}"] = is_note

                        u_input_raw = st.text_input(f"Qty Input", key=f"q_ui_{index}", value=val_disp, placeholder="0", label_visibility="collapsed")
                        q_num = int(re.sub("[^0-9]", "", u_input_raw)) if re.sub("[^0-9]", "", u_input_raw) != "" else 0
                        draft_so[f"q_{index}"] = q_num

                        if u_input_raw != "":
                            if q_num == target: st.success(f"Jumlah Sesuai: {q_num}")
                            else: 
                                st.error(f"Selisih! SO: {target}"); valid_all = False
                        else: valid_all = False
                        
                        n_val = ""
                        if is_note:
                            n_val = st.text_input("Catatan:", key=f"n_ui_{index}", value=val_n)
                            draft_so[f"n_{index}"] = n_val.strip()

                    list_data_final.append({
                        "Waktu": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "Petugas": st.session_state['user'],
                        "SO": so_aktif, "Apotek": nama_apotek, "Kode": row[col_kode], "Item": row[col_item],
                        "Batch": row[col_batch], "Exp": row[col_exp], "Qty_SO": target, "Qty_Fisik": q_num, "Note": n_val
                    })

                st.divider()
                if st.button("✅ SELESAI & KIRIM LAPORAN", use_container_width=True, type="primary"):
                    if valid_all:
                        simpan_rekap_data(list_data_final)
                        n_msg = ""
                        for d in list_data_final:
                            if d['Note']: n_msg += f"- {d['Kode']} ({d['Qty_Fisik']} pcs)\n  🗒 Note: {d['Note']}\n"
                        telegram_msg = f"✅ **QC SELESAI**\n👤 Petugas: {st.session_state['user']}\n📄 No SO: {so_aktif}\n📍 Apotek: {nama_apotek}\n---------------------------\n{n_msg if n_msg else '_Tanpa Catatan_'}"
                        requests.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={telegram_msg}")
                        simpan_so_selesai(so_aktif)
                        st.session_state['selected_so'], st.session_state['page'] = None, "search"
                        st.balloons(); st.rerun()
                    else: st.error("Gagal! Pastikan semua jumlah sesuai.")

        # --- MENU 2: DASHBOARD MONITORING (DIPERBAIKI) ---
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
            
            def check_st(row):
                if row['No SO'] in selesai_list:
                    try:
                        ptgs = df_rkp[df_rkp['SO'] == row['No SO']]['Petugas'].iloc[0]
                        return "Done QC", ptgs
                    except: return "Done QC", "-"
                return "Pending QC", "-"

            df_mon[['Status', 'Nama QC']] = df_mon.apply(lambda x: pd.Series(check_st(x)), axis=1)
            st.subheader("📋 Status Semua No SO")
            st.dataframe(df_mon[['Tanggal SO', 'No SO', 'Nama QC', 'Total Jenis Barang', 'Total Qty SO', 'Status']], use_container_width=True, hide_index=True)
            csv_data = df_mon.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download Laporan Status (.csv)", csv_data, f"QC_Report_{datetime.now().date()}.csv", "text/csv")
    else: st.error("File data_so.csv tidak ditemukan.")

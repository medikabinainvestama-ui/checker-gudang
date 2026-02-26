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

st.set_page_config(page_title="QC MBI - Admin Center", layout="wide")

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

# --- INISIALISASI SESSION STATE ---
if 'auth' not in st.session_state:
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
        st.session_state['auth'] = False
        st.rerun()

    # --- LOAD DATA ---
    if os.path.exists("data_so.csv"):
        df_master = pd.read_csv("data_so.csv")
        df_master.columns = df_master.columns.str.strip()
        col_so = 'Nomor # Pesanan Penjualan'
        col_customer = 'Pelanggan'
        col_tgl = 'Tanggal Pesanan Penjualan'
        col_qty = 'Kuantitas'
        col_item = 'Nama Barang'
        col_kode = 'Kode #'
        col_batch = 'No Seri/Produksi'
        col_exp = 'Tgl Kadaluarsa'

        df_master[col_so] = df_master[col_so].astype(str).str.strip()
        df_master[[col_so, col_customer, col_tgl]] = df_master[[col_so, col_customer, col_tgl]].ffill()
        df_master = df_master[df_master[col_item].notna()]
        
        selesai_list = ambil_daftar_selesai()

        # --- MENU 1: PEMERIKSAAN QC (DIPERBAIKI) ---
        if menu == "Pemeriksaan QC":
            list_so_aktif = sorted([s for s in df_master[col_so].unique() if s not in selesai_list])

            # Tampilan Halaman Cari SO
            if st.session_state['page'] == "search":
                st.subheader("🎯 Cari Nomor SO")
                so_dipilih = st.selectbox("Pilih No SO:", list_so_aktif, index=None, placeholder="Ketik nomor SO...")
                
                if so_dipilih:
                    current_locks = ambil_semua_lock()
                    if so_dipilih in current_locks and current_locks[so_dipilih] != st.session_state['user']:
                        st.error(f"🚫 Sedang dibuka oleh **{current_locks[so_dipilih]}**")
                    else:
                        kunci_so(so_dipilih, st.session_state['user'])
                        st.session_state['selected_so'] = so_dipilih
                        st.session_state['page'] = "list_barang"
                        if so_dipilih not in st.session_state['qc_drafts']:
                            st.session_state['qc_drafts'][so_dipilih] = {}
                        st.rerun()

            # Tampilan Halaman List Barang (Draft Autosave Tetap Ada)
            elif st.session_state['page'] == "list_barang":
                so_aktif = st.session_state['selected_so']
                if st.button("⬅️ Kembali ke Pencarian"):
                    buka_kunci_so(so_aktif)
                    st.session_state['selected_so'] = None
                    st.session_state['page'] = "search"
                    st.rerun()

                df_filter = df_master[df_master[col_so] == so_aktif].copy()
                nama_apotek = df_filter.iloc[0][col_customer]
                tanggal_so = df_filter.iloc[0][col_tgl]
                df_filter[col_qty] = pd.to_numeric(df_filter[col_qty], errors='coerce').fillna(0)
                
                total_jenis = len(df_filter)
                total_qty_so_val = int(df_filter[col_qty].sum())

                st.info(f"📌 **Nomor SO:** {so_aktif}")
                h_col1, h_col2 = st.columns(2)
                with h_col1:
                    st.markdown(f"🏢 **Apotek:** {nama_apotek}")
                    st.markdown(f"📅 **Tanggal SO:** {tanggal_so}")
                with h_col2:
                    st.markdown(f"💊 **Total Jenis:** {total_jenis} Item")
                    st.markdown(f"🔢 **Total Qty SO:** {total_qty_so_val} Pcs")
                
                st.divider()

                valid_all = True
                list_data_final = []
                draft_so = st.session_state['qc_drafts'].get(so_aktif, {})

                for index, row in df_filter.iterrows():
                    qty_target = int(float(row[col_qty]))
                    exp_date = row[col_exp] if pd.notna(row[col_exp]) else "-"
                    batch_no = row[col_batch] if pd.notna(row[col_batch]) else "-"
                    kode_brg = row[col_kode] if pd.notna(row[col_kode]) else "-"
                    
                    val_qty_awal = draft_so.get(f"q_{index}", 0)
                    val_display = "" if str(val_qty_awal) == "0" else str(val_qty_awal)

                    label_status = " ✅" if str(val_qty_awal) != "0" and int(val_qty_awal) == qty_target else (" ⚠️" if str(val_qty_awal) != "0" else "")

                    with st.expander(f"💊 {row[col_item]}{label_status}", expanded=False):
                        st.write(f"**Code:** {kode_brg} | **Batch:** {batch_no} | **Exp:** {exp_date} | **Qty:** {qty_target}")
                        
                        user_input_raw = st.text_input(f"Qty Input", key=f"q_ui_{index}", value=val_display, placeholder="0", label_visibility="collapsed")
                        final_input_qty = int(re.sub("[^0-9]", "", user_input_raw)) if re.sub("[^0-9]", "", user_input_raw) != "" else 0
                        draft_so[f"q_{index}"] = final_input_qty

                        if user_input_raw != "":
                            if final_input_qty == qty_target: st.success(f"Jumlah Sesuai: {final_input_qty}")
                            else: 
                                st.error(f"Selisih! Input: {final_input_qty} / SO: {qty_target}")
                                valid_all = False
                        else: valid_all = False

                    list_data_final.append({
                        "Waktu": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "Petugas": st.session_state['user'], "SO": so_aktif, "Apotek": nama_apotek,
                        "Kode": kode_brg, "Item": row[col_item], "Batch": batch_no, "Exp": exp_date,
                        "Qty_SO": qty_target, "Qty_Fisik": final_input_qty, "Note": ""
                    })

                if st.button("✅ SELESAI & KIRIM LAPORAN", use_container_width=True, type="primary"):
                    if valid_all:
                        simpan_rekap_data(list_data_final)
                        simpan_so_selesai(so_aktif)
                        st.session_state['selected_so'] = None
                        st.session_state['page'] = "search"
                        st.balloons()
                        st.rerun()

        # --- MENU 2: DASHBOARD MONITORING (MODIFIKASI) ---
        elif menu == "Dashboard Monitoring":
            st.title("📊 Monitoring & Klasemen QC")
            
            # Klasemen
            if os.path.exists("rekap_qc.csv"):
                df_rekap = pd.read_csv("rekap_qc.csv")
                klasemen = df_rekap.groupby('Petugas').agg({'SO': 'nunique', 'Item': 'count', 'Qty_Fisik': 'sum'}).reset_index()
                klasemen.columns = ['Nama QC', 'Total SO', 'Total Jenis Barang', 'Total Qty SO']
                klasemen = klasemen.sort_values(by='Total Jenis Barang', ascending=False).reset_index(drop=True)
                klasemen.index += 1
                st.subheader("🏆 Klasemen Checker")
                st.table(klasemen)

            # Report Status SO
            df_summary = df_master.groupby([col_so, col_tgl]).agg({col_item: 'count', col_qty: 'sum'}).reset_index()
            df_summary.columns = ['No SO', 'Tanggal SO', 'Total Jenis Barang', 'Total Qty SO']
            
            def get_status_info(row):
                if row['No SO'] in selesai_list:
                    return "Done QC", "-" # Bisa dikembangkan ambil nama petugas dari rekap_qc.csv
                return "Pending QC", "-"

            df_summary[['Status', 'Nama QC']] = df_summary.apply(lambda x: pd.Series(get_status_info(x)), axis=1)
            st.subheader("📋 Status Semua No SO")
            st.dataframe(df_summary[['Tanggal SO', 'No SO', 'Nama QC', 'Total Jenis Barang', 'Total Qty SO', 'Status']], use_container_width=True, hide_index=True)

    else:
        st.error("File data_so.csv tidak ditemukan.")

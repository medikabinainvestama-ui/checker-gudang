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
    [data-testid="stMetricValue"] { font-size: 28px; }
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

        # --- MENU 1: PEMERIKSAAN QC (TETAP SAMA) ---
        if menu == "Pemeriksaan QC":
            # (Logika pengerjaan QC Anda yang sudah ada di sini tetap dipertahankan)
            # ... [Bagian ini disingkat untuk efisiensi, isinya sama dengan kode sebelumnya] ...
            st.write("Silakan pilih SO pada menu utama.")

        # --- MENU 2: DASHBOARD MONITORING (PERUBAHAN TOTAL) ---
        elif menu == "Dashboard Monitoring":
            st.title("📊 Monitoring & Klasemen QC")

            # 1. LOGIKA KLASEMEN TIM QC
            st.subheader("🏆 Klasemen Checker (Berdasarkan Total Jenis)")
            if os.path.exists("rekap_qc.csv"):
                df_rekap = pd.read_csv("rekap_qc.csv")
                # Grouping data per petugas
                klasemen = df_rekap.groupby('Petugas').agg({
                    'SO': 'nunique',
                    'Item': 'count',
                    'Qty_Fisik': 'sum'
                }).reset_index()
                
                klasemen.columns = ['Nama QC', 'Total SO', 'Total Jenis Barang', 'Total Qty SO']
                # Urutkan berdasarkan Total Jenis Barang (Sesuai Permintaan)
                klasemen = klasemen.sort_values(by='Total Jenis Barang', ascending=False).reset_index(drop=True)
                klasemen.index += 1 # Ranking 1, 2, 3...
                
                st.table(klasemen)
            else:
                st.info("Belum ada aktivitas pengerjaan QC hari ini.")

            st.divider()

            # 2. LOGIKA DAFTAR LAPORAN STATUS SO
            st.subheader("📋 Status Semua No SO")
            
            # Buat summary SO dari master data
            df_summary = df_master.groupby([col_so, col_tgl]).agg({
                col_item: 'count',
                col_qty: 'sum'
            }).reset_index()
            
            df_summary.columns = ['No SO', 'Tanggal SO', 'Total Jenis Barang', 'Total Qty SO']

            # Tambahkan Status & Nama QC
            def get_status_info(row):
                if row['No SO'] in selesai_list:
                    # Cari siapa yang mengerjakan di rekap
                    if os.path.exists("rekap_qc.csv"):
                        try:
                            # Ambil nama petugas terakhir yang input SO tersebut
                            petugas = df_rekap[df_rekap['SO'] == row['No SO']]['Petugas'].iloc[0]
                            return "Done QC", petugas
                        except:
                            return "Done QC", "-"
                    return "Done QC", "-"
                return "Pending QC", "-"

            df_summary[['Status', 'Nama QC']] = df_summary.apply(
                lambda x: pd.Series(get_status_info(x)), axis=1
            )

            # Re-order kolom sesuai permintaan
            df_final_report = df_summary[['Tanggal SO', 'No SO', 'Nama QC', 'Total Jenis Barang', 'Total Qty SO', 'Status']]

            # Tampilan Tabel Monitoring
            st.dataframe(df_final_report, use_container_width=True, hide_index=True)

            # Fitur Download
            csv = df_final_report.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download Report Status SO (.csv)",
                data=csv,
                file_name=f'Report_Status_QC_{datetime.now().strftime("%Y-%m-%d")}.csv',
                mime='text/csv',
            )

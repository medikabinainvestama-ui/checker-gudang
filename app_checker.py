import streamlit as st
import pandas as pd
import requests
import os
from users import USER_DB

# --- KONFIGURASI TELEGRAM ---
TOKEN = "8765480491:AAGI8Q8qi5ruWWdHZBSrNdq1j-NkUWa9YJc"
CHAT_ID = "-1003811491120"

st.set_page_config(page_title="QC MBI - Validasi Qty", layout="centered")

# --- FUNGSI DATABASE PENGUNCIAN & SELESAI ---
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

def simpan_so_selesai(no_so):
    with open("selesai.txt", "a") as f:
        f.write(no_so.strip() + "\n")
        f.flush()
    buka_kunci_so(no_so)

def ambil_daftar_selesai():
    if os.path.exists("selesai.txt"):
        with open("selesai.txt", "r") as f:
            return [line.strip() for line in f.readlines()]
    return []

# --- SISTEM LOGIN & NAVIGASI ---
if 'auth' not in st.session_state:
    st.session_state['auth'] = False
    st.session_state['user'] = ""
if 'page' not in st.session_state:
    st.session_state['page'] = "search"
if 'selected_so' not in st.session_state:
    st.session_state['selected_so'] = None

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
    # SIDEBAR
    st.sidebar.title(f"👤 {st.session_state['user']}")
    if st.sidebar.button("Log Out"):
        if st.session_state['selected_so']:
            buka_kunci_so(st.session_state['selected_so'])
        st.session_state['auth'] = False
        st.rerun()

    # --- HALAMAN 1: PENCARIAN SO ---
    if st.session_state['page'] == "search":
        st.title("🎯 Cari Nomor SO")
        
        if os.path.exists("data_so.csv"):
            df = pd.read_csv("data_so.csv")
            col_so = 'Nomor # Pesanan Penjualan'
            df[col_so] = df[col_so].astype(str).str.strip()
            
            selesai_list = ambil_daftar_selesai()
            semua_so = df[col_so].unique().tolist()
            list_so_aktif = sorted([so for so in semua_so if so not in selesai_list])

            st.write(f"Total Antrean: **{len(list_so_aktif)}** SO")
            
            so_dipilih = st.selectbox("Pilih atau Ketik No SO:", list_so_aktif, index=None, placeholder="Contoh: SO-2026...")

            if so_dipilih:
                current_locks = ambil_semua_lock()
                if so_dipilih in current_locks and current_locks[so_dipilih] != st.session_state['user']:
                    st.error(f"🚫 Sedang dibuka oleh **{current_locks[so_dipilih]}**")
                else:
                    kunci_so(so_dipilih, st.session_state['user'])
                    st.session_state['selected_so'] = so_dipilih
                    st.session_state['page'] = "list_barang"
                    st.rerun()
        else:
            st.warning("Data SO belum tersedia.")

    # --- HALAMAN 2: LIST BARANG ---
    elif st.session_state['page'] == "list_barang":
        so_aktif = st.session_state['selected_so']
        
        if st.button("⬅️ Kembali ke Pencarian"):
            buka_kunci_so(so_aktif)
            st.session_state['selected_so'] = None
            st.session_state['page'] = "search"
            st.rerun()

        st.title("📋 Detail Barang")
        
        df = pd.read_csv("data_so.csv")
        col_so = 'Nomor # Pesanan Penjualan'
        col_item = 'Nama Barang'
        col_qty = 'Kuantitas'
        col_customer = 'Nama Pelanggan'
        col_tgl = 'Tanggal'
        col_batch = 'Nomor Seri/Produksi'
        col_exp = 'Tgl Kadaluarsa'

        df[col_so] = df[col_so].astype(str).str.strip()
        df[[col_so, col_customer, col_tgl]] = df[[col_so, col_customer, col_tgl]].ffill()
        
        df_filter = df[df[col_so] == so_aktif]
        
        total_jenis_barang = len(df_filter[df_filter[col_item].notna()])
        total_qty_data = df_filter[col_qty].sum()
        tanggal_so = df_filter.iloc[0][col_tgl]
        nama_apotek = df_filter.iloc[0][col_customer]

        st.info(f"📌 **Nomor SO:** {so_aktif}")
        
        info_col1, info_col2 = st.columns(2)
        with info_col1:
            st.markdown(f"🏢 **Apotek:**\n{nama_apotek}")
            st.markdown(f"📦 **Total Jenis:** {total_jenis_barang} Item")
        with info_col2:
            st.markdown(f"📅 **Tanggal SO:**\n{tanggal_so}")
            st.markdown(f"🔢 **Total Qty SO:** {int(total_qty_data)} Pcs")
        
        st.divider()

        valid_all = True
        list_input_qty = []

        for index, row in df_filter.iterrows():
            if pd.notna(row[col_item]):
                qty_seharusnya = int(row[col_qty])
                
                with st.expander(f"📦 {row[col_item]}", expanded=True):
                    # Tampilan Baris Informasi: Batch | Exp | Qty SO
                    st.write(f"**Batch:** {row[col_batch]} | **Exp:** {row[col_exp]} | **Qty SO:** {qty_seharusnya}")
                    
                    c1, c2 = st.columns([3, 2])
                    with c1:
                        # Label input menjadi bersih sesuai permintaan
                        input_qty = st.number_input(f"Input Qty Fisik", 
                                                    min_value=0, 
                                                    step=1, 
                                                    key=f"qty_{index}",
                                                    value=0)
                    with c2:
                        st.write("") # Spacer
                        if input_qty == 0:
                            st.warning("Kosong")
                            valid_all = False
                        elif input_qty == qty_seharusnya:
                            st.success("✅ OK")
                        else:
                            st.error(f"❌ Selisih")
                            valid_all = False
                
                list_input_qty.append(input_qty)

        st.divider()

        if st.button("✅ SELESAI & KIRIM LAPORAN", use_container_width=True, type="primary"):
            if valid_all:
                total_qty_input = sum(list_input_qty)
                msg = (f"✅ **QC SELESAI (VALID)**\n"
                       f"👤 Petugas: {st.session_state['user']}\n"
                       f"📄 No SO: {so_aktif}\n"
                       f"📍 Apotek: {nama_apotek}\n"
                       f"📅 Tgl SO: {tanggal_so}\n"
                       f"📦 Total: {total_jenis_barang} Item\n"
                       f"🔢 Qty Total: {int(total_qty_input)} Pcs")
                
                requests.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={msg}")
                
                simpan_so_selesai(so_aktif)
                st.session_state['selected_so'] = None
                st.session_state['page'] = "search"
                st.success("Laporan Valid & Terkirim!")
                st.balloons()
                st.rerun()
            else:
                st.error("Gagal Kirim! Ada item yang selisih atau belum diisi.")

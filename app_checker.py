import streamlit as st
import pandas as pd
import requests
import os
from users import USER_DB # Mengambil data akun dari file sebelah

# Masukkan Data Telegram Anda
TOKEN = "8765480491:AAGI8Q8qi5ruWWdHZBSrNdq1j-NkUWa9YJc"
CHAT_ID = "-1003811491120"

st.set_page_config(page_title="QC MBI - Berjenjang", layout="centered")

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
    st.session_state['page'] = "search" # Halaman default
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
                    # Kunci dan pindah halaman
                    kunci_so(so_dipilih, st.session_state['user'])
                    st.session_state['selected_so'] = so_dipilih
                    st.session_state['page'] = "list_barang"
                    st.rerun()
        else:
            st.warning("Data SO belum tersedia.")

    # --- HALAMAN 2: LIST BARANG ---
    elif st.session_state['page'] == "list_barang":
        so_aktif = st.session_state['selected_so']
        
        # Tombol Kembali
        if st.button("⬅️ Kembali ke Pencarian"):
            buka_kunci_so(so_aktif)
            st.session_state['selected_so'] = None
            st.session_state['page'] = "search"
            st.rerun()

        st.title("📋 Detail Barang")
        st.info(f"📍 **Nomor SO:** {so_aktif}")

        df = pd.read_csv("data_so.csv")
        # Sesuaikan kolom
        col_so = 'Nomor # Pesanan Penjualan'
        col_item = 'Nama Barang'
        col_batch = 'Nomor Seri/Produksi'
        col_exp = 'Tgl Kadaluarsa'
        col_qty = 'Kuantitas'
        col_customer = 'Nama Pelanggan'
        col_tgl = 'Tanggal'

        df[col_so] = df[col_so].astype(str).str.strip()
        df[[col_so, col_customer, col_tgl]] = df[[col_so, col_customer, col_tgl]].ffill()
        
        df_filter = df[df[col_so] == so_aktif]
        
        st.write(f"Apotek: **{df_filter.iloc[0][col_customer]}**")
        st.divider()

        status_checks = []
        for index, row in df_filter.iterrows():
            if pd.notna(row[col_item]):
                with st.expander(f"📦 {row[col_item]}", expanded=True):
                    c1, c2 = st.columns([1, 4])
                    with c1:
                        is_ok = st.checkbox("OK", key=f"check_{index}")
                        status_checks.append(is_ok)
                    with c2:
                        st.write(f"**Batch:** {row[col_batch]} | **Exp:** {row[col_exp]}")
                        st.write(f"**Jumlah:** {row[col_qty]} Pcs")

        if st.button("✅ SELESAI & KIRIM LAPORAN", use_container_width=True, type="primary"):
            if all(status_checks) and len(status_checks) > 0:
                msg = f"✅ **QC SELESAI**\n👤 {st.session_state['user']}\n📄 {so_aktif}\n📍 {df_filter.iloc[0][col_customer]}"
                requests.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={msg}")
                
                simpan_so_selesai(so_aktif)
                st.session_state['selected_so'] = None
                st.session_state['page'] = "search"
                st.success("Terkirim!")
                st.balloons()
                st.rerun()
            else:
                st.error("Centang semua barang dulu!")

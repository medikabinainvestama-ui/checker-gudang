import streamlit as st
import pandas as pd
import requests
import os
from users import USER_DB # Mengambil data akun dari file sebelah

# Masukkan Data Telegram Anda
TOKEN = "8765480491:AAGI8Q8qi5ruWWdHZBSrNdq1j-NkUWa9YJc"
CHAT_ID = "-1003811491120"

st.set_page_config(page_title="Login QC - MBI", layout="centered")

# --- SISTEM LOGIN ---
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False
    st.session_state['user_fullname'] = ""

if not st.session_state['authenticated']:
    st.title("🔐 Login Sistem QC")
    user_input = st.text_input("Username").lower().strip()
    pass_input = st.text_input("Password", type="password")
    
    if st.button("Masuk"):
        if user_input in USER_DB and USER_DB[user_input] == pass_input:
            st.session_state['authenticated'] = True
            st.session_state['user_fullname'] = user_input.capitalize()
            st.rerun()
        else:
            st.error("Username atau Password salah!")
else:
    # --- HALAMAN SETELAH LOGIN BERHASIL ---
    st.sidebar.write(f"👤 Petugas: **{st.session_state['user_fullname']}**")
    if st.sidebar.button("Log Out"):
        st.session_state['authenticated'] = False
        st.rerun()

    st.title(f"📦 Digital Checker")

    def simpan_so_selesai(no_so):
        with open("selesai.txt", "a") as f:
            f.write(no_so + "\n")

    def ambil_daftar_selesai():
        if os.path.exists("selesai.txt"):
            with open("selesai.txt", "r") as f:
                return [line.strip() for line in f.readlines()]
        return []

    if os.path.exists("data_so.csv"):
        df = pd.read_csv("data_so.csv")
        col_so = 'Nomor # Pesanan Penjualan'
        col_customer = 'Nama Pelanggan'
        col_tgl = 'Tanggal'
        col_item = 'Nama Barang'
        col_batch = 'Nomor Seri/Produksi'
        col_exp = 'Tgl Kadaluarsa'
        col_qty = 'Kuantitas'

        df[[col_so, col_customer, col_tgl]] = df[[col_so, col_customer, col_tgl]].ffill()

        selesai_list = ambil_daftar_selesai()
        semua_so = df[col_so].unique().tolist()
        list_so_aktif = sorted([so for so in semua_so if so not in selesai_list])

        st.write(f"Halo **{st.session_state['user_fullname']}**, sisa SO: **{len(list_so_aktif)}**")
        
        so_terpilih = st.selectbox("🎯 CARI NOMOR SO:", list_so_aktif, index=None, placeholder="Ketik nomor SO...")

        if so_terpilih:
            df_filter = df[df[col_so] == so_terpilih]
            apotek = df_filter.iloc[0][col_customer]
            tanggal = df_filter.iloc[0][col_tgl]
            
            st.info(f"**Nomor SO:** {so_terpilih}  \n**Apotek:** {apotek}")

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

            if st.button("✅ KIRIM LAPORAN", use_container_width=True, type="primary"):
                if all(status_checks) and len(status_checks) > 0:
                    # Menambahkan Nama Petugas di Laporan Telegram
                    msg = (f"✅ **LAPORAN QC SELESAI**\n\n"
                           f"👤 **Petugas:** {st.session_state['user_fullname']}\n"
                           f"📄 **No SO:** {so_terpilih}\n"
                           f"📍 **Apotek:** {apotek}\n"
                           f"📅 **Tanggal:** {tanggal}")
                    
                    requests.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={msg}&parse_mode=Markdown")
                    simpan_so_selesai(so_terpilih)
                    st.success("Laporan terkirim!")
                    st.balloons()
                    st.rerun()
                else:
                    st.error("Mohon centang semua barang!")
    else:
        st.warning("Belum ada data. Hubungi Admin.")

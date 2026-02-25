import streamlit as st
import pandas as pd
import requests
import os

# Masukkan Data Telegram Anda
TOKEN = "8765480491:AAGI8Q8qi5ruWWdHZBSrNdq1j-NkUWa9YJc"
CHAT_ID = "-1003811491120"

st.set_page_config(page_title="QC - Checker MBI", layout="centered")

st.title("📦 Digital Checker")

# Fungsi untuk membaca data yang disimpan admin
if os.path.exists("data_so.csv"):
    df = pd.read_csv("data_so.csv")
    df[['Nomor # Pesanan Penjualan', 'Nama Pelanggan', 'Tanggal']] = df[['Nomor # Pesanan Penjualan', 'Nama Pelanggan', 'Tanggal']].ffill()

    list_so = df['Nomor # Pesanan Penjualan'].unique().tolist()
    so_terpilih = st.selectbox("🎯 PILIH NOMOR SO:", ["-- Pilih SO --"] + list_so)

    if so_terpilih != "-- Pilih SO --":
        df_filter = df[df['Nomor # Pesanan Penjualan'] == so_terpilih]
        pelanggan = df_filter.iloc[0]['Nama Pelanggan']
        
        st.info(f"**PELANGGAN:** {pelanggan}")

        status_checks = []
        for index, row in df_filter.iterrows():
            if pd.notna(row['Nama Barang']):
                with st.expander(f"📦 {row['Nama Barang']}", expanded=True):
                    c1, c2 = st.columns([1, 4])
                    with c1:
                        is_ok = st.checkbox("OK", key=f"check_{index}")
                        status_checks.append(is_ok)
                    with c2:
                        st.write(f"**Batch:** {row['Nomor Seri/Produksi']} | **Qty:** {row['Kuantitas']}")

        if st.button("KIRIM LAPORAN SELESAI", use_container_width=True, type="primary"):
            if all(status_checks):
                msg = f"✅ **QC SELESAI**\n\n📍 **{pelanggan}**\n📄 **{so_terpilih}**"
                requests.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={msg}")
                st.success("Terkirim!")
else:
    st.warning("Belum ada data SO. Mohon hubungi Admin untuk upload file.")

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
    
    # Mapping nama kolom sesuai file Excel Anda
    col_so = 'Nomor # Pesanan Penjualan'
    col_customer = 'Nama Pelanggan'
    col_tgl = 'Tanggal'
    col_item = 'Nama Barang'
    col_batch = 'Nomor Seri/Produksi'
    col_exp = 'Tgl Kadaluarsa' # Kolom ini akan kita tampilkan kembali
    col_qty = 'Kuantitas'

    # Memastikan baris kosong terisi data di atasnya (ffill)
    df[[col_so, col_customer, col_tgl]] = df[[col_so, col_customer, col_tgl]].ffill()

    # PILIH NOMOR SO
    list_so = df[col_so].unique().tolist()
    so_terpilih = st.selectbox("🎯 PILIH NOMOR SO:", ["-- Pilih SO --"] + list_so)

    if so_terpilih != "-- Pilih SO --":
        # Filter data berdasarkan SO yang dipilih
        df_filter = df[df[col_so] == so_terpilih]
        
        # Ambil info untuk kotak biru
        apotek = df_filter.iloc[0][col_customer]
        tanggal = df_filter.iloc[0][col_tgl]
        
        # 1. TAMPILAN KOTAK BIRU (3 Poin Informasi)
        st.info(f"""
        **INFORMASI PESANAN:**
        1. **Nomor SO:** {so_terpilih}
        2. **Nama Apotek:** {apotek}
        3. **Tanggal SO:** {tanggal}
        """)

        st.subheader(f"📋 Daftar Barang")
        
        status_checks = []
        for index, row in df_filter.iterrows():
            if pd.notna(row[col_item]):
                with st.expander(f"📦 {row[col_item]}", expanded=True):
                    c1, c2 = st.columns([1, 4])
                    with c1:
                        # Checkbox untuk QC
                        is_ok = st.checkbox("OK", key=f"check_{index}")
                        status_checks.append(is_ok)
                    with c2:
                        # 2. MENAMPILKAN KEMBALI EXPIRED DATE
                        st.write(f"**Batch:** {row[col_batch]} | **Exp:** {row[col_exp]}")
                        st.write(f"**Jumlah:** {row[col_qty]} Pcs")

        st.divider()
        
        # TOMBOL KIRIM LAPORAN
        if st.button("✅ KIRIM LAPORAN SELESAI", use_container_width=True, type="primary"):
            if all(status_checks) and len(status_checks) > 0:
                msg = (f"✅ **LAPORAN QC SELESAI**\n\n"
                       f"📄 **No SO:** {so_terpilih}\n"
                       f"📍 **Apotek:** {apotek}\n"
                       f"📅 **Tanggal:** {tanggal}\n"
                       f"📦 **Total:** {len(df_filter)} Item\n\n"
                       f"Status: **SEMUA SUDAH SESUAI**")
                
                requests.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={msg}&parse_mode=Markdown")
                st.success(f"Laporan {so_terpilih} Berhasil Terkirim!")
                st.balloons()
            else:
                st.error("Pastikan semua item sudah diperiksa dan dicentang!")
else:
    st.warning("Data belum tersedia. Admin perlu upload file di menu samping terlebih dahulu.")

import streamlit as st
import pandas as pd
import requests
import os

# Masukkan Data Telegram Anda
TOKEN = "8765480491:AAGI8Q8qi5ruWWdHZBSrNdq1j-NkUWa9YJc"
CHAT_ID = "-1003811491120"

st.set_page_config(page_title="QC - Checker MBI", layout="centered")

st.title("📦 Digital Checker")

# --- FUNGSI DATABASE SO SELESAI ---
def simpan_so_selesai(no_so):
    with open("selesai.txt", "a") as f:
        f.write(no_so + "\n")

def ambil_daftar_selesai():
    if os.path.exists("selesai.txt"):
        with open("selesai.txt", "r") as f:
            return [line.strip() for line in f.readlines()]
    return []

# --- MENU RESET (Opsional untuk Admin) ---
# Jika ingin menghapus semua daftar selesai, hapus file selesai.txt di server

# 1. BACA DATA SO DARI ADMIN
if os.path.exists("data_so.csv"):
    df = pd.read_csv("data_so.csv")
    
    # Kolom mapping
    col_so = 'Nomor # Pesanan Penjualan'
    col_customer = 'Nama Pelanggan'
    col_tgl = 'Tanggal'
    col_item = 'Nama Barang'
    col_batch = 'Nomor Seri/Produksi'
    col_exp = 'Tgl Kadaluarsa'
    col_qty = 'Kuantitas'

    df[[col_so, col_customer, col_tgl]] = df[[col_so, col_customer, col_tgl]].ffill()

    # 2. FILTER SO YANG BELUM SELESAI
    selesai_list = ambil_daftar_selesai()
    semua_so = df[col_so].unique().tolist()
    # Hanya tampilkan SO yang tidak ada di dalam selesai_list
    list_so_aktif = [so for so in semua_so if so not in selesai_list]

    st.write(f"Sisa SO yang perlu di-QC: **{len(list_so_aktif)}**")
    
    so_terpilih = st.selectbox("🎯 PILIH NOMOR SO:", ["-- Pilih SO --"] + list_so_aktif)

    if so_terpilih != "-- Pilih SO --":
        df_filter = df[df[col_so] == so_terpilih]
        apotek = df_filter.iloc[0][col_customer]
        tanggal = df_filter.iloc[0][col_tgl]
        
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
                        is_ok = st.checkbox("OK", key=f"check_{index}")
                        status_checks.append(is_ok)
                    with c2:
                        st.write(f"**Batch:** {row[col_batch]} | **Exp:** {row[col_exp]}")
                        st.write(f"**Jumlah:** {row[col_qty]} Pcs")

        st.divider()
        
        if st.button("✅ KIRIM LAPORAN SELESAI", use_container_width=True, type="primary"):
            if all(status_checks) and len(status_checks) > 0:
                # KIRIM KE TELEGRAM
                msg = (f"✅ **LAPORAN QC SELESAI**\n\n"
                       f"📄 **No SO:** {so_terpilih}\n"
                       f"📍 **Apotek:** {apotek}\n"
                       f"📅 **Tanggal:** {tanggal}\n"
                       f"📦 **Total:** {len(df_filter)} Item")
                
                requests.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={msg}&parse_mode=Markdown")
                
                # SIMPAN KE DAFTAR SELESAI AGAR HILANG DARI LIST
                simpan_so_selesai(so_terpilih)
                
                st.success(f"Laporan {so_terpilih} terkirim dan telah dihapus dari daftar aktif!")
                st.balloons()
                
                # Refresh halaman otomatis agar SO hilang dari dropdown
                st.rerun()
            else:
                st.error("Mohon centang semua barang!")
else:
    st.warning("Data belum tersedia. Admin perlu upload file di menu samping.")

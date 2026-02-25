import streamlit as st
import pandas as pd
import requests

# Masukkan Data Telegram Anda
TOKEN = "8765480491:AAGI8Q8qi5ruWWdHZBSrNdq1j-NkUWa9YJc"
CHAT_ID = "-1003811491120"

st.set_page_config(page_title="Checker MBI - Rekap SO", layout="centered")

st.title("📦 Digital Checker - Multi SO")
st.caption("Gunakan file rekap Sales vs COGS untuk pengecekan massal")

uploaded_file = st.file_uploader("Upload File Rekap SO (Excel/CSV)", type=["csv", "xlsx"])

if uploaded_file:
    # 1. BACA DATA
    try:
        # Membaca file dan menghapus kolom yang benar-benar kosong (Unnamed)
        df = pd.read_csv(uploaded_file).dropna(axis=1, how='all')
    except:
        df = pd.read_excel(uploaded_file).dropna(axis=1, how='all')
    
    # Bersihkan nama kolom dari spasi atau karakter aneh
    df.columns = [str(c).strip() for c in df.columns]

    # 2. PERBAIKI DATA (Handle kolom kosong di tengah)
    # Mencari nama kolom yang benar walaupun ada kolom kosong di Excelnya
    col_so = 'Nomor # Pesanan Penjualan'
    col_customer = 'Nama Pelanggan'
    col_item = 'Nama Barang'
    col_qty = 'Kuantitas'
    col_batch = 'Nomor Seri/Produksi'
    col_exp = 'Tgl Kadaluarsa'
    col_tgl = 'Tanggal'

    # Mengisi baris kosong ke bawah (ffill) untuk No SO, Pelanggan, dan Tanggal
    df[[col_so, col_customer, col_tgl]] = df[[col_so, col_customer, col_tgl]].ffill()

    # 3. MENU PILIHAN SO
    list_so = df[col_so].dropna().unique().tolist()
    
    st.write("---")
    so_terpilih = st.selectbox("🎯 SILAKAN PILIH NOMOR SO:", ["-- Pilih SO --"] + list_so)

    if so_terpilih != "-- Pilih SO --":
        # Filter data berdasarkan SO yang dipilih
        df_filter = df[df[col_so] == so_terpilih]
        
        # Ambil info pelanggan
        pelanggan = df_filter.iloc[0][col_customer]
        tgl_so = df_filter.iloc[0][col_tgl]

        st.info(f"**PELANGGAN:** {pelanggan}  \n**TANGGAL:** {tgl_so}")

        st.subheader(f"📋 Daftar Item ({len(df_filter)} jenis barang)")
        
        status_checks = []
        for index, row in df_filter.iterrows():
            if pd.notna(row[col_item]):
                # Tampilan per barang
                with st.expander(f"📦 {row[col_item]}", expanded=True):
                    c1, c2 = st.columns([1, 4])
                    with c1:
                        is_ok = st.checkbox("OK", key=f"check_{index}")
                        status_checks.append(is_ok)
                    with c2:
                        st.write(f"**Batch:** {row[col_batch]} | **Exp:** {row[col_exp]}")
                        st.write(f"**Qty:** {row[col_qty]} Pcs")

        st.divider()
        
        # 4. TOMBOL KIRIM LAPORAN
        if st.button("KIRIM LAPORAN SELESAI", use_container_width=True, type="primary"):
            if all(status_checks) and len(status_checks) > 0:
                msg = (f"✅ **LAPORAN QC SELESAI (MULTI-SO)**\n\n"
                       f"📍 **Apotek:** {pelanggan}\n"
                       f"📄 **No SO:** {so_terpilih}\n"
                       f"📅 **Tanggal:** {tgl_so}\n"
                       f"📦 **Total Item:** {len(df_filter)}\n\n"
                       f"Status: **SEMUA BARANG SESUAI**")
                
                url = f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={msg}&parse_mode=Markdown"
                requests.get(url)
                st.success(f"Notifikasi untuk {so_terpilih} telah dikirim!")
                st.balloons()
            else:
                st.error("Gagal! Pastikan semua item sudah dicentang.")
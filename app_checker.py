import streamlit as st
import pandas as pd
import requests

# Masukkan Data Telegram Anda
TOKEN = "8765480491:AAGI8Q8qi5ruWWdHZBSrNdq1j-NkUWa9YJc"
CHAT_ID = "-1003811491120"

st.set_page_config(page_title="Checker Gudang MBI", layout="centered")

st.title("📦 Checker Gudang Digital")

uploaded_file = st.file_uploader("Upload File Picking (Excel/CSV)", type=["csv", "xlsx"])

if uploaded_file:
    # 1. MENGAMBIL INFORMASI HEADER (Nomor SO, Apotek, Tanggal, Picker)
    # Kita baca 5 baris pertama saja untuk ambil info header
    try:
        df_header = pd.read_csv(uploaded_file, nrows=5, header=None)
    except:
        df_header = pd.read_excel(uploaded_file, nrows=5, header=None)

    # Logika mengambil teks setelah tanda titik dua (:)
    def get_info(row_idx):
        try:
            text = str(df_header.iloc[row_idx, 1]) # Ambil kolom kedua
            return text.replace(":", "").strip()
        except:
            return "-"

    no_so = get_info(0)
    tgl_so = get_info(1)
    apotek = get_info(2) # Berdasarkan file Anda, Nama Apotek ada di baris ke-3 (indeks 2)
    picker = get_info(3)

    # Menampilkan Informasi Header di Kotak Biru
    st.info(f"""
    **INFORMASI PESANAN:**
    * **No. SO:** {no_so}
    * **Apotek:** {apotek}
    * **Tanggal:** {tgl_so}
    * **Picker:** {picker}
    """)

    # 2. MENGAMBIL DAFTAR BARANG
    # Baca ulang file, kali ini skip 7 baris untuk ambil tabel barang
    uploaded_file.seek(0) # Reset posisi baca file
    try:
        df = pd.read_csv(uploaded_file, skiprows=7)
    except:
        df = pd.read_excel(uploaded_file, skiprows=7)

    st.subheader("📋 Daftar Barang")
    
    status_checks = []
    for index, row in df.iterrows():
        if pd.notna(row['Produk']):
            with st.expander(f"📦 {row['Produk']}", expanded=True):
                col1, col2 = st.columns([1, 4])
                with col1:
                    is_ok = st.checkbox("OK", key=f"check_{index}")
                    status_checks.append(is_ok)
                with col2:
                    st.write(f"**Batch:** {row['Batch']} | **Exp:** {row['Expired']}")
                    st.write(f"**Jumlah:** {row['Qty']}")

    st.divider()
    
    if st.button("KIRIM LAPORAN KE ADMIN", use_container_width=True, type="primary"):
        if all(status_checks) and len(status_checks) > 0:
            msg = (f"✅ **LAPORAN CHECKER SELESAI**\n\n"
                   f"📍 **Apotek:** {apotek}\n"
                   f"📄 **No SO:** {no_so}\n"
                   f"👤 **Picker:** {picker}\n"
                   f"📅 **Tanggal:** {tgl_so}\n\n"
                   f"Status: **SEMUA BARANG SESUAI**")
            
            url = f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={msg}&parse_mode=Markdown"
            requests.get(url)
            st.success("Laporan terkirim ke Telegram!")
            st.balloons()
        else:
            st.error("Mohon centang semua barang terlebih dahulu!")
import streamlit as st
import pandas as pd
import requests

# Masukkan Data Telegram Anda
TOKEN = "8765480491:AAGI8Q8qi5ruWWdHZBSrNdq1j-NkUWa9YJc"
CHAT_ID = "-1003811491120"

st.set_page_config(page_title="Checker Gudang MBI", layout="centered")

st.title("📦 Checker Gudang Digital")
st.write("Upload file picking untuk memulai pengecekan.")

# Upload File
uploaded_file = st.file_uploader("Pilih file CSV/Excel", type=["csv", "xlsx"])

if uploaded_file:
    # Membaca data mulai dari baris ke-8 (skip 7 baris header judul)
    try:
        df = pd.read_csv(uploaded_file, skiprows=7)
    except:
        df = pd.read_excel(uploaded_file, skiprows=7)

    st.subheader(f"Daftar Barang - {uploaded_file.name}")
    
    # Membuat checklist
    status_checks = []
    for index, row in df.iterrows():
        # Pastikan kolom tidak kosong
        if pd.notna(row['Produk']):
            with st.expander(f"📦 {row['Produk']}", expanded=True):
                col1, col2 = st.columns([1, 4])
                with col1:
                    is_ok = st.checkbox("SESUAI", key=f"check_{index}")
                    status_checks.append(is_ok)
                with col2:
                    st.write(f"**Batch:** {row['Batch']} | **Exp:** {row['Expired']}")
                    st.write(f"**Jumlah:** {row['Qty']}")

    st.divider()
    
    # Tombol Kirim
    if st.button("KIRIM LAPORAN KE ADMIN", use_container_width=True):
        if all(status_checks) and len(status_checks) > 0:
            msg = f"✅ LAPORAN SELESAI\nFile: {uploaded_file.name}\nStatus: SEMUA BARANG SESUAI"
            url = f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={msg}"
            requests.get(url)
            st.success("Notifikasi terkirim ke Telegram Admin!")
            st.balloons()
        else:
            st.error("Gagal! Pastikan semua barang sudah dicentang.")
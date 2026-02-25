import streamlit as st
import pandas as pd

st.set_page_config(page_title="Admin Panel")
st.title("⚙️ Admin - Upload Data SO")

password = st.text_input("Masukkan Password Admin", type="password")

if password == "pickingplanmbi": # Ganti password sesuka Anda
    uploaded_file = st.file_uploader("Upload Rekap Sales vs COGS", type=["csv", "xlsx"])
    
    if uploaded_file:
        try:
            df = pd.read_csv(uploaded_file).dropna(axis=1, how='all')
        except:
            df = pd.read_excel(uploaded_file).dropna(axis=1, how='all')
        
        # Simpan permanen di server
        df.to_csv("data_so.csv", index=False)
        st.success("Data Berhasil Diperbarui! Tim QC sudah bisa melihat data ini.")

# Tambahkan ini di bagian bawah admin.py setelah proses simpan data_so.csv
import os
if st.button("Hapus Riwayat SO Selesai"): # Tombol manual jika ingin reset
    if os.path.exists("selesai.txt"):
        os.remove("selesai.txt")
        st.success("Riwayat pengerjaan telah dikosongkan!")

# Atau jika ingin otomatis reset saat upload file baru:
# (Masukkan ini di dalam blok 'if uploaded_file:')
if os.path.exists("selesai.txt"):
    os.remove("selesai.txt")

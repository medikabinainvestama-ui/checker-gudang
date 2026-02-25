import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="Admin Panel", layout="centered")

st.title("⚙️ Admin - Update Data SO")

password = st.text_input("Masukkan Password Admin", type="password")

if password == "pickingplanmbi":
    st.write("---")
    uploaded_file = st.file_uploader("Upload File Rekap Baru", type=["csv", "xlsx"])
    
    if uploaded_file:
        try:
            df = pd.read_csv(uploaded_file).dropna(axis=1, how='all')
        except:
            df = pd.read_excel(uploaded_file).dropna(axis=1, how='all')
        
        # Simpan data SO utama
        df.to_csv("data_so.csv", index=False)
        
        st.success("✅ Data Berhasil Diperbarui!")
        st.info("Riwayat SO yang sudah dikerjakan sebelumnya TETAP TERSIMPAN (Tidak muncul lagi di QC).")

    st.divider()
    
    # Opsi Reset jika benar-benar dibutuhkan (misal ganti bulan/tahun)
    st.subheader("⚠️ Zona Bahaya")
    if st.button("KOSONGKAN SEMUA RIWAYAT QC"):
        if os.path.exists("selesai.txt"):
            os.remove("selesai.txt")
            st.success("Semua riwayat pengerjaan telah dihapus. Semua SO akan muncul kembali.")
        else:
            st.info("Riwayat sudah kosong.")

# Tambahkan ini di admin.py saat upload file baru
if os.path.exists("sedang_diproses.txt"):
    os.remove("sedang_diproses.txt")

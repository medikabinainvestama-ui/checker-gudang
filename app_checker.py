import streamlit as st
import pandas as pd
import requests

# Masukkan Data Telegram Anda
TOKEN = "8765480491:AAGI8Q8qi5ruWWdHZBSrNdq1j-NkUWa9YJc"
CHAT_ID = "-1003811491120"

st.set_page_config(page_title="Checker Gudang MBI", layout="centered")

st.title("📦 Checker Gudang Digital")
st.write("Format Baru Terdeteksi (SO-2026)")

uploaded_file = st.file_uploader("Upload File Picking Baru", type=["csv", "xlsx"])

if uploaded_file:
    # Membaca file (Format baru biasanya mulai dari baris 1 atau ada header langsung)
    try:
        # Jika file CSV hasil export sistem biasanya langsung terbaca
        df = pd.read_csv(uploaded_file)
    except:
        df = pd.read_excel(uploaded_file)

    # Membersihkan data jika ada baris kosong di awal (opsional)
    df.columns = df.columns.str.strip() # hapus spasi di nama kolom
    
    # Mengambil informasi header dari baris pertama (index 0)
    if not df.empty:
        no_so = df.iloc[0]['Nomor # Pesanan Penjualan']
        tgl_so = df.iloc[0]['Tanggal']
        apotek = df.iloc[0]['Nama Pelanggan']
        
        # Menampilkan Informasi di Aplikasi
        st.info(f"""
        **DATA PESANAN:**
        * **Apotek:** {apotek}
        * **No. SO:** {no_so}
        * **Tanggal:** {tgl_so}
        """)

        st.subheader("📋 Daftar Barang")
        
        status_checks = []
        # Melakukan looping untuk setiap baris barang
        for index, row in df.iterrows():
            # Pastikan hanya menampilkan baris yang ada Nama Barang
            if pd.notna(row['Nama Barang']):
                with st.expander(f"📦 {row['Nama Barang']}", expanded=True):
                    col1, col2 = st.columns([1, 4])
                    with col1:
                        is_ok = st.checkbox("OK", key=f"check_{index}")
                        status_checks.append(is_ok)
                    with col2:
                        st.write(f"**Batch:** {row['Nomor Seri/Produksi']} | **Exp:** {row['Tgl Kadaluarsa']}")
                        st.write(f"**Jumlah:** {row['Kuantitas']} Pcs")

        st.divider()
        
        # Tombol Kirim Laporan
        if st.button("KIRIM LAPORAN KE ADMIN", use_container_width=True, type="primary"):
            if all(status_checks) and len(status_checks) > 0:
                msg = (f"✅ **LAPORAN CHECKER SELESAI**\n\n"
                       f"📍 **Apotek:** {apotek}\n"
                       f"📄 **No SO:** {no_so}\n"
                       f"📅 **Tanggal:** {tgl_so}\n\n"
                       f"Status: **SEMUA BARANG SESUAI**")
                
                url = f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={msg}&parse_mode=Markdown"
                requests.get(url)
                st.success("Laporan terkirim ke Telegram!")
                st.balloons()
            else:
                st.error("Mohon centang semua barang terlebih dahulu!")
    else:
        st.error("File kosong atau format tidak sesuai.")
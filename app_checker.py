import streamlit as st
import pandas as pd
import requests
import os
from users import USER_DB # Mengambil data akun dari file sebelah

# Masukkan Data Telegram Anda
TOKEN = "8765480491:AAGI8Q8qi5ruWWdHZBSrNdq1j-NkUWa9YJc"
CHAT_ID = "-1003811491120"

st.set_page_config(page_title="QC MBI - Team Mode", layout="centered")

# --- FUNGSI DATABASE SEDANG DIPROSES ---
def catat_sedang_diproses(no_so, nama_petugas):
    # Membaca data lama
    data = ambil_semua_proses()
    data[no_so] = nama_petugas
    # Simpan kembali
    with open("sedang_diproses.txt", "w") as f:
        for s, p in data.items():
            f.write(f"{s}|{p}\n")

def ambil_semua_proses():
    proses_dict = {}
    if os.path.exists("sedang_diproses.txt"):
        with open("sedang_diproses.txt", "r") as f:
            for line in f:
                if "|" in line:
                    s, p = line.strip().split("|")
                    proses_dict[s] = p
    return proses_dict

def hapus_dari_proses(no_so):
    data = ambil_semua_proses()
    if no_so in data:
        del data[no_so]
        with open("sedang_diproses.txt", "w") as f:
            for s, p in data.items():
                f.write(f"{s}|{p}\n")

def simpan_so_selesai(no_so):
    with open("selesai.txt", "a") as f:
        f.write(no_so.strip() + "\n")
    hapus_dari_proses(no_so)

def ambil_daftar_selesai():
    if os.path.exists("selesai.txt"):
        with open("selesai.txt", "r") as f:
            return [line.strip() for line in f.readlines()]
    return []

# --- SISTEM LOGIN ---
if 'auth' not in st.session_state:
    st.session_state['auth'] = False
    st.session_state['user'] = ""

if not st.session_state['auth']:
    st.title("🔐 Login Checker MBI")
    u_input = st.text_input("Username").lower().strip()
    p_input = st.text_input("Password", type="password")
    
    if st.button("Masuk", use_container_width=True):
        if u_input in USER_DB and USER_DB[u_input] == p_input:
            st.session_state['auth'] = True
            st.session_state['user'] = u_input.capitalize()
            st.rerun()
        else:
            st.error("Username atau Password salah!")
else:
    st.sidebar.title(f"👤 {st.session_state['user']}")
    if st.sidebar.button("Keluar (Log Out)"):
        st.session_state['auth'] = False
        st.rerun()

    st.title("📦 Digital Checker")

    if os.path.exists("data_so.csv"):
        df = pd.read_csv("data_so.csv")
        col_so = 'Nomor # Pesanan Penjualan'
        col_customer = 'Nama Pelanggan'
        col_tgl = 'Tanggal'
        col_item = 'Nama Barang'
        col_batch = 'Nomor Seri/Produksi'
        col_exp = 'Tgl Kadaluarsa'
        col_qty = 'Kuantitas'

        df[col_so] = df[col_so].astype(str).str.strip()
        df[[col_so, col_customer, col_tgl]] = df[[col_so, col_customer, col_tgl]].ffill()

        selesai_list = ambil_daftar_selesai()
        sedang_diproses = ambil_semua_proses()
        
        semua_so = df[col_so].unique().tolist()
        list_so_aktif = sorted([so for so in semua_so if so not in selesai_list])

        # MEMBUAT LABEL DROPDOWN DENGAN NAMA PETUGAS
        label_opsi = []
        mapping_opsi = {} # Untuk mengembalikan label ke No SO asli
        
        for so in list_so_aktif:
            if so in sedang_diproses and sedang_diproses[so] != st.session_state['user']:
                label = f"{so} (🟠 Sedang dicek oleh {sedang_diproses[so]})"
            elif so in sedang_diproses and sedang_diproses[so] == st.session_state['user']:
                label = f"{so} (🔵 Sedang Anda kerjakan)"
            else:
                label = so
            label_opsi.append(label)
            mapping_opsi[label] = so

        st.write(f"Sisa antrean: **{len(list_so_aktif)}** SO")
        
        opsi_terpilih = st.selectbox(
            "🎯 CARI NOMOR SO:", 
            label_opsi, 
            index=None, 
            placeholder="Ketik nomor SO di sini..."
        )

        if opsi_terpilih:
            so_asli = mapping_opsi[opsi_terpilih]
            
            # CEK APAKAH SO SEDANG DIKERJAKAN ORANG LAIN
            if so_asli in sedang_diproses and sedang_diproses[so_asli] != st.session_state['user']:
                st.warning(f"⚠️ Perhatian: SO ini sedang dibuka oleh **{sedang_diproses[so_asli]}**. Mohon koordinasi agar tidak terjadi double check.")

            # Catat bahwa user ini sedang membuka SO tersebut
            catat_sedang_diproses(so_asli, st.session_state['user'])
            
            df_filter = df[df[col_so] == so_asli]
            apotek = df_filter.iloc[0][col_customer]
            tanggal = df_filter.iloc[0][col_tgl]
            
            st.info(f"**Nomor SO:** {so_asli}  \n**Apotek:** {apotek}")

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
                    msg = (f"✅ **LAPORAN QC SELESAI**\n\n"
                           f"👤 **Petugas:** {st.session_state['user']}\n"
                           f"📄 **No SO:** {so_asli}\n"
                           f"📍 **Apotek:** {apotek}")
                    
                    requests.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={msg}&parse_mode=Markdown")
                    simpan_so_selesai(so_asli)
                    st.success("Laporan terkirim!")
                    st.balloons()
                    st.rerun()
                else:
                    st.error("Mohon centang semua barang!")
    else:
        st.warning("Data belum tersedia. Hubungi Admin.")

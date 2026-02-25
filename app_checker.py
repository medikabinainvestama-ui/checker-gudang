import streamlit as st
import pandas as pd
import requests
import os
from users import USER_DB # Mengambil data akun dari file sebelah

# Masukkan Data Telegram Anda
TOKEN = "8765480491:AAGI8Q8qi5ruWWdHZBSrNdq1j-NkUWa9YJc"
CHAT_ID = "-1003811491120"

st.set_page_config(page_title="QC MBI - Auto Lock", layout="centered")

# --- FUNGSI DATABASE PENGUNCIAN ---
def ambil_semua_lock():
    locks = {}
    if os.path.exists("locks.txt"):
        try:
            with open("locks.txt", "r") as f:
                for line in f:
                    if "|" in line:
                        s, p = line.strip().split("|")
                        locks[s] = p
        except:
            pass
    return locks

def kunci_so(no_so, nama_petugas):
    locks = ambil_semua_lock()
    if no_so not in locks:
        with open("locks.txt", "a") as f:
            f.write(f"{no_so}|{nama_petugas}\n")
            f.flush()

def buka_kunci_so(no_so):
    locks = ambil_semua_lock()
    if no_so in locks:
        del locks[no_so]
        with open("locks.txt", "w") as f:
            for s, p in locks.items():
                f.write(f"{s}|{p}\n")
            f.flush()

def simpan_so_selesai(no_so):
    with open("selesai.txt", "a") as f:
        f.write(no_so.strip() + "\n")
        f.flush()
    buka_kunci_so(no_so)

def ambil_daftar_selesai():
    if os.path.exists("selesai.txt"):
        with open("selesai.txt", "r") as f:
            return [line.strip() for line in f.readlines()]
    return []

# --- SISTEM LOGIN ---
if 'auth' not in st.session_state:
    st.session_state['auth'] = False
    st.session_state['user'] = ""
if 'last_so' not in st.session_state:
    st.session_state['last_so'] = None

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
    if st.sidebar.button("Log Out"):
        # Jika logout, pastikan kunci dilepas
        if st.session_state['last_so']:
            buka_kunci_so(st.session_state['last_so'])
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
        
        semua_so = df[col_so].unique().tolist()
        list_so_aktif = sorted([so for so in semua_so if so not in selesai_list])

        # Dropdown
        so_terpilih = st.selectbox(
            "🎯 CARI NOMOR SO:", 
            list_so_aktif, 
            index=None, 
            placeholder="Ketik nomor SO di sini..."
        )

        # --- LOGIKA AUTO UNLOCK (PENTING) ---
        # Jika user pindah SO atau kembali ke None, buka kunci SO sebelumnya
        if st.session_state['last_so'] and st.session_state['last_so'] != so_terpilih:
            buka_kunci_so(st.session_state['last_so'])
            st.session_state['last_so'] = None
            st.rerun()

        if so_terpilih:
            # Cek status kunci terbaru
            current_locks = ambil_semua_lock()
            
            if so_terpilih in current_locks and current_locks[so_terpilih] != st.session_state['user']:
                st.error(f"🚫 SO ini sedang dibuka oleh **{current_locks[so_terpilih]}**")
                st.info("Silakan pilih SO lain atau tunggu rekan Anda kembali ke menu utama.")
                if st.button("Cek Apakah Sudah Dilepas?"):
                    st.rerun()
            else:
                # Kunci untuk diri sendiri
                kunci_so(so_terpilih, st.session_state['user'])
                st.session_state['last_so'] = so_terpilih
                
                df_filter = df[df[col_so] == so_terpilih]
                apotek = df_filter.iloc[0][col_customer]
                tanggal = df_filter.iloc[0][col_tgl]
                
                st.info(f"**Apotek:** {apotek} | **No SO:** {so_terpilih}")

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
                                st.write(f"**Qty:** {row[col_qty]} Pcs")

                if st.button("✅ KIRIM LAPORAN SELESAI", use_container_width=True, type="primary"):
                    if all(status_checks) and len(status_checks) > 0:
                        msg = f"✅ **QC SELESAI**\n👤 {st.session_state['user']}\n📄 {so_terpilih}\n📍 {apotek}"
                        requests.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={msg}")
                        simpan_so_selesai(so_terpilih)
                        st.session_state['last_so'] = None # Reset state setelah selesai
                        st.success("Laporan terkirim!")
                        st.balloons()
                        st.rerun()
                    else:
                        st.error("Mohon centang semua barang!")
    else:
        st.warning("Data belum tersedia. Hubungi Admin.")

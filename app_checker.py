import streamlit as st
import pandas as pd
import requests
import os
from users import USER_DB

# --- KONFIGURASI TELEGRAM ---
TOKEN = "8765480491:AAGI8Q8qi5ruWWdHZBSrNdq1j-NkUWa9YJc"
CHAT_ID = "-1003811491120"

st.set_page_config(page_title="QC MBI - Filter Header", layout="centered")

# --- FUNGSI DATABASE PENGUNCIAN & SELESAI ---
def ambil_semua_lock():
    locks = {}
    if os.path.exists("locks.txt"):
        try:
            with open("locks.txt", "r") as f:
                for line in f:
                    if "|" in line:
                        s, p = line.strip().split("|")
                        locks[s] = p
        except: pass
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

# --- SISTEM LOGIN & NAVIGASI ---
if 'auth' not in st.session_state:
    st.session_state['auth'] = False
    st.session_state['user'] = ""
if 'page' not in st.session_state:
    st.session_state['page'] = "search"
if 'selected_so' not in st.session_state:
    st.session_state['selected_so'] = None

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
        if st.session_state['selected_so']:
            buka_kunci_so(st.session_state['selected_so'])
        st.session_state['auth'] = False
        st.rerun()

    st.title("📦 Digital Checker")

    if os.path.exists("data_so.csv"):
        df = pd.read_csv("data_so.csv")
        
        # Penamaan Kolom sesuai file baru Anda
        col_so = 'Nomor Pesanan'
        col_customer = 'Pelanggan'
        col_tgl = 'Tanggal'
        col_item = 'Barang'
        col_batch = 'Nomor Seri'
        col_exp = 'Tanggal Kedaluwarsa'
        col_qty = 'Kuantitas'

        # --- LOGIKA PEMBERSIHAN HEADER BERULANG ---
        # Membuang baris di mana kolom 'Nomor Pesanan' berisi tulisan 'Nomor Pesanan'
        df = df[df[col_so] != col_so]
        
        # Membersihkan spasi dan mengisi baris kosong (ffill)
        df[col_so] = df[col_so].astype(str).str.strip()
        df[[col_so, col_customer, col_tgl]] = df[[col_so, col_customer, col_tgl]].ffill()

        selesai_list = ambil_daftar_selesai()
        semua_so = [s for s in df[col_so].unique().tolist() if s != 'nan']
        list_so_aktif = sorted([so for so in semua_so if so not in selesai_list])

        # --- HALAMAN 1: PENCARIAN ---
        if st.session_state['page'] == "search":
            st.subheader("🎯 Cari Nomor SO")
            st.write(f"Antrean: **{len(list_so_aktif)}** SO")
            
            so_dipilih = st.selectbox("Pilih No SO:", list_so_aktif, index=None, placeholder="Ketik nomor SO...")

            if so_dipilih:
                current_locks = ambil_semua_lock()
                if so_dipilih in current_locks and current_locks[so_dipilih] != st.session_state['user']:
                    st.error(f"🚫 Sedang dibuka oleh **{current_locks[so_dipilih]}**")
                else:
                    kunci_so(so_dipilih, st.session_state['user'])
                    st.session_state['selected_so'] = so_dipilih
                    st.session_state['page'] = "list_barang"
                    st.rerun()

        # --- HALAMAN 2: DETAIL BARANG ---
        elif st.session_state['page'] == "list_barang":
            so_aktif = st.session_state['selected_so']
            
            if st.button("⬅️ Kembali"):
                buka_kunci_so(so_aktif)
                st.session_state['selected_so'] = None
                st.session_state['page'] = "search"
                st.rerun()

            df_filter = df[df[col_so] == so_aktif]
            
            # Info Header
            nama_apotek = df_filter.iloc[0][col_customer]
            tanggal_so = df_filter.iloc[0][col_tgl]
            total_jenis = len(df_filter[df_filter[col_item].notna()])
            # Pastikan Qty adalah angka sebelum dijumlah
            df_filter[col_qty] = pd.to_numeric(df_filter[col_qty], errors='coerce').fillna(0)
            total_qty_data = df_filter[col_qty].sum()

            st.info(f"📌 **SO:** {so_aktif}")
            c1, c2 = st.columns(2)
            with c1:
                st.markdown(f"🏢 **Apotek:**\n{nama_apotek}")
                st.markdown(f"📦 **Total:** {total_jenis} Jenis")
            with c2:
                st.markdown(f"📅 **Tanggal:**\n{tanggal_so}")
                st.markdown(f"🔢 **Qty SO:** {int(total_qty_data)} Pcs")
            
            st.divider()

            valid_all = True
            list_input_qty = []

            for index, row in df_filter.iterrows():
                if pd.notna(row[col_item]):
                    qty_target = int(float(row[col_qty]))
                    exp_date = row[col_exp] if pd.notna(row[col_exp]) else "-"
                    batch_no = row[col_batch] if pd.notna(row[col_batch]) else "-"

                    with st.expander(f"📦 {row[col_item]}", expanded=True):
                        st.write(f"**Batch:** {batch_no} | **Exp:** {exp_date} | **Qty SO:** {qty_target}")
                        
                        col_in, col_st = st.columns([3, 2])
                        with col_in:
                            input_val = st.number_input(f"Input Qty Fisik", min_value=0, step=1, key=f"q_{index}", value=0)
                        with col_st:
                            st.write("")
                            if input_val == 0:
                                st.warning("Kosong")
                                valid_all = False
                            elif input_val == qty_target:
                                st.success("✅ OK")
                            else:
                                st.error("❌ Selisih")
                                valid_all = False
                    list_input_qty.append(input_val)

            if st.button("✅ KIRIM LAPORAN", use_container_width=True, type="primary"):
                if valid_all:
                    msg = (f"✅ **QC SELESAI**\nPetugas: {st.session_state['user']}\nSO: {so_aktif}\nApotek: {nama_apotek}\nTotal Qty: {int(sum(list_input_qty))}")
                    requests.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={msg}")
                    simpan_so_selesai(so_aktif)
                    st.session_state['selected_so'] = None
                    st.session_state['page'] = "search"
                    st.rerun()
                else:
                    st.error("Pastikan semua Qty sudah sesuai!")
    else:
        st.warning("Data belum tersedia. Silakan upload file di Admin.")

import streamlit as st
import pandas as pd
import requests
import os
from datetime import datetime
from users import USER_DB

# --- KONFIGURASI TELEGRAM ---
TOKEN = "8765480491:AAGI8Q8qi5ruWWdHZBSrNdq1j-NkUWa9YJc"
CHAT_ID = "-1003811491120"

st.set_page_config(page_title="QC MBI - Checker", layout="centered")

# --- INISIALISASI SESSION STATE ---
if 'auth' not in st.session_state:
    st.session_state['auth'] = False
if 'user' not in st.session_state:
    st.session_state['user'] = ""
if 'page' not in st.session_state:
    st.session_state['page'] = "search"
if 'selected_so' not in st.session_state:
    st.session_state['selected_so'] = None

# --- FUNGSI DATABASE & LOGGING ---
def simpan_rekap_data(data_list):
    file_rekap = "rekap_qc.csv"
    df_baru = pd.DataFrame(data_list)
    if not os.path.exists(file_rekap):
        df_baru.to_csv(file_rekap, index=False)
    else:
        df_baru.to_csv(file_rekap, mode='a', header=False, index=False)

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

# --- SISTEM LOGIN ---
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
    # SIDEBAR
    st.sidebar.title(f"👤 {st.session_state['user']}")
    if os.path.exists("rekap_qc.csv"):
        rekap_df = pd.read_csv("rekap_qc.csv")
        st.sidebar.download_button(
            label="📊 Download Data Rekap QC",
            data=rekap_df.to_csv(index=False),
            file_name=f"rekap_qc_{datetime.now().strftime('%d%m%Y')}.csv",
            mime="text/csv"
        )
    if st.sidebar.button("Log Out"):
        if st.session_state['selected_so']:
            buka_kunci_so(st.session_state['selected_so'])
        st.session_state['auth'] = False
        st.rerun()

    if os.path.exists("data_so.csv"):
        df = pd.read_csv("data_so.csv")
        df.columns = df.columns.str.strip() 
        
        col_so = 'Nomor # Pesanan Penjualan'
        col_customer = 'Pelanggan'
        col_tgl = 'Tanggal Pesanan Penjualan'
        col_kode = 'Kode #'
        col_item = 'Nama Barang'
        col_batch = 'No Seri/Produksi'
        col_exp = 'Tgl Kadaluarsa'
        col_qty = 'Kuantitas'

        df[col_so] = df[col_so].astype(str).str.strip()
        df[[col_so, col_customer, col_tgl]] = df[[col_so, col_customer, col_tgl]].ffill()
        df = df[df[col_item].notna()]

        selesai_list = ambil_daftar_selesai()
        semua_so = [s for s in df[col_so].unique().tolist() if s not in ['nan', 'None', '']]
        list_so_aktif = sorted([so for so in semua_so if so not in selesai_list])

        # --- HALAMAN 1: PENCARIAN ---
        if st.session_state['page'] == "search":
            st.title("🎯 Cari Nomor SO")
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

        # --- HALAMAN 2: LIST BARANG (TAMPILAN DIKEMBALIKAN) ---
        elif st.session_state['page'] == "list_barang":
            so_aktif = st.session_state['selected_so']
            if st.button("⬅️ Kembali"):
                buka_kunci_so(so_aktif)
                st.session_state['selected_so'] = None
                st.session_state['page'] = "search"
                st.rerun()

            df_filter = df[df[col_so] == so_aktif].copy()
            nama_apotek = df_filter.iloc[0][col_customer]
            tanggal_so = df_filter.iloc[0][col_tgl]
            df_filter[col_qty] = pd.to_numeric(df_filter[col_qty], errors='coerce').fillna(0)

            # HEADER INFORMASI LENGKAP
            st.info(f"📌 **Nomor SO:** {so_aktif}")
            h_col1, h_col2 = st.columns(2)
            with h_col1:
                st.markdown(f"🏢 **Apotek:**\n{nama_apotek}")
            with h_col2:
                st.markdown(f"📅 **Tanggal SO:**\n{tanggal_so}")
            
            st.divider()

            valid_all = True
            list_data_final = []

            for index, row in df_filter.iterrows():
                qty_target = int(float(row[col_qty]))
                exp_date = row[col_exp] if pd.notna(row[col_exp]) else "-"
                batch_no = row[col_batch] if pd.notna(row[col_batch]) else "-"
                kode_brg = row[col_kode] if pd.notna(row[col_kode]) else "-"

                with st.expander(f"📦 {row[col_item]}", expanded=True):
                    # Baris Info Barang (Tulisan Batch & Exp Lengkap)
                    c_info, c_note_toggle = st.columns([4.5, 1])
                    with c_info:
                        st.write(f"**Batch:** {batch_no} | **Exp:** {exp_date} | **Qty SO:** {qty_target}")
                    with c_note_toggle:
                        is_note_active = st.checkbox("📝", key=f"tog_{index}")
                    
                    # Baris Input Qty
                    col_in, col_st = st.columns([3, 2])
                    with col_in:
                        input_val = st.number_input(f"Input Qty", min_value=0, step=1, key=f"q_{index}", value=0, label_visibility="collapsed")
                    with col_st:
                        if input_val == qty_target and input_val > 0:
                            st.success("✅ OK")
                        elif input_val == 0:
                            st.warning("Kosong")
                            valid_all = False
                        else:
                            st.error("❌ Selisih")
                            valid_all = False
                    
                    # Box Catatan jika 📝 diklik
                    note_val = ""
                    if is_note_active:
                        note_val = st.text_input("Catatan:", key=f"n_{index}")
                
                list_data_final.append({
                    "Waktu": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Petugas": st.session_state['user'],
                    "Nomor_SO": so_aktif,
                    "Apotek": nama_apotek,
                    "Kode": kode_brg,
                    "Barang": row[col_item],
                    "Batch": batch_no,
                    "Exp": exp_date,
                    "Qty_SO": qty_target,
                    "Qty_Fisik": input_val,
                    "Catatan": note_val.strip()
                })

            st.divider()

            if st.button("✅ SELESAI & KIRIM LAPORAN", use_container_width=True, type="primary"):
                if valid_all:
                    simpan_rekap_data(list_data_final)
                    
                    detail_pesan = ""
                    for d in list_data_final:
                        if d['Catatan'] != "":
                            detail_pesan += f"- {d['Kode']} | {d['Batch']} | {d['Exp']} ({int(d['Qty_Fisik'])} pcs)\n  🗒 Note: {d['Catatan']}\n"
                    if detail_pesan == "": detail_pesan = "_Tidak ada catatan khusus._\n"

                    msg = (f"✅ **QC SELESAI**\n👤 Petugas: {st.session_state['user']}\n📄 No SO: {so_aktif}\n📍 Apotek: {nama_apotek}\n---------------------------\n{detail_pesan}---------------------------")
                    requests.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={msg}")
                    
                    simpan_so_selesai(so_aktif)
                    st.session_state['selected_so'] = None
                    st.session_state['page'] = "search"
                    st.success("Terkirim & Tersimpan!")
                    st.balloons()
                    st.rerun()
                else:
                    st.error("Gagal! Pastikan semua Qty sudah OK.")
    else:
        st.warning("Data SO tidak ditemukan.")

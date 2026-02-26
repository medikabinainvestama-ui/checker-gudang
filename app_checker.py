import streamlit as st
import pandas as pd
import requests
import os
from datetime import datetime
from users import USER_DB

# --- KONFIGURASI TELEGRAM ---
TOKEN = "8765480491:AAGI8Q8qi5ruWWdHZBSrNdq1j-NkUWa9YJc"
CHAT_ID = "-1003811491120"

st.set_page_config(page_title="QC MBI - Checker", layout="wide")

# --- STYLING CSS UNTUK WARNA TAB ---
st.markdown("""
    <style>
    .stExpander { border: 1px solid #ddd; border-radius: 8px; margin-bottom: 10px; }
    </style>
""", unsafe_allow_html=True)

# --- INISIALISASI SESSION STATE ---
if 'auth' not in st.session_state:
    params = st.query_params
    if "user" in params and params["user"] in USER_DB:
        st.session_state['auth'] = True
        st.session_state['user'] = params["user"].capitalize()
    else:
        st.session_state['auth'] = False

if 'page' not in st.session_state:
    st.session_state['page'] = "search"
if 'selected_so' not in st.session_state:
    st.session_state['selected_so'] = None
if 'qc_drafts' not in st.session_state:
    st.session_state['qc_drafts'] = {}

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
    if os.path.exists("selesai.txt"):
        with open("selesai.txt", "a") as f:
            f.write(no_so.strip() + "\n")
            f.flush()
    else:
        with open("selesai.txt", "w") as f:
            f.write(no_so.strip() + "\n")
            f.flush()
    buka_kunci_so(no_so)
    if no_so in st.session_state['qc_drafts']:
        del st.session_state['qc_drafts'][no_so]

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
            st.query_params["user"] = u_input
            st.rerun()
        else:
            st.error("Username atau Password salah!")
else:
    # --- SIDEBAR MENU ---
    st.sidebar.title(f"👤 {st.session_state['user']}")
    menu = st.sidebar.radio("Menu Utama", ["Pemeriksaan QC", "Dashboard Admin"])
    
    if st.sidebar.button("Log Out"):
        if st.session_state['selected_so']:
            buka_kunci_so(st.session_state['selected_so'])
        st.session_state['auth'] = False
        st.query_params.clear()
        st.rerun()

    if os.path.exists("data_so.csv"):
        df_master = pd.read_csv("data_so.csv")
        df_master.columns = df_master.columns.str.strip()
        
        col_so = 'Nomor # Pesanan Penjualan'
        col_customer = 'Pelanggan'
        col_tgl = 'Tanggal Pesanan Penjualan'
        col_kode = 'Kode #'
        col_item = 'Nama Barang'
        col_batch = 'No Seri/Produksi'
        col_exp = 'Tgl Kadaluarsa'
        col_qty = 'Kuantitas'

        df_master[col_so] = df_master[col_so].astype(str).str.strip()
        df_master[[col_so, col_customer, col_tgl]] = df_master[[col_so, col_customer, col_tgl]].ffill()
        df_master = df_master[df_master[col_item].notna()]

        if menu == "Pemeriksaan QC":
            selesai_list = ambil_daftar_selesai()
            semua_so = [s for s in df_master[col_so].unique().tolist() if s not in ['nan', 'None', '']]
            list_so_aktif = sorted([so for so in semua_so if so not in selesai_list])

            if st.session_state['page'] == "search":
                st.subheader("🎯 Cari Nomor SO")
                so_dipilih = st.selectbox("Pilih No SO:", list_so_aktif, index=None, placeholder="Ketik nomor SO...")
                if so_dipilih:
                    current_locks = ambil_semua_lock()
                    if so_dipilih in current_locks and current_locks[so_dipilih] != st.session_state['user']:
                        st.error(f"🚫 Sedang dibuka oleh **{current_locks[so_dipilih]}**")
                    else:
                        kunci_so(so_dipilih, st.session_state['user'])
                        st.session_state['selected_so'] = so_dipilih
                        st.session_state['page'] = "list_barang"
                        if so_dipilih not in st.session_state['qc_drafts']:
                            st.session_state['qc_drafts'][so_dipilih] = {}
                        st.rerun()

            elif st.session_state['page'] == "list_barang":
                so_aktif = st.session_state['selected_so']
                if st.button("⬅️ Kembali ke Pencarian"):
                    buka_kunci_so(so_aktif)
                    st.session_state['selected_so'] = None
                    st.session_state['page'] = "search"
                    st.rerun()

                df_filter = df_master[df_master[col_so] == so_aktif].copy()
                nama_apotek = df_filter.iloc[0][col_customer]
                tanggal_so = df_filter.iloc[0][col_tgl]
                df_filter[col_qty] = pd.to_numeric(df_filter[col_qty], errors='coerce').fillna(0)
                
                total_jenis = len(df_filter)
                total_qty_so_val = int(df_filter[col_qty].sum())

                st.info(f"📌 **Nomor SO:** {so_aktif}")
                
                h_col1, h_col2 = st.columns(2)
                with h_col1:
                    st.markdown(f"🏢 **Apotek:** {nama_apotek}")
                    st.markdown(f"📅 **Tanggal SO:** {tanggal_so}")
                with h_col2:
                    st.markdown(f"💊 **Total Jenis:** {total_jenis} Item")
                    st.markdown(f"🔢 **Total Qty SO:** {total_qty_so_val} Pcs")
                
                st.divider()

                valid_all = True
                list_data_final = []
                draft_so = st.session_state['qc_drafts'].get(so_aktif, {})

                for index, row in df_filter.iterrows():
                    qty_target = int(float(row[col_qty]))
                    exp_date = row[col_exp] if pd.notna(row[col_exp]) else "-"
                    batch_no = row[col_batch] if pd.notna(row[col_batch]) else "-"
                    kode_brg = row[col_kode] if pd.notna(row[col_kode]) else "-"
                    
                    val_qty_awal = draft_so.get(f"q_{index}", 0)
                    val_note_awal = draft_so.get(f"n_{index}", "")
                    val_tog_awal = draft_so.get(f"tog_{index}", False)

                    label_status = ""
                    if val_qty_awal == qty_target and val_qty_awal > 0:
                        label_status = " ✅"
                    elif val_qty_awal > 0 and val_qty_awal != qty_target:
                        label_status = " ⚠️"

                    # --- EXPANDER ---
                    with st.expander(f"💊 {row[col_item]}{label_status}", expanded=False):
                        # Info Item (KODE BARANG DI DEPAN BATCH)
                        c_info, c_note_toggle = st.columns([4.5, 1])
                        c_info.write(f"**Code:** {kode_brg} | **Batch:** {batch_no} | **Exp:** {exp_date} | **Qty:** {qty_target}")
                        is_note_active = c_note_toggle.checkbox("📝", key=f"tog_ui_{index}", value=val_tog_awal)
                        draft_so[f"tog_{index}"] = is_note_active

                        input_val = st.number_input(f"Qty Input", min_value=0, step=1, key=f"q_ui_{index}", value=val_qty_awal, label_visibility="collapsed")
                        draft_so[f"q_{index}"] = input_val
                        
                        if input_val == qty_target and input_val > 0:
                            st.success(f"Jumlah Sesuai: {input_val}")
                        elif input_val > 0:
                            st.error(f"Selisih! Input: {input_val} / SO: {qty_target}")
                            valid_all = False
                        else:
                            valid_all = False
                        
                        note_val = ""
                        if is_note_active:
                            note_val = st.text_input("Catatan:", key=f"n_ui_{index}", value=val_note_awal)
                            draft_so[f"n_{index}"] = note_val.strip()
                    
                    list_data_final.append({
                        "Waktu": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "Petugas": st.session_state['user'],
                        "SO": so_aktif,
                        "Apotek": nama_apotek,
                        "Kode": kode_brg,
                        "Item": row[col_item],
                        "Batch": batch_no,
                        "Exp": exp_date,
                        "Qty_SO": qty_target,
                        "Qty_Fisik": input_val,
                        "Note": note_val.strip()
                    })

                st.divider()
                if st.button("✅ SELESAI & KIRIM LAPORAN", use_container_width=True, type="primary"):
                    if valid_all:
                        simpan_rekap_data(list_data_final)
                        detail_msg = ""
                        for d in list_data_final:
                            if d['Note'] != "":
                                detail_msg += f"- {d['Kode']} | {d['Batch']} | {d['Exp']} ({int(d['Qty_Fisik'])} pcs)\n  🗒 Note: {d['Note']}\n"
                        
                        msg = f"✅ **QC SELESAI**\n👤 Petugas: {st.session_state['user']}\n📄 No SO: {so_aktif}\n📍 Apotek: {nama_apotek}\n---------------------------\n{detail_msg if detail_msg else '_Tanpa Catatan_'}\n---------------------------"
                        requests.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={msg}")
                        
                        simpan_so_selesai(so_aktif)
                        st.session_state['selected_so'] = None
                        st.session_state['page'] = "search"
                        st.success("Terkirim!")
                        st.balloons()
                        st.rerun()
                    else:
                        st.error("Gagal! Pastikan semua barang sudah sesuai.")

        elif menu == "Dashboard Admin":
            st.subheader("📊 Dashboard Report QC")
            if os.path.exists("rekap_qc.csv"):
                df_rekap = pd.read_csv("rekap_qc.csv")
                selesai_count = len(df_rekap['SO'].unique())
                m1, m2, m3 = st.columns(3)
                m1.metric("Total SO Selesai", selesai_count)
                m2.metric("Total Item Dicek", len(df_rekap))
                m3.metric("Petugas Aktif", len(df_rekap['Petugas'].unique()))
                st.divider()
                search_term = st.text_input("Filter Apotek / No SO:")
                df_filtered = df_rekap[df_rekap.apply(lambda row: search_term.lower() in row.astype(str).str.lower().values, axis=1)]
                st.dataframe(df_filtered, use_container_width=True)
                st.download_button(label="📥 Download Rekap CSV", data=df_rekap.to_csv(index=False), file_name=f"Report_QC_{datetime.now().strftime('%d%m%Y')}.csv", mime="text/csv")
            else:
                st.warning("Belum ada data QC.")
    else:
        st.error("File data_so.csv tidak ditemukan.")

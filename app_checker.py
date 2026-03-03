import streamlit as st
import pandas as pd
import requests
import os
import re
import json
from datetime import datetime
from users import USER_DB

# --- KONFIGURASI TELEGRAM ---
TOKEN = "8765480491:AAGI8Q8qi5ruWWdHZBSrNdq1j-NkUWa9YJc"
CHAT_ID = "-1003811491120"

st.set_page_config(page_title="QC MBI - Checker Center", layout="wide")

# --- INISIALISASI SESSION STATE (PENGATURAN & AUTH) ---
if 'theme' not in st.session_state: st.session_state['theme'] = "Terang"
if 'font_size' not in st.session_state: st.session_state['font_size'] = 16
if 'auth' not in st.session_state:
    params = st.query_params
    if "u" in params and params["u"] in USER_DB:
        st.session_state['auth'] = True
        st.session_state['user'] = params["u"].capitalize()
    else:
        st.session_state['auth'] = False

if 'user' not in st.session_state: st.session_state['user'] = ""
if 'page' not in st.session_state: st.session_state['page'] = "search"
if 'selected_so' not in st.session_state: st.session_state['selected_so'] = None
if 'qc_drafts' not in st.session_state: st.session_state['qc_drafts'] = {}

# --- STYLING CSS DINAMIS (TEMA & FONT) ---
theme_bg = "#ffffff" if st.session_state['theme'] == "Terang" else "#1e1e1e"
theme_text = "#000000" if st.session_state['theme'] == "Terang" else "#ffffff"
card_bg = "#f0f2f6" if st.session_state['theme'] == "Terang" else "#333333"
pending_bg = "#ffffff" if st.session_state['theme'] == "Terang" else "#444444"

st.markdown(f"""
    <style>
    footer {{visibility: hidden !important;}}
    #MainMenu {{visibility: hidden !important;}}
    .viewerBadge_container__1QSob, .viewerBadge_link__1QSob, .st-emotion-cache-1aege4m, .st-emotion-cache-zq5wrt,
    div[data-testid="stStatusWidget"], div[class^="viewerBadge"] {{ display: none !important; }}
    
    /* Font Size & Theme */
    html, body, [data-testid="stWidgetLabel"] p, .stMarkdown p, .stSelectbox label, .stSlider label {{
        font-size: {st.session_state['font_size']}px !important;
        color: {theme_text};
    }}
    .stApp {{ background-color: {theme_bg}; }}
    
    table, thead, tbody, th, td {{ text-align: center !important; vertical-align: middle !important; }}
    .block-container {{ padding-top: 2rem !important; padding-bottom: 0rem !important; }}
    
    div[data-testid="stExpander"] {{ border: 1px solid #ddd; border-radius: 8px; margin-bottom: -15px !important; }}
    
    .metric-card {{
        background-color: {card_bg};
        padding: 15px;
        border-radius: 10px;
        text-align: center;
        border: 1px solid #e0e0e0;
        margin-bottom: 10px;
    }}

    .status-ok {{ background-color: #d4edda !important; border-radius: 8px; border-left: 10px solid #28a745; margin-bottom: -15px !important; }}
    .status-err {{ background-color: #f8d7da !important; border-radius: 8px; border-left: 10px solid #dc3545; margin-bottom: -15px !important; }}
    .status-pending {{ background-color: {pending_bg} !important; border-radius: 8px; border-left: 10px solid #6c757d; margin-bottom: -15px !important; }}
    </style>
""", unsafe_allow_html=True)

# --- FUNGSI DATABASE & TOOLS ---
def update_password_db(username, new_password):
    USER_DB[username.lower()] = new_password
    with open("users.py", "w") as f:
        f.write(f"USER_DB = {json.dumps(USER_DB, indent=4)}")

def get_user_photo(username):
    photo_path = f"photos/{username.lower()}.png"
    return photo_path if os.path.exists(photo_path) else None

def simpan_draft_ke_file(so_aktif, draft_data):
    if not os.path.exists("drafts"): os.makedirs("drafts")
    with open(f"drafts/draft_{so_aktif}.json", "w") as f: json.dump(draft_data, f)

def muat_draft_dari_file(so_aktif):
    file_path = f"drafts/draft_{so_aktif}.json"
    if os.path.exists(file_path):
        try:
            with open(file_path, "r") as f: return json.load(f)
        except: return {}
    return {}

def hapus_file_draft(so_aktif):
    file_path = f"drafts/draft_{so_aktif}.json"
    if os.path.exists(file_path): os.remove(file_path)

def ambil_semua_lock():
    locks = {}
    if os.path.exists("locks.txt"):
        try:
            with open("locks.txt", "r") as f:
                for line in f:
                    if "|" in line:
                        s, p = line.strip().split("|"); locks[s] = p
        except: pass
    return locks

def kunci_so(no_so, nama_petugas):
    locks = ambil_semua_lock()
    if no_so not in locks:
        with open("locks.txt", "a") as f: f.write(f"{no_so}|{nama_petugas}\n"); f.flush()

def buka_kunci_so(no_so):
    locks = ambil_semua_lock()
    if no_so in locks:
        del locks[no_so]
        with open("locks.txt", "w") as f:
            for s, p in locks.items(): f.write(f"{s}|{p}\n"); f.flush()

def ambil_daftar_selesai():
    if os.path.exists("selesai.txt"):
        with open("selesai.txt", "r") as f: return [line.strip() for line in f.readlines()]
    return []

def simpan_rekap_data(data_list):
    file_rekap = "rekap_qc.csv"
    df_baru = pd.DataFrame(data_list)
    if not os.path.exists(file_rekap): df_baru.to_csv(file_rekap, index=False)
    else: df_baru.to_csv(file_rekap, mode='a', header=False, index=False)

def simpan_so_selesai(no_so):
    path_selesai = "selesai.txt"
    with open(path_selesai, "a" if os.path.exists(path_selesai) else "w") as f:
        f.write(no_so.strip() + "\n"); f.flush()
    buka_kunci_so(no_so); hapus_file_draft(no_so)
    if no_so in st.session_state['qc_drafts']: del st.session_state['qc_drafts'][no_so]

def kirim_telegram(pesan):
    try: requests.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={pesan}")
    except: pass

# --- SISTEM LOGIN ---
if not st.session_state['auth']:
    st.title("🔐 Login Checker MBI")
    u_input = st.text_input("Username").lower().strip()
    p_input = st.text_input("Password", type="password")
    if st.button("Masuk", use_container_width=True):
        if u_input in USER_DB and USER_DB[u_input] == p_input:
            st.session_state['auth'], st.session_state['user'] = True, u_input.capitalize()
            st.query_params["u"] = u_input; st.rerun()
        else: st.error("Username atau Password salah!")
else:
    # --- SIDEBAR ---
    is_admin = st.session_state['user'].lower() == "galang"
    with st.sidebar:
        photo = get_user_photo(st.session_state['user'])
        if photo: st.image(photo, width=100)
        st.title(f"👤 {st.session_state['user']}")
        
        m_list = ["Pemeriksaan QC", "Dashboard Monitoring", "⚙️ Pengaturan"] if is_admin else ["Pemeriksaan QC", "⚙️ Pengaturan"]
        menu = st.radio("Menu Utama", m_list)
        
        if st.sidebar.button("Log Out"):
            if st.session_state['selected_so']: buka_kunci_so(st.session_state['selected_so'])
            st.session_state['auth'] = False; st.query_params.clear(); st.rerun()

    # --- LOAD DATA MASTER ---
    if os.path.exists("data_so.csv"):
        df_master = pd.read_csv("data_so.csv")
        df_master.columns = df_master.columns.str.strip()
        col_so, col_customer, col_tgl = 'Nomor # Pesanan Penjualan', 'Pelanggan', 'Tanggal Pesanan Penjualan'
        col_qty, col_item, col_kode = 'Kuantitas', 'Nama Barang', 'Kode #'
        col_batch, col_exp = 'No Seri/Produksi', 'Tgl Kadaluarsa'
        df_master[col_so] = df_master[col_so].astype(str).str.strip()
        df_master[[col_so, col_customer, col_tgl]] = df_master[[col_so, col_customer, col_tgl]].ffill()
        df_master = df_master[df_master[col_item].notna()]
        selesai_list = ambil_daftar_selesai()

        if menu == "⚙️ Pengaturan":
            st.header("⚙️ Pengaturan Akun")
            c1, c2 = st.columns(2)
            with c1: st.session_state['theme'] = st.selectbox("Tema", ["Terang", "Gelap"], index=0 if st.session_state['theme']=="Terang" else 1)
            with c2: st.session_state['font_size'] = st.slider("Ukuran Font", 12, 24, st.session_state['font_size'])
            
            st.subheader("🖼️ Update Foto")
            up_f = st.file_uploader("Upload PNG/JPG", type=['png', 'jpg'])
            if up_f:
                if not os.path.exists("photos"): os.makedirs("photos")
                with open(f"photos/{st.session_state['user'].lower()}.png", "wb") as f: f.write(up_f.getbuffer())
                st.success("Foto Berhasil! Silakan Refresh browser."); st.rerun()
            
            st.subheader("🔑 Ganti Password")
            p1 = st.text_input("Password Baru", type="password")
            p2 = st.text_input("Konfirmasi", type="password")
            if st.button("Simpan Password"):
                if p1 == p2 and p1 != "": update_password_db(st.session_state['user'], p1); st.success("Berhasil!")
                else: st.error("Gagal!")

        elif menu == "Pemeriksaan QC":
            if st.session_state['page'] == "search":
                l_all = df_master[col_so].unique()
                l_aktif = sorted([s for s in l_all if s not in selesai_list])
                st.subheader("🎯 Cari Nomor SO")
                
                # Admin Tools (Khusus Galang)
                if is_admin:
                    with st.expander("🛠️ ADMIN TOOLS (Galang Only)", expanded=False):
                        s_adm = st.selectbox("Action SO:", l_aktif, key="adm_slct")
                        if s_adm:
                            ca, cb, cc, cd = st.columns(4)
                            if ca.button("🔓 Unlock"): buka_kunci_so(s_adm); st.rerun()
                            if cb.button("♻️ Reset"): hapus_file_draft(s_adm); st.rerun()
                            if cc.button("🗑️ Hapus"): simpan_so_selesai(s_adm); st.rerun()
                            if cd.button("⚡ Quick"): 
                                simpan_so_selesai(s_adm)
                                kirim_telegram(f"⚡ QUICK DONE BY ADMIN: {s_adm}"); st.rerun()

                so_dipilih = st.selectbox("Pilih No SO:", l_aktif, index=None, placeholder="Ketik nomor SO...")
                
                # Metrics (Bawah Pencarian)
                st.divider()
                m1, m2, m3 = st.columns(3)
                m1.markdown(f'<div class="metric-card">📦 <b>Total SO</b><br>{len(l_all)}</div>', unsafe_allow_html=True)
                m2.markdown(f'<div class="metric-card">⏳ <b>Belum QC</b><br>{len(l_aktif)}</div>', unsafe_allow_html=True)
                m3.markdown(f'<div class="metric-card">✅ <b>Selesai</b><br>{len(selesai_list)}</div>', unsafe_allow_html=True)
                
                locks = ambil_semua_lock()
                if locks:
                    with st.expander("👥 Petugas Aktif", expanded=True):
                        for s, p in locks.items(): st.caption(f"🔵 **{p}** sedang cek **{s}**")

                if so_dipilih:
                    if so_dipilih in locks and locks[so_dipilih] != st.session_state['user']: st.error(f"Dikunci {locks[so_dipilih]}")
                    else:
                        kunci_so(so_dipilih, st.session_state['user'])
                        st.session_state['selected_so'], st.session_state['page'] = so_dipilih, "list_barang"
                        st.session_state['qc_drafts'][so_dipilih] = muat_draft_dari_file(so_dipilih); st.rerun()

            elif st.session_state['page'] == "list_barang":
                so_aktif = st.session_state['selected_so']
                if st.button("⬅️ Kembali"): buka_kunci_so(so_aktif); st.session_state['selected_so'], st.session_state['page'] = None, "search"; st.rerun()

                df_f = df_master[df_master[col_so] == so_aktif].copy()
                n_apt, t_so = df_f.iloc[0][col_customer], df_f.iloc[0][col_tgl]
                st.info(f"📌 **SO:** {so_aktif}")
                h1, h2 = st.columns(2)
                h1.markdown(f"🏢 **Apotek:** {n_apt}\n\n📅 **Tgl:** {t_so}")
                h2.markdown(f"💊 **Jenis:** {len(df_f)}\n\n🔢 **Qty:** {int(df_f[col_qty].sum())}")
                st.divider()

                v_all, l_final, draft = True, [], st.session_state['qc_drafts'].get(so_aktif, {})
                for idx, row in df_f.iterrows():
                    iid = str(row[col_kode]).strip(); target = int(float(row[col_qty]))
                    vq, vn, vt = draft.get(f"q_{iid}", 0), draft.get(f"n_{iid}", ""), draft.get(f"t_{iid}", False)
                    s_clp = "status-pending"; icon = " ⏳"
                    if str(vq) != "0":
                        if int(vq) == target: s_clp, icon = "status-ok", " ✅"
                        else: s_clp, icon = "status-err", " ⚠️"

                    st.markdown(f'<div class="{s_clp}">', unsafe_allow_html=True)
                    with st.expander(f"💊 {row[col_item]}{icon}"):
                        c_in, c_note = st.columns([4, 1.5])
                        t_ui = c_note.checkbox("📝", key=f"t_{so_aktif}_{iid}", value=vt)
                        u_in = st.text_input("Qty", key=f"q_{so_aktif}_{iid}", value="" if vq==0 else str(vq), placeholder="0", label_visibility="collapsed")
                        q_num = int(re.sub("[^0-9]", "", u_in)) if re.sub("[^0-9]", "", u_in) != "" else 0
                        n_ui = st.text_input("Note", key=f"n_{so_aktif}_{iid}", value=vn) if t_ui else ""
                        
                        if draft.get(f"q_{iid}") != q_num or draft.get(f"n_{iid}") != n_ui or draft.get(f"t_{iid}") != t_ui:
                            draft.update({f"q_{iid}": q_num, f"n_{iid}": n_ui, f"t_{iid}": t_ui})
                            simpan_draft_ke_file(so_aktif, draft); st.rerun()
                        if u_in == "" or q_num != target: v_all = False
                    st.markdown('</div>', unsafe_allow_html=True)
                    l_final.append({"Waktu": datetime.now().strftime("%H:%M"), "Petugas": st.session_state['user'], "SO": so_aktif, "Apotek": n_apt, "Kode": iid, "Item": row[col_item], "Qty_SO": target, "Qty_Fisik": q_num, "Note": n_ui})

                if st.button("✅ KIRIM LAPORAN", use_container_width=True, type="primary"):
                    if v_all:
                        simpan_rekap_data(l_final); kirim_telegram(f"✅ QC SELESAI: {so_aktif} oleh {st.session_state['user']}")
                        simpan_so_selesai(so_aktif); st.balloons(); st.rerun()
                    else: st.error("Pastikan semua Hijau!")

        elif menu == "Dashboard Monitoring":
            st.title("📊 Monitoring QC")
            if os.path.exists("rekap_qc.csv"):
                rkp = pd.read_csv("rekap_qc.csv")
                kls = rkp.groupby('Petugas').agg({'SO': 'nunique', 'Item': 'count', 'Qty_Fisik': 'sum'}).reset_index()
                kls.columns = ['Nama', 'Total SO', 'Total Item', 'Total Qty']
                st.subheader("🏆 Klasemen")
                st.table(kls.sort_values(by='Total Item', ascending=False))
            
            mon = df_master.groupby([col_so, col_tgl]).agg({col_item: 'count', col_qty: 'sum'}).reset_index()
            mon.columns = ['No SO', 'Tanggal', 'Jenis', 'Qty']
            def check_st(r):
                if r['No SO'] in selesai_list: return "Done", rkp[rkp['SO']==r['No SO']]['Petugas'].iloc[0] if 'rkp' in locals() else "-"
                return "Pending", "-"
            mon[['Status', 'QC']] = mon.apply(lambda x: pd.Series(check_st(x)), axis=1)
            st.subheader("📋 Status SO")
            st.dataframe(mon, use_container_width=True, hide_index=True)
    else: st.error("data_so.csv tidak ditemukan.")

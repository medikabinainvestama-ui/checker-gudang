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

# --- INISIALISASI SESSION STATE ---
if 'font_size' not in st.session_state: st.session_state['font_size'] = 16
if 'auth' not in st.session_state:
    params = st.query_params
    if "u" in params and params["u"] in USER_DB:
        st.session_state['auth'], st.session_state['user'] = True, params["u"].capitalize()
    else: st.session_state['auth'] = False

if 'user' not in st.session_state: st.session_state['user'] = ""
if 'page' not in st.session_state: st.session_state['page'] = "search"
if 'selected_so' not in st.session_state: st.session_state['selected_so'] = None
if 'qc_drafts' not in st.session_state: st.session_state['qc_drafts'] = {}

# --- STYLING CSS ---
st.markdown(f"""
    <style>
    footer {{visibility: hidden !important;}}
    .stAppDeployButton {{ display: none !important; }}

    /* Font Size Global */
    html, body, [data-testid="stWidgetLabel"] p, .stMarkdown p, .stSelectbox label, label {{
        font-size: {st.session_state['font_size']}px !important;
    }}

    table, thead, tbody, th, td {{ text-align: center !important; vertical-align: middle !important; }}
    .block-container {{ padding-top: 2rem !important; padding-bottom: 0rem !important; }}
    div[data-testid="stExpander"] {{ border: 1px solid #ddd; border-radius: 8px; margin-bottom: -15px !important; }}

    .metric-card {{
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 10px;
        text-align: center;
        border: 1px solid #e0e0e0;
        margin-top: 10px;
        margin-bottom: 10px;
    }}

    .status-ok {{ background-color: #d4edda !important; border-radius: 8px; border-left: 10px solid #28a745; margin-bottom: -15px !important; }}
    .status-err {{ background-color: #f8d7da !important; border-radius: 8px; border-left: 10px solid #dc3545; margin-bottom: -15px !important; }}
    .status-pending {{ background-color: #ffffff !important; border-radius: 8px; border-left: 10px solid #6c757d; margin-bottom: -15px !important; }}
    </style>
""", unsafe_allow_html=True)

# --- FUNGSI CORE ---
def update_password_db(u, p):
    USER_DB[u.lower()] = p
    with open("users.py", "w") as f: f.write(f"USER_DB = {json.dumps(USER_DB, indent=4)}")

def get_user_photo(u):
    path = f"photos/{u.lower()}.png"
    return path if os.path.exists(path) else None

def simpan_draft_ke_file(so, data):
    if not os.path.exists("drafts"): os.makedirs("drafts")
    with open(f"drafts/draft_{so}.json", "w") as f: json.dump(data, f)

def muat_draft_dari_file(so):
    path = f"drafts/draft_{so}.json"
    if os.path.exists(path):
        try:
            with open(path, "r") as f: return json.load(f)
        except: return {}
    return {}

def hapus_file_draft(so):
    path = f"drafts/draft_{so}.json"
    if os.path.exists(path): os.remove(path)

def ambil_semua_lock():
    locks = {}
    if os.path.exists("locks.txt"):
        try:
            with open("locks.txt", "r") as f:
                for line in f:
                    if "|" in line: s, p = line.strip().split("|"); locks[s] = p
        except: pass
    return locks

def kunci_so(so, p):
    locks = ambil_semua_lock()
    if so not in locks:
        with open("locks.txt", "a") as f: f.write(f"{so}|{p}\n"); f.flush()

def buka_kunci_so(so):
    locks = ambil_semua_lock()
    if so in locks:
        del locks[so]
        with open("locks.txt", "w") as f:
            for s, p in locks.items(): f.write(f"{s}|{p}\n"); f.flush()

def ambil_daftar_selesai():
    if os.path.exists("selesai.txt"):
        with open("selesai.txt", "r") as f: return [line.strip() for line in f.readlines()]
    return []

def simpan_rekap_data(l):
    if not os.path.exists("rekap_qc.csv"): pd.DataFrame(l).to_csv("rekap_qc.csv", index=False)
    else: pd.DataFrame(l).to_csv("rekap_qc.csv", mode='a', header=False, index=False)

def simpan_so_selesai(so):
    with open("selesai.txt", "a" if os.path.exists("selesai.txt") else "w") as f: 
        f.write(so.strip() + "\n"); f.flush()
    buka_kunci_so(so); hapus_file_draft(so)
    if so in st.session_state['qc_drafts']: del st.session_state['qc_drafts'][so]

def kirim_telegram(m):
    try: requests.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={m}")
    except: pass

# --- LOGIN ---
if not st.session_state['auth']:
    st.title("🔐 Login Checker MBI")
    u_in = st.text_input("Username").lower().strip()
    p_in = st.text_input("Password", type="password")
    if st.button("Masuk", use_container_width=True):
        if u_in in USER_DB and USER_DB[u_in] == p_in:
            st.session_state['auth'], st.session_state['user'] = True, u_in.capitalize()
            st.query_params["u"] = u_in; st.rerun()
        else: st.error("Username atau Password salah!")
else:
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

    if os.path.exists("data_so.csv"):
        df_master = pd.read_csv("data_so.csv")
        df_master.columns = df_master.columns.str.strip()
        c_so, c_cust, c_tgl = 'Nomor # Pesanan Penjualan', 'Pelanggan', 'Tanggal Pesanan Penjualan'
        c_qty, c_item, c_kd = 'Kuantitas', 'Nama Barang', 'Kode #'
        c_btch, c_exp = 'No Seri/Produksi', 'Tgl Kadaluarsa'
        df_master[c_so] = df_master[c_so].astype(str).str.strip()
        df_master[[c_so, c_cust, c_tgl]] = df_master[[c_so, c_cust, c_tgl]].ffill()
        df_master = df_master[df_master[c_item].notna()]
        selesai_list = ambil_daftar_selesai()

        if menu == "⚙️ Pengaturan":
            st.header("⚙️ Pengaturan Akun")
            st.session_state['font_size'] = st.slider("Ukuran Font", 12, 24, st.session_state['font_size'])
            st.subheader("🖼️ Update Foto Profil")
            up_f = st.file_uploader("Upload Foto", type=['png', 'jpg'])
            if up_f:
                if not os.path.exists("photos"): os.makedirs("photos")
                with open(f"photos/{st.session_state['user'].lower()}.png", "wb") as f: f.write(up_f.getbuffer())
                st.success("Foto Berhasil!"); st.rerun()
            st.subheader("🔑 Ganti Password")
            p1, p2 = st.text_input("Baru", type="password"), st.text_input("Konfirmasi", type="password")
            if st.button("Simpan Password"):
                if p1 == p2 and p1 != "": update_password_db(st.session_state['user'], p1); st.success("Berhasil!")
                else: st.error("Gagal!")

        elif menu == "Pemeriksaan QC":
            if st.session_state['page'] == "search":
                # --- HEADER PROFIL SEJAJAR (FOTO DI SAMPING NAMA) ---
                user_photo = get_user_photo(st.session_state['user'])
                col_p1, col_p2 = st.columns([1, 5])
                with col_p1:
                    if user_photo: st.image(user_photo, width=80)
                    else: st.markdown("<h1 style='margin:0;'>👤</h1>", unsafe_allow_html=True)
                with col_p2:
                    st.markdown(f"<div style='padding-top: 10px;'><p style='margin:0; color: gray;'>Selamat Bekerja,</p><h2 style='margin:0;'>{st.session_state['user']}</h2></div>", unsafe_allow_html=True)

                l_all = df_master[c_so].unique()
                l_aktif = sorted([s for s in l_all if s not in selesai_list])
                st.subheader("🎯 Cari Nomor SO")
                if is_admin:
                    with st.expander("🛠️ ADMIN TOOLS (Galang Only)", expanded=False):
                        s_adm = st.selectbox("Action SO:", l_aktif, key="adm_s")
                        if s_adm:
                            ca, cb, cc, cd = st.columns(4)
                            if ca.button("🔓 Unlock"): buka_kunci_so(s_adm); st.rerun()
                            if cb.button("♻️ Reset"): hapus_file_draft(s_adm); st.rerun()
                            if cc.button("🗑️ Hapus"): simpan_so_selesai(s_adm); st.rerun()
                            if cd.button("⚡ Quick Done"): simpan_so_selesai(s_adm); kirim_telegram(f"⚡ QUICK DONE BY ADMIN: {s_adm}"); st.rerun()
                
                so_dipilih = st.selectbox("Pilih No SO:", l_aktif, index=None, placeholder="Ketik nomor SO...")
                
                st.divider()
                m1, m2, m3 = st.columns(3)
                m1.markdown(f'<div class="metric-card">📦 <b>Total SO</b><br><span style="font-size:24px">{len(l_all)}</span></div>', unsafe_allow_html=True)
                m2.markdown(f'<div class="metric-card">⏳ <b>Belum QC</b><br><span style="font-size:24px">{len(list(l_aktif))}</span></div>', unsafe_allow_html=True)
                m3.markdown(f'<div class="metric-card">✅ <b>Selesai</b><br><span style="font-size:24px">{len(selesai_list)}</span></div>', unsafe_allow_html=True)
                
                locks = ambil_semua_lock()
                if locks:
                    with st.expander("👥 Petugas Aktif Saat Ini", expanded=True):
                        for s, p in locks.items(): st.caption(f"🔵 **{p}** sedang mengerjakan **{s}**")
                
                if so_dipilih:
                    if so_dipilih in locks and locks[so_dipilih] != st.session_state['user']: st.error(f"🚫 Sedang dibuka oleh {locks[so_dipilih]}")
                    else:
                        kunci_so(so_dipilih, st.session_state['user'])
                        st.session_state['selected_so'], st.session_state['page'] = so_dipilih, "list_barang"
                        st.session_state['qc_drafts'][so_dipilih] = muat_draft_dari_file(so_dipilih); st.rerun()

            elif st.session_state['page'] == "list_barang":
                so_aktif = st.session_state['selected_so']
                if st.button("⬅️ Kembali ke Pencarian"):
                    buka_kunci_so(so_aktif); st.session_state['selected_so'], st.session_state['page'] = None, "search"; st.rerun()
                
                df_f = df_master[df_master[c_so] == so_aktif].copy()
                n_apt, t_so = df_f.iloc[0][c_cust], df_f.iloc[0][c_tgl]
                df_f[c_qty] = pd.to_numeric(df_f[c_qty], errors='coerce').fillna(0)
                
                st.info(f"📌 **Nomor SO:** {so_aktif}")
                h1, h2 = st.columns(2)
                h1.markdown(f"🏢 **Apotek:** {n_apt}\n\n📅 **Tanggal SO:** {t_so}")
                h2.markdown(f"💊 **Total Jenis:** {len(df_f)} Item\n\n🔢 **Total Qty SO:** {int(df_f[c_qty].sum())} Pcs")
                st.divider()

                v_all, l_final, draft = True, [], st.session_state['qc_drafts'].get(so_aktif, {})
                for idx, row in df_f.iterrows():
                    iid = str(row[c_kd]).strip(); target = int(float(row[c_qty]))
                    vq, vn, vt = draft.get(f"q_{iid}", 0), draft.get(f"n_{iid}", ""), draft.get(f"t_{iid}", False)
                    s_clp, icon = "status-pending", " ⏳"
                    if str(vq) != "0":
                        if int(vq) == target: s_clp, icon = "status-ok", " ✅"
                        else: s_clp, icon = "status-err", " ⚠️"
                    
                    st.markdown(f'<div class="{s_clp}">', unsafe_allow_html=True)
                    with st.expander(f"💊 {row[c_item]}{icon}", expanded=False):
                        ci, ct = st.columns([4.5, 1])
                        ci.write(f"**Code:** {row[c_kd]} | **Batch:** {row[c_btch]} | **Exp:** {row[c_exp]} | **Qty:** {target}")
                        t_ui = ct.checkbox("📝 Note", key=f"t_{so_aktif}_{iid}", value=vt)
                        u_in = st.text_input("Input Fisik", key=f"q_{so_aktif}_{iid}", value="" if vq==0 else str(vq), placeholder="0", label_visibility="collapsed")
                        
                        q_num = int(re.sub("[^0-9]", "", u_in)) if re.sub("[^0-9]", "", u_in) != "" else 0
                        n_ui = st.text_input("Catatan:", key=f"n_{so_aktif}_{iid}", value=vn).strip() if t_ui else ""
                        
                        if draft.get(f"q_{iid}") != q_num or draft.get(f"n_{iid}") != n_ui or draft.get(f"t_{iid}") != t_ui:
                            draft.update({f"q_{iid}": q_num, f"n_{iid}": n_ui, f"t_{iid}": t_ui})
                            simpan_draft_ke_file(so_aktif, draft); st.rerun()
                        
                        if u_in == "" or q_num != target: v_all = False
                    st.markdown('</div>', unsafe_allow_html=True)
                    l_final.append({"Petugas": st.session_state['user'], "SO": so_aktif, "Apotek": n_apt, "Kode": iid, "Item": row[c_item], "Qty_SO": target, "Qty_Fisik": q_num, "Note": n_ui})

                if st.button("✅ SELESAI & KIRIM LAPORAN", use_container_width=True, type="primary"):
                    if v_all:
                        simpan_rekap_data(l_final)
                        nt = ""
                        for d in l_final:
                            if d['Note']: nt += f"- {d['Kode']} ({d['Qty_Fisik']} pcs)\n  🗒 Note: {d['Note']}\n"
                        kirim_telegram(f"✅ *QC SELESAI*\n👤 Petugas: {st.session_state['user']}\n📄 No SO: {so_aktif}\n📍 Apotek: {n_apt}\n---------------------------\n{nt if nt else '_Tanpa Catatan_'}")
                        simpan_so_selesai(so_aktif); st.balloons(); st.rerun()
                    else: st.error("Lengkapi semua barang (Warna Hijau) sebelum kirim!")

        elif menu == "Dashboard Monitoring":
            st.title("📊 Monitoring QC")
            if os.path.exists("rekap_qc.csv"):
                rkp = pd.read_csv("rekap_qc.csv")
                kls = rkp.groupby('Petugas').agg({'SO': 'nunique', 'Item': 'count', 'Qty_Fisik': 'sum'}).reset_index()
                kls.columns = ['Nama QC', 'Total SO', 'Total Item', 'Total Qty']
                st.subheader("🏆 Klasemen Checker")
                st.table(kls.sort_values(by='Total Item', ascending=False).reset_index(drop=True))
            
            mon = df_master.groupby([c_so, c_tgl]).agg({c_item: 'count', c_qty: 'sum'}).reset_index()
            mon.columns = ['No SO', 'Tanggal SO', 'Total Jenis Barang', 'Total Qty SO']
            def ck_st(r):
                if r['No SO'] in selesai_list:
                    try: return "Done", rkp[rkp['SO'] == r['No SO']]['Petugas'].iloc[0]
                    except: return "Done", "-"
                return "Pending", "-"
            mon[['Status', 'Nama QC']] = mon.apply(lambda x: pd.Series(ck_st(x)), axis=1)
            st.subheader("📋 Status Semua No SO")
            st.dataframe(mon, use_container_width=True, hide_index=True)
    else: st.error("❌ File data_so.csv tidak ditemukan.")

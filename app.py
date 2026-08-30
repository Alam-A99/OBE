import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import io
import os
import re

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.units import cm

import matplotlib.pyplot as plt

st.set_page_config(page_title="Dashboard CPL - Multi Mata Kuliah", layout="wide", page_icon="📊")

# =========================================================
# Konfigurasi dasar
# =========================================================
components = ["Tugas", "Partisipasi", "Proyek", "UTS", "Quiz", "UAS"]
REQUIRED_COLS = ["Nama"] + components

COLUMN_ALIASES = {
    "Projek": "Proyek",
    "Project": "Proyek",
    "Quis": "Quiz",
    "Kuis": "Quiz",
    "Kuiz": "Quiz",
}

NILAI_SHEET_NAMES = ["nilai", "data", "grades", "nilai mahasiswa"]
BOBOT_SHEET_NAMES = ["bobot_cpl", "bobot cpl", "bobotcpl", "bobot", "cpl"]
INFO_SHEET_NAMES = ["info", "identitas"]


def normalize_columns(df):
    df = df.rename(columns=lambda c: str(c).strip())
    df = df.rename(columns=COLUMN_ALIASES)
    return df


def cpl_sort_key(cpl_code):
    m = re.search(r"(\d+)", str(cpl_code))
    return (int(m.group(1)) if m else 999, str(cpl_code))


def find_sheet(sheets_dict, candidate_names):
    for key in sheets_dict.keys():
        if key.strip().lower() in candidate_names:
            return key
    return None


def status_color(val, threshold):
    if pd.isna(val):
        return "background-color: #f0f0f0; color: #999999;"
    if val >= threshold:
        return "background-color: #d4edda; color: #155724;"
    elif val >= threshold - 15:
        return "background-color: #fff3cd; color: #856404;"
    else:
        return "background-color: #f8d7da; color: #721c24;"


def style_status(styler_input, func, threshold):
    """Kompatibel pandas baru (Styler.map) maupun lama (Styler.applymap,
    dihapus mulai pandas >= 2.2/3.0)."""
    styler = styler_input.style if hasattr(styler_input, "style") else styler_input
    if hasattr(styler, "map"):
        return styler.map(lambda v: func(v, threshold))
    return styler.applymap(lambda v: func(v, threshold))


# =========================================================
# Parsing 1 file Excel matkul (Nilai + Bobot_CPL + Info)
# =========================================================
def parse_course_file(uploaded_file):
    try:
        sheets = pd.read_excel(uploaded_file, sheet_name=None)
    except Exception as e:
        return {"error": f"Gagal membaca file: {e}"}

    # --- Sheet Nilai ---
    nilai_key = find_sheet(sheets, NILAI_SHEET_NAMES)
    if nilai_key is None:
        nilai_key = list(sheets.keys())[0]  # fallback: sheet pertama
    df_nilai = normalize_columns(sheets[nilai_key].copy())

    missing_nilai = [c for c in REQUIRED_COLS if c not in df_nilai.columns]
    if missing_nilai:
        return {"error": f"Sheet nilai ('{nilai_key}'): kolom hilang {missing_nilai}. "
                          f"Kolom tersedia: {list(df_nilai.columns)}"}

    # --- Sheet Bobot_CPL ---
    bobot_key = find_sheet(sheets, BOBOT_SHEET_NAMES)
    if bobot_key is None:
        return {"error": "Sheet 'Bobot_CPL' tidak ditemukan. Gunakan template terbaru "
                          "(sheet: Nilai, Bobot_CPL, Info)."}

    df_bobot = sheets[bobot_key].copy()
    df_bobot = df_bobot.rename(columns=lambda c: str(c).strip())
    first_col = df_bobot.columns[0]
    df_bobot = df_bobot.rename(columns={first_col: "CPL"})
    df_bobot = df_bobot.rename(columns=COLUMN_ALIASES)

    missing_comp = [c for c in components if c not in df_bobot.columns]
    if missing_comp:
        return {"error": f"Sheet Bobot_CPL: kolom komponen hilang {missing_comp}. "
                          f"Kolom tersedia: {list(df_bobot.columns)}"}

    df_bobot["CPL"] = df_bobot["CPL"].astype(str).str.strip().str.upper().str.replace(" ", "")
    df_bobot = df_bobot.dropna(subset=["CPL"])
    df_bobot = df_bobot[df_bobot["CPL"] != ""]
    df_bobot = df_bobot.set_index("CPL")[components].fillna(0.0).astype(float)
    df_bobot = df_bobot[df_bobot.sum(axis=1) > 0]  # buang baris CPL yang bobotnya kosong semua

    if df_bobot.empty:
        return {"error": "Sheet Bobot_CPL tidak berisi baris CPL dengan bobot > 0."}

    # --- Sheet Info (opsional) ---
    meta = {
        "nama_matkul": os.path.splitext(uploaded_file.name)[0].replace("_", " "),
        "sks": 3,
        "kelas": "A",
        "dosen": "-",
    }
    info_key = find_sheet(sheets, INFO_SHEET_NAMES)
    if info_key is not None:
        df_info = sheets[info_key]
        if df_info.shape[1] >= 2:
            kv = dict(zip(
                df_info.iloc[:, 0].astype(str).str.strip().str.lower(),
                df_info.iloc[:, 1]
            ))
            if "mata kuliah" in kv and pd.notna(kv["mata kuliah"]):
                meta["nama_matkul"] = str(kv["mata kuliah"])
            if "sks" in kv and pd.notna(kv["sks"]):
                try:
                    meta["sks"] = int(float(kv["sks"]))
                except Exception:
                    pass
            if "kelas" in kv and pd.notna(kv["kelas"]):
                meta["kelas"] = str(kv["kelas"])
            if "dosen" in kv and pd.notna(kv["dosen"]):
                meta["dosen"] = str(kv["dosen"])

    return {"error": None, "df": df_nilai, "weights_df": df_bobot, "meta": meta}


# =========================================================
# Template Excel (3 sheet: Nilai, Bobot_CPL, Info)
# =========================================================
def generate_template_excel():
    df_nilai = pd.DataFrame({
        "Nama": ["MHS_1", "MHS_2", "MHS_3"],
        "Tugas": [80, 85, 75],
        "Partisipasi": [75, 80, 70],
        "Proyek": [82, 88, 79],
        "UTS": [78, 84, 72],
        "Quiz": [77, 83, 74],
        "UAS": [81, 87, 76],
    })

    df_bobot = pd.DataFrame({
        "CPL": ["CPL1", "CPL3", "CPL5"],
        "Tugas": [20, 10, 15],
        "Partisipasi": [10, 10, 10],
        "Proyek": [20, 30, 25],
        "UTS": [20, 20, 20],
        "Quiz": [10, 10, 10],
        "UAS": [20, 20, 20],
    })

    df_info = pd.DataFrame({
        "Field": ["Mata Kuliah", "SKS", "Kelas", "Dosen"],
        "Value": ["Algoritma dan Pemrograman", 3, "A", "Nama Dosen"]
    })

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_nilai.to_excel(writer, sheet_name="Nilai", index=False)
        df_bobot.to_excel(writer, sheet_name="Bobot_CPL", index=False)
        df_info.to_excel(writer, sheet_name="Info", index=False)
    output.seek(0)
    return output


def generate_default_course(shift, cpl_map, nama_matkul, sks):
    n = 25
    df_nilai = pd.DataFrame({
        "Nama": [f"MHS_{i}" for i in range(1, n + 1)],
        "Tugas": [80 + (i + shift) % 10 for i in range(n)],
        "Partisipasi": [75 + (i + shift) % 10 for i in range(n)],
        "Proyek": [78 + (i + shift) % 10 for i in range(n)],
        "UTS": [77 + (i + shift) % 10 for i in range(n)],
        "Quiz": [76 + (i + shift) % 10 for i in range(n)],
        "UAS": [79 + (i + shift) % 10 for i in range(n)],
    })
    df_bobot = pd.DataFrame(
        {comp: [round(100 / len(components), 2)] * len(cpl_map) for comp in components},
        index=cpl_map
    )
    meta = {"nama_matkul": nama_matkul, "sks": sks, "kelas": "A", "dosen": "-"}
    return {"error": None, "df": df_nilai, "weights_df": df_bobot, "meta": meta}


# =========================================================
# Header
# =========================================================
st.title("📊 Dashboard CPL Multi Mata Kuliah — 1 File Excel = 1 Mata Kuliah")
st.caption(
    "Bobot CPL dan identitas matkul sekarang cukup diisi **di dalam file Excel** "
    "(sheet Nilai, Bobot_CPL, Info) — tidak perlu diatur manual lagi di aplikasi. "
    "Upload beberapa file sekaligus untuk 1 semester penuh."
)

with st.expander("📥 Download Template Excel (Nilai + Bobot_CPL + Info)", expanded=False):
    st.download_button(
        "Download Template Excel",
        generate_template_excel(),
        file_name="Template_CPL_Lengkap.xlsx"
    )
    st.markdown(
        """
**Cara isi template (3 sheet):**
- **Nilai** — data mahasiswa: `Nama, Tugas, Partisipasi, Proyek, UTS, Quiz, UAS`
- **Bobot_CPL** — baris = kode CPL, kolom = komponen. Total bobot tiap baris CPL idealnya **100**.
  Contoh: `CPL1 | Tugas=20 | Partisipasi=10 | Proyek=20 | UTS=20 | Quiz=10 | UAS=20`
- **Info** — dua kolom `Field / Value`: Mata Kuliah, SKS, Kelas, Dosen

Setiap file Excel = 1 mata kuliah, dengan CPL & bobotnya sendiri-sendiri.
        """
    )

# =========================================================
# Upload multi-file
# =========================================================
st.subheader("📥 Upload File Excel — Boleh Banyak Mata Kuliah Sekaligus")

uploaded_files = st.file_uploader(
    "Upload file Excel (masing-masing berisi sheet Nilai, Bobot_CPL, Info)",
    type=["xlsx"],
    accept_multiple_files=True,
    key="multi_uploader"
)

if "courses_raw" not in st.session_state:
    st.session_state.courses_raw = {}

if uploaded_files:
    st.session_state.courses_raw = {}
    for f in uploaded_files:
        st.session_state.courses_raw[f.name] = parse_course_file(f)
else:
    if not st.session_state.courses_raw:
        st.session_state.courses_raw = {
            "Contoh_Algoritma.xlsx": generate_default_course(0, ["CPL1", "CPL2"], "Algoritma", 3),
            "Contoh_Basis_Data.xlsx": generate_default_course(3, ["CPL2", "CPL3"], "Basis Data", 3),
            "Contoh_Kewirausahaan.xlsx": generate_default_course(6, ["CPL1", "CPL4"], "Kewirausahaan", 2),
        }
        st.info("Belum ada file diupload — menampilkan 3 dataset contoh (masing-masing CPL & bobot berbeda). "
                "Upload file untuk mengganti.")

for fname, info in st.session_state.courses_raw.items():
    if info["error"]:
        st.error(f"❌ **{fname}**: {info['error']}")

valid_files = {k: v for k, v in st.session_state.courses_raw.items() if v["error"] is None}

if not valid_files:
    st.warning("Belum ada file valid untuk diproses.")
    st.stop()

# =========================================================
# Ringkasan file yang terbaca (verifikasi cepat, tanpa perlu input manual)
# =========================================================
st.subheader("✅ Mata Kuliah Terbaca")
summary_rows = []
for fname, info in valid_files.items():
    meta = info["meta"]
    cpl_terbaca = ", ".join(sorted(info["weights_df"].index, key=cpl_sort_key))
    total_check = info["weights_df"].sum(axis=1)
    not_100 = total_check[(total_check - 100).abs() > 0.01]
    warn = f"⚠️ {len(not_100)} CPL bobotnya ≠100%" if len(not_100) > 0 else "✅ OK"
    summary_rows.append({
        "File": fname,
        "Mata Kuliah": meta["nama_matkul"],
        "SKS": meta["sks"],
        "Kelas": meta["kelas"],
        "Dosen": meta["dosen"],
        "Jml Mahasiswa": len(info["df"]),
        "CPL Diampu": cpl_terbaca,
        "Cek Bobot": warn,
    })
st.dataframe(pd.DataFrame(summary_rows), use_container_width=True, hide_index=True)

with st.expander("✏️ Edit manual (opsional) — jika ada file yang perlu koreksi cepat tanpa upload ulang"):
    edit_target = st.selectbox("Pilih file untuk dikoreksi", list(valid_files.keys()))
    if edit_target:
        cur = valid_files[edit_target]
        e1, e2, e3, e4 = st.columns(4)
        with e1:
            new_nama = st.text_input("Mata Kuliah", cur["meta"]["nama_matkul"], key=f"edit_nama_{edit_target}")
        with e2:
            new_sks = st.number_input("SKS", 1, 6, cur["meta"]["sks"], key=f"edit_sks_{edit_target}")
        with e3:
            new_kelas = st.text_input("Kelas", cur["meta"]["kelas"], key=f"edit_kelas_{edit_target}")
        with e4:
            new_dosen = st.text_input("Dosen", cur["meta"]["dosen"], key=f"edit_dosen_{edit_target}")

        st.caption("Tabel bobot CPL (bisa diedit langsung):")
        edited_weights = st.data_editor(
            cur["weights_df"],
            column_config={
                comp: st.column_config.NumberColumn(comp, min_value=0.0, max_value=100.0, step=1.0, format="%.1f")
                for comp in components
            },
            use_container_width=True,
            key=f"edit_weights_{edit_target}"
        )

        if st.button("💾 Terapkan Perubahan", key=f"apply_{edit_target}"):
            st.session_state.courses_raw[edit_target]["meta"] = {
                "nama_matkul": new_nama, "sks": new_sks, "kelas": new_kelas, "dosen": new_dosen
            }
            st.session_state.courses_raw[edit_target]["weights_df"] = edited_weights
            st.success("Perubahan diterapkan.")
            st.rerun()

st.divider()

# =========================================================
# Sidebar — pengaturan tampilan & agregasi program
# =========================================================
union_cpl = sorted(
    {cpl for info in valid_files.values() for cpl in info["weights_df"].index},
    key=cpl_sort_key
)

st.sidebar.header("⚙️ Pengaturan Rekap Program")
all_program_cpl = st.sidebar.multiselect(
    "CPL yang ditampilkan di Rekap Program",
    union_cpl,
    default=union_cpl,
    help="Otomatis terdeteksi dari sheet Bobot_CPL semua file yang diupload."
)
weighting_basis = st.sidebar.radio(
    "📐 Dasar Pembobotan Rekap Program",
    ["SKS", "Jumlah Mahasiswa", "Rata-rata Sederhana"],
    help="Untuk tiap CPL, hanya mata kuliah yang mengampu CPL tersebut yang ikut dirata-ratakan."
)
AMBANG_KETERCAPAIAN = st.sidebar.slider("🎯 Ambang Ketercapaian per Mahasiswa", 0, 100, 70)

if not all_program_cpl:
    st.warning("⚠️ Tidak ada CPL terdeteksi / terpilih.")
    st.stop()

# =========================================================
# Hitung CPL untuk setiap mata kuliah
# =========================================================
results = {}
for fname, info in valid_files.items():
    df = info["df"].copy()
    weights_df = info["weights_df"]
    course_cpl = list(weights_df.index)

    for cpl in course_cpl:
        df[cpl] = 0.0
        for comp in components:
            df[cpl] += df[comp] * (weights_df.loc[cpl, comp] / 100)

    cpl_avg = df[course_cpl].mean()
    cpl_attainment = (df[course_cpl] >= AMBANG_KETERCAPAIAN).sum() / len(df) * 100

    results[fname] = {
        "df": df,
        "cpl_avg": cpl_avg,
        "cpl_attainment": cpl_attainment,
        "selected_cpl": course_cpl,
        "meta": info["meta"],
        "n_mhs": len(df),
    }

# =========================================================
# Rekap Program — agregasi hanya dari matkul yang mengampu CPL tsb
# =========================================================
def compute_program_summary(results, all_program_cpl, basis):
    avg_table = pd.DataFrame(index=list(results.keys()), columns=all_program_cpl, dtype=float)
    att_table = pd.DataFrame(index=list(results.keys()), columns=all_program_cpl, dtype=float)

    for fname, r in results.items():
        for cpl in r["selected_cpl"]:
            if cpl in all_program_cpl:
                avg_table.loc[fname, cpl] = r["cpl_avg"][cpl]
                att_table.loc[fname, cpl] = r["cpl_attainment"][cpl]

    program_avg, program_attainment, contributor_count = {}, {}, {}
    for cpl in all_program_cpl:
        contributing = {f: r for f, r in results.items() if cpl in r["selected_cpl"]}
        contributor_count[cpl] = len(contributing)
        if not contributing:
            program_avg[cpl] = float("nan")
            program_attainment[cpl] = float("nan")
            continue
        if basis == "SKS":
            w = pd.Series({f: r["meta"]["sks"] for f, r in contributing.items()}, dtype=float)
        elif basis == "Jumlah Mahasiswa":
            w = pd.Series({f: r["n_mhs"] for f, r in contributing.items()}, dtype=float)
        else:
            w = pd.Series({f: 1.0 for f in contributing})
        w_norm = w / w.sum()
        avg_vals = pd.Series({f: r["cpl_avg"][cpl] for f, r in contributing.items()})
        att_vals = pd.Series({f: r["cpl_attainment"][cpl] for f, r in contributing.items()})
        program_avg[cpl] = (avg_vals * w_norm).sum()
        program_attainment[cpl] = (att_vals * w_norm).sum()

    return avg_table, att_table, pd.Series(program_avg), pd.Series(program_attainment), pd.Series(contributor_count)


avg_table, att_table, program_avg, program_attainment, contributor_count = compute_program_summary(
    results, all_program_cpl, weighting_basis
)

cpl_no_coverage = [c for c in all_program_cpl if contributor_count[c] == 0]
if cpl_no_coverage:
    st.warning(f"⚠️ Belum ada mata kuliah yang mengampu: {', '.join(cpl_no_coverage)}")

# =========================================================
# TABS
# =========================================================
tab_labels = ["📈 Rekap Program"] + [f"📚 {results[f]['meta']['nama_matkul']}" for f in results.keys()]
tabs = st.tabs(tab_labels)

with tabs[0]:
    st.subheader("📈 Rekap Ketercapaian CPL — Tingkat Program Studi")
    st.caption(
        f"Digabungkan dari {len(results)} mata kuliah, dibobot berdasarkan **{weighting_basis}**. "
        "Tiap CPL hanya dihitung dari mata kuliah yang mengampunya (sesuai sheet Bobot_CPL)."
    )

    total_mhs = sum(r["n_mhs"] for r in results.values())
    covered_cpl = [c for c in all_program_cpl if contributor_count[c] > 0]
    avg_overall_attainment = program_attainment[covered_cpl].mean() if covered_cpl else 0
    n_tercapai = (program_attainment[covered_cpl] >= AMBANG_KETERCAPAIAN).sum() if covered_cpl else 0

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Jumlah Mata Kuliah", len(results))
    m2.metric("Total Mahasiswa", total_mhs)
    m3.metric("Rata-rata Ketercapaian CPL", f"{avg_overall_attainment:.1f}%")
    m4.metric("CPL Tercapai", f"{n_tercapai}/{len(covered_cpl)}")

    st.markdown("#### 🗺️ Matriks Pemetaan CPL – Mata Kuliah")
    st.caption("Diambil otomatis dari sheet Bobot_CPL tiap file. Sel \"-\" = tidak diampu.")
    matrix_display = att_table.copy()
    matrix_display.index = [results[f]["meta"]["nama_matkul"] for f in matrix_display.index]
    styled_matrix = style_status(matrix_display, status_color, AMBANG_KETERCAPAIAN).format("{:.1f}%", na_rep="-")
    st.dataframe(styled_matrix, use_container_width=True)

    st.markdown("#### 🎯 Ketercapaian CPL Program (%)")
    METRICS_PER_ROW = 7
    for row_start in range(0, len(all_program_cpl), METRICS_PER_ROW):
        row_cpls = all_program_cpl[row_start:row_start + METRICS_PER_ROW]
        cols_metric = st.columns(METRICS_PER_ROW)
        for i, cpl in enumerate(row_cpls):
            val = program_attainment[cpl]
            n_mk = contributor_count[cpl]
            if pd.isna(val):
                cols_metric[i].metric(cpl, "-", "belum ada MK")
            else:
                delta = val - AMBANG_KETERCAPAIAN
                cols_metric[i].metric(cpl, f"{val:.1f}%", f"{delta:+.1f} ({n_mk} MK)")

    if covered_cpl:
        st.markdown("#### 📊 Perbandingan Nilai Rata-rata CPL Antar Mata Kuliah")
        avg_long = avg_table[covered_cpl].reset_index().melt(id_vars="index", var_name="CPL", value_name="Nilai")
        avg_long = avg_long.rename(columns={"index": "Mata Kuliah"}).dropna(subset=["Nilai"])
        avg_long["Mata Kuliah"] = avg_long["Mata Kuliah"].map(lambda f: results[f]["meta"]["nama_matkul"])
        fig_bar = px.bar(avg_long, x="CPL", y="Nilai", color="Mata Kuliah", barmode="group",
                          text_auto=".1f", height=420)
        fig_bar.add_hline(y=AMBANG_KETERCAPAIAN, line_dash="dash", line_color="red",
                           annotation_text=f"Ambang {AMBANG_KETERCAPAIAN}")
        st.plotly_chart(fig_bar, use_container_width=True)

        st.markdown("#### 🕸️ Profil CPL — Overlay Semua Mata Kuliah + Program")
        fig_radar = go.Figure()
        for fname, r in results.items():
            if not r["selected_cpl"]:
                continue
            vals = list(r["cpl_avg"].values) + [r["cpl_avg"].values[0]]
            labels = list(r["cpl_avg"].index) + [r["cpl_avg"].index[0]]
            fig_radar.add_trace(go.Scatterpolar(r=vals, theta=labels, name=r["meta"]["nama_matkul"], opacity=0.6))
        prog_series = program_avg[covered_cpl]
        prog_vals = list(prog_series.values) + [prog_series.values[0]]
        prog_labels = list(prog_series.index) + [prog_series.index[0]]
        fig_radar.add_trace(go.Scatterpolar(r=prog_vals, theta=prog_labels, name="🎓 Program (Gabungan)",
                                             line=dict(color="black", width=3)))
        fig_radar.update_layout(height=480, polar=dict(radialaxis=dict(visible=True, range=[0, 100])))
        st.plotly_chart(fig_radar, use_container_width=True)

    st.markdown("#### 📌 Analisis CQI (Continuous Quality Improvement) — Tingkat Program")
    for cpl in all_program_cpl:
        val = program_attainment[cpl]
        n_mk = contributor_count[cpl]
        if pd.isna(val):
            st.info(f"**{cpl}**: belum diampu mata kuliah manapun.")
        elif val >= AMBANG_KETERCAPAIAN:
            st.success(f"**{cpl}**: {val:.1f}% (dari {n_mk} MK) — ✅ Tercapai.")
        elif val >= AMBANG_KETERCAPAIAN - 15:
            st.warning(f"**{cpl}**: {val:.1f}% (dari {n_mk} MK) — ⚠️ Mendekati ambang.")
        else:
            st.error(f"**{cpl}**: {val:.1f}% (dari {n_mk} MK) — ❌ Belum tercapai.")

for tab, fname in zip(tabs[1:], results.keys()):
    r = results[fname]
    with tab:
        meta = r["meta"]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Mata Kuliah", meta["nama_matkul"])
        c2.metric("Kelas / SKS", f"{meta['kelas']} / {meta['sks']} SKS")
        c3.metric("Dosen", meta["dosen"])
        c4.metric("Jumlah Mahasiswa", r["n_mhs"])

        st.markdown("##### 📋 Data Nilai")
        st.dataframe(r["df"], use_container_width=True, height=250)

        cA, cB = st.columns([1, 1])
        with cA:
            st.markdown("##### 📊 Rata-rata CPL")
            st.dataframe(r["cpl_avg"].to_frame("Nilai").style.format("{:.1f}"), use_container_width=True)
        with cB:
            st.markdown("##### 🎯 Ketercapaian CPL (%)")
            st.dataframe(
                style_status(r["cpl_attainment"].to_frame("Ketercapaian"), status_color, AMBANG_KETERCAPAIAN).format("{:.1f}%"),
                use_container_width=True
            )

        radar_df = pd.DataFrame({"CPL": r["cpl_avg"].index, "Nilai": r["cpl_avg"].values})
        fig = px.line_polar(radar_df, r="Nilai", theta="CPL", line_close=True, range_r=[0, 100])
        fig.update_traces(fill="toself")
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("##### 🔎 Cari Mahasiswa")
        sel_student = st.selectbox("Pilih Mahasiswa", r["df"]["Nama"], key=f"student_{fname}")
        st.dataframe(r["df"][r["df"]["Nama"] == sel_student], use_container_width=True)

# =========================================================
# PDF
# =========================================================
def generate_radar_png(cpl_avg, filename):
    labels = list(cpl_avg.index)
    values = list(cpl_avg.values)
    values += values[:1]
    labels += labels[:1]
    plt.figure(figsize=(4, 4))
    ax = plt.subplot(111, polar=True)
    ax.plot(values, color="#2E5EAA")
    ax.fill(values, alpha=0.15, color="#2E5EAA")
    ax.set_xticks(range(len(labels) - 1))
    ax.set_xticklabels(labels[:-1])
    ax.set_ylim(0, 100)
    plt.tight_layout()
    plt.savefig(filename, dpi=120)
    plt.close()
    return filename


def df_to_pdf_table(series_dict, col_label, styles):
    data = [["CPL", col_label]]
    for k, v in series_dict.items():
        data.append([k, "-" if pd.isna(v) else f"{v:.2f}"])
    t = Table(data, colWidths=[4 * cm, 4 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2E5EAA")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ALIGN", (1, 1), (-1, -1), "CENTER"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
    ]))
    return t


def generate_pdf_gabungan(results, program_avg, program_attainment, contributor_count,
                           weighting_basis, all_program_cpl, filename="laporan_cpl_gabungan.pdf"):
    doc = SimpleDocTemplate(filename, topMargin=2 * cm, bottomMargin=2 * cm)
    styles = getSampleStyleSheet()
    content = []

    content.append(Paragraph("LAPORAN KETERCAPAIAN CPL — REKAP PROGRAM STUDI", styles["Title"]))
    content.append(Spacer(1, 6))
    content.append(Paragraph(f"Jumlah Mata Kuliah: {len(results)}", styles["Normal"]))
    content.append(Paragraph(f"Total Mahasiswa: {sum(r['n_mhs'] for r in results.values())}", styles["Normal"]))
    content.append(Paragraph(f"Dasar Pembobotan: {weighting_basis}", styles["Normal"]))
    content.append(Spacer(1, 12))

    content.append(Paragraph("Ringkasan Ketercapaian CPL Program", styles["Heading2"]))
    content.append(df_to_pdf_table(program_attainment.to_dict(), "Ketercapaian (%)", styles))
    content.append(Spacer(1, 12))

    covered_cpl = [c for c in all_program_cpl if contributor_count[c] > 0]
    if covered_cpl:
        radar_prog = generate_radar_png(program_avg[covered_cpl], "radar_program.png")
        content.append(Paragraph("Profil CPL Program (Gabungan)", styles["Heading2"]))
        content.append(Image(radar_prog, width=320, height=320))
        content.append(Spacer(1, 12))

    content.append(Paragraph("Analisis CQI Tingkat Program", styles["Heading2"]))
    for cpl, val in program_attainment.items():
        n_mk = contributor_count[cpl]
        if pd.isna(val):
            content.append(Paragraph(f"{cpl}: belum ada MK yang mengampu", styles["Normal"]))
        else:
            status = "Tercapai" if val >= AMBANG_KETERCAPAIAN else "Belum Tercapai"
            content.append(Paragraph(f"{cpl}: {val:.2f}% ({n_mk} MK) — {status}", styles["Normal"]))

    content.append(PageBreak())

    for fname, r in results.items():
        meta = r["meta"]
        content.append(Paragraph(f"Mata Kuliah: {meta['nama_matkul']}", styles["Title"]))
        content.append(Paragraph(
            f"Kelas: {meta['kelas']} | SKS: {meta['sks']} | Dosen: {meta['dosen']} | "
            f"Jumlah Mahasiswa: {r['n_mhs']} | CPL Diampu: {', '.join(r['selected_cpl'])}",
            styles["Normal"]
        ))
        content.append(Spacer(1, 10))
        content.append(Paragraph("Rata-rata CPL", styles["Heading2"]))
        content.append(df_to_pdf_table(r["cpl_avg"].to_dict(), "Nilai", styles))
        content.append(Spacer(1, 10))
        content.append(Paragraph("Ketercapaian CPL (%)", styles["Heading2"]))
        content.append(df_to_pdf_table(r["cpl_attainment"].to_dict(), "Ketercapaian (%)", styles))
        content.append(Spacer(1, 10))
        radar_path = generate_radar_png(r["cpl_avg"], f"radar_{fname}.png")
        content.append(Image(radar_path, width=280, height=280))
        content.append(Spacer(1, 10))
        content.append(Paragraph("Analisis CQI", styles["Heading2"]))
        for cpl, val in r["cpl_attainment"].items():
            status = "Tercapai" if val >= AMBANG_KETERCAPAIAN else "Belum"
            content.append(Paragraph(f"{cpl}: {status} ({val:.2f}%)", styles["Normal"]))
        content.append(PageBreak())

    doc.build(content)
    return filename


# =========================================================
# Export
# =========================================================
st.divider()
st.subheader("📄 Export Laporan")

col_exp1, col_exp2 = st.columns(2)
with col_exp1:
    if st.button("📥 Generate Laporan PDF Gabungan", use_container_width=True):
        pdf_path = generate_pdf_gabungan(
            results, program_avg, program_attainment, contributor_count, weighting_basis, all_program_cpl
        )
        with open(pdf_path, "rb") as f:
            st.download_button("⬇️ Download PDF Laporan Gabungan", f,
                                file_name="Laporan_CPL_Program_Gabungan.pdf",
                                mime="application/pdf", use_container_width=True)

with col_exp2:
    excel_buf = io.BytesIO()
    with pd.ExcelWriter(excel_buf, engine="openpyxl") as writer:
        avg_export = avg_table.copy()
        avg_export.index = [results[f]["meta"]["nama_matkul"] for f in avg_export.index]
        avg_export.loc["Program (Gabungan)"] = program_avg
        avg_export.to_excel(writer, sheet_name="Rata-rata CPL")

        att_export = att_table.copy()
        att_export.index = [results[f]["meta"]["nama_matkul"] for f in att_export.index]
        att_export.loc["Program (Gabungan)"] = program_attainment
        att_export.to_excel(writer, sheet_name="Ketercapaian CPL")

        coverage = (~att_table.isna()).astype(int)
        coverage.index = [results[f]["meta"]["nama_matkul"] for f in coverage.index]
        coverage.to_excel(writer, sheet_name="Matriks CPL-MK")
    excel_buf.seek(0)
    st.download_button("⬇️ Download Rekap Excel", excel_buf,
                        file_name="Rekap_CPL_Program.xlsx", use_container_width=True)

st.divider()
if st.button("🔄 Reset Semua Data"):
    st.session_state.courses_raw = {}
    st.rerun()

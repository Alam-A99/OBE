import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import io
import os

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
cpl_list = [f"CPL{i}" for i in range(1, 15)]  # CPL1 - CPL14

COLUMN_ALIASES = {
    "Projek": "Proyek",
    "Project": "Proyek",
    "Quis": "Quiz",
    "Kuis": "Quiz",
    "Kuiz": "Quiz",
}


def normalize_columns(df):
    df = df.rename(columns=lambda c: str(c).strip())
    df = df.rename(columns=COLUMN_ALIASES)
    return df


def generate_default_data(seed_shift=0):
    n = 30
    data = {
        "Nama": [f"MHS_{i}" for i in range(1, n + 1)],
        "Tugas": [80 + (i + seed_shift) % 10 for i in range(n)],
        "Partisipasi": [75 + (i + seed_shift) % 10 for i in range(n)],
        "Proyek": [78 + (i + seed_shift) % 10 for i in range(n)],
        "UTS": [77 + (i + seed_shift) % 10 for i in range(n)],
        "Quiz": [76 + (i + seed_shift) % 10 for i in range(n)],
        "UAS": [79 + (i + seed_shift) % 10 for i in range(n)]
    }
    return pd.DataFrame(data)


def generate_template_excel():
    data = {
        "Nama": ["MHS_1", "MHS_2"],
        "Tugas": [80, 85],
        "Partisipasi": [75, 80],
        "Proyek": [82, 88],
        "UTS": [78, 84],
        "Quiz": [77, 83],
        "UAS": [81, 87]
    }
    df = pd.DataFrame(data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    output.seek(0)
    return output


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
# Header
# =========================================================
st.title("📊 Dashboard CPL Multi Mata Kuliah — 1 Semester (Bobot per Matkul)")
st.caption(
    "Upload seluruh mata kuliah dalam 1 semester. Setiap mata kuliah punya "
    "pemetaan CPL dan bobot komponen penilaian sendiri-sendiri (sesuai RPS masing-masing), "
    "lalu digabung otomatis jadi rekap ketercapaian CPL tingkat program studi."
)

with st.expander("📥 Download Template Excel"):
    st.download_button(
        "Download Template Excel",
        generate_template_excel(),
        file_name="Template_CPL.xlsx"
    )
    st.caption("Kolom wajib: Nama, Tugas, Partisipasi, Proyek, UTS, Quiz, UAS")

# =========================================================
# Upload multi-file
# =========================================================
st.subheader("📥 Upload Nilai — Seluruh Mata Kuliah dalam 1 Semester")

uploaded_files = st.file_uploader(
    "Upload File Excel Nilai Mahasiswa (satu file = satu mata kuliah, boleh banyak sekaligus)",
    type=["xlsx"],
    accept_multiple_files=True,
    key="multi_uploader"
)

if "courses_raw" not in st.session_state:
    st.session_state.courses_raw = {}  # key -> {"df":..., "error":...}

if uploaded_files:
    st.session_state.courses_raw = {}
    for f in uploaded_files:
        try:
            df_raw = pd.read_excel(f)
            df_raw = normalize_columns(df_raw)
            missing = [c for c in REQUIRED_COLS if c not in df_raw.columns]
            if missing:
                st.session_state.courses_raw[f.name] = {
                    "df": None,
                    "error": f"Kolom hilang: {', '.join(missing)}. Kolom tersedia: {', '.join(df_raw.columns)}"
                }
            else:
                st.session_state.courses_raw[f.name] = {"df": df_raw, "error": None}
        except Exception as e:
            st.session_state.courses_raw[f.name] = {"df": None, "error": f"Gagal membaca file: {e}"}
else:
    if not st.session_state.courses_raw:
        st.session_state.courses_raw = {
            "Contoh_Matkul_A.xlsx": {"df": generate_default_data(0), "error": None},
            "Contoh_Matkul_B.xlsx": {"df": generate_default_data(3), "error": None},
            "Contoh_Matkul_C.xlsx": {"df": generate_default_data(6), "error": None},
        }
        st.info("Belum ada file diupload — menampilkan 3 dataset contoh. Upload file untuk mengganti.")

for fname, info in st.session_state.courses_raw.items():
    if info["error"]:
        st.error(f"❌ **{fname}**: {info['error']}")

valid_files = {k: v for k, v in st.session_state.courses_raw.items() if v["error"] is None}

if not valid_files:
    st.warning("Belum ada file valid untuk diproses.")
    st.stop()

# =========================================================
# Sidebar — pengaturan tingkat program
# =========================================================
st.sidebar.header("⚙️ Pengaturan Program Studi")

all_program_cpl = st.sidebar.multiselect(
    "CPL yang ditrack tingkat Program Studi",
    cpl_list,
    default=cpl_list,
    help="Daftar CPL keseluruhan program. Tiap mata kuliah nanti memilih SUBSET dari daftar ini "
         "sesuai CPL yang benar-benar diampu (dibebankan) mata kuliah tersebut."
)

weighting_basis = st.sidebar.radio(
    "📐 Dasar Pembobotan Rekap Program",
    ["SKS", "Jumlah Mahasiswa", "Rata-rata Sederhana"],
    help="Untuk tiap CPL, hanya mata kuliah yang MENGAMPU CPL tersebut yang ikut dirata-ratakan."
)

AMBANG_KETERCAPAIAN = st.sidebar.slider("🎯 Ambang Ketercapaian per Mahasiswa", 0, 100, 70)

st.sidebar.divider()
st.sidebar.caption(
    "💡 Bobot komponen (Tugas, UTS, dst) → CPL sekarang diatur **per mata kuliah**, "
    "langsung di bagian utama halaman (bukan di sidebar lagi), karena tiap matkul "
    "biasanya punya pemetaan CPL dan bobot berbeda."
)

if not all_program_cpl:
    st.warning("⚠️ Pilih minimal 1 CPL program studi di sidebar.")
    st.stop()

# =========================================================
# Identitas + Pemetaan CPL & Bobot PER MATA KULIAH
# =========================================================
st.subheader("📌 Identitas, Pemetaan CPL & Bobot — Per Mata Kuliah")
st.caption(
    "Untuk setiap mata kuliah: pilih CPL yang diampu (sesuai matriks CPL-MK di RPS), "
    "lalu atur bobot tiap komponen penilaian terhadap CPL tersebut (total per CPL harus 100%)."
)


def sync_course_weights(state_key, selected_cpl_course):
    if state_key not in st.session_state:
        st.session_state[state_key] = pd.DataFrame(0.0, index=[], columns=components)
    df_w = st.session_state[state_key]
    for cpl in selected_cpl_course:
        if cpl not in df_w.index:
            df_w.loc[cpl] = [0.0] * len(components)
    df_w = df_w.loc[[c for c in selected_cpl_course if c in df_w.index]]
    st.session_state[state_key] = df_w
    return st.session_state[state_key]


course_meta = {}

for fname in valid_files.keys():
    default_name = os.path.splitext(fname)[0].replace("_", " ")
    weights_key = f"course_weights_{fname}"

    with st.expander(f"📁 **{fname}**", expanded=True):
        id_col1, id_col2, id_col3 = st.columns(3)
        with id_col1:
            nama_matkul = st.text_input("Mata Kuliah", default_name, key=f"matkul_{fname}")
        with id_col2:
            sks = st.number_input("SKS", min_value=1, max_value=6, value=3, key=f"sks_{fname}")
        with id_col3:
            kelas = st.text_input("Kelas", "A", key=f"kelas_{fname}")

        default_cpl_course = all_program_cpl[:5] if len(all_program_cpl) >= 5 else all_program_cpl

        selected_cpl_course = st.multiselect(
            "🎯 CPL yang diampu mata kuliah ini",
            all_program_cpl,
            default=default_cpl_course,
            key=f"cplsel_{fname}"
        )

        weights_df_course = sync_course_weights(weights_key, selected_cpl_course)

        if selected_cpl_course:
            bcol1, bcol2 = st.columns(2)
            with bcol1:
                if st.button("⚖️ Ratakan Bobot", key=f"ratakan_{fname}", use_container_width=True):
                    for cpl in selected_cpl_course:
                        st.session_state[weights_key].loc[cpl] = round(100 / len(components), 2)
                    st.rerun()
            with bcol2:
                if st.button("🎯 Normalisasi 100%", key=f"norm_{fname}", use_container_width=True):
                    dfw = st.session_state[weights_key]
                    for cpl in selected_cpl_course:
                        tot = dfw.loc[cpl].sum()
                        if tot > 0:
                            dfw.loc[cpl] = (dfw.loc[cpl] / tot * 100).round(2)
                    st.rerun()

            edited = st.data_editor(
                weights_df_course,
                column_config={
                    comp: st.column_config.NumberColumn(comp, min_value=0.0, max_value=100.0, step=1.0, format="%.1f")
                    for comp in components
                },
                use_container_width=True,
                key=f"editor_{fname}"
            )
            st.session_state[weights_key] = edited

            status_lines = []
            for cpl in selected_cpl_course:
                tot = edited.loc[cpl].sum()
                if abs(tot - 100) < 0.01:
                    status_lines.append(f"✅ {cpl}: {tot:.1f}%")
                else:
                    status_lines.append(f"⚠️ {cpl}: {tot:.1f}%")
            st.caption(" &nbsp;|&nbsp; ".join(status_lines))

            course_weights_dict = edited.loc[selected_cpl_course].to_dict(orient="index")
        else:
            course_weights_dict = {}
            st.info("Belum ada CPL dipilih — mata kuliah ini tidak akan dihitung dalam rekap CPL.")

        course_meta[fname] = {
            "nama_matkul": nama_matkul,
            "sks": sks,
            "kelas": kelas,
            "selected_cpl": selected_cpl_course,
            "weights": course_weights_dict,
        }

st.divider()

# =========================================================
# Hitung CPL untuk setiap mata kuliah (pakai bobot masing-masing)
# =========================================================
results = {}

for fname, info in valid_files.items():
    meta = course_meta[fname]
    course_cpl = meta["selected_cpl"]
    weights = meta["weights"]

    df = info["df"].copy()

    if course_cpl:
        try:
            for cpl in course_cpl:
                df[cpl] = 0
                for comp in components:
                    df[cpl] += df[comp] * (weights[cpl][comp] / 100)
        except KeyError as e:
            st.error(f"❌ {fname}: kolom {e} tidak ditemukan.")
            continue

        cpl_avg = df[course_cpl].mean()
        cpl_attainment = (df[course_cpl] >= AMBANG_KETERCAPAIAN).sum() / len(df) * 100
    else:
        cpl_avg = pd.Series(dtype=float)
        cpl_attainment = pd.Series(dtype=float)

    results[fname] = {
        "df": df,
        "cpl_avg": cpl_avg,
        "cpl_attainment": cpl_attainment,
        "selected_cpl": course_cpl,
        "meta": meta,
        "n_mhs": len(df),
    }

if not results:
    st.stop()

courses_with_cpl = {f: r for f, r in results.items() if r["selected_cpl"]}
if not courses_with_cpl:
    st.warning("⚠️ Belum ada mata kuliah yang memiliki pemetaan CPL. Atur di bagian atas terlebih dahulu.")
    st.stop()

# =========================================================
# Rekap Program — agregasi HANYA dari matkul yang mengampu CPL tsb
# =========================================================


def compute_program_summary(results, all_program_cpl, basis):
    avg_table = pd.DataFrame(index=list(results.keys()), columns=all_program_cpl, dtype=float)
    att_table = pd.DataFrame(index=list(results.keys()), columns=all_program_cpl, dtype=float)

    for fname, r in results.items():
        for cpl in r["selected_cpl"]:
            avg_table.loc[fname, cpl] = r["cpl_avg"][cpl]
            att_table.loc[fname, cpl] = r["cpl_attainment"][cpl]

    program_avg = {}
    program_attainment = {}
    contributor_count = {}

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

# ---------- TAB REKAP PROGRAM ----------
with tabs[0]:
    st.subheader("📈 Rekap Ketercapaian CPL — Tingkat Program Studi (1 Semester)")
    st.caption(
        f"Digabungkan dari {len(courses_with_cpl)} mata kuliah aktif, dibobot berdasarkan **{weighting_basis}**. "
        "Tiap CPL hanya dihitung dari mata kuliah yang benar-benar mengampunya."
    )

    total_mhs = sum(r["n_mhs"] for r in results.values())
    covered_cpl = [c for c in all_program_cpl if contributor_count[c] > 0]
    avg_overall_attainment = program_attainment[covered_cpl].mean() if covered_cpl else 0
    n_tercapai = (program_attainment[covered_cpl] >= AMBANG_KETERCAPAIAN).sum() if covered_cpl else 0

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Jumlah Mata Kuliah", len(results))
    m2.metric("Total Mahasiswa (semua matkul)", total_mhs)
    m3.metric("Rata-rata Ketercapaian CPL", f"{avg_overall_attainment:.1f}%")
    m4.metric("CPL Tercapai", f"{n_tercapai}/{len(covered_cpl)}")

    st.markdown("#### 🗺️ Matriks Pemetaan CPL – Mata Kuliah")
    st.caption("Sel abu-abu (\"-\") berarti mata kuliah tersebut tidak mengampu CPL itu.")
    matrix_display = att_table.copy()
    matrix_display.index = [results[f]["meta"]["nama_matkul"] for f in matrix_display.index]
    styled_matrix = style_status(matrix_display, status_color, AMBANG_KETERCAPAIAN).format(
        "{:.1f}%", na_rep="-"
    )
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
        fig_bar = px.bar(
            avg_long, x="CPL", y="Nilai", color="Mata Kuliah", barmode="group",
            text_auto=".1f", height=420
        )
        fig_bar.add_hline(y=AMBANG_KETERCAPAIAN, line_dash="dash", line_color="red",
                           annotation_text=f"Ambang {AMBANG_KETERCAPAIAN}")
        st.plotly_chart(fig_bar, use_container_width=True)

        st.markdown("#### 🕸️ Profil CPL — Overlay Semua Mata Kuliah + Program")
        fig_radar = go.Figure()
        for fname, r in courses_with_cpl.items():
            vals = list(r["cpl_avg"].values) + [r["cpl_avg"].values[0]]
            labels = list(r["cpl_avg"].index) + [r["cpl_avg"].index[0]]
            fig_radar.add_trace(go.Scatterpolar(
                r=vals, theta=labels, name=r["meta"]["nama_matkul"], opacity=0.6
            ))
        prog_series = program_avg[covered_cpl]
        prog_vals = list(prog_series.values) + [prog_series.values[0]]
        prog_labels = list(prog_series.index) + [prog_series.index[0]]
        fig_radar.add_trace(go.Scatterpolar(
            r=prog_vals, theta=prog_labels, name="🎓 Program (Gabungan)",
            line=dict(color="black", width=3)
        ))
        fig_radar.update_layout(height=480, polar=dict(radialaxis=dict(visible=True, range=[0, 100])))
        st.plotly_chart(fig_radar, use_container_width=True)

    st.markdown("#### 📌 Analisis CQI (Continuous Quality Improvement) — Tingkat Program")
    for cpl in all_program_cpl:
        val = program_attainment[cpl]
        n_mk = contributor_count[cpl]
        if pd.isna(val):
            st.info(f"**{cpl}**: belum diampu mata kuliah manapun — perlu pemetaan CPL-MK.")
        elif val >= AMBANG_KETERCAPAIAN:
            st.success(f"**{cpl}**: {val:.1f}% (dari {n_mk} MK) — ✅ Tercapai. Pertahankan strategi pembelajaran.")
        elif val >= AMBANG_KETERCAPAIAN - 15:
            st.warning(f"**{cpl}**: {val:.1f}% (dari {n_mk} MK) — ⚠️ Mendekati ambang. Perlu penguatan.")
        else:
            st.error(f"**{cpl}**: {val:.1f}% (dari {n_mk} MK) — ❌ Belum tercapai. Perlu tindak lanjut (CQI).")

# ---------- TAB PER MATA KULIAH ----------
for tab, fname in zip(tabs[1:], results.keys()):
    r = results[fname]
    with tab:
        meta = r["meta"]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Mata Kuliah", meta["nama_matkul"])
        c2.metric("Kelas / SKS", f"{meta['kelas']} / {meta['sks']} SKS")
        c3.metric("Jumlah Mahasiswa", r["n_mhs"])
        c4.metric("CPL Diampu", len(r["selected_cpl"]))

        if not r["selected_cpl"]:
            st.warning("Mata kuliah ini belum memiliki pemetaan CPL. Atur di bagian atas halaman.")
            st.dataframe(r["df"], use_container_width=True, height=250)
            continue

        st.markdown("##### 📋 Data Nilai")
        st.dataframe(r["df"], use_container_width=True, height=250)

        cA, cB = st.columns([1, 1])
        with cA:
            st.markdown("##### 📊 Rata-rata CPL")
            st.dataframe(
                r["cpl_avg"].to_frame("Nilai").style.format("{:.1f}"),
                use_container_width=True
            )
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
# PDF: Fungsi generate laporan gabungan
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
        val_str = "-" if pd.isna(v) else f"{v:.2f}"
        data.append([k, val_str])
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

    content.append(Paragraph("LAPORAN KETERCAPAIAN CPL — REKAP PROGRAM STUDI (1 SEMESTER)", styles["Title"]))
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
            f"Kelas: {meta['kelas']} | SKS: {meta['sks']} | Jumlah Mahasiswa: {r['n_mhs']} | "
            f"CPL Diampu: {', '.join(r['selected_cpl']) if r['selected_cpl'] else '-'}",
            styles["Normal"]
        ))
        content.append(Spacer(1, 10))

        if not r["selected_cpl"]:
            content.append(Paragraph("Belum ada pemetaan CPL untuk mata kuliah ini.", styles["Normal"]))
            content.append(PageBreak())
            continue

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
    if st.button("📥 Generate Laporan PDF Gabungan (Semua Matkul + Program)", use_container_width=True):
        pdf_path = generate_pdf_gabungan(
            results, program_avg, program_attainment, contributor_count, weighting_basis, all_program_cpl
        )
        with open(pdf_path, "rb") as f:
            st.download_button(
                "⬇️ Download PDF Laporan Gabungan",
                f,
                file_name="Laporan_CPL_Program_Gabungan.pdf",
                mime="application/pdf",
                use_container_width=True
            )

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
    st.download_button(
        "⬇️ Download Rekap Excel (Semua Matkul + Program + Matriks CPL-MK)",
        excel_buf,
        file_name="Rekap_CPL_Program.xlsx",
        use_container_width=True
    )

# RESET
st.divider()
if st.button("🔄 Reset Semua Data"):
    keys_to_clear = [k for k in st.session_state.keys() if k.startswith(("course_weights_", "cplsel_", "matkul_", "sks_", "kelas_", "editor_"))]
    for k in keys_to_clear:
        del st.session_state[k]
    st.session_state.courses_raw = {}
    st.rerun()

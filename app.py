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

st.set_page_config(page_title="Dashboard CPL - OBE", layout="wide", page_icon="📊")

# =========================================================
# Konfigurasi dasar
# =========================================================
components = ["Tugas", "Partisipasi", "Proyek", "UTS", "Quiz", "UAS"]
REQUIRED_COLS = ["Nama"] + components
cpl_list = ["CPL1", "CPL2", "CPL3", "CPL4", "CPL5", "CPL6", "CPL7"]

COLUMN_ALIASES = {
    "Projek": "Proyek",
    "Project": "Proyek",
    "Quis": "Quiz",
    "Kuis": "Quiz",
    "Kuiz": "Quiz",
}

AMBANG_KETERCAPAIAN = 70  # nilai minimum per mahasiswa dianggap "tercapai"


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


def status_color(val, threshold=AMBANG_KETERCAPAIAN):
    if val >= threshold:
        return "background-color: #d4edda; color: #155724;"
    elif val >= threshold - 15:
        return "background-color: #fff3cd; color: #856404;"
    else:
        return "background-color: #f8d7da; color: #721c24;"


def style_status(styler_input, func):
    """Kompatibel pandas baru (Styler.map) maupun lama (Styler.applymap,
    dihapus mulai pandas >= 2.2/3.0)."""
    styler = styler_input.style if hasattr(styler_input, "style") else styler_input
    if hasattr(styler, "map"):
        return styler.map(func)
    return styler.applymap(func)


# =========================================================
# Header
# =========================================================
st.title("📊 Dashboard CPL OBE")
st.caption(
    "Upload beberapa file nilai (per mata kuliah), atur bobot CPL sekali, "
    "dan lihat rekap ketercapaian CPL baik per matkul maupun tingkat program studi."
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
st.subheader("📥 Upload Nilai — Bisa Banyak Mata Kuliah Sekaligus")

uploaded_files = st.file_uploader(
    "Upload File Excel Nilai Mahasiswa (boleh lebih dari 1 file, misal 4 mata kuliah)",
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
        # dataset default: 2 matkul contoh supaya fitur multi-matkul langsung terlihat
        st.session_state.courses_raw = {
            "Contoh_Matkul_A.xlsx": {"df": generate_default_data(0), "error": None},
            "Contoh_Matkul_B.xlsx": {"df": generate_default_data(3), "error": None},
        }
        st.info("Belum ada file diupload — menampilkan 2 dataset contoh. Upload file untuk mengganti.")

# tampilkan error per file kalau ada
for fname, info in st.session_state.courses_raw.items():
    if info["error"]:
        st.error(f"❌ **{fname}**: {info['error']}")

valid_files = {k: v for k, v in st.session_state.courses_raw.items() if v["error"] is None}

if not valid_files:
    st.warning("Belum ada file valid untuk diproses.")
    st.stop()

# =========================================================
# Identitas per Mata Kuliah
# =========================================================
st.subheader("📌 Identitas Mata Kuliah")
st.caption("Isi nama matkul, SKS, dan kelas untuk masing-masing file yang diupload.")

course_meta = {}
meta_cols = st.columns(min(len(valid_files), 4)) if len(valid_files) <= 4 else None

for i, fname in enumerate(valid_files.keys()):
    default_name = os.path.splitext(fname)[0].replace("_", " ")
    container = meta_cols[i % 4] if meta_cols else st.container()
    with container:
        st.markdown(f"**📁 {fname}**")
        nama_matkul = st.text_input("Mata Kuliah", default_name, key=f"matkul_{fname}")
        sks = st.number_input("SKS", min_value=1, max_value=6, value=3, key=f"sks_{fname}")
        kelas = st.text_input("Kelas", "A", key=f"kelas_{fname}")
        course_meta[fname] = {"nama_matkul": nama_matkul, "sks": sks, "kelas": kelas}

st.divider()

# =========================================================
# Pengaturan Bobot CPL (global, berlaku ke semua matkul)
# =========================================================
st.sidebar.header("⚙️ Pengaturan CPL")
st.sidebar.caption("Bobot ini berlaku untuk semua mata kuliah yang diupload.")

selected_cpl = st.sidebar.multiselect(
    "Pilih CPL",
    cpl_list,
    default=["CPL1", "CPL3", "CPL4", "CPL5"]
)

if "weights_df" not in st.session_state:
    st.session_state.weights_df = pd.DataFrame(0.0, index=[], columns=components)


def sync_weights_table(cpl_now, equal_split=False):
    df_w = st.session_state.weights_df
    for cpl in cpl_now:
        if cpl not in df_w.index:
            val = round(100 / len(components), 2) if equal_split else 0.0
            df_w.loc[cpl] = [val] * len(components)
    df_w = df_w.loc[[c for c in cpl_now if c in df_w.index]]
    st.session_state.weights_df = df_w


sync_weights_table(selected_cpl)

col1, col2 = st.sidebar.columns(2)
with col1:
    if st.button("⚖️ Ratakan Bobot", use_container_width=True):
        for cpl in selected_cpl:
            st.session_state.weights_df.loc[cpl] = round(100 / len(components), 2)
        st.rerun()
with col2:
    if st.button("🎯 Normalisasi 100%", use_container_width=True):
        df_w = st.session_state.weights_df
        for cpl in selected_cpl:
            row_total = df_w.loc[cpl].sum()
            if row_total > 0:
                df_w.loc[cpl] = (df_w.loc[cpl] / row_total * 100).round(2)
        st.rerun()

if selected_cpl:
    edited_df = st.sidebar.data_editor(
        st.session_state.weights_df,
        column_config={
            comp: st.column_config.NumberColumn(comp, min_value=0.0, max_value=100.0, step=1.0, format="%.1f")
            for comp in components
        },
        use_container_width=True,
        key="weights_editor"
    )
    st.session_state.weights_df = edited_df

    for cpl in selected_cpl:
        total = edited_df.loc[cpl].sum()
        if abs(total - 100) < 0.01:
            st.sidebar.success(f"{cpl}: {total:.1f}% ✅")
        else:
            st.sidebar.warning(f"{cpl}: {total:.1f}% ⚠️")

    cpl_weights = edited_df.loc[selected_cpl].to_dict(orient="index")
else:
    cpl_weights = {}
    st.sidebar.info("Pilih minimal 1 CPL.")

st.sidebar.divider()
weighting_basis = st.sidebar.radio(
    "📐 Dasar Pembobotan Rekap Program",
    ["SKS", "Jumlah Mahasiswa", "Rata-rata Sederhana"],
    help="Menentukan cara menggabungkan hasil CPL antar mata kuliah menjadi rekap tingkat program studi."
)
ambang = st.sidebar.slider("🎯 Ambang Ketercapaian per Mahasiswa", 0, 100, AMBANG_KETERCAPAIAN)
AMBANG_KETERCAPAIAN = ambang

if not selected_cpl:
    st.warning("⚠️ Pilih minimal 1 CPL di sidebar untuk melihat hasil.")
    st.stop()

invalid_cpl = [c for c in selected_cpl if abs(sum(cpl_weights[c].values()) - 100) > 0.01]
if invalid_cpl:
    st.warning(f"⚠️ Bobot untuk {', '.join(invalid_cpl)} belum 100%. Hasil tetap dihitung, tapi periksa kembali di sidebar.")

# =========================================================
# Hitung CPL untuk setiap mata kuliah
# =========================================================
results = {}  # fname -> dict(df, cpl_avg, cpl_attainment, meta)

for fname, info in valid_files.items():
    df = info["df"].copy()
    try:
        for cpl in selected_cpl:
            df[cpl] = 0
            for comp in components:
                df[cpl] += df[comp] * (cpl_weights[cpl][comp] / 100)
    except KeyError as e:
        st.error(f"❌ {fname}: kolom {e} tidak ditemukan.")
        continue

    cpl_avg = df[selected_cpl].mean()
    cpl_attainment = (df[selected_cpl] >= AMBANG_KETERCAPAIAN).sum() / len(df) * 100

    results[fname] = {
        "df": df,
        "cpl_avg": cpl_avg,
        "cpl_attainment": cpl_attainment,
        "meta": course_meta[fname],
        "n_mhs": len(df),
    }

if not results:
    st.stop()

# =========================================================
# Rekap Program (gabungan lintas matkul)
# =========================================================


def compute_program_summary(results, basis):
    avg_table = pd.DataFrame({fname: r["cpl_avg"] for fname, r in results.items()}).T
    att_table = pd.DataFrame({fname: r["cpl_attainment"] for fname, r in results.items()}).T

    if basis == "SKS":
        w = pd.Series({fname: r["meta"]["sks"] for fname, r in results.items()})
    elif basis == "Jumlah Mahasiswa":
        w = pd.Series({fname: r["n_mhs"] for fname, r in results.items()})
    else:
        w = pd.Series({fname: 1 for fname, r in results.items()})

    w_norm = w / w.sum()

    program_avg = (avg_table.T * w_norm).T.sum()
    program_attainment = (att_table.T * w_norm).T.sum()

    return avg_table, att_table, program_avg, program_attainment, w


avg_table, att_table, program_avg, program_attainment, weights_used = compute_program_summary(results, weighting_basis)

# =========================================================
# TABS
# =========================================================
tab_labels = ["📈 Rekap Program"] + [f"📚 {results[f]['meta']['nama_matkul']}" for f in results.keys()]
tabs = st.tabs(tab_labels)

# ---------- TAB REKAP PROGRAM ----------
with tabs[0]:
    st.subheader("📈 Rekap Ketercapaian CPL — Tingkat Program Studi")
    st.caption(f"Digabungkan dari {len(results)} mata kuliah, dibobot berdasarkan **{weighting_basis}**.")

    total_mhs = sum(r["n_mhs"] for r in results.values())
    avg_overall_attainment = program_attainment.mean()
    n_tercapai = (program_attainment >= AMBANG_KETERCAPAIAN).sum()

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Jumlah Mata Kuliah", len(results))
    m2.metric("Total Mahasiswa (semua matkul)", total_mhs)
    m3.metric("Rata-rata Ketercapaian CPL", f"{avg_overall_attainment:.1f}%")
    m4.metric("CPL Tercapai", f"{n_tercapai}/{len(selected_cpl)}")

    st.markdown("#### 🎯 Ketercapaian CPL Program (%)")
    cols_metric = st.columns(len(selected_cpl))
    for i, cpl in enumerate(selected_cpl):
        val = program_attainment[cpl]
        delta = val - AMBANG_KETERCAPAIAN
        cols_metric[i].metric(cpl, f"{val:.1f}%", f"{delta:+.1f} vs ambang")

    st.markdown("#### 📊 Perbandingan Nilai Rata-rata CPL Antar Mata Kuliah")
    avg_long = avg_table.reset_index().melt(id_vars="index", var_name="CPL", value_name="Nilai")
    avg_long = avg_long.rename(columns={"index": "Mata Kuliah"})
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
    for fname, r in results.items():
        vals = list(r["cpl_avg"].values) + [r["cpl_avg"].values[0]]
        labels = list(r["cpl_avg"].index) + [r["cpl_avg"].index[0]]
        fig_radar.add_trace(go.Scatterpolar(
            r=vals, theta=labels, name=r["meta"]["nama_matkul"], opacity=0.6
        ))
    prog_vals = list(program_avg.values) + [program_avg.values[0]]
    prog_labels = list(program_avg.index) + [program_avg.index[0]]
    fig_radar.add_trace(go.Scatterpolar(
        r=prog_vals, theta=prog_labels, name="🎓 Program (Gabungan)",
        line=dict(color="black", width=3)
    ))
    fig_radar.update_layout(height=480, polar=dict(radialaxis=dict(visible=True, range=[0, 100])))
    st.plotly_chart(fig_radar, use_container_width=True)

    st.markdown("#### 📋 Tabel Ketercapaian CPL per Mata Kuliah")
    att_display = att_table.copy()
    att_display.index = [results[f]["meta"]["nama_matkul"] for f in att_display.index]
    att_display.loc["🎓 Program (Gabungan)"] = program_attainment
    styled = style_status(att_display, status_color).format("{:.1f}%")
    st.dataframe(styled, use_container_width=True)

    st.markdown("#### 📌 Analisis CQI (Continuous Quality Improvement) — Tingkat Program")
    for cpl in selected_cpl:
        val = program_attainment[cpl]
        if val >= AMBANG_KETERCAPAIAN:
            st.success(f"**{cpl}**: {val:.1f}% — ✅ Tercapai. Pertahankan strategi pembelajaran saat ini.")
        elif val >= AMBANG_KETERCAPAIAN - 15:
            st.warning(f"**{cpl}**: {val:.1f}% — ⚠️ Mendekati ambang. Perlu penguatan pada komponen dengan bobot besar.")
        else:
            st.error(f"**{cpl}**: {val:.1f}% — ❌ Belum tercapai. Perlu tindak lanjut (remedial/redesain RPS).")

# ---------- TAB PER MATA KULIAH ----------
for tab, fname in zip(tabs[1:], results.keys()):
    r = results[fname]
    with tab:
        meta = r["meta"]
        c1, c2, c3 = st.columns(3)
        c1.metric("Mata Kuliah", meta["nama_matkul"])
        c2.metric("Kelas / SKS", f"{meta['kelas']} / {meta['sks']} SKS")
        c3.metric("Jumlah Mahasiswa", r["n_mhs"])

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
                style_status(r["cpl_attainment"].to_frame("Ketercapaian"), status_color).format("{:.1f}%"),
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
        data.append([k, f"{v:.2f}"])
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


def generate_pdf_gabungan(results, program_avg, program_attainment, weighting_basis, filename="laporan_cpl_gabungan.pdf"):
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

    radar_prog = generate_radar_png(program_avg, "radar_program.png")
    content.append(Paragraph("Profil CPL Program (Gabungan)", styles["Heading2"]))
    content.append(Image(radar_prog, width=320, height=320))
    content.append(Spacer(1, 12))

    content.append(Paragraph("Analisis CQI Tingkat Program", styles["Heading2"]))
    for cpl, val in program_attainment.items():
        status = "Tercapai ✅" if val >= AMBANG_KETERCAPAIAN else "Belum Tercapai ❌"
        content.append(Paragraph(f"{cpl}: {val:.2f}% — {status}", styles["Normal"]))

    content.append(PageBreak())

    for fname, r in results.items():
        meta = r["meta"]
        content.append(Paragraph(f"Mata Kuliah: {meta['nama_matkul']}", styles["Title"]))
        content.append(Paragraph(f"Kelas: {meta['kelas']} | SKS: {meta['sks']} | Jumlah Mahasiswa: {r['n_mhs']}", styles["Normal"]))
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
    if st.button("📥 Generate Laporan PDF Gabungan (Semua Matkul + Program)", use_container_width=True):
        pdf_path = generate_pdf_gabungan(results, program_avg, program_attainment, weighting_basis)
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
    excel_buf.seek(0)
    st.download_button(
        "⬇️ Download Rekap Excel (Semua Matkul + Program)",
        excel_buf,
        file_name="Rekap_CPL_Program.xlsx",
        use_container_width=True
    )

# RESET
st.divider()
if st.button("🔄 Reset Semua Data"):
    st.session_state.courses_raw = {}
    st.session_state.weights_df = pd.DataFrame(0.0, index=[], columns=components)
    st.rerun()

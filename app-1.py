import streamlit as st
import pandas as pd
import plotly.express as px
import io

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet

import matplotlib.pyplot as plt

st.set_page_config(page_title="Dashboard CPL OBE", layout="wide")
st.title("📊 Dashboard CPL - OBE BISNIS DIGITAL")

# =========================================================
# Konfigurasi dasar
# =========================================================
components = ["Tugas", "Partisipasi", "Proyek", "UTS", "Quiz", "UAS"]
REQUIRED_COLS = ["Nama"] + components

# Alias kolom yang sering tertukar penulisannya di file upload
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


def generate_default_data():
    data = {
        "Nama": [f"MHS_{i}" for i in range(1, 31)],
        "Tugas": [80 + i % 10 for i in range(30)],
        "Partisipasi": [75 + i % 10 for i in range(30)],
        "Proyek": [78 + i % 10 for i in range(30)],
        "UTS": [77 + i % 10 for i in range(30)],
        "Quiz": [76 + i % 10 for i in range(30)],
        "UAS": [79 + i % 10 for i in range(30)]
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


if "data" not in st.session_state:
    st.session_state.data = None

# =========================================================
# Upload / Template
# =========================================================
st.subheader("📥 Download Template Excel")

template_file = generate_template_excel()

st.download_button(
    "Download Template Excel",
    template_file,
    file_name="Template_CPL.xlsx"
)

uploaded_file = st.file_uploader(
    "Upload File Excel Nilai Mahasiswa",
    type=["xlsx"],
    key="main_uploader"
)

if uploaded_file:
    try:
        df_upload = pd.read_excel(uploaded_file)
        df_upload = normalize_columns(df_upload)

        missing = [c for c in REQUIRED_COLS if c not in df_upload.columns]
        if missing:
            st.error(
                f"❌ Kolom berikut tidak ditemukan di file: {', '.join(missing)}. "
                f"Kolom yang tersedia: {', '.join(df_upload.columns)}. "
                "Pastikan nama kolom sesuai template (Nama, Tugas, Partisipasi, "
                "Proyek, UTS, Quiz, UAS)."
            )
            st.stop()

        st.session_state.data = df_upload
        st.success("File berhasil diupload ✅")
    except Exception as e:
        st.error(f"Gagal membaca file: {e}")
        st.stop()
else:
    if st.session_state.data is None:
        st.session_state.data = generate_default_data()
        st.info("Menggunakan dataset default")

# =========================================================
# Pengaturan CPL (versi praktis: tabel editable)
# =========================================================
st.sidebar.header("⚙️ Pengaturan CPL")

cpl_list = ["CPL1", "CPL2", "CPL3", "CPL4", "CPL5", "CPL6", "CPL7"]

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

st.sidebar.caption("Edit langsung di tabel. Klik sel untuk ubah nilai.")

if selected_cpl:
    edited_df = st.sidebar.data_editor(
        st.session_state.weights_df,
        column_config={
            comp: st.column_config.NumberColumn(
                comp, min_value=0.0, max_value=100.0, step=1.0, format="%.1f"
            )
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
            st.sidebar.warning(f"{cpl}: {total:.1f}% ⚠️ (harus 100%)")

    cpl_weights = edited_df.loc[selected_cpl].to_dict(orient="index")
else:
    cpl_weights = {}
    st.sidebar.info("Pilih minimal 1 CPL di atas.")

# =========================================================
# Fungsi Radar Chart & PDF
# =========================================================


def generate_radar_chart(cpl_avg, filename="radar.png"):
    labels = list(cpl_avg.index)
    values = list(cpl_avg.values)

    values += values[:1]
    labels += labels[:1]

    plt.figure()
    ax = plt.subplot(111, polar=True)
    ax.plot(values)
    ax.fill(values, alpha=0.1)
    ax.set_xticks(range(len(labels) - 1))
    ax.set_xticklabels(labels[:-1])

    plt.savefig(filename)
    plt.close()

    return filename


def generate_pdf(cpl_avg, cpl_attainment, matkul, kelas, jumlah_mhs, filename="laporan_cpl.pdf"):
    doc = SimpleDocTemplate(filename)
    styles = getSampleStyleSheet()
    content = []

    content.append(Paragraph("LAPORAN CPL - OBE", styles["Title"]))
    content.append(Spacer(1, 12))

    content.append(Paragraph(f"Mata Kuliah: {matkul}", styles["Normal"]))
    content.append(Paragraph(f"Kelas: {kelas}", styles["Normal"]))
    content.append(Paragraph(f"Jumlah Mahasiswa: {jumlah_mhs}", styles["Normal"]))

    content.append(Spacer(1, 12))

    content.append(Paragraph("Rata-rata CPL:", styles["Heading2"]))
    for cpl, val in cpl_avg.items():
        content.append(Paragraph(f"{cpl}: {round(val, 2)}", styles["Normal"]))

    content.append(Spacer(1, 12))

    content.append(Paragraph("Ketercapaian CPL (%):", styles["Heading2"]))
    for cpl, val in cpl_attainment.items():
        content.append(Paragraph(f"{cpl}: {round(val, 2)}%", styles["Normal"]))

    content.append(Spacer(1, 12))

    radar_path = generate_radar_chart(cpl_avg)
    content.append(Paragraph("Spider Chart CPL:", styles["Heading2"]))
    content.append(Image(radar_path, width=400, height=300))

    content.append(Spacer(1, 12))

    content.append(Paragraph("Analisis CQI:", styles["Heading2"]))
    for cpl, val in cpl_attainment.items():
        status = "Tercapai" if val >= 70 else "Belum"
        content.append(Paragraph(f"{cpl}: {status}", styles["Normal"]))

    doc.build(content)
    return filename


# =========================================================
# Data & Perhitungan
# =========================================================
df = st.session_state.data.copy()

st.subheader("📋 Data")
st.dataframe(df)

if not selected_cpl:
    st.warning("⚠️ Pilih minimal 1 CPL di sidebar untuk melihat hasil perhitungan.")
    st.stop()

# Validasi bobot sebelum hitung
invalid_cpl = [
    cpl for cpl in selected_cpl
    if abs(sum(cpl_weights[cpl].values()) - 100) > 0.01
]
if invalid_cpl:
    st.warning(
        f"⚠️ Bobot untuk {', '.join(invalid_cpl)} belum berjumlah 100%. "
        "Gunakan tombol 'Normalisasi 100%' di sidebar atau perbaiki manual."
    )

# Hitung CPL (dengan guard KeyError)
try:
    for cpl in selected_cpl:
        df[cpl] = 0
        for comp in components:
            df[cpl] += df[comp] * (cpl_weights[cpl][comp] / 100)
except KeyError as e:
    st.error(f"❌ Kolom {e} tidak ditemukan di data. Periksa kembali file yang diupload.")
    st.stop()

# Rekap
cpl_avg = df[selected_cpl].mean()
cpl_attainment = (df[selected_cpl] >= 70).sum() / len(df) * 100

st.subheader("📊 Rekap CPL")
st.dataframe(cpl_avg)
st.dataframe(cpl_attainment)

# Radar chart
radar_df = pd.DataFrame({"CPL": cpl_avg.index, "Nilai": cpl_avg.values})
st.plotly_chart(px.line_polar(radar_df, r="Nilai", theta="CPL", line_close=True))

# =========================================================
# Detail Mahasiswa
# =========================================================
st.subheader("🔎 Mahasiswa")

selected_student = st.selectbox("Pilih Mahasiswa", df["Nama"])
student_data = df[df["Nama"] == selected_student]

st.dataframe(student_data)

st.subheader("📌 Identitas")

matkul = st.text_input("Mata Kuliah", "Algoritma")
kelas = st.text_input("Kelas", "A")
Dosen = st.text_input("Dosen", "Alam dan Yin")
jumlah_mhs = len(df)

# =========================================================
# Export PDF
# =========================================================
st.subheader("📄 Export")

if st.button("Generate PDF"):
    pdf_file = generate_pdf(cpl_avg, cpl_attainment, matkul, kelas, jumlah_mhs)

    with open(pdf_file, "rb") as f:
        st.download_button(
            "Download PDF",
            f,
            file_name="Laporan_CPL_OBE.pdf",
            mime="application/pdf"
        )

# RESET
if st.button("🔄 Reset"):
    st.session_state.data = generate_default_data()
    st.session_state.weights_df = pd.DataFrame(0.0, index=[], columns=components)
    st.rerun()

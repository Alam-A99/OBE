import streamlit as st
import pandas as pd
import plotly.express as px
import io

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet

import matplotlib.pyplot as plt

st.set_page_config(page_title="Dashboard CPL OBE", layout="wide")
st.title("📊 Dashboard CPL - OBE BISNIS DIGITAL")


def generate_default_data():
    data = {
        "Nama": [f"MHS_{i}" for i in range(1, 31)],
        "Tugas": [80+i%10 for i in range(30)],
        "Partisipasi": [75+i%10 for i in range(30)],
        "Proyek": [78+i%10 for i in range(30)],
        "UTS": [77+i%10 for i in range(30)],
        "Quiz": [76+i%10 for i in range(30)],
        "UAS": [79+i%10 for i in range(30)]
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
        df = pd.read_excel(uploaded_file)
        st.session_state.data = df
        st.success("File berhasil diupload ✅")
    except Exception as e:
        st.error(e)
else:
    if st.session_state.data is None:
        st.session_state.data = generate_default_data()
        st.info("Menggunakan dataset default")


st.sidebar.header("⚙️ Pengaturan CPL")

cpl_list = ["CPL1","CPL2","CPL3","CPL4","CPL5","CPL6","CPL7"]

selected_cpl = st.sidebar.multiselect(
    "Pilih CPL",
    cpl_list,
    default=["CPL1","CPL3","CPL4","CPL5"]
)

components = ["Tugas","Partisipasi","Proyek","UTS","Quiz","UAS"]

cpl_weights = {}

for cpl in selected_cpl:
    st.sidebar.subheader(f"Bobot {cpl}")
    weights = {}
    total = 0

    for comp in components:
        val = st.sidebar.number_input(
            f"{cpl}-{comp}",
            0.0, 100.0, 0.0,
            key=f"{cpl}_{comp}"
        )
        weights[comp] = val
        total += val

    st.sidebar.write(f"Total: {total}%")

    if total != 100:
        st.sidebar.warning("⚠️ Total harus 100%")

    cpl_weights[cpl] = weights


def generate_radar_chart(cpl_avg, filename="radar.png"):
    labels = list(cpl_avg.index)
    values = list(cpl_avg.values)

    values += values[:1]
    labels += labels[:1]

    plt.figure()
    ax = plt.subplot(111, polar=True)
    ax.plot(values)
    ax.fill(values, alpha=0.1)
    ax.set_xticks(range(len(labels)-1))
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
        content.append(Paragraph(f"{cpl}: {round(val,2)}", styles["Normal"]))

    content.append(Spacer(1, 12))

    content.append(Paragraph("Ketercapaian CPL (%):", styles["Heading2"]))
    for cpl, val in cpl_attainment.items():
        content.append(Paragraph(f"{cpl}: {round(val,2)}%", styles["Normal"]))

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


df = st.session_state.data.copy()

st.subheader("📋 Data")
st.dataframe(df)

# Hitung CPL
for cpl in selected_cpl:
    df[cpl] = 0
    for comp in components:
        df[cpl] += df[comp] * (cpl_weights[cpl][comp] / 100)

# Rekap
cpl_avg = df[selected_cpl].mean()
cpl_attainment = (df[selected_cpl] >= 70).sum() / len(df) * 100

st.subheader("📊 Rekap CPL")
st.dataframe(cpl_avg)
st.dataframe(cpl_attainment)

# Radar chart
radar_df = pd.DataFrame({"CPL": cpl_avg.index, "Nilai": cpl_avg.values})
st.plotly_chart(px.line_polar(radar_df, r="Nilai", theta="CPL", line_close=True))


st.subheader("🔎 Mahasiswa")

selected_student = st.selectbox("Pilih Mahasiswa", df["Nama"])
student_data = df[df["Nama"] == selected_student]

st.dataframe(student_data)

st.subheader("📌 Identitas")

matkul = st.text_input("Mata Kuliah", "Algoritma")
kelas = st.text_input("Kelas", "A")
Dosen = st.text_input("Dosen", "Alam dan Yin")
jumlah_mhs = len(df)


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
    st.rerun()

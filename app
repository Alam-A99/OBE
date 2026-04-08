import streamlit as st
import pandas as pd
import plotly.express as px

# PDF
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet

# Radar chart image
import matplotlib.pyplot as plt

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="Dashboard CPL OBE", layout="wide")
st.title("📊 Dashboard CPL - OBE BISNIS DIGITAL UNM")

# =========================
# SESSION
# =========================
if "data" not in st.session_state:
    st.session_state.data = None

# UPLOAD
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

# SIDEBAR CPL
st.sidebar.header("⚙️ Pengaturan CPL")

cpl_list = ["CPL1","CPL2","CPL3","CPL4","CPL5","CPL6","CPL7"]

selected_cpl = st.sidebar.multiselect(
    "Pilih CPL",
    cpl_list,
    default=["CPL1","CPL2","CPL3","CPL4"]
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

# RADAR IMAGE FUNCTION
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

# PDF FUNCTION
def generate_pdf(cpl_avg, cpl_attainment, matkul, kelas, jumlah_mhs, filename="laporan_cpl.pdf"):
    doc = SimpleDocTemplate(filename)
    styles = getSampleStyleSheet()
    content = []

    # Judul
    content.append(Paragraph("LAPORAN CPL - OBE", styles["Title"]))
    content.append(Spacer(1, 12))

    # Identitas
    content.append(Paragraph(f"Mata Kuliah: {matkul}", styles["Normal"]))
    content.append(Paragraph(f"Kelas: {kelas}", styles["Normal"]))
    content.append(Paragraph(f"Jumlah Mahasiswa: {jumlah_mhs}", styles["Normal"]))
    content.append(Spacer(1, 12))

    # Rata-rata
    content.append(Paragraph("Rata-rata CPL:", styles["Heading2"]))
    for cpl, val in cpl_avg.items():
        content.append(Paragraph(f"{cpl}: {round(val,2)}", styles["Normal"]))

    content.append(Spacer(1, 12))

    # Ketercapaian
    content.append(Paragraph("Ketercapaian CPL (%):", styles["Heading2"]))
    for cpl, val in cpl_attainment.items():
        content.append(Paragraph(f"{cpl}: {round(val,2)}%", styles["Normal"]))

    content.append(Spacer(1, 12))

    # Radar Chart
    radar_path = generate_radar_chart(cpl_avg)
    content.append(Paragraph("Spider Chart CPL:", styles["Heading2"]))
    content.append(Image(radar_path, width=400, height=300))

    content.append(Spacer(1, 12))

    # CQI
    content.append(Paragraph("Analisis CQI:", styles["Heading2"]))
    for cpl, val in cpl_attainment.items():
        if val >= 80:
            status = "Sangat Baik"
        elif val >= 60:
            status = "Perlu peningkatan"
        else:
            status = "Perlu perbaikan"

        content.append(Paragraph(f"{cpl}: {status}", styles["Normal"]))

    doc.build(content)
    return filename

# PROCESS
if st.session_state.data is not None:

    df = st.session_state.data.copy()

    st.subheader("📋 Data Awal")
    st.dataframe(df)

    # Validasi
    missing = [col for col in components if col not in df.columns]
    if missing:
        st.error(f"Kolom tidak lengkap: {missing}")
        st.stop()

    # Hitung CPL
    for cpl in selected_cpl:
        df[cpl] = 0
        for comp in components:
            df[cpl] += df[comp] * (cpl_weights[cpl][comp] / 100)

    # Nilai akhir
    df["Nilai Akhir"] = df[selected_cpl].mean(axis=1)

    def indeks(x):
        if x >= 85:
            return "A"
        elif x >= 70:
            return "B"
        elif x >= 60:
            return "C"
        else:
            return "D"

    df["Indeks"] = df["Nilai Akhir"].apply(indeks)

    st.subheader("✅ Hasil CPL")
    st.dataframe(df)

    # Rekap
    cpl_avg = df[selected_cpl].mean()
    cpl_attainment = (df[selected_cpl] >= 70).sum() / len(df) * 100

    st.subheader("📊 Rekap CPL")
    st.dataframe(cpl_avg)
    st.dataframe(cpl_attainment)

    # Radar chart
    radar_df = pd.DataFrame({"CPL": cpl_avg.index, "Nilai": cpl_avg.values})
    st.plotly_chart(px.line_polar(radar_df, r="Nilai", theta="CPL", line_close=True))

    # IDENTITAS INPUT
    st.subheader("📌 Identitas Laporan")

    matkul = st.text_input("Mata Kuliah", "Algoritma dan Pemrograman")
    kelas = st.text_input("Kelas", "A")
    Dosen = st.text_input("Dosen", "alam dan yin")
    jumlah_mhs = len(df)

    # EXPORT PDF
  
    st.subheader("📄 Export PDF")

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
    st.session_state.data = None
    st.rerun()

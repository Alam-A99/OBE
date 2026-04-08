# 📊 Dashboard CPL Berbasis OBE
### Program Studi Bisnis Digital
### Fakultas Ekonomi dan Bisnis
### Universitas Negeri Makassar (UNM)
---
## Deskripsi Sistem

Dashboard ini merupakan sistem berbasis **Outcome-Based Education (OBE)** yang digunakan untuk:

* Mengukur capaian pembelajaran lulusan (**CPL**)
* Menganalisis performa mahasiswa
* Mendukung evaluasi berkelanjutan (**Continuous Quality Improvement / CQI**)
* Menyediakan laporan otomatis untuk kebutuhan akreditasi (BAN-PT / LAMEMBA)


## ⚙️ Fitur Utama

* ✅ Upload dataset nilai mahasiswa (Excel)
* ✅ Template Excel siap pakai
* ✅ Dataset default (untuk demo)
* ✅ Mapping CPL dinamis (CPL1–CPL7)
* ✅ Pengaturan bobot penilaian (Tugas, UTS, dll.)
* ✅ Dashboard visual (Radar Chart & Bar Chart)
* ✅ Analisis per mahasiswa
* ✅ Status ketercapaian CPL (≥70)
* ✅ Analisis CQI otomatis
* ✅ Export laporan PDF (lengkap dengan grafik dan identitas)


## Konsep OBE yang Digunakan

Sistem ini mengacu pada:

* Outcome-Based Education (OBE)
* Constructive Alignment
* Multi-dimensional Learning Outcomes

Pendekatan:

```text
Komponen Nilai → CPL (Mata Kuliah) → CPL (Prodi) → Evaluasi CQI
```

## Struktur Proyek

```bash
cpl-dashboard/
│
├── app.py
├── requirements.txt
├── README.md
```

## Requirements

Buat file `requirements.txt`:

```txt
streamlit
pandas
plotly
openpyxl
reportlab
matplotlib
```


##  Instalasi Lokal

```bash
pip install -r requirements.txt
streamlit run app.py
```


## Deployment ke GitHub

### 1. Inisialisasi Git

```bash
git init
git add .
git commit -m "Initial commit CPL Dashboard"
```

### 2. Hubungkan ke Repository

```bash
git remote add origin https://github.com/USERNAME/cpl-dashboard.git
git branch -M main
git push -u origin main
```

## Deployment ke Streamlit Cloud
👉 Streamlit Community Cloud

### Langkah:
1. Login ke Streamlit Cloud
2. Klik **New App**
3. Pilih repository GitHub
4. Pilih file:
   * `app.py`
5. Klik **Deploy**


## 🔁 Auto Deployment
Setiap perubahan kode:

```bash
git add .
git commit -m "update"
git push
```

➡️ Akan otomatis:

* Update di GitHub
* Redeploy aplikasi di Streamlit

## 🌍 Integrasi dengan Blogger
Aplikasi dapat di-embed ke Blogger menggunakan iframe:

```html
<iframe 
    src="https://obe-cpl-bisdigunm.streamlit.app/"
    width="100%" 
    height="800">
</iframe>
```
## 📊 Struktur Dataset

Format Excel:

| Nama | Tugas | Partisipasi | Proyek | UTS | Quiz | UAS |
| ---- | ----- | ----------- | ------ | --- | ---- | --- |

## Output Sistem

* Rata-rata CPL
* Ketercapaian (%)
* Radar Chart
* Analisis mahasiswa
* Status CPL
* Laporan PDF otomatis

## Output PDF

Laporan PDF berisi:

* Identitas:
  * Mata Kuliah
  * Kelas
  * Jumlah Mahasiswa
* Rata-rata CPL
* Ketercapaian CPL
* Spider Chart
* Analisis CQI


## 🧠 Interpretasi CPL

| Nilai | Status         |
| ----- | -------------- |
| ≥ 70  | Tercapai       |
| < 70  | Belum Tercapai |


## Pengembangan Lanjutan

* Multi mata kuliah → CPL Prodi
* Integrasi database (PostgreSQL)
* Login multi-user (dosen)
* Tracking CPL antar semester
* Integrasi sistem akademik

## 👨‍🏫 Pengembang

**Program Studi Bisnis Digital**
Fakultas Ekonomi dan Bisnis
Universitas Negeri Makassar


## 📌 Lisensi

Digunakan untuk keperluan akademik, penelitian, dan pengembangan sistem OBE di lingkungan pendidikan tinggi.
---

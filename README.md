# SIHADIR — Sistem Informasi Kehadiran Digital

![Python](https://img.shields.io/badge/Python-3.13-3776AB?style=flat&logo=python&logoColor=white)
![Django](https://img.shields.io/badge/Django-5.2.19-092E20?style=flat&logo=django&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Neon-4169E1?style=flat&logo=postgresql&logoColor=white)
![Bootstrap](https://img.shields.io/badge/Bootstrap-5-7952B3?style=flat&logo=bootstrap&logoColor=white)
![Vercel](https://img.shields.io/badge/Deployment-Vercel-000000?style=flat&logo=vercel&logoColor=white)

**SIHADIR** merupakan aplikasi presensi perkuliahan berbasis web yang dikembangkan untuk membantu proses pencatatan, pemantauan, koreksi, dan rekapitulasi kehadiran mahasiswa secara digital.

Proyek ini dikembangkan menggunakan metodologi **Waterfall** sebagai bagian dari tugas mata kuliah **Manajemen Proyek Teknologi Informasi (MPTI)** pada Program Studi Pendidikan Teknik Informatika dan Komputer, Fakultas Teknik, Universitas Negeri Medan.

🌐 **Live Staging:** [https://sihadir-staging.vercel.app](https://sihadir-staging.vercel.app)

---

## Fitur Utama

### 1. Autentikasi dan Manajemen Akun
- **Multi-Role Access:** Pemisahan hak akses untuk Mahasiswa dan Dosen.
- **Registrasi Mahasiswa:** Pendaftaran akun secara mandiri menggunakan NIM sebagai username.
- **Manajemen Profil:** Mahasiswa dapat memperbarui informasi profil dan kata sandi.
- **Administrasi Pengguna:** Pengelolaan akun dosen dan administrasi sistem melalui Django Admin.

### 2. Manajemen Kelas
- **Pembuatan Kelas:** Dosen dapat membuat dan mengelola kelas perkuliahan.
- **Kode Bergabung Otomatis:** Sistem menghasilkan kode kelas unik sepanjang 6 karakter berupa kombinasi huruf dan angka.
- **Keanggotaan Kelas:** Mahasiswa dapat bergabung menggunakan kode yang diberikan dosen.
- **Riwayat Keanggotaan:** Sistem menyimpan periode bergabung dan keluar mahasiswa sehingga riwayat kelas tetap dapat ditelusuri.

### 3. Sesi dan Pengisian Presensi
- **Kode Presensi Otomatis:** Sistem menghasilkan kode presensi 4 karakter ketika dosen membuka sesi.
- **Pengaturan Durasi:** Dosen dapat memilih durasi sesi selama 5, 10, 15, 20, atau 30 menit.
- **Satu Sesi Aktif per Kelas:** Sistem membatasi hanya satu sesi presensi aktif pada setiap kelas.
- **Validasi Presensi:** Sistem memeriksa kode, status sesi, dan keanggotaan mahasiswa sebelum mencatat kehadiran.
- **Pencegahan Pengiriman Ganda:** Mahasiswa tidak dapat mengirimkan presensi berulang pada sesi yang sama.
- **Pembatasan Percobaan Kode:** Maksimal 5 percobaan kode yang salah dengan masa pembatasan selama 600 detik.

### 4. Koreksi dan Rekapitulasi Kehadiran
- **Koreksi Status:** Dosen dapat memperbarui status kehadiran setelah sesi berakhir atau ditutup.
- **Status Kehadiran:** Hadir, Izin, Sakit, dan Alfa.
- **Audit Log:** Setiap perubahan status disertai alasan serta pencatatan identitas pengubah dan waktu perubahan.
- **Rekapitulasi Dosen:** Dosen dapat melihat rekapitulasi kehadiran berdasarkan kelas dan rentang tanggal.
- **Riwayat Mahasiswa:** Mahasiswa dapat melihat riwayat dan status kehadiran pribadi, termasuk dari kelas yang pernah diikuti.

---

## Alur Penggunaan

### Mahasiswa
1. Melakukan registrasi menggunakan NIM.
2. Login ke aplikasi dan melengkapi profil.
3. Bergabung ke kelas menggunakan kode yang diberikan dosen.
4. Membuka halaman kelas untuk melihat sesi presensi.
5. Memasukkan kode presensi ketika sesi masih aktif.
6. Melihat status dan riwayat kehadiran melalui halaman pribadi.

### Dosen
1. Login menggunakan akun yang telah disediakan administrator.
2. Membuat kelas perkuliahan dan membagikan kode bergabung.
3. Membuka sesi presensi serta menentukan durasinya.
4. Membagikan kode presensi yang dihasilkan sistem kepada mahasiswa.
5. Memantau mahasiswa yang telah mengisi presensi.
6. Melakukan koreksi status jika diperlukan dan melihat rekapitulasi kehadiran.

---

## Teknologi yang Digunakan

| Komponen | Teknologi |
|:---|:---|
| **Backend** | Python 3.13, Django 5.2.19 |
| **Frontend** | HTML5, CSS3, Bootstrap 5, JavaScript |
| **Database Lokal** | SQLite |
| **Database Deployment** | PostgreSQL (Neon) |
| **Web Server** | Gunicorn |
| **Static Files** | WhiteNoise |
| **Hosting & Deployment** | Vercel (Region Singapore `sin1`) |
| **Version Control** | Git dan GitHub |
| **Pemodelan Sistem** | diagrams.net |

---

## Instalasi dan Menjalankan Aplikasi

Ikuti langkah berikut untuk menjalankan SIHADIR secara lokal.

### 1. Clone Repository

```bash
git clone https://github.com/byJoshF/mpti-sistem-informasi-presensi.git
```

Masuk ke direktori proyek:

```bash
cd mpti-sistem-informasi-presensi
```

### 2. Membuat Virtual Environment

```bash
python -m venv .venv
```

**Windows PowerShell:**

```powershell
.\.venv\Scripts\Activate.ps1
```

**Linux / macOS:**

```bash
source .venv/bin/activate
```

### 3. Menginstal Dependensi

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Konfigurasi Database dan Environment

Sesuaikan konfigurasi database dan variabel lingkungan dengan pengaturan proyek. Untuk pengembangan lokal, gunakan SQLite apabila konfigurasi lokal sudah mengaturnya.

Apabila tersedia file `.env.example`, salin menjadi `.env` dan sesuaikan nilainya:

```powershell
Copy-Item .env.example .env
```

Jangan mengunggah file `.env`, secret key, password, atau kredensial database ke GitHub.

### 5. Migrasi Database

```bash
python manage.py migrate
```

### 6. Membuat Akun Administrator

```bash
python manage.py createsuperuser
```

Akun administrator digunakan untuk mengakses halaman Django Admin dan mengelola kebutuhan administrasi pengguna.

### 7. Menjalankan Server

```bash
python manage.py runserver
```

Aplikasi dapat diakses melalui:

- **Aplikasi:** http://127.0.0.1:8000/
- **Django Admin:** http://127.0.0.1:8000/admin/

---

## Deployment

SIHADIR menggunakan Vercel sebagai platform deployment dan Neon sebagai penyedia database PostgreSQL.

| Komponen | Konfigurasi |
|:---|:---|
| **Platform Hosting** | Vercel |
| **Region Hosting** | Singapore (`sin1`) |
| **Database** | PostgreSQL (Neon) |
| **Region Database** | Asia Pacific (Singapore) |
| **Lingkungan** | Staging |

🌐 **Akses Aplikasi:** [SIHADIR Staging](https://sihadir-staging.vercel.app)

Lingkungan staging digunakan untuk demonstrasi dan pengujian hasil pengembangan proyek.

---

## Tim Pengembang - Kelompok 9

**Mata Kuliah:** Manajemen Proyek Teknologi Informasi (MPTI)

**Dosen Pengampu:** Harvei Desmon Hutahaean, S.Kom., M.Kom.

| Nama | GitHub | Peran |
|:---|:---|:---|
| **Joshua F. Sitanggang** | [@byJoshF](https://github.com/byJoshF) | Developer & Integrator |
| **Roland Anugrah Sitanggang** | [@rolandsitanggang](https://github.com/rolandsitanggang) | Project Manager & Analis |
| **Fransiskus Jul Rikar Gea** | [@fransiskus07-jr](https://github.com/fransiskus07-jr) | UI/UX Designer & QA |

---

<p align="center">
  <strong>~ SIHADIR ~</strong>
</p>

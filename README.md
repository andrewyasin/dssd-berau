# 📊 Dashboard Rekap Tahapan DSSD

Website publik untuk memantau progress keterisian **Data Statistik Sektoral Daerah (DSSD)** di e-Walidata SIPD — tanpa perlu login, bisa diakses siapa saja.

🔗 **Demo:** [andrewyasin.github.io/dssd-berau](https://andrewyasin.github.io/dssd-berau/)

---

## 📋 Apa itu dashboard ini?

Dashboard ini menampilkan seberapa jauh OPD-OPD di suatu daerah telah mengisi data statistik sektoral mereka di sistem e-Walidata SIPD. Data yang ditampilkan mencakup:

- Jumlah data induk per urusan pemerintahan
- Berapa yang sudah terisi, belum terisi, dan tidak aktif
- Persentase keterisian per urusan
- Progress keseluruhan dalam satu grafik

---

## 🚀 Cara Membuat Dashboard untuk Instansi Lain

### Yang Dibutuhkan
- Akun GitHub (gratis) → daftar di [github.com](https://github.com)
- Akses login ke e-Walidata SIPD daerah Anda
- Waktu sekitar 15 menit

---

### Langkah 1 — Salin (Fork) Repository Ini

1. Klik tombol **Fork** di pojok kanan atas halaman ini
2. Isi nama repository sesuai instansi Anda, contoh: `dssd-kotasamarinda`
3. Pastikan pilih **Public**
4. Klik **Create fork**

---

### Langkah 2 — Aktifkan GitHub Pages

1. Di repository hasil fork, buka tab **Settings**
2. Di menu kiri klik **Pages**
3. Bagian **Source** → pilih **Deploy from a branch**
4. Branch: **main**, folder: **/ (root)**
5. Klik **Save**

Tunggu 1–2 menit. Website Anda akan aktif di:
```
https://[username-github-anda].github.io/[nama-repo]/
```

---

### Langkah 3 — Sesuaikan untuk Daerah Anda

Buka file **`index.html`** di GitHub → klik ikon pensil ✏️, lalu cari dan ubah bagian berikut:

**Nama daerah** (cari teks `KAB. BERAU`, ganti sesuai daerah Anda):
```
PEMERINTAH KAB. BERAU        → PEMERINTAH KOTA SAMARINDA
e-Walidata · KAB. BERAU      → e-Walidata · KOTA SAMARINDA
Kabupaten Berau (6403)        → Kota Samarinda (6472)
```

**Kode pemda** (cari `kodepemda=6403`, ganti dengan kode daerah Anda):
```
kodepemda=6403   →   kodepemda=6472
```

> 💡 Kode pemda bisa dilihat di URL saat login ke SIPD e-Walidata daerah Anda.

Setelah selesai klik **Commit changes**.

---

### Langkah 4 — Isi Data Pertama Kali

Data yang tampil di website dibaca dari file `data/rekap.json`. Anda perlu mengisinya dengan data dari SIPD daerah Anda.

**Cara mengambil data dari SIPD:**

1. Login ke SIPD e-Walidata daerah Anda
2. Buka menu **Master → Rekap Tahapan DSSD**
3. Tekan **F12** di keyboard → klik tab **Network**
4. Tekan **F5** untuk refresh halaman
5. Di daftar yang muncul, cari request bernama `ajax_list_pemda_keterisian`
6. Klik request tersebut → klik tab **Response**
7. Tekan **Ctrl+A** lalu **Ctrl+C** untuk menyalin semua teks JSON-nya

**Cara memasukkan data ke GitHub:**

1. Buka repo Anda → tab **Actions** → klik **Update Data DSSD**
2. Klik tombol **Run workflow**
3. Pada kolom input yang muncul, tekan **Ctrl+V** untuk paste JSON tadi
4. Klik **Run workflow** (tombol hijau)

Tunggu sekitar 30 detik, data di website akan otomatis diperbarui beserta tanggal & waktu update-nya.

---

### Langkah 5 — Sesuaikan Urusan yang Ditampilkan

Beberapa urusan mungkin tidak relevan untuk daerah Anda (contoh: Kekhususan Aceh, Papua, dll). Untuk menyembunyikannya, buka `index.html` → cari baris:

```javascript
const EXCLUDE_KODE = ['3.28','3.29','5.06','5.07','9.01','9.02','9.03','7.02','7.03'];
```

Tambahkan kode urusan yang ingin disembunyikan di dalam array tersebut.

---

## 🔄 Cara Update Data Rutin

Setiap kali ingin memperbarui data (misalnya seminggu sekali atau sebulan sekali):

| Langkah | Keterangan |
|---------|------------|
| 1 | Login SIPD → Rekap DSSD → **F12** → **Network** → **F5** |
| 2 | Klik request `ajax_list_pemda_keterisian` → tab **Response** → **Ctrl+A** → **Ctrl+C** |
| 3 | Buka GitHub → **Actions** → **Update Data DSSD** → **Run workflow** |
| 4 | Paste JSON → klik **Run workflow** |
| 5 | Selesai ✅ — website otomatis terupdate |

---

## ❓ Pertanyaan Umum

**Apakah data ini aman?**
Ya. Data yang ditampilkan adalah rekap statistik yang bersifat publik. Tidak ada data pribadi atau rahasia yang ditampilkan. Password SIPD Anda tidak disimpan di mana pun.

**Apakah orang lain bisa mengubah data?**
Tidak. Hanya pemilik repository (akun GitHub Anda) yang bisa mengubah data.

**Seberapa sering data harus diupdate?**
Sesuai kebutuhan. Disarankan update setiap kali ada perubahan signifikan di SIPD, misalnya setelah deadline pengisian data.

**Bagaimana jika tampilan website tidak berubah setelah update?**
Coba tekan **Ctrl+Shift+R** (hard refresh) di browser untuk menghapus cache.

---

## 🛠️ Struktur File

```
dssd-berau/
├── index.html          ← Tampilan website (edit di sini untuk kustomisasi)
├── data/
│   └── rekap.json      ← Data rekap DSSD (diupdate via GitHub Actions)
└── .github/
    └── workflows/
        └── update-data.yml   ← Workflow untuk update data
```

---

## 📝 Lisensi

Bebas digunakan dan dimodifikasi untuk keperluan pemerintahan daerah di Indonesia.

Dibuat oleh **Diskominfo Kabupaten Berau** · Kalimantan Timur

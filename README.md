# Dashboard Rekap Tahapan DSSD — KAB. BERAU

Website publik untuk memantau progress keterisian Data Statistik Sektoral Daerah (DSSD) Kabupaten Berau (6403) di e-Walidata SIPD — tanpa perlu login.

---

## 🚀 Cara Deploy ke GitHub Pages (Langkah demi Langkah)

### Langkah 1 — Buat akun GitHub
Jika belum punya, daftar di [github.com](https://github.com).

---

### Langkah 2 — Buat repository baru
1. Klik tombol **+** di pojok kanan atas → **New repository**
2. Isi nama repo, contoh: `dssd-berau`
3. Pilih **Public**
4. Klik **Create repository**

---

### Langkah 3 — Upload semua file
1. Di halaman repo yang baru dibuat, klik **uploading an existing file**
2. Drag & drop **semua file dan folder** dari zip ini:
   - `index.html`
   - `data/rekap.json`
   - `.github/workflows/update-data.yml`
3. Klik **Commit changes**

> ⚠️ Pastikan struktur folder terjaga:
> ```
> dssd-berau/
> ├── index.html
> ├── data/
> │   └── rekap.json
> └── .github/
>     └── workflows/
>         └── update-data.yml
> ```

---

### Langkah 4 — Aktifkan GitHub Pages
1. Buka tab **Settings** di repo
2. Di menu kiri klik **Pages**
3. Di bagian **Source**, pilih **Deploy from a branch**
4. Branch: **main**, folder: **/ (root)**
5. Klik **Save**

Tunggu 1–2 menit, lalu website Anda akan aktif di:
```
https://[username-github-anda].github.io/dssd-berau/
```

---

### Langkah 5 — Setup Auto-Update Data (Opsional tapi Dianjurkan)

Supaya data otomatis diperbarui setiap hari, Anda perlu simpan **Session SIPD** sebagai GitHub Secret.

#### 5a. Ambil nilai cookie dari browser
1. Login ke SIPD e-Walidata
2. Tekan F12 → tab **Application** → **Cookies** → `sipd.go.id`
3. Catat nilai:
   - `PHPSESSID` (contoh: `1503j3c8c2iqjfrg92m10ou3fd`)
   - `pemda` (contoh: `%7B%22domain%22%3A...`)
4. Catat juga **session token** dari URL:
   - URL: `sipd.go.id/ewalidata/`**`196bacb336268525cff0c84e1dd8f5d0ec16d47d`**`/?m=...`

#### 5b. Simpan sebagai GitHub Secrets
1. Di repo, buka **Settings** → **Secrets and variables** → **Actions**
2. Klik **New repository secret**, tambahkan satu per satu:

| Name | Value |
|------|-------|
| `PHPSESSID` | nilai PHPSESSID dari cookie |
| `PEMDA_COOKIE` | nilai pemda dari cookie (URL-encoded) |
| `SESSION_TOKEN` | token 40 karakter dari URL SIPD |

#### 5c. Jalankan pertama kali manual
1. Buka tab **Actions** di repo
2. Klik workflow **Update Data DSSD**
3. Klik **Run workflow** → **Run workflow**

Setelah berhasil, data akan otomatis diperbarui setiap hari jam 07.00 dan 13.00 WITA.

---

## ⚠️ Catatan Penting

- **Session PHPSESSID akan expired** setelah beberapa jam/hari. Ketika auto-update mulai gagal, Anda perlu login ulang ke SIPD dan perbarui secrets.
- **Alternatif manual**: Setiap kali ingin update data, download JSON terbaru dari DevTools SIPD dan replace file `data/rekap.json` di GitHub.
- Data yang tampil di website adalah **snapshot terakhir** yang berhasil di-fetch.

---

## 📋 Cara Update Data Secara Manual

Jika tidak ingin pakai auto-update:

1. Login ke SIPD e-Walidata
2. Buka halaman Rekap DSSD
3. F12 → Network → cari request `ajax_list_pemda_keterisian` → tab Response → salin semua
4. Buka file `data/rekap.json` di GitHub → klik ikon pensil → ganti isinya
5. Format JSON yang diperlukan:
```json
{
  "data": [ ...isi response dari SIPD... ],
  "meta": {
    "last_updated": "2025-06-08T10:00:00+08:00",
    "source": "e-Walidata SIPD",
    "tahun": "2025",
    "kodepemda": "6403"
  }
}
```

---

## 🔗 Link Setelah Deploy

```
https://[username-anda].github.io/dssd-berau/
```

Bagikan link ini ke siapa saja — tidak perlu login SIPD untuk melihat datanya.

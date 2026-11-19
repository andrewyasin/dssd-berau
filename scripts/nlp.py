"""
Modul NLP bersama untuk pipeline ulasan Disdukcapil Berau.

Dipakai oleh:
  - scrape.py      : kategorisasi topik (kamus kata kunci) + skor model sentimen
  - train_model.py : melatih dan mengevaluasi model sentimen berbasis teks

Isi:
  1. normalisasi()      : membersihkan teks ulasan (unicode, huruf berulang, bahasa gaul, emoji)
  2. daftar_kategori()  : topik berbasis kamus, dijalankan pada teks yang SUDAH dinormalisasi
  3. skor_negatif()     : probabilitas ulasan bernada negatif dari model (prediksi out-of-fold
                          untuk ulasan yang dipakai melatih model, model akhir untuk ulasan baru)
"""

import os
import re
import unicodedata

# ── 1. NORMALISASI TEKS ──────────────────────────────────────────────────────
# Peta kata gaul / singkatan / ejaan ke bentuk baku. Hanya kata yang benar-benar muncul
# di ulasan atau sangat umum di bahasa tulis pengguna aplikasi pemerintah.
PETA_KATA = {
    # negasi
    "tdk": "tidak", "tak": "tidak", "gak": "tidak", "ga": "tidak", "gk": "tidak", "g": "tidak",
    "nga": "tidak", "nda": "tidak", "ndak": "tidak", "nggak": "tidak", "enggak": "tidak",
    "engga": "tidak", "gakbisa": "tidak bisa", "tdkbisa": "tidak bisa",
    # singkatan umum
    "bsa": "bisa", "bs": "bisa", "yg": "yang", "dgn": "dengan", "krn": "karena", "karna": "karena",
    "sdh": "sudah", "udh": "sudah", "udah": "sudah", "blm": "belum", "jd": "jadi", "jdi": "jadi",
    "utk": "untuk", "knp": "kenapa", "kenpa": "kenapa", "nmr": "nomor",
    "hp": "hp", "pdhl": "padahal", "tp": "tapi", "dr": "dari", "dri": "dari", "sy": "saya",
    "aq": "saya", "ajj": "saja", "aja": "saja", "kmarin": "kemarin", "kemrin": "kemarin",
    "skrg": "sekarang", "smpai": "sampai", "sampe": "sampai", "org": "orang", "bgt": "banget",
    "trus": "terus", "trs": "terus", "gmn": "bagaimana", "gimana": "bagaimana",
    # aplikasi dan istilah teknis
    "apk": "aplikasi", "app": "aplikasi", "aplikasix": "aplikasi", "eror": "error", "erorr": "error",
    "updet": "update", "upgarde": "update", "upgrade": "update", "donlod": "unduh", "donloat": "unduh",
    "donwload": "unduh", "download": "unduh", "mendonloat": "mengunduh", "mendownload": "mengunduh",
    "didonwload": "diunduh", "didownload": "diunduh", "maintanace": "maintenance",
    "maintenence": "maintenance", "mainten": "maintenance",
    # pujian (ejaan bervariasi dan bahasa Inggris)
    "mantab": "mantap", "mantul": "mantap", "matap": "mantap", "mantaap": "mantap", "matul": "mantap",
    "jos": "mantap", "oke": "oke", "ok": "oke", "okey": "oke", "okay": "oke",
    "good": "bagus", "nice": "bagus", "great": "bagus", "best": "terbaik", "bagusss": "bagus",
    "keren": "keren", "kereen": "keren", "sipplah": "bagus", "siplah": "bagus", "sip": "bagus",
    "recomanded": "rekomendasi", "recommended": "rekomendasi", "recomended": "rekomendasi",
    "terimakasih": "terima kasih", "makasih": "terima kasih", "thanks": "terima kasih",
    "thx": "terima kasih", "tks": "terima kasih", "trimakasih": "terima kasih",
    "membatu": "membantu", "terbaiik": "terbaik", "mempermuda": "mempermudah",
    "pempersulit": "mempersulit", "dukcapil": "disdukcapil", "disduk": "disdukcapil",
}

EMOJI_POSITIF = "👍👌🤩😍🥰❤💯👏😊🙂😁😄🙌🔥✅⭐🌟"
EMOJI_NEGATIF = "👎😡😠😤🤬😭😞😢😫🤦"

_POLA_HURUF_ULANG = re.compile(r"(.)\1{2,}")           # "baguuus" -> "bagus"
_POLA_SPASI = re.compile(r"\s+")


def normalisasi(teks) -> str:
    """Ubah teks ulasan mentah menjadi teks bersih yang konsisten.

    - NFKC: huruf matematika/fullwidth ("𝙈𝙖𝙣𝙩𝙖𝙥") menjadi huruf biasa ("Mantap")
    - huruf kecil, emoji jadi token (emoji_positif / emoji_negatif)
    - huruf berulang >2 kali dipadatkan ("mantabbbb" -> "mantab")
    - bahasa gaul dan singkatan dibakukan lewat PETA_KATA
    """
    if not isinstance(teks, str):
        return ""
    t = unicodedata.normalize("NFKC", teks).lower()
    t = "".join(
        " emoji_positif " if c in EMOJI_POSITIF else " emoji_negatif " if c in EMOJI_NEGATIF else c
        for c in t
    )
    t = _POLA_HURUF_ULANG.sub(r"\1", t)

    def ganti(m: re.Match) -> str:
        kata = m.group(0)
        return PETA_KATA.get(kata, kata)

    t = re.sub(r"[a-z0-9]+(?:-[a-z0-9]+)?", ganti, t)
    return _POLA_SPASI.sub(" ", t).strip()


# ── 2. KAMUS KATEGORI (dijalankan pada teks hasil normalisasi) ───────────────
KATEGORI_KEYWORDS = {
    "KTP / e-KTP": ["ktp", "e-ktp", "ktp digital", "kartu tanda penduduk", "nik"],
    "Akta Kelahiran": ["akta", "akte", "kelahiran", "lahir", "bayi", "anak"],
    "Kartu Keluarga": ["kk", "kartu keluarga", "anggota", "rumah tangga"],
    "Kecepatan Proses": [
        "lama", "lambat", "cepat", "lelet", "tunggu", "antri",
        "proses", "menunggu", "nunggu", "instan", "segera", "kilat",
    ],
    "Kemudahan Aplikasi": [
        "mudah", "susah", "ribet", "bingung", "sulit", "gampang",
        "simpel", "simple", "fitur", "menu", "tampilan", "navigasi", "ux",
        "memudahkan", "mempermudah", "permudah", "dimudahkan", "lebih muda",
    ],
    "Error / Bug": [
        "error", "crash", "bug", "tidak bisa", "gagal", "force close",
        "loading", "macet", "blank", "kosong", "masalah", "kendala",
        "tidak mau", "tidak online", "tidak terhubung", "tidak dapat", "maintenance",
        "server", "terhubung",
    ],
    "Pelayanan": [
        "pelayanan", "petugas", "staff", "layanan", "respon",
        "bantuan", "admin", "cs", "customer service", "call center",
    ],
    "Dokumen": ["dokumen", "berkas", "persyaratan", "syarat", "upload", "foto", "scan", "file"],
    "Pujian Umum": [
        "bagus", "baik", "mantap", "keren", "membantu", "top", "hebat",
        "sangat baik", "terbaik", "solusi", "inovasi", "bermanfaat", "rekomendasi",
        "oke", "terima kasih", "puas", "memuaskan", "terbantu", "berguna", "sukses",
        "alhamdulillah", "mendukung", "maju", "emoji_positif",
    ],
    "Login / Akun": [
        "login", "akun", "daftar", "registrasi", "kata sandi", "password",
        "gagal masuk", "susah masuk", "sulit masuk", "tidak bisa masuk",
        "nomor hp", "otp", "verifikasi",
    ],
    "Update / Versi": ["update", "versi", "perbarui", "pembaharuan"],
    "Unduh & Instalasi": [
        "unduh", "diunduh", "mengunduh", "install", "instal", "app store", "appstore", "play store",
    ],
    "Cakupan & Kompatibilitas": [
        "iphone", "ios", "android", "luar daerah", "luar kota", "kota lain",
        "seluruh indonesia", "daerah tertentu", "penduduk luar", "samarinda",
    ],
    "Keluhan Umum": [
        "jelek", "buruk", "payah", "parah", "kecewa", "receh", "tidak bagus",
        "tidak baik", "tidak puas", "becus", "dipersulit", "mempersulit", "pusing",
    ],
}

# Kategori bermakna positif: tidak boleh terpicu bila didahului negasi ("tidak bagus")
KATEGORI_POSITIF = {"Pujian Umum"}
_NEGASI = r"(?:tidak|tak|kurang|belum|bukan|kok)"


def _pola(kw: str) -> re.Pattern:
    """Kata <=3 huruf dicocokkan utuh ('nik' tidak cocok dengan 'elektronik'); kata lebih
    panjang dicocokkan dari awal kata ('proses' cocok dengan 'prosesnya')."""
    esc = re.escape(kw)
    return re.compile(rf"\b{esc}\b") if len(kw) <= 3 else re.compile(rf"\b{esc}")


def _pola_negasi(kw: str) -> re.Pattern:
    return re.compile(rf"\b{_NEGASI}\s+(?:\w+\s+)?{re.escape(kw)}")


_POLA = {k: [(_pola(kw), _pola_negasi(kw)) for kw in kws] for k, kws in KATEGORI_KEYWORDS.items()}


def daftar_kategori(teks) -> list:
    """Daftar kategori topik untuk satu ulasan (teks mentah; dinormalisasi di sini)."""
    t = normalisasi(teks)
    if not t:
        return ["Lainnya"]
    hasil = []
    for kat, pola_list in _POLA.items():
        for p, p_neg in pola_list:
            if p.search(t):
                if kat in KATEGORI_POSITIF and p_neg.search(t):
                    continue
                hasil.append(kat)
                break
    return hasil if hasil else ["Lainnya"]


def kategorisasi(teks) -> str:
    return ", ".join(daftar_kategori(teks))


# ── 3. SKOR MODEL SENTIMEN ───────────────────────────────────────────────────
DIR_MODEL = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models")
PATH_MODEL = os.path.join(DIR_MODEL, "model_sentimen.joblib")
PATH_OOF = os.path.join(DIR_MODEL, "prediksi_oof.csv")


def skor_negatif(df):
    """Tambahkan p_negatif (probabilitas ulasan bernada negatif) ke DataFrame ulasan.

    Aturan penting (agar tidak curang): ulasan yang dipakai melatih model memakai prediksi
    OUT-OF-FOLD yang disimpan saat pelatihan (model tidak pernah melihat ulasan itu saat
    memprediksinya). Hanya ulasan baru yang diprediksi oleh model akhir.
    Jika model belum ada, kolom diisi None dan pipeline tetap berjalan.
    """
    import pandas as pd

    df = df.copy()
    df["p_negatif"] = None
    if not (os.path.exists(PATH_MODEL) and os.path.exists(PATH_OOF)):
        return df
    import joblib

    oof = pd.read_csv(PATH_OOF).set_index("review_id")["p_negatif"]
    df["p_negatif"] = df["review_id"].map(oof)
    baru = df["p_negatif"].isna()
    if baru.any():
        model = joblib.load(PATH_MODEL)
        teks = df.loc[baru, "isi"].map(normalisasi)
        df.loc[baru, "p_negatif"] = model.predict_proba(teks)[:, 1]
    df["p_negatif"] = df["p_negatif"].astype(float).round(3)
    return df

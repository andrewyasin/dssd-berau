"""
Melatih dan mengevaluasi model deteksi ulasan negatif (teks) untuk aplikasi Disdukcapil Berau.

Masalah   : rating bintang tidak selalu sejalan dengan isi ulasan (mis. 5 bintang tetapi isinya
            keluhan). Model ini membaca TEKS ulasan dan memperkirakan peluang ulasan bernada
            negatif, sehingga keluhan yang "bersembunyi" di rating tinggi bisa ditemukan.
Label     : negatif = rating 1-2 bintang; bukan negatif = rating 3-5 bintang.
Validasi  : StratifiedGroupKFold 5-lipat x 5 ulangan. Ulasan dengan isi yang sama setelah
            normalisasi (66 ulasan, mis. "Ok", "Mantab") DIKELOMPOKKAN agar tidak bocor antara data latih
            dan uji. Pemilihan hiperparameter dilakukan di dalam tiap lipatan (nested).
            Ditambah uji temporal: latih <= 2022, uji 2023-2026.
Keluaran  : models/model_sentimen.joblib, models/prediksi_oof.csv,
            reports/metrics.json, reports/*.png, reports/ketidaksesuaian.csv

Jalankan dari akar repo:  python scripts/train_model.py [docs/reviews.csv]
"""

import json
import os
import sys
import warnings

import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score, balanced_accuracy_score, confusion_matrix, f1_score,
    precision_recall_curve, precision_score, recall_score, roc_auc_score,
)
from sklearn.model_selection import GridSearchCV, StratifiedGroupKFold
from sklearn.naive_bayes import ComplementNB
from sklearn.pipeline import FeatureUnion, Pipeline
from sklearn.svm import LinearSVC

import nlp

warnings.filterwarnings("ignore")
HIJAU, MERAH, KUNING, ABU = "#00923F", "#C0392B", "#E8B900", "#6B7280"
RAKAR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR_LAP = os.path.join(RAKAR, "reports")
SEED = 42
N_ULANG, N_LIPAT = 5, 5


# ── Data ─────────────────────────────────────────────────────────────────────
def muat(path: str):
    df = pd.read_csv(path, encoding="utf-8-sig")
    df = df.dropna(subset=["isi", "bintang"]).reset_index(drop=True)
    df["teks"] = df["isi"].map(nlp.normalisasi)
    df["y"] = (df["bintang"] <= 2).astype(int)                 # 1 = negatif
    df["grup"] = pd.factorize(df["teks"])[0]                    # isi sama -> satu kelompok
    return df


# ── Model ────────────────────────────────────────────────────────────────────
def fitur_kata():
    return TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, min_df=1)


def fitur_kata_karakter():
    return FeatureUnion([
        ("kata", TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, min_df=1)),
        ("char", TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), sublinear_tf=True, min_df=2)),
    ])


def buat_lr(fitur, grid=(0.3, 1, 3, 10, 30)):
    pipa = Pipeline([("fit", fitur), ("clf", LogisticRegression(class_weight="balanced", max_iter=2000))])
    return GridSearchCV(pipa, {"clf__C": list(grid)}, scoring="average_precision",
                        cv=StratifiedGroupKFold(3, shuffle=True, random_state=SEED), n_jobs=1)


def buat_svc():
    pipa = Pipeline([("fit", fitur_kata_karakter()), ("clf", LinearSVC(class_weight="balanced"))])
    return GridSearchCV(pipa, {"clf__C": [0.1, 0.3, 1]}, scoring="average_precision",
                        cv=StratifiedGroupKFold(3, shuffle=True, random_state=SEED), n_jobs=1)


def buat_nb():
    pipa = Pipeline([("fit", fitur_kata()), ("clf", ComplementNB())])
    return GridSearchCV(pipa, {"clf__alpha": [0.1, 0.3, 1.0]}, scoring="average_precision",
                        cv=StratifiedGroupKFold(3, shuffle=True, random_state=SEED), n_jobs=1)


# (nama, pembuat, jenis skor, ambang untuk F1)
MODEL = {
    "LR kata+karakter (dipilih)": (lambda: buat_lr(fitur_kata_karakter()), "proba", 0.5),
    "LR kata": (lambda: buat_lr(fitur_kata()), "proba", 0.5),
    "Complement NB kata": (buat_nb, "proba", 0.5),
    "Linear SVM kata+karakter": (buat_svc, "margin", 0.0),
}


def skor(model, X, jenis):
    return model.predict_proba(X)[:, 1] if jenis == "proba" else model.decision_function(X)


def metrik(y, s, ambang):
    pred = (s >= ambang).astype(int)
    return {
        "roc_auc": roc_auc_score(y, s),
        "pr_auc": average_precision_score(y, s),
        "f1_negatif": f1_score(y, pred),
        "presisi_negatif": precision_score(y, pred, zero_division=0),
        "recall_negatif": recall_score(y, pred),
        "balanced_acc": balanced_accuracy_score(y, pred),
    }


def baseline_kamus(df):
    """Aturan sederhana tanpa pembelajaran: negatif jika terdeteksi kategori Error/Bug atau Keluhan Umum."""
    kat = df["isi"].map(nlp.daftar_kategori)
    return kat.map(lambda k: int(("Error / Bug" in k) or ("Keluhan Umum" in k))).to_numpy()


# ── Validasi silang berulang (nested, berkelompok) ───────────────────────────
def validasi_silang(df):
    X, y, g = df["teks"].to_numpy(), df["y"].to_numpy(), df["grup"].to_numpy()
    hasil = {nama: [] for nama in MODEL}
    oof_lr = np.zeros((N_ULANG, len(df)))
    c_terpilih = []
    for r in range(N_ULANG):
        pemisah = StratifiedGroupKFold(N_LIPAT, shuffle=True, random_state=SEED + r)
        oof = {nama: np.zeros(len(df)) for nama in MODEL}
        for tr, te in pemisah.split(X, y, g):
            for nama, (pembuat, jenis, _) in MODEL.items():
                m = pembuat().fit(X[tr], y[tr], groups=g[tr])
                oof[nama][te] = skor(m, X[te], jenis)
                if nama.startswith("LR kata+karakter"):
                    c_terpilih.append(m.best_params_["clf__C"])
        for nama, (_, _, ambang) in MODEL.items():
            hasil[nama].append(metrik(y, oof[nama], ambang))
        oof_lr[r] = oof["LR kata+karakter (dipilih)"]
        print(f"  ulangan {r + 1}/{N_ULANG} selesai", flush=True)
    ringkas = {}
    for nama, daftar in hasil.items():
        d = pd.DataFrame(daftar)
        ringkas[nama] = {k: {"rata2": round(float(d[k].mean()), 3), "sd": round(float(d[k].std()), 3)} for k in d}
    return ringkas, oof_lr.mean(axis=0), c_terpilih


def uji_temporal(df):
    tr, te = df[df["tahun"] <= 2022], df[df["tahun"] >= 2023]
    keluar = {"n_latih": len(tr), "n_uji": len(te), "prevalensi_negatif_uji": round(float(te["y"].mean()), 3)}
    for nama, (pembuat, jenis, ambang) in MODEL.items():
        m = pembuat().fit(tr["teks"].to_numpy(), tr["y"].to_numpy(), groups=tr["grup"].to_numpy())
        keluar[nama] = {k: round(float(v), 3) for k, v in metrik(te["y"].to_numpy(), skor(m, te["teks"].to_numpy(), jenis), ambang).items()}
    keluar["Baseline kamus kata kunci"] = {
        k: round(float(v), 3) for k, v in metrik(te["y"].to_numpy(), baseline_kamus(te), 0.5).items()}
    return keluar


# ── Laporan ──────────────────────────────────────────────────────────────────
def gaya():
    plt.rcParams.update({"font.family": "DejaVu Sans", "axes.spines.top": False, "axes.spines.right": False,
                         "axes.titleweight": "bold", "axes.titlesize": 13, "figure.dpi": 150})


def gambar_pr(df, p_oof, base):
    fig, ax = plt.subplots(figsize=(6.2, 4.6))
    pr, rc, _ = precision_recall_curve(df["y"], p_oof)
    ax.plot(rc, pr, color=HIJAU, lw=2.4, label=f"Model teks (PR-AUC {average_precision_score(df['y'], p_oof):.2f})")
    ax.scatter([recall_score(df["y"], base)], [precision_score(df["y"], base)], color=MERAH, s=70, zorder=3,
               label=f"Kamus kata kunci (recall {recall_score(df['y'], base):.2f}, presisi {precision_score(df['y'], base):.2f})")
    ax.axhline(df["y"].mean(), color=ABU, ls="--", lw=1.2, label=f"Acak (prevalensi {df['y'].mean():.0%})")
    ax.set_xlabel("Recall (ulasan negatif yang tertangkap)"); ax.set_ylabel("Presisi")
    ax.set_title("Mendeteksi ulasan negatif dari teks"); ax.set_ylim(0, 1.02); ax.legend(loc="lower left", frameon=False)
    fig.tight_layout(); fig.savefig(os.path.join(DIR_LAP, "kurva_presisi_recall.png")); plt.close(fig)


def gambar_matriks(df, p_oof):
    cm = confusion_matrix(df["y"], (p_oof >= 0.5).astype(int))
    fig, ax = plt.subplots(figsize=(4.6, 4.2))
    ax.imshow(cm, cmap="Greens")
    for i in range(2):
        for j in range(2):
            ax.text(j, i, cm[i, j], ha="center", va="center", fontsize=16, fontweight="bold",
                    color="white" if cm[i, j] > cm.max() / 2 else "#14281D")
    ax.set_xticks([0, 1], ["Bukan negatif", "Negatif"]); ax.set_yticks([0, 1], ["Bukan negatif", "Negatif"])
    ax.set_xlabel("Prediksi model"); ax.set_ylabel("Label (rating)"); ax.set_title("Matriks kebingungan (out-of-fold)")
    fig.tight_layout(); fig.savefig(os.path.join(DIR_LAP, "matriks_kebingungan.png")); plt.close(fig)


def gambar_fitur(df):
    vek = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, min_df=5)
    Xk = vek.fit_transform(df["teks"])
    lr = LogisticRegression(class_weight="balanced", C=3, max_iter=2000).fit(Xk, df["y"])
    koef = pd.Series(lr.coef_[0], index=vek.get_feature_names_out()).sort_values()
    atas, bawah = koef.tail(12), koef.head(12)
    fig, ax = plt.subplots(figsize=(7, 5.4))
    gab = pd.concat([bawah, atas])
    gab.index = [i.replace("emoji_positif", "(emoji positif)").replace("emoji_negatif", "(emoji negatif)") for i in gab.index]
    ax.barh(gab.index, gab.values, color=[HIJAU if v < 0 else MERAH for v in gab.values])
    ax.set_title("Kata yang paling membedakan ulasan"); ax.set_xlabel("Koefisien (hijau: bukan negatif, merah: negatif)")
    fig.tight_layout(); fig.savefig(os.path.join(DIR_LAP, "kata_pembeda.png")); plt.close(fig)
    return {"negatif": list(atas.index[::-1]), "bukan_negatif": list(bawah.index)}


def gambar_sebaran(df, p_oof):
    fig, ax = plt.subplots(figsize=(6.2, 4.4))
    rng = np.random.default_rng(SEED)
    for b in range(1, 6):
        v = p_oof[df["bintang"].to_numpy() == b]
        ax.scatter(b + rng.uniform(-0.28, 0.28, len(v)), v, s=14, alpha=0.55,
                   color=MERAH if b <= 2 else KUNING if b == 3 else HIJAU)
    ax.axhline(0.5, color=ABU, ls="--", lw=1)
    ax.set_xlabel("Rating bintang"); ax.set_ylabel("Peluang negatif menurut teks")
    ax.set_title("Peluang negatif menurut teks, per rating")
    ax.text(5.45, 0.9, "keluhan di\nrating tinggi", ha="right", va="top", fontsize=9, color=MERAH)
    fig.tight_layout(); fig.savefig(os.path.join(DIR_LAP, "teks_vs_rating.png")); plt.close(fig)


def analisis_ketidaksesuaian(df, p_oof):
    d = df.assign(p_negatif=p_oof.round(3))
    keluhan_tinggi = d[(d["bintang"] >= 4) & (d["p_negatif"] >= 0.5)].sort_values("p_negatif", ascending=False)
    pujian_rendah = d[(d["bintang"] <= 2) & (d["p_negatif"] < 0.2)].sort_values("p_negatif")
    kolom = ["review_id", "tanggal_date", "bintang", "p_negatif", "isi"]
    keluar = pd.concat([
        keluhan_tinggi[kolom].assign(jenis="Keluhan di rating tinggi"),
        pujian_rendah[kolom].assign(jenis="Pujian di rating rendah"),
    ])
    keluar.to_csv(os.path.join(DIR_LAP, "ketidaksesuaian.csv"), index=False, encoding="utf-8")
    return len(keluhan_tinggi), len(pujian_rendah), int((d["bintang"] >= 4).sum()), int((d["bintang"] <= 2).sum()), keluhan_tinggi, pujian_rendah


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(RAKAR, "docs", "reviews.csv")
    os.makedirs(DIR_LAP, exist_ok=True)
    os.makedirs(nlp.DIR_MODEL, exist_ok=True)
    gaya()
    df = muat(path)
    print(f"{len(df)} ulasan | negatif {df['y'].sum()} ({df['y'].mean():.1%}) | kelompok unik {df['grup'].nunique()}")

    print("Validasi silang berulang (nested, berkelompok)...")
    ringkas, p_oof, c_terpilih = validasi_silang(df)
    base = baseline_kamus(df)
    ringkas["Baseline kamus kata kunci"] = {k: {"rata2": round(float(v), 3), "sd": 0.0} for k, v in metrik(df["y"].to_numpy(), base, 0.5).items()}
    ringkas["Baseline mayoritas"] = {"roc_auc": {"rata2": 0.5, "sd": 0.0}, "pr_auc": {"rata2": round(float(df["y"].mean()), 3), "sd": 0.0},
                                     "f1_negatif": {"rata2": 0.0, "sd": 0.0}}

    print("Uji temporal (latih <= 2022, uji 2023-2026)...")
    temporal = uji_temporal(df)

    print("Model akhir pada seluruh data...")
    c_akhir = int(pd.Series(c_terpilih).mode().iloc[0]) if all(float(c).is_integer() for c in c_terpilih) else float(pd.Series(c_terpilih).mode().iloc[0])
    akhir = Pipeline([("fit", fitur_kata_karakter()),
                      ("clf", LogisticRegression(class_weight="balanced", C=c_akhir, max_iter=2000))])
    akhir.fit(df["teks"], df["y"])
    joblib.dump(akhir, nlp.PATH_MODEL, compress=3)
    pd.DataFrame({"review_id": df["review_id"], "p_negatif": p_oof.round(4)}).to_csv(nlp.PATH_OOF, index=False)

    kata = gambar_fitur(df)
    gambar_pr(df, p_oof, base); gambar_matriks(df, p_oof); gambar_sebaran(df, p_oof)
    n_kt, n_pr, n_tinggi, n_rendah, kt, pr = analisis_ketidaksesuaian(df, p_oof)

    out = {
        "data": {"n": len(df), "negatif": int(df["y"].sum()), "prevalensi_negatif": round(float(df["y"].mean()), 3),
                 "kelompok_unik": int(df["grup"].nunique()), "isi_duplikat": int(len(df) - df["grup"].nunique())},
        "validasi_silang": {"skema": f"StratifiedGroupKFold {N_LIPAT}-lipat x {N_ULANG} ulangan, nested", "hasil": ringkas,
                            "C_terpilih_LR": sorted(set(c_terpilih))},
        "uji_temporal": temporal,
        "ketidaksesuaian": {"keluhan_di_rating_tinggi": n_kt, "dari_ulasan_4_5_bintang": n_tinggi,
                            "pujian_di_rating_rendah": n_pr, "dari_ulasan_1_2_bintang": n_rendah},
        "kata_pembeda": kata, "C_model_akhir": c_akhir,
    }
    with open(os.path.join(DIR_LAP, "metrics.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(json.dumps(out["validasi_silang"]["hasil"], ensure_ascii=False, indent=1))
    print("TEMPORAL:", json.dumps(temporal, ensure_ascii=False))
    print("KETIDAKSESUAIAN:", out["ketidaksesuaian"])
    print("KATA:", kata)


if __name__ == "__main__":
    main()

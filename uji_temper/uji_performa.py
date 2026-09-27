"""
UJI PERFORMA & UKURAN
=======================
Ini menjawab 2 poin pengujian wajib dari spesifikasi tugas yang belum
ada scriptnya:
  1. Waktu penandatanganan & verifikasi, rata-rata dari 30 kali percobaan.
  2. Ukuran signature dan ukuran public key.

Hasilnya otomatis ditulis ke file Excel "Data_Pengujian.xlsx" (salah satu
luaran wajib yang diminta terpisah dari laporan PDF).

Cara pakai:
    1. Taruh file ini di folder uji_temper/ (sejajar dengan tamper.py)
    2. Install dulu library buat nulis Excel (sekali aja):
           pip install openpyxl
    3. Jalankan dari folder ROOT repo (bukan dari dalam uji_temper/):
           python uji_temper/uji_performa.py
"""

import os
import sys
import time
import statistics

# 1. Supaya bisa import "crypto_core" yang letaknya di root repo.
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

from crypto_core.signer import CryptoSigner
from cryptography.hazmat.primitives import serialization

try:
    from openpyxl import Workbook
except ImportError:
    print("Library 'openpyxl' belum terpasang. Jalankan dulu: pip install openpyxl")
    sys.exit(1)


JUMLAH_PERCOBAAN = 30
FILE_UJI = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dokumen_polos.pdf")
FILE_OUTPUT_XLSX = os.path.join(ROOT_DIR, "Data_Pengujian.xlsx")


def uji_waktu_eksekusi(signer: CryptoSigner):
    """
    Mengukur waktu SIGN (hash + tanda tangan) dan waktu VERIFY (hash +
    verifikasi) sebanyak JUMLAH_PERCOBAAN kali, lalu kembalikan semua
    catatan waktunya (dalam milidetik) untuk dianalisis & ditulis ke Excel.
    """
    waktu_sign_ms = []
    waktu_verify_ms = []

    for percobaan in range(1, JUMLAH_PERCOBAAN + 1):
        # --- Ukur waktu SIGN ---
        # time.perf_counter() dipakai (bukan time.time()) karena presisinya
        # jauh lebih tinggi, cocok buat ngukur operasi yang cepat (milidetik).
        mulai = time.perf_counter()
        pdf_hash = signer.get_file_hash(FILE_UJI)
        signature = signer.sign_hash(pdf_hash)
        selesai = time.perf_counter()
        waktu_sign_ms.append((selesai - mulai) * 1000)  # detik -> milidetik

        # --- Ukur waktu VERIFY ---
        # Verifikasi pakai hash & signature yang baru saja dihasilkan,
        # dengan public key yang benar (skenario normal, bukan uji kunci salah).
        mulai = time.perf_counter()
        hash_ulang = signer.get_file_hash(FILE_UJI)
        hasil = signer.verify_signature(hash_ulang, signature, public_key=signer.public_key)
        selesai = time.perf_counter()
        waktu_verify_ms.append((selesai - mulai) * 1000)

        assert hasil is True, "Verifikasi seharusnya valid di sini, ada yang salah!"
        print(f"Percobaan {percobaan:2d}/{JUMLAH_PERCOBAAN} "
              f"-> sign: {waktu_sign_ms[-1]:.3f} ms | verify: {waktu_verify_ms[-1]:.3f} ms")

    return waktu_sign_ms, waktu_verify_ms


def uji_ukuran(signer: CryptoSigner):
    """
    Mengukur ukuran signature (dalam byte) dan ukuran public key
    (dalam byte, format PEM dan DER, plus panjang kunci dalam bit).
    """
    pdf_hash = signer.get_file_hash(FILE_UJI)
    signature = signer.sign_hash(pdf_hash)

    # Ukuran signature dalam byte (langsung dari panjang bytes-nya)
    ukuran_signature_bytes = len(signature)

    # Ukuran public key, diserialisasi ke format PEM (teks, umum dipakai
    # buat disimpan/ditampilkan) dan format DER (biner, lebih ringkas)
    public_key_pem = signer.public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    public_key_der = signer.public_key.public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )

    return {
        "ukuran_signature_bytes": ukuran_signature_bytes,
        "ukuran_public_key_pem_bytes": len(public_key_pem),
        "ukuran_public_key_der_bytes": len(public_key_der),
        "panjang_kunci_bit": signer.public_key.key_size,
    }


def tulis_ke_excel(waktu_sign_ms, waktu_verify_ms, hasil_ukuran):
    """
    Menulis semua hasil pengujian ke Data_Pengujian.xlsx dengan 2 sheet:
    - "Waktu Eksekusi": data per-percobaan + rata-rata/min/max
    - "Ukuran": ukuran signature & public key
    """
    wb = Workbook()

    # --- Sheet 1: Waktu Eksekusi ---
    ws1 = wb.active
    ws1.title = "Waktu Eksekusi"
    ws1.append(["Percobaan ke-", "Waktu Sign (ms)", "Waktu Verify (ms)"])
    for i, (t_sign, t_verify) in enumerate(zip(waktu_sign_ms, waktu_verify_ms), start=1):
        ws1.append([i, round(t_sign, 4), round(t_verify, 4)])

    ws1.append([])  # baris kosong pemisah
    ws1.append(["Statistik", "Sign (ms)", "Verify (ms)"])
    ws1.append(["Rata-rata", round(statistics.mean(waktu_sign_ms), 4), round(statistics.mean(waktu_verify_ms), 4)])
    ws1.append(["Minimum", round(min(waktu_sign_ms), 4), round(min(waktu_verify_ms), 4)])
    ws1.append(["Maksimum", round(max(waktu_sign_ms), 4), round(max(waktu_verify_ms), 4)])
    ws1.append(["Standar Deviasi", round(statistics.pstdev(waktu_sign_ms), 4), round(statistics.pstdev(waktu_verify_ms), 4)])

    # --- Sheet 2: Ukuran ---
    ws2 = wb.create_sheet("Ukuran")
    ws2.append(["Item", "Nilai"])
    ws2.append(["Ukuran signature (byte)", hasil_ukuran["ukuran_signature_bytes"]])
    ws2.append(["Ukuran public key - format PEM (byte)", hasil_ukuran["ukuran_public_key_pem_bytes"]])
    ws2.append(["Ukuran public key - format DER (byte)", hasil_ukuran["ukuran_public_key_der_bytes"]])
    ws2.append(["Panjang kunci (bit)", hasil_ukuran["panjang_kunci_bit"]])

    wb.save(FILE_OUTPUT_XLSX)
    print(f"\nSelesai. Data pengujian tersimpan di: {FILE_OUTPUT_XLSX}")


def main():
    if not os.path.exists(FILE_UJI):
        print(f"File uji '{FILE_UJI}' tidak ditemukan. Sesuaikan FILE_UJI ke PDF yang ada di uji_temper/.")
        return

    # 1 signer dipakai konsisten untuk seluruh 30 percobaan, supaya adil
    # (kalau key beda-beda tiap percobaan, waktunya bakal ketambahan waktu
    # generate key 2048-bit yang jauh lebih lambat daripada sign/verify).
    signer = CryptoSigner()

    print("=" * 60)
    print(f"UJI WAKTU EKSEKUSI ({JUMLAH_PERCOBAAN}x percobaan)")
    print("=" * 60)
    waktu_sign_ms, waktu_verify_ms = uji_waktu_eksekusi(signer)

    print("\n" + "=" * 60)
    print("RINGKASAN WAKTU EKSEKUSI")
    print("=" * 60)
    print(f"Rata-rata waktu SIGN   : {statistics.mean(waktu_sign_ms):.4f} ms")
    print(f"Rata-rata waktu VERIFY : {statistics.mean(waktu_verify_ms):.4f} ms")

    print("\n" + "=" * 60)
    print("UJI UKURAN SIGNATURE & PUBLIC KEY")
    print("=" * 60)
    hasil_ukuran = uji_ukuran(signer)
    for k, v in hasil_ukuran.items():
        print(f"{k:35s}: {v}")

    tulis_ke_excel(waktu_sign_ms, waktu_verify_ms, hasil_ukuran)


if __name__ == "__main__":
    main()
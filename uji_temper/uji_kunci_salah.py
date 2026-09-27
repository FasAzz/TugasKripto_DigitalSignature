"""
UJI KUNCI SALAH
================
Tujuan: membuktikan bahwa signature RSA-PSS terikat ke SATU pasangan kunci
spesifik. Kalau diverifikasi pakai public key yang BUKAN pasangannya, hasilnya
harus GAGAL (invalid). Ini beda dari uji tamper (isi dokumen diubah) —
di sini isi dokumen TIDAK diubah sama sekali, yang beda cuma kunci yang
dipakai untuk verifikasi.

Cara pakai:
    1. Taruh file ini di folder uji_temper/ (sejajar dengan tamper.py)
    2. Jalankan dari folder ROOT repo (bukan dari dalam uji_temper/), contoh:
           python uji_temper/uji_kunci_salah.py
       (Ini penting karena kita perlu import "crypto_core", yang letaknya
       di root repo, bukan di dalam uji_temper/)
"""

import os
import sys

# 1. Supaya Python bisa nemuin folder "crypto_core" di root repo,
#    kita tambahkan folder induk (root repo) ke sys.path secara manual.
#    Tanpa ini, "from crypto_core.signer import CryptoSigner" akan error
#    kalau script dijalankan langsung dari dalam folder uji_temper/.
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

from crypto_core.signer import CryptoSigner


def cetak_hasil(judul: str, hasil: bool, ekspektasi: bool):
    status = "SESUAI EKSPEKTASI ✅" if hasil == ekspektasi else "TIDAK SESUAI ❌"
    print(f"{judul}")
    print(f"  Hasil verifikasi : {hasil}")
    print(f"  Ekspektasi       : {ekspektasi}")
    print(f"  Kesimpulan       : {status}\n")


def main():
    # 2. SIGNER ASLI: ini yang berperan sebagai pemilik dokumen sah.
    #    CryptoSigner() otomatis generate 1 pasangan kunci RSA-2048 baru
    #    (lihat crypto_core/signer.py baris __init__).
    signer_asli = CryptoSigner()

    # 3. Kita perlu 1 file untuk dihitung hash-nya. Pakai file PDF yang
    #    sudah ada di folder uji_temper/. Ganti nama file ini kalau perlu.
    file_uji = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dokumen_polos.pdf")
    if not os.path.exists(file_uji):
        print(f"File '{file_uji}' tidak ditemukan. Ganti FILE_UJI ke file PDF yang ada di folder uji_temper/.")
        return

    # 4. Hitung hash SHA-256 dari dokumen (isi dokumen TIDAK diubah,
    #    jadi ini murni menguji soal kunci, bukan soal tamper isi file).
    pdf_hash = signer_asli.get_file_hash(file_uji)

    # 5. Signer ASLI menandatangani hash dokumen pakai PRIVATE KEY miliknya.
    signature = signer_asli.sign_hash(pdf_hash)

    print("=" * 60)
    print("SKENARIO 1 — Baseline: verifikasi pakai kunci yang BENAR")
    print("=" * 60)
    # 6. Verifikasi pakai public key MILIK signer_asli sendiri (pasangan
    #    yang benar dari private key yang tadi menandatangani).
    #    Ini harus VALID -> hasilnya True.
    hasil_kunci_benar = signer_asli.verify_signature(
        pdf_hash, signature, public_key=signer_asli.public_key
    )
    cetak_hasil("Verifikasi dengan public key ASLI (pasangan yang benar)",
                hasil_kunci_benar, ekspektasi=True)

    print("=" * 60)
    print("SKENARIO 2 — Uji kunci salah: verifikasi pakai kunci LAIN")
    print("=" * 60)
    # 7. SIGNER LAIN: pasangan kunci RSA yang SAMA SEKALI BEDA dan tidak
    #    ada hubungannya dengan signer_asli. Ini mensimulasikan "penyerang"
    #    atau pihak lain yang punya key pair sendiri, lalu mencoba
    #    memverifikasi dokumen orang lain pakai public key miliknya sendiri
    #    (yang jelas salah / tidak berpasangan).
    signer_lain = CryptoSigner()

    # 8. Verifikasi hash & signature yang SAMA seperti tadi, tapi kali ini
    #    pakai public_key milik signer_lain (BUKAN pasangan dari private
    #    key yang menandatangani). Ini harus GAGAL -> hasilnya False.
    hasil_kunci_salah = signer_asli.verify_signature(
        pdf_hash, signature, public_key=signer_lain.public_key
    )
    cetak_hasil("Verifikasi dengan public key LAIN (tidak berpasangan)",
                hasil_kunci_salah, ekspektasi=False)

    # 9. Ringkasan akhir buat ditempel di laporan.
    print("=" * 60)
    print("RINGKASAN")
    print("=" * 60)
    print(f"Isi dokumen uji           : {os.path.basename(file_uji)}")
    print(f"Hash SHA-256 dokumen      : {pdf_hash.hex()}")
    print(f"Signature (potongan awal): {signature.hex()[:32]}...")
    print(f"Kunci benar -> valid?     : {hasil_kunci_benar}")
    print(f"Kunci salah -> valid?     : {hasil_kunci_salah}")


if __name__ == "__main__":
    main()
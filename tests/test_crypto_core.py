"""
UNIT TEST — FUNGSI INTI DIGITAL SIGNATURE
============================================
Menjawab poin wajib spesifikasi tugas: "Sertakan minimal lima unit test
untuk fungsi inti seperti enkripsi, penyisipan, ekstraksi, atau verifikasi."

BEDA dengan script di folder uji_temper/ (tamper.py, uji_kunci_salah.py, dst):
- Script di uji_temper/ itu SKRIP DEMONSTRASI -- hasilnya dicetak ke layar,
  dan BENAR/SALAH-nya dicek dengan MATA kita sendiri.
- File ini adalah UNIT TEST FORMAL -- tiap fungsi dites otomatis pakai
  `assert`, dan Python sendiri yang memutuskan PASS/FAIL, tanpa perlu
  dibaca manual. Ini yang dimaksud "unit test" di rubrik penilaian.

Cara menjalankan (dari folder ROOT repo):
    python -m unittest discover -s tests -v

atau kalau sudah install pytest:
    pip install pytest
    pytest tests/ -v
"""

import os
import sys
import shutil
import tempfile
import unittest

# Supaya bisa import "crypto_core" dan "pdf_handler" yang ada di root repo,
# padahal file test ini ada di dalam folder tests/.
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

# Set passphrase test SEBELUM import CryptoSigner, karena CryptoSigner
# butuh PRIVATE_KEY_PASSPHRASE ada di environment variable saat dibuat.
# Ini passphrase KHUSUS UNTUK TESTING, terpisah dari .env asli kamu,
# jadi tidak akan mengganggu key production/asli.
os.environ.setdefault("PRIVATE_KEY_PASSPHRASE", "passphrase-khusus-unit-test")

from crypto_core.signer import CryptoSigner, muat_public_key_dari_pem, verifikasi_dengan_public_key
from pdf_handler.embed_pdf import embed_qr_ke_pdf
from pdf_handler.extract_qr import ekstraksi_semua_qr

import json
import qrcode
import pymupdf as fitz


class TestCryptoSigner(unittest.TestCase):
    """Unit test untuk fungsi-fungsi inti di crypto_core/signer.py"""

    def setUp(self):
        # Tiap test dapat folder sementara sendiri-sendiri, supaya key
        # yang dibuat saat testing TIDAK bercampur dengan key production
        # asli kamu di folder keys/, dan tidak saling mengganggu antar test.
        self.temp_dir = tempfile.mkdtemp()
        self.key_path = os.path.join(self.temp_dir, "test_key.pem")

        # Siapkan 1 file dummy untuk dihitung hash-nya di beberapa test.
        self.file_a = os.path.join(self.temp_dir, "dokumen_a.txt")
        with open(self.file_a, "wb") as f:
            f.write(b"Ini isi dokumen A untuk keperluan unit test.")

        self.file_b = os.path.join(self.temp_dir, "dokumen_b.txt")
        with open(self.file_b, "wb") as f:
            f.write(b"Ini isi dokumen B, sengaja dibuat BEDA dari dokumen A.")

    def tearDown(self):
        # Bersihkan folder sementara setelah tiap test selesai.
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    # ---- TEST 1 ----
    def test_hash_konsisten_untuk_file_yang_sama(self):
        """get_file_hash() harus menghasilkan nilai yang SAMA persis
        kalau dipanggil berkali-kali pada file yang isinya tidak berubah."""
        signer = CryptoSigner(key_path=self.key_path)
        hash_1 = signer.get_file_hash(self.file_a)
        hash_2 = signer.get_file_hash(self.file_a)
        self.assertEqual(hash_1, hash_2)

    # ---- TEST 2 ----
    def test_hash_berbeda_untuk_isi_file_berbeda(self):
        """Dua file dengan isi berbeda harus punya hash SHA-256 yang
        berbeda (sifat dasar fungsi hash: avalanche effect)."""
        signer = CryptoSigner(key_path=self.key_path)
        hash_a = signer.get_file_hash(self.file_a)
        hash_b = signer.get_file_hash(self.file_b)
        self.assertNotEqual(hash_a, hash_b)

    # ---- TEST 3 ----
    def test_sign_dan_verify_dengan_kunci_benar_harus_valid(self):
        """Skenario normal: dokumen ditandatangani, lalu diverifikasi
        dengan public key pasangannya sendiri -> harus VALID (True)."""
        signer = CryptoSigner(key_path=self.key_path)
        pdf_hash = signer.get_file_hash(self.file_a)
        signature = signer.sign_hash(pdf_hash)

        hasil = signer.verify_signature(pdf_hash, signature, public_key=signer.public_key)
        self.assertTrue(hasil)

    # ---- TEST 4 ----
    def test_verify_gagal_jika_isi_dokumen_berubah(self):
        """Uji tamper: signature dibuat untuk file_a, tapi hash yang
        dicocokkan berasal dari file_b (isi berbeda) -> harus GAGAL (False)."""
        signer = CryptoSigner(key_path=self.key_path)
        hash_asli = signer.get_file_hash(self.file_a)
        signature = signer.sign_hash(hash_asli)

        hash_setelah_diubah = signer.get_file_hash(self.file_b)
        hasil = signer.verify_signature(hash_setelah_diubah, signature, public_key=signer.public_key)
        self.assertFalse(hasil)

    # ---- TEST 5 ----
    def test_verify_gagal_dengan_public_key_yang_salah(self):
        """Uji kunci salah: signature dibuat oleh signer_asli, tapi
        diverifikasi pakai public key milik signer_lain yang sama
        sekali tidak berpasangan -> harus GAGAL (False)."""
        signer_asli = CryptoSigner(key_path=self.key_path)
        pdf_hash = signer_asli.get_file_hash(self.file_a)
        signature = signer_asli.sign_hash(pdf_hash)

        key_path_lain = os.path.join(self.temp_dir, "signer_lain.pem")
        signer_lain = CryptoSigner(key_path=key_path_lain)

        hasil = signer_asli.verify_signature(pdf_hash, signature, public_key=signer_lain.public_key)
        self.assertFalse(hasil)

    # ---- TEST 6 ----
    def test_private_key_persisten_setelah_di_load_ulang(self):
        """Setelah CryptoSigner dibuat sekali (key baru tersimpan ke
        disk), instance BARU dengan key_path yang SAMA harus memuat
        key yang SAMA PERSIS (bukan generate ulang key baru yang beda).
        Ini yang memastikan bug 'restart server = key hilang' sudah
        benar-benar tidak terjadi lagi."""
        signer_pertama = CryptoSigner(key_path=self.key_path)
        pem_pertama = signer_pertama.export_public_key_pem()

        # Simulasikan "restart": buat instance CryptoSigner baru dengan
        # key_path yang sama persis.
        signer_kedua = CryptoSigner(key_path=self.key_path)
        pem_kedua = signer_kedua.export_public_key_pem()

        self.assertEqual(pem_pertama, pem_kedua)

    # ---- TEST 7 ----
    def test_export_dan_muat_ulang_public_key_pem_konsisten(self):
        """Public key yang di-export ke teks PEM (untuk ditempel di QR),
        kalau dimuat ulang dengan muat_public_key_dari_pem(), harus
        menghasilkan key yang tetap valid dipakai untuk verifikasi."""
        signer = CryptoSigner(key_path=self.key_path)
        pdf_hash = signer.get_file_hash(self.file_a)
        signature = signer.sign_hash(pdf_hash)

        pem_text = signer.export_public_key_pem()
        public_key_hasil_muat_ulang = muat_public_key_dari_pem(pem_text)

        hasil = verifikasi_dengan_public_key(pdf_hash, signature, public_key_hasil_muat_ulang)
        self.assertTrue(hasil)


class TestEmbedDanEkstraksiQR(unittest.TestCase):
    """Unit test untuk fungsi penempelan & ekstraksi QR-Code dari PDF
    (pdf_handler/embed_pdf.py dan pdf_handler/extract_qr.py)."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

        # Buat 1 PDF kosong sederhana secara langsung pakai PyMuPDF,
        # supaya test ini berdiri sendiri (tidak bergantung file PDF
        # contoh yang mungkin tidak selalu ada di komputer lain).
        self.pdf_asli = os.path.join(self.temp_dir, "dokumen_kosong.pdf")
        doc = fitz.open()
        halaman = doc.new_page()
        halaman.insert_text((50, 50), "Dokumen uji coba untuk unit test.")
        doc.save(self.pdf_asli)
        doc.close()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    # ---- TEST 8 (bonus, lebih dari 5 minimum yang diminta) ----
    def test_embed_dan_ekstraksi_qr_roundtrip(self):
        """Metadata yang ditempel sebagai QR ke sebuah PDF, ketika
        diekstrak lagi, isinya harus SAMA PERSIS dengan yang ditempel
        (roundtrip test)."""
        metadata_asli = {
            "urutan": 1,
            "signer": "Penguji Unit Test",
            "jabatan": "Mahasiswa",
            "institusi": "Universitas Siliwangi",
            "hash_sha256": "abcd1234",
            "signature": "ef567890",
        }

        qr_path = os.path.join(self.temp_dir, "qr_test.png")
        qrcode.make(json.dumps(metadata_asli)).save(qr_path)

        pdf_hasil = os.path.join(self.temp_dir, "dokumen_ber_qr.pdf")
        hasil_embed = embed_qr_ke_pdf(
            pdf_masukan=self.pdf_asli,
            qr_gambar=qr_path,
            pdf_keluaran=pdf_hasil,
            indeks_qr=0
        )
        self.assertIsNotNone(hasil_embed)

        daftar_metadata = ekstraksi_semua_qr(pdf_hasil)
        self.assertEqual(len(daftar_metadata), 1)
        self.assertEqual(daftar_metadata[0], metadata_asli)


if __name__ == "__main__":
    unittest.main(verbosity=2)
import shutil
import pymupdf as fitz

def embed_qr_ke_pdf(pdf_masukan, qr_gambar, pdf_keluaran, posisi_x=400, posisi_y=650, ukuran=100):
    """
    Fungsi untuk menempelkan gambar QR Code ke halaman PDF.
    Memakai incremental save supaya byte-byte dokumen sebelum QR
    ditempel tetap 100% utuh, sehingga bisa dihitung ulang hash-nya
    secara identik saat proses verifikasi.
    """
    try:
        # 1. Salin dulu file asli ke path output, lalu dibuka dari path itu
        shutil.copy(pdf_masukan, pdf_keluaran)
        doc = fitz.open(pdf_keluaran)

        # 2. Pilih halaman pertama (indeks 0)
        halaman = doc[0]

        # 3. Tentukan area/kotak koordinat penempelan (x0, y0, x1, y1)
        area_penempelan = fitz.Rect(posisi_x, posisi_y, posisi_x + ukuran, posisi_y + ukuran)

        # 4. Tempelkan gambar QR Code ke area tersebut
        halaman.insert_image(area_penempelan, filename=qr_gambar)

        # 5. Simpan SECARA INKREMENTAL (menambah di belakang file,
        #    bukan menulis ulang keseluruhan file dari awal)
        doc.saveIncr()
        doc.close()

        print(f"BERHASIL! PDF ber-QR Code disimpan di: {pdf_keluaran}")
        return pdf_keluaran

    except Exception as error:
        print(f"Gagal menempelkan QR Code ke PDF: {error}")
        return None


# UJI COBA LOKAL HARI 3

if __name__ == "__main__":
    embed_qr_ke_pdf(
        pdf_masukan="dokumen_test.pdf",
        qr_gambar="qrcode_hasil.png",
        pdf_keluaran="dokumen_signed.pdf"
    )
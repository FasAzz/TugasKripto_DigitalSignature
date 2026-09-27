import shutil
import pymupdf as fitz

def embed_qr_ke_pdf(pdf_masukan, qr_gambar, pdf_keluaran, indeks_qr=0, posisi_x=400, posisi_y=650, ukuran=100):
    """
    Fungsi untuk menempelkan gambar QR Code ke halaman PDF.
    Memakai incremental save supaya byte-byte dokumen sebelum QR
    ditempel tetap 100% utuh, sehingga bisa dihitung ulang hash-nya
    secara identik saat proses verifikasi.

    indeks_qr: urutan QR ini (0 = penandatangan pertama, 1 = penandatangan
    kedua, dst). Dipakai untuk menggeser posisi QR ke bawah supaya QR
    baru TIDAK menimpa/tertumpuk pas dengan QR milik penandatangan
    sebelumnya -- ini yang bikin fitur multi-signer (beberapa
    penandatangan dalam satu dokumen) bisa jalan.
    """
    try:
        shutil.copy(pdf_masukan, pdf_keluaran)
        doc = fitz.open(pdf_keluaran)
        halaman = doc[0]

        # Geser QR ke bawah sejauh (ukuran + jarak) untuk tiap indeks
        # berikutnya. Kalau posisinya jadi terlalu mepet ke tepi atas
        # (dokumen sudah dipenuhi banyak QR), tahan di posisi minimum
        # supaya tidak keluar halaman.
        jarak_antar_qr = ukuran + 20
        posisi_y_final = posisi_y - (indeks_qr * jarak_antar_qr)
        posisi_y_final = max(posisi_y_final, 20)

        area_penempelan = fitz.Rect(posisi_x, posisi_y_final, posisi_x + ukuran, posisi_y_final + ukuran)
        halaman.insert_image(area_penempelan, filename=qr_gambar)

        doc.saveIncr()
        doc.close()

        print(f"BERHASIL! QR ke-{indeks_qr + 1} ditempel di: {pdf_keluaran}")
        return pdf_keluaran

    except Exception as error:
        print(f"Gagal menempelkan QR Code ke PDF: {error}")
        return None


if __name__ == "__main__":
    embed_qr_ke_pdf(
        pdf_masukan="dokumen_test.pdf",
        qr_gambar="qrcode_hasil.png",
        pdf_keluaran="dokumen_signed.pdf",
        indeks_qr=0
    )
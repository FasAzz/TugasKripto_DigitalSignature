import pymupdf as fitz

def embed_qr_ke_pdf(pdf_masukan, qr_gambar, pdf_keluaran, posisi_x=400, posisi_y=650, ukuran=100):
    """
    Fungsi untuk menempelkan gambar QR Code ke halaman PDF
    """
    try:
        # 1. Buka berkas PDF
        doc = fitz.open(pdf_masukan)
        
        # 2. Pilih halaman pertama (indeks 0)
        halaman = doc[0]
        
        # 3. Tentukan area/kotak koordinat penempelan (x0, y0, x1, y1)
        area_penempelan = fitz.Rect(posisi_x, posisi_y, posisi_x + ukuran, posisi_y + ukuran)
        
        # 4. Tempelkan gambar QR Code ke area tersebut
        halaman.insert_image(area_penempelan, filename=qr_gambar)
        
        # 5. Simpan berkas PDF baru
        doc.save(pdf_keluaran)
        doc.close()
        
        print(f"BERHASIL! PDF ber-QR Code disimpan di: {pdf_keluaran}")
        return pdf_keluaran

    except Exception as error:
        print(f"Gagal menempelkan QR Code ke PDF: {error}")
        return None



# UJI COBA LOKAL HARI 3

if __name__ == "__main__":
    # Jalankan penempelan
    embed_qr_ke_pdf(
        pdf_masukan="dokumen_test.pdf",
        qr_gambar="qrcode_hasil.png",
        pdf_keluaran="dokumen_signed.pdf"
    )
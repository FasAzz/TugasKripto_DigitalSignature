import qrcode
import json
import fitz  # ini pymupdf
import shutil

# 1. PDF target yang mau "dipalsukan" seolah-olah sudah ditandatangani
pdf_asli = "dokumen_polos.pdf"
pdf_hasil = "dokumen_qr_palsu.pdf"

# 2. Metadata NGARANG BEBAS, seperti yang dibuat penyerang yang TIDAK
#    punya akses ke private key server, jadi cuma bisa nebak-nebak
metadata_palsu = {
    "signer": "Orang Iseng",
    "jabatan": "Bukan Siapa-siapa",
    "institusi": "Universitas Karangan",
    "tanggal": "2026-01-01 00:00:00",
    "hash_sha256": "0" * 64,
    "signature": "ab" * 256,
    "ukuran_asli": 999999
}

# 3. Ubah metadata ngarang itu jadi gambar QR
qr_img = qrcode.make(json.dumps(metadata_palsu))
qr_img.save("qr_palsu.png")

# 4. Tempel manual ke PDF target
shutil.copy(pdf_asli, pdf_hasil)
doc = fitz.open(pdf_hasil)
halaman = doc[0]
area = fitz.Rect(400, 650, 500, 750)
halaman.insert_image(area, filename="qr_palsu.png")
doc.saveIncr()
doc.close()

print(f"Selesai. Dokumen dengan QR palsu: {pdf_hasil}")
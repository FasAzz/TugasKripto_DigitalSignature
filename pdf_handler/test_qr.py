import qrcode
import json
import os
from pdf_handler.extract_qr import ekstraksi_dan_baca_qr

def buat_qr_code_digital_signature(data_metadata, nama_file_output="qrcode_hasil.png"):
    """
    Fungsi untuk mengubah metadata dan digital signature menjadi gambar QR Code
    """
    try:
        # 1. Konversi dictionary/data ke bentuk string JSON
        payload_string = json.dumps(data_metadata)
        
        # 2. Atur konfigurasi QR Code
        qr = qrcode.QRCode(
            version=None, # Otomatis menyesuaikan ukuran data
            error_correction=qrcode.constants.ERROR_CORRECT_M, # Tingkat koreksi eror sedang
            box_size=10, # Ukuran per piksel kotak
            border=4,    # Ketebalan garis tepi
        )
        
        # 3. Masukkan data string ke QR Code
        qr.add_data(payload_string)
        qr.make(fit=True)
        
        # 4. Generate gambar QR Code
        img = qr.make_image(fill_color="black", back_color="white")
        
        # 5. Simpan gambar ke file
        img.save(nama_file_output)
        
        print(f"Berhasil! QR Code disimpan dengan nama: {nama_file_output}")
        return nama_file_output

    except Exception as error:
        print(f"Terjadi kesalahan: {error}")


# ==========================================
# AREA UJI COBA LOKAL
# ==========================================
if __name__ == "__main__":
    print("--- UJI COBA 1: GENERATE QR CODE ---")
    sample_payload = {
        "doc_id": "DOC-UNSIL-2026-001",
        "signer": "Ir. Alam Rahmatulloh, S.T., M.T.",
        "jabatan": "Dosen Pengampu",
        "institusi": "Universitas Siliwangi",
        "timestamp": "2026-09-24 20:15:00",
        "hash_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "signature": "MEQCID3a8X99123891238912389123891238912389123"
    }

    # Jalankan pembuat QR Code
    buat_qr_code_digital_signature(sample_payload, "pdf_handler/qrcode_hasil.png")

    print("\n--- UJI COBA 2: EKSTRAKSI QR CODE DARI PDF ---")
    target_pdf = "pdf_handler/dokumen_signed.pdf"
    
    if os.path.exists(target_pdf):
        hasil = ekstraksi_dan_baca_qr(target_pdf)

        if hasil:
            print("=== QR CODE BERHASIL DIEKSTRAKSI ===")
            print("Penandatangan :", hasil.get("signer", "-"))
            print("Jabatan       :", hasil.get("jabatan", "-"))
            print("Institusi     :", hasil.get("institusi", "-"))
            print("Hash SHA-256  :", hasil.get("hash_sha256", "-"))
            print("Signature     :", hasil.get("signature", "-"))
        else:
            print("QR Code tidak ditemukan atau tidak dapat dibaca di dalam PDF!")
    else:
        print(f"File '{target_pdf}' belum ada. Jalankan embed_pdf.py terlebih dahulu untuk menghasilkan PDF bertanda tangan.")
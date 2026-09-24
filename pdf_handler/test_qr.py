import qrcode
import json

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
            error_correction=qrcode.constants.ERROR_CORRECT_M, # Tingkat koreksi eror sedang (standar)
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


# AREA UJI COBA LOKAL

if __name__ == "__main__":
    # Ini simulasi data metadata & signature yang nantinya kamu dapat dari Anggota 1
    sample_payload = {
        "doc_id": "DOC-UNSIL-2026-001",
        "signer": "Ir. Alam Rahmatulloh, S.T., M.T.",
        "institution": "Universitas Siliwangi",
        "timestamp": "2026-09-24 20:15:00",
        "signature": "MEQCID3a8X99123891238912389123891238912389123"
    }

    # Jalankan fungsinya
    buat_qr_code_digital_signature(sample_payload)
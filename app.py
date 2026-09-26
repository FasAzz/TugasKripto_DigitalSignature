from flask import Flask, request, jsonify, send_file, render_template
import os
import json
import hashlib
import qrcode
from datetime import datetime
from crypto_core.signer import CryptoSigner
from pdf_handler.embed_pdf import embed_qr_ke_pdf
from pdf_handler.extract_qr import ekstraksi_dan_baca_qr

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'output'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

signer = CryptoSigner()

@app.route('/')
def home():
    return render_template('index.html')

# ==========================================
# 1. ENDPOINT PENANDATANGANAN DOKUMEN (SIGN)
# ==========================================
@app.route('/api/sign', methods=['POST'])
def sign_document():
    try:
        if 'file' not in request.files:
            return jsonify({"error": "Tidak ada file PDF yang diunggah"}), 400

        file = request.files['file']

        signer_name = request.form.get('signer_name', 'Anonim')
        jabatan = request.form.get('jabatan', 'Mahasiswa')
        institusi = request.form.get('institusi', 'Universitas Siliwangi')
        tanggal_sign = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 1. Simpan file PDF Asli
        input_pdf_path = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(input_pdf_path)
        output_pdf_path = os.path.join(OUTPUT_FOLDER, f"signed_{file.filename}")

        # 2. Catat ukuran file ASLI (sebelum QR ditempel), dipakai lagi saat verifikasi
        ukuran_asli = os.path.getsize(input_pdf_path)

        # 3. Hitung Hash SHA-256 dari PDF Asli & Buat Signature RSA-2048
        pdf_hash_bytes = signer.get_file_hash(input_pdf_path)
        pdf_hash_hex = pdf_hash_bytes.hex()
        signature_bytes = signer.sign_hash(pdf_hash_bytes)
        signature_hex = signature_bytes.hex()

        # 4. Buat Metadata JSON Lengkap
        metadata = {
            "signer": signer_name,
            "jabatan": jabatan,
            "institusi": institusi,
            "tanggal": tanggal_sign,
            "hash_sha256": pdf_hash_hex,
            "signature": signature_hex,
            "ukuran_asli": ukuran_asli
        }

        # 5. Generate Gambar QR Code
        qr_image_path = os.path.join(UPLOAD_FOLDER, f"qr_{file.filename}.png")
        qr_img = qrcode.make(json.dumps(metadata))
        qr_img.save(qr_image_path)

        # 6. Tempelkan QR Code ke PDF (pakai incremental save di embed_qr_ke_pdf)
        result = embed_qr_ke_pdf(
            pdf_masukan=input_pdf_path,
            qr_gambar=qr_image_path,
            pdf_keluaran=output_pdf_path
        )

        if os.path.exists(qr_image_path):
            os.remove(qr_image_path)

        if not result:
            return jsonify({"error": "Gagal menempelkan QR Code ke PDF"}), 500

        return jsonify({
            "message": "Dokumen berhasil ditandatangani dan ter-embed QR Code!",
            "signer": signer_name,
            "jabatan": jabatan,
            "institusi": institusi,
            "tanggal": tanggal_sign,
            "signed_pdf_url": f"/download/signed_{file.filename}"
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==========================================
# 2. ENDPOINT VERIFIKASI KEASLIAN DOKUMEN (VERIFY)
# ==========================================
@app.route('/api/verify', methods=['POST'])
def verify_document():
    try:
        if 'file' not in request.files:
            return jsonify({"error": "Tidak ada file PDF yang diunggah untuk verifikasi"}), 400

        file = request.files['file']
        temp_pdf_path = os.path.join(UPLOAD_FOLDER, f"verify_{file.filename}")
        file.save(temp_pdf_path)

        # 1. Ekstrak metadata dari QR Code di PDF
        metadata = ekstraksi_dan_baca_qr(temp_pdf_path)

        if not metadata:
            if os.path.exists(temp_pdf_path):
                os.remove(temp_pdf_path)
            return jsonify({
                "status": "INVALID",
                "message": "Dokumen tidak memiliki QR Code Tanda Tangan Digital yang sah!"
            }), 200

        # 2. Ambil data asli dari metadata QR Code
        original_signer = metadata.get("signer", "Tidak Diketahui")
        original_jabatan = metadata.get("jabatan", "-")
        original_institusi = metadata.get("institusi", "-")
        original_tanggal = metadata.get("tanggal", "-")
        original_hash_hex = metadata.get("hash_sha256", "")
        signature_hex = metadata.get("signature", "")
        ukuran_asli = metadata.get("ukuran_asli")

        signature_bytes = bytes.fromhex(signature_hex)
        original_hash_bytes = bytes.fromhex(original_hash_hex)

        # 3. INI PENGECEKAN YANG SEBELUMNYA HILANG:
        #    hitung ulang hash dari isi dokumen yang BENAR-BENAR diupload sekarang
        #    (ambil persis N byte pertama, N = ukuran dokumen sebelum QR ditempel),
        #    lalu cocokkan dengan hash yang tercatat di dalam QR
        konten_cocok = False
        if ukuran_asli is not None:
            with open(temp_pdf_path, "rb") as f:
                data_upload = f.read()
            konten_asli_upload = data_upload[:ukuran_asli]
            hash_ulang_hex = hashlib.sha256(konten_asli_upload).hexdigest()
            konten_cocok = (hash_ulang_hex == original_hash_hex)

        if os.path.exists(temp_pdf_path):
            os.remove(temp_pdf_path)

        if not konten_cocok:
            return jsonify({
                "status": "MODIFIED",
                "message": "PERINGATAN: Isi dokumen sudah berubah, hash tidak cocok dengan catatan saat penandatanganan!",
                "signer": original_signer
            }), 200

        # 4. Baru setelah isi dokumen dipastikan cocok, verifikasi tanda tangan RSA-nya
        is_signature_valid = signer.verify_signature(original_hash_bytes, signature_bytes)

        # 5. Evaluasi Keaslian
        if is_signature_valid:
            return jsonify({
                "status": "VALID",
                "message": "Dokumen 100% Asli & Belum Pernah Dimodifikasi!",
                "signer": original_signer,
                "jabatan": original_jabatan,
                "institusi": original_institusi,
                "tanggal": original_tanggal,
                "hash_sha256": original_hash_hex
            }), 200
        else:
            return jsonify({
                "status": "MODIFIED",
                "message": "PERINGATAN: Tanda tangan kriptografi RSA tidak cocok/sah!",
                "signer": original_signer
            }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==========================================
# 3. ENDPOINT DOWNLOAD FILE DOKUMEN
# ==========================================
@app.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    file_path = os.path.join(OUTPUT_FOLDER, filename)
    return send_file(file_path, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
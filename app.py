from flask import Flask, request, jsonify, send_file, render_template
import os
import json
import qrcode
from crypto_core.signer import CryptoSigner
from pdf_handler.embed_pdf import embed_qr_ke_pdf  # Menggunakan modul Kamila
from crypto_core.verifier import extract_qr_data_from_pdf  # Modul pembaca QR verifikasi

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
        
        # 1. Simpan file PDF input
        input_pdf_path = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(input_pdf_path)
        
        # 2. Hitung Hash SHA-256 PDF & Tandatangani dengan RSA-2048
        pdf_hash_bytes = signer.get_file_hash(input_pdf_path)
        pdf_hash_hex = pdf_hash_bytes.hex()
        signature_bytes = signer.sign_hash(pdf_hash_bytes)
        signature_hex = signature_bytes.hex()
        
        # 3. Kemas Metadata ke JSON & Generate Gambar QR Code
        metadata = {
            "signer": signer_name,
            "hash_sha256": pdf_hash_hex,
            "signature": signature_hex
        }
        
        qr_image_path = os.path.join(UPLOAD_FOLDER, f"qr_{file.filename}.png")
        qr_img = qrcode.make(json.dumps(metadata))
        qr_img.save(qr_image_path)
        
        # 4. Tempel QR Code ke PDF Menggunakan Fungsi Kamila
        output_pdf_path = os.path.join(OUTPUT_FOLDER, f"signed_{file.filename}")
        result = embed_qr_ke_pdf(
            pdf_masukan=input_pdf_path,
            qr_gambar=qr_image_path,
            pdf_keluaran=output_pdf_path
        )
        
        if not result:
            return jsonify({"error": "Gagal menempelkan QR Code ke PDF"}), 500
        
        return jsonify({
            "message": "Dokumen berhasil ditandatangani dan ter-embed QR Code!",
            "signer": signer_name,
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

        # 1. Ekstrak metadata JSON dari QR Code di dalam PDF
        metadata = extract_qr_data_from_pdf(temp_pdf_path)
        if not metadata:
            if os.path.exists(temp_pdf_path):
                os.remove(temp_pdf_path)
            return jsonify({
                "status": "INVALID",
                "message": "Dokumen tidak memiliki QR Code Tanda Tangan Digital yang sah!"
            }), 200

        # 2. Hitung ulang Hash SHA-256 dari PDF yang diunggah saat ini
        current_hash_bytes = signer.get_file_hash(temp_pdf_path)
        current_hash_hex = current_hash_bytes.hex()

        # 3. Ambil data asli dari QR Code
        original_signer = metadata.get("signer", "Tidak Diketahui")
        original_hash_hex = metadata.get("hash_sha256", "")
        signature_hex = metadata.get("signature", "")

        signature_bytes = bytes.fromhex(signature_hex)

        # 4. Verifikasi Tanda Tangan Kriptografi RSA-2048 & Hash
        is_signature_valid = signer.verify_signature(current_hash_bytes, signature_bytes)
        is_hash_matching = (current_hash_hex == original_hash_hex)

        if os.path.exists(temp_pdf_path):
            os.remove(temp_pdf_path)

        # 5. Hasil Evaluasi Keaslian Dokumen
        if is_signature_valid and is_hash_matching:
            return jsonify({
                "status": "VALID",
                "message": "Dokumen 100% Asli & Belum Pernah Dimodifikasi!",
                "signer": original_signer,
                "hash_sha256": current_hash_hex
            }), 200
        else:
            return jsonify({
                "status": "MODIFIED",
                "message": "PERINGATAN: Dokumen telah dimodifikasi atau tanda tangan tidak sah!",
                "signer": original_signer,
                "current_hash": current_hash_hex,
                "original_hash": original_hash_hex
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
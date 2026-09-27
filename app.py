from flask import Flask, request, jsonify, send_file, render_template
from dotenv import load_dotenv
import os
import re
import json
import hashlib
import qrcode
from datetime import datetime
from crypto_core.signer import CryptoSigner, muat_public_key_dari_pem, verifikasi_dengan_public_key
from pdf_handler.embed_pdf import embed_qr_ke_pdf
from pdf_handler.extract_qr import ekstraksi_semua_qr

load_dotenv()  # baca isi file .env, taruh ke environment variable

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'output'
KEYS_FOLDER = 'keys'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
os.makedirs(KEYS_FOLDER, exist_ok=True)


def ambil_signer_untuk(signer_id: str) -> CryptoSigner:
    """
    Mengembalikan CryptoSigner milik 'signer_id' tertentu. Kalau id ini
    belum pernah dipakai, key pair baru otomatis dibuat & disimpan
    terenkripsi di keys/<signer_id>.pem. Kalau sudah pernah, key lama
    yang sama dipakai lagi -- jadi identitas kriptografis tiap orang
    konsisten setiap kali dia menandatangani dokumen apa pun.
    """
    # Sanitasi id supaya tidak bisa dipakai untuk keluar dari folder keys/
    # (mencegah path traversal semacam "../../secret").
    signer_id_aman = re.sub(r'[^a-zA-Z0-9_-]', '', signer_id).lower()
    if not signer_id_aman:
        signer_id_aman = "anonim"
    key_path = os.path.join(KEYS_FOLDER, f"{signer_id_aman}.pem")
    return CryptoSigner(key_path=key_path)


@app.route('/')
def home():
    return render_template('index.html')

# ==========================================
# 1. ENDPOINT PENANDATANGANAN DOKUMEN (SIGN)
#    Mendukung MULTI-SIGNER: kalau dokumen yang diunggah sudah pernah
#    ditandatangani sebelumnya, tanda tangan baru ini ditambahkan
#    sebagai penandatangan BERIKUTNYA (bukan menimpa yang lama).
# ==========================================
@app.route('/api/sign', methods=['POST'])
def sign_document():
    try:
        if 'file' not in request.files:
            return jsonify({"error": "Tidak ada file PDF yang diunggah"}), 400

        file = request.files['file']

        signer_id = request.form.get('signer_id', '').strip()
        signer_name = request.form.get('signer_name', 'Anonim')
        jabatan = request.form.get('jabatan', 'Mahasiswa')
        institusi = request.form.get('institusi', 'Universitas Siliwangi')
        tanggal_sign = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if not signer_id:
            return jsonify({"error": "ID penandatangan wajib diisi (mis. 'anggota1')"}), 400

        signer_ini = ambil_signer_untuk(signer_id)

        # 1. Simpan file PDF yang diunggah (bisa PDF asli, ATAU PDF yang
        #    sudah ditandatangani orang lain sebelumnya -- dua-duanya
        #    diperlakukan sama di sini).
        input_pdf_path = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(input_pdf_path)
        output_pdf_path = os.path.join(OUTPUT_FOLDER, f"signed_{file.filename}")

        # 2. Cek dulu berapa banyak QR/penandatangan yang SUDAH ada di
        #    dokumen ini, supaya tahu ini penandatangan ke berapa, dan
        #    supaya QR baru ditempel di posisi yang tidak menumpuk.
        qr_sebelumnya = ekstraksi_semua_qr(input_pdf_path)
        urutan_ke = len(qr_sebelumnya) + 1

        # 3. Catat ukuran file PERSIS seperti yang diunggah sekarang
        #    (kalau ini penandatangan ke-2/3, ukuran ini SUDAH termasuk
        #    QR-QR sebelumnya -- itu memang yang mau ditandatangani:
        #    seluruh riwayat sampai saat ini).
        ukuran_sebelum_qr_baru = os.path.getsize(input_pdf_path)

        # 4. Hitung Hash SHA-256 & buat signature RSA-PSS
        pdf_hash_bytes = signer_ini.get_file_hash(input_pdf_path)
        pdf_hash_hex = pdf_hash_bytes.hex()
        signature_bytes = signer_ini.sign_hash(pdf_hash_bytes)
        signature_hex = signature_bytes.hex()

        # 5. Metadata milik penandatangan ini SAJA (bukan seluruh rantai --
        #    entri sebelumnya sudah ada secara fisik sebagai QR terpisah
        #    di halaman yang sama).
        metadata = {
            "urutan": urutan_ke,
            "signer_id": re.sub(r'[^a-zA-Z0-9_-]', '', signer_id).lower(),
            "signer": signer_name,
            "jabatan": jabatan,
            "institusi": institusi,
            "tanggal": tanggal_sign,
            "hash_sha256": pdf_hash_hex,
            "signature": signature_hex,
            "ukuran_asli": ukuran_sebelum_qr_baru,
            "public_key_pem": signer_ini.export_public_key_pem(),
        }

        # 6. Generate & tempelkan QR baru di posisi ke-(urutan_ke - 1)
        qr_image_path = os.path.join(UPLOAD_FOLDER, f"qr_{urutan_ke}_{file.filename}.png")
        qr_img = qrcode.make(json.dumps(metadata))
        qr_img.save(qr_image_path)

        result = embed_qr_ke_pdf(
            pdf_masukan=input_pdf_path,
            qr_gambar=qr_image_path,
            pdf_keluaran=output_pdf_path,
            indeks_qr=urutan_ke - 1
        )

        if os.path.exists(qr_image_path):
            os.remove(qr_image_path)

        if not result:
            return jsonify({"error": "Gagal menempelkan QR Code ke PDF"}), 500

        return jsonify({
            "message": "Dokumen berhasil ditandatangani dan ter-embed QR Code!",
            "urutan": urutan_ke,
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
#    Mengecek SELURUH rantai tanda tangan yang ada di dokumen.
#    Dokumen dinyatakan VALID hanya kalau SEMUA tanda tangan
#    dalam rantai itu valid.
# ==========================================
@app.route('/api/verify', methods=['POST'])
def verify_document():
    try:
        if 'file' not in request.files:
            return jsonify({"error": "Tidak ada file PDF yang diunggah untuk verifikasi"}), 400

        file = request.files['file']
        temp_pdf_path = os.path.join(UPLOAD_FOLDER, f"verify_{file.filename}")
        file.save(temp_pdf_path)

        with open(temp_pdf_path, "rb") as f:
            data_upload = f.read()

        daftar_qr = ekstraksi_semua_qr(temp_pdf_path)

        if os.path.exists(temp_pdf_path):
            os.remove(temp_pdf_path)

        if not daftar_qr:
            return jsonify({
                "status": "INVALID",
                "message": "Dokumen tidak memiliki QR Code Tanda Tangan Digital yang sah!"
            }), 200

        # Urutkan berdasarkan field "urutan" supaya pengecekan rantai
        # dari penandatangan pertama -> terakhir, tidak bergantung pada
        # urutan QR yang dibaca dari halaman.
        daftar_qr.sort(key=lambda m: m.get("urutan", 0))

        hasil_per_signer = []
        dokumen_valid_total = True

        for entri in daftar_qr:
            original_hash_hex = entri.get("hash_sha256", "")
            signature_hex = entri.get("signature", "")
            ukuran_asli = entri.get("ukuran_asli")
            public_key_pem = entri.get("public_key_pem")

            info_signer = {
                "urutan": entri.get("urutan"),
                "signer": entri.get("signer", "Tidak Diketahui"),
                "jabatan": entri.get("jabatan", "-"),
                "institusi": entri.get("institusi", "-"),
                "tanggal": entri.get("tanggal", "-"),
                "hash_sha256": original_hash_hex,
            }

            # 1. Cek isi dokumen pada TAHAP penandatangan ini belum berubah:
            #    potong data upload sepanjang ukuran_asli tahap ini, hash
            #    ulang, cocokkan dengan hash yang tercatat di QR tahap ini.
            konten_cocok = False
            if ukuran_asli is not None and ukuran_asli <= len(data_upload):
                potongan = data_upload[:ukuran_asli]
                hash_ulang_hex = hashlib.sha256(potongan).hexdigest()
                konten_cocok = (hash_ulang_hex == original_hash_hex)

            if not konten_cocok:
                info_signer["status"] = "MODIFIED"
                info_signer["keterangan"] = "Isi dokumen pada tahap ini sudah berubah, hash tidak cocok."
                hasil_per_signer.append(info_signer)
                dokumen_valid_total = False
                continue

            # 2. Cek signature RSA tahap ini, pakai public key YANG
            #    TERTEMPEL di QR tahap ini sendiri (bukan kunci sistem
            #    global) -- supaya tiap penandatangan diverifikasi
            #    dengan kuncinya masing-masing.
            try:
                pub_key = muat_public_key_dari_pem(public_key_pem)
                signature_bytes = bytes.fromhex(signature_hex)
                original_hash_bytes = bytes.fromhex(original_hash_hex)
                is_valid = verifikasi_dengan_public_key(original_hash_bytes, signature_bytes, pub_key)
            except Exception:
                is_valid = False

            if is_valid:
                info_signer["status"] = "VALID"
            else:
                info_signer["status"] = "MODIFIED"
                info_signer["keterangan"] = "Tanda tangan kriptografi RSA tidak cocok/sah pada tahap ini."
                dokumen_valid_total = False

            hasil_per_signer.append(info_signer)

        if dokumen_valid_total:
            return jsonify({
                "status": "VALID",
                "message": f"Dokumen 100% Asli & Belum Pernah Dimodifikasi! "
                            f"({len(hasil_per_signer)} penandatangan terverifikasi)",
                "signers": hasil_per_signer
            }), 200
        else:
            return jsonify({
                "status": "MODIFIED",
                "message": "PERINGATAN: Dokumen ini telah dimodifikasi atau ada tanda tangan yang tidak sah!",
                "signers": hasil_per_signer
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
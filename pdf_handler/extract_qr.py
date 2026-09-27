import pymupdf as fitz
import cv2
import numpy as np
import json
try:
    from pyzbar.pyzbar import decode as pyzbar_decode
except Exception:
    pyzbar_decode = None


def _decode_satu_gambar(img):
    """Coba baca 1 QR dari 1 gambar, pakai 3 strategi berurutan
    (OpenCV standar -> upscale 2x -> PyZbar). Kembalikan dict metadata
    kalau ketemu & valid JSON, None kalau tidak."""
    detector = cv2.QRCodeDetector()

    data, _, _ = detector.detectAndDecode(img)
    if data:
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            pass

    resized_img = cv2.resize(img, (0, 0), fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    data, _, _ = detector.detectAndDecode(resized_img)
    if data:
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            pass

    if pyzbar_decode:
        decoded_objs = pyzbar_decode(img)
        for obj in decoded_objs:
            if obj.data:
                try:
                    return json.loads(obj.data.decode('utf-8'))
                except json.JSONDecodeError:
                    pass
    return None


def ekstraksi_semua_qr(pdf_path: str) -> list:
    """
    BEDA DARI VERSI SEBELUMNYA (ekstraksi_dan_baca_qr):
    Dulu fungsi ini langsung 'return' begitu QR PERTAMA ketemu, jadi
    hanya mendukung 1 penandatangan per dokumen. Sekarang, semua QR di
    semua halaman dikumpulkan dan dikembalikan sebagai LIST, sesuai
    urutan kemunculannya di dalam PDF -- ini yang dipakai untuk
    merekonstruksi rantai multi-signer.

    Return: list berisi dict metadata, urut dari penandatangan pertama
    sampai yang terakhir. List kosong kalau tidak ada QR sama sekali.
    """
    hasil = []
    try:
        doc = fitz.open(pdf_path)

        for page_num in range(len(doc)):
            page = doc[page_num]
            image_list = page.get_images()

            for img_info in image_list:
                xref = img_info[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]

                nparr = np.frombuffer(image_bytes, np.uint8)
                img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                if img is None:
                    continue

                metadata = _decode_satu_gambar(img)
                if metadata is not None:
                    hasil.append(metadata)

        doc.close()
        return hasil
    except Exception as e:
        print(f"[Error Ekstraksi QR]: {e}")
        return hasil


# Dibiarkan ada untuk kompatibilitas kalau ada bagian lain yang masih
# memanggil nama lama -- sekarang hanya pembungkus ekstraksi_semua_qr,
# mengembalikan entri PERTAMA saja (perilaku lama).
def ekstraksi_dan_baca_qr(pdf_path: str):
    semua = ekstraksi_semua_qr(pdf_path)
    return semua[0] if semua else None
import pymupdf as fitz
import cv2
import numpy as np
import json
try:
    from pyzbar.pyzbar import decode as pyzbar_decode
except ImportError:
    pyzbar_decode = None

def ekstraksi_dan_baca_qr(pdf_path: str) -> dict:
    try:
        doc = fitz.open(pdf_path)
        detector = cv2.QRCodeDetector()

        for page_num in range(len(doc)):
            page = doc[page_num]
            image_list = page.get_images()

            for img_info in image_list:
                xref = img_info[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]

                # Convert byte image ke OpenCV format
                nparr = np.frombuffer(image_bytes, np.uint8)
                img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

                if img is None:
                    continue

                # Percobaan 1: OpenCV Standar
                data, _, _ = detector.detectAndDecode(img)
                if data:
                    doc.close()
                    return json.loads(data)

                # Percobaan 2: Perbesar ukuran gambar 2x (Upscaling) jika gambar agak buram
                resized_img = cv2.resize(img, (0, 0), fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
                data, _, _ = detector.detectAndDecode(resized_img)
                if data:
                    doc.close()
                    return json.loads(data)

                # Percobaan 3: Gunakan PyZbar jika OpenCV gagal
                if pyzbar_decode:
                    decoded_objs = pyzbar_decode(img)
                    for obj in decoded_objs:
                        if obj.data:
                            doc.close()
                            return json.loads(obj.data.decode('utf-8'))

        doc.close()
        return None
    except Exception as e:
        print(f"[Error Ekstraksi QR]: {e}")
        return None
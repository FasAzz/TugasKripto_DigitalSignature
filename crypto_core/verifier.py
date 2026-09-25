import fitz  # PyMuPDF
import cv2
import numpy as np
import json
from PIL import Image

def extract_qr_data_from_pdf(pdf_path: str) -> dict:
    """
    Membuka PDF, mengekstrak gambar dari halaman, 
    dan membaca data JSON di dalam QR Code.
    """
    try:
        doc = fitz.open(pdf_path)
        qr_detector = cv2.QRCodeDetector()

        for page_index in range(len(doc)):
            page = doc[page_index]
            image_list = page.get_images()

            for img_info in image_list:
                xref = img_info[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]

                # Konversi bytes gambar ke format OpenCV (numpy array)
                nparr = np.frombuffer(image_bytes, np.uint8)
                img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

                # Deteksi dan dekode QR Code
                data, bbox, _ = qr_detector.detectAndDecode(img)
                if data:
                    doc.close()
                    return json.loads(data) # Mengembalikan dictionary metadata

        doc.close()
        return None # Tidak ditemukan QR Code
    except Exception as e:
        print(f"Error extracting QR: {e}")
        return None
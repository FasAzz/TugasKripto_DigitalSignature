import hashlib
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization

class CryptoSigner:
    def __init__(self):
        # 1. Pembangkitan Pasangan Kunci RSA-2048 (Slide 45)
        self.private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
        self.public_key = self.private_key.public_key()

    def get_file_hash(self, file_path: str) -> bytes:
        """Menghitung Hash SHA-256 dari berkas PDF (Slide 43)"""
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for block in iter(lambda: f.read(4096), b""):
                sha256.update(block)
        return sha256.digest()

    def sign_hash(self, pdf_hash: bytes) -> bytes:
        """Menandatangani Hash menggunakan Private Key (RSA-PSS)"""
        return self.private_key.sign(
            pdf_hash,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )

    def verify_signature(self, pdf_hash: bytes, signature: bytes, public_key=None) -> bool:
        """Memverifikasi keaslian dokumen menggunakan Public Key (Slide 44)"""
        pub_key = public_key if public_key else self.public_key
        try:
            pub_key.verify(
                signature,
                pdf_hash,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            return True   # Valid / Asli
        except Exception:
            return False  # Palsu / Terubah

# Uji Coba Sederhana Lokal
if __name__ == "__main__":
    signer = CryptoSigner()
    print("✓ Pasangan Kunci RSA-2048 (Python) Berhasil Dibuat!")
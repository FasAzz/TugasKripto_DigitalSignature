import os
import hashlib
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization


class CryptoSigner:
    def __init__(self, key_path: str = "private_key.pem", passphrase: str = None):
        """
        key_path bisa disesuaikan per identitas penandatangan, contoh:
        "keys/anggota1.pem". Ini yang memungkinkan MULTI-SIGNER --
        tiap orang punya file key sendiri, bukan berbagi 1 kunci sistem.
        """
        self.key_path = key_path

        if passphrase is None:
            passphrase = os.environ.get("PRIVATE_KEY_PASSPHRASE")

        if not passphrase:
            raise ValueError(
                "PRIVATE_KEY_PASSPHRASE belum diset. "
                "Isi dulu di file .env (lihat .env.example), "
                "atau set environment variable-nya secara manual."
            )

        self._passphrase_bytes = passphrase.encode("utf-8")

        # Pastikan folder induk key_path ada (mis. folder "keys/"),
        # supaya tidak error saat pertama kali menyimpan file key baru.
        folder_induk = os.path.dirname(self.key_path)
        if folder_induk:
            os.makedirs(folder_induk, exist_ok=True)

        if os.path.exists(self.key_path):
            self.private_key = self._load_private_key()
        else:
            self.private_key = self._generate_dan_simpan_private_key()

        self.public_key = self.private_key.public_key()

    def _generate_dan_simpan_private_key(self):
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
        pem_terenkripsi = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.BestAvailableEncryption(self._passphrase_bytes)
        )
        with open(self.key_path, "wb") as f:
            f.write(pem_terenkripsi)
        return private_key

    def _load_private_key(self):
        with open(self.key_path, "rb") as f:
            pem_terenkripsi = f.read()
        return serialization.load_pem_private_key(
            pem_terenkripsi,
            password=self._passphrase_bytes
        )

    def get_file_hash(self, file_path: str) -> bytes:
        """Menghitung Hash SHA-256 dari berkas PDF"""
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
        """Memverifikasi keaslian dokumen menggunakan Public Key"""
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
            return True
        except Exception:
            return False

    def export_public_key_pem(self) -> str:
        """
        Mengubah public key jadi teks PEM, supaya bisa ditempel LANGSUNG
        di dalam QR-Code. Ini penting untuk multi-signer: verifikasi jadi
        tidak bergantung pada file 'keys/<id>.pem' tersedia di komputer
        yang melakukan verifikasi -- semua info yang dibutuhkan sudah
        menempel di dokumennya sendiri.
        """
        pem_bytes = self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        return pem_bytes.decode("utf-8")


def muat_public_key_dari_pem(pem_str: str):
    """Fungsi bantuan: mengubah teks PEM (yang diambil dari dalam QR)
    kembali menjadi objek public key yang bisa dipakai verify_signature()."""
    return serialization.load_pem_public_key(pem_str.encode("utf-8"))


def verifikasi_dengan_public_key(pdf_hash: bytes, signature: bytes, public_key) -> bool:
    """
    Verifikasi berdiri sendiri (tidak perlu instance CryptoSigner),
    dipakai saat memverifikasi tanda tangan milik ORANG LAIN yang
    public key-nya didapat dari QR-Code (bukan dari signer lokal kita).
    """
    try:
        public_key.verify(
            signature,
            pdf_hash,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        return True
    except Exception:
        return False


# Uji Coba Sederhana Lokal
if __name__ == "__main__":
    signer = CryptoSigner()
    print("✓ Private key siap dipakai!")
    print(signer.export_public_key_pem())
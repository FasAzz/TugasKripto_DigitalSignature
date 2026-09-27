# TugasKripto_DigitalSignature

Aplikasi web Tanda Tangan Digital untuk dokumen PDF, dibangun untuk Tugas
Proyek Aplikasi Kriptografi — mata kuliah Keamanan Informasi, Program
Studi Informatika, Universitas Siliwangi.

Topik: **D. Aplikasi Digital Signature**

## Anggota Kelompok

| Nama | NPM |
|---|---|
| _Mochamad Fariz Arkan Nugraha_ | _247006111017_ |
| _Kamila Zahra Ridwan_ | _247006111161_ |
| _Mochammad Fasha Ajvikri_ | _247006111178_ |

## Fitur

- Pembangkitan pasangan kunci **RSA-2048** per penandatangan, disimpan
  **terenkripsi** di disk (bukan di kode sumber, bukan hanya di memori).
- Tanda tangan atas hash **SHA-256** dokumen PDF memakai skema **RSA-PSS**.
- Metadata & signature ditempel ke PDF dalam bentuk **QR-Code**
  (nama, jabatan, institusi, tanggal, hash, signature, dan public key
  penandatangan).
- Verifikasi otomatis menolak dokumen yang isinya berubah (tamper) atau
  yang diverifikasi dengan kunci yang tidak cocok.
- **Multi-signer**: satu dokumen bisa ditandatangani lebih dari satu
  orang secara berurutan — tiap tanda tangan independen dengan kunci
  masing-masing, ditempel sebagai QR terpisah.

## Struktur Proyek

```
app.py                      Aplikasi web Flask (endpoint sign & verify)
crypto_core/signer.py       Fungsi inti: hash, sign, verify, kelola key
pdf_handler/embed_pdf.py    Menempelkan QR-Code ke halaman PDF
pdf_handler/extract_qr.py   Mengekstrak & membaca semua QR dari PDF
templates/index.html        Antarmuka web
tests/test_crypto_core.py   Unit test otomatis (lihat bagian Testing)
uji_temper/                 Skrip pengujian keamanan (tamper, kunci
                             salah, QR palsu, performa)
keys/                       Private key tiap penandatangan (dibuat
                             otomatis, TIDAK ikut ter-commit ke GitHub)
```

## Instalasi

1. Clone repo ini dan masuk ke foldernya:
   ```bash
   git clone https://github.com/FasAzz/TugasKripto_DigitalSignature.git
   cd TugasKripto_DigitalSignature
   ```

2. (Opsional tapi disarankan) buat virtual environment:
   ```bash
   python -m venv venv
   venv\Scripts\activate      # Windows
   source venv/bin/activate   # macOS/Linux
   ```

3. Install semua dependency:
   ```bash
   pip install -r requirements.txt
   ```

4. Buat file `.env` di root folder (sejajar `app.py`), isi dengan
   passphrase bebas untuk mengenkripsi private key:
   ```
   PRIVATE_KEY_PASSPHRASE=ganti-dengan-passphrase-rahasiamu-sendiri
   ```
   File `.env` ini **jangan pernah di-commit** ke GitHub (sudah masuk
   `.gitignore`).

## Menjalankan Aplikasi

```bash
python app.py
```

Buka browser ke `http://127.0.0.1:5000`.

## Cara Pakai

**Menandatangani dokumen (tab "Tandatangani"):**
1. Isi **ID Penandatangan** — pengenal singkat untuk kunci kriptografi
   milikmu sendiri, misalnya `anggota1` atau `fasha`. ID yang sama akan
   selalu memakai key pair yang sama setiap kali dipakai.
2. Isi nama, jabatan, dan institusi (ini yang tampil sebagai metadata,
   bukan bagian dari kunci kriptografi).
3. Unggah berkas PDF, klik **Tandatangani dokumen**, lalu unduh hasilnya.
4. Untuk menambahkan penandatangan kedua/ketiga pada dokumen yang sama,
   unggah ulang **hasil unduhan tadi** di tab yang sama dengan ID
   penandatangan yang berbeda — QR baru akan ditambahkan tanpa
   menghapus QR sebelumnya.

**Memverifikasi dokumen (tab "Verifikasi"):**
1. Unggah berkas PDF yang ingin diperiksa.
2. Klik **Verifikasi keaslian**. Sistem akan membaca semua QR yang ada
   dan menampilkan status tiap penandatangan (VALID/MODIFIED).

## Testing

**Unit test otomatis** (fungsi inti: hash, sign, verify, tamper, kunci
salah, key persistence, embed/ekstrak QR):
```bash
python -m unittest discover -s tests -v
```

**Skrip pengujian keamanan** (jalankan dari folder root, satu per satu):
```bash
python uji_temper/tamper.py           # uji tamper 1 byte
python uji_temper/uji_kunci_salah.py  # uji verifikasi dgn kunci salah
python uji_temper/buat_qr_palsu.py    # uji QR-Code yang dipalsukan
python uji_temper/uji_performa.py     # waktu eksekusi 30x & ukuran signature/key
                                       # -> menghasilkan Data_Pengujian.xlsx
```

## Catatan Keamanan

- Private key setiap penandatangan disimpan di `keys/<id>.pem`,
  **dienkripsi** memakai passphrase dari `.env` (format PKCS8 +
  `BestAvailableEncryption`). Folder `keys/` dan file `.env` **tidak**
  ikut ter-commit ke repositori (lihat `.gitignore`).
- Public key tiap penandatangan ditempel langsung di dalam QR-nya
  masing-masing, sehingga verifikasi tidak bergantung pada akses ke
  file `keys/` di komputan manapun.
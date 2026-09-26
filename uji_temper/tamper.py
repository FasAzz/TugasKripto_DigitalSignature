import shutil

file_asli = "signed_tugas_baru.pdf"
file_tamper = "signed_tugas_baru_tamper.pdf"

# 1. Salin dulu, jangan langsung ubah file aslinya
shutil.copy(file_asli, file_tamper)

# 2. Buka dalam mode BINARY (rb/wb), ini WAJIB, jangan mode teks biasa
with open(file_tamper, "rb") as f:
    data = bytearray(f.read())

# 3. Pilih posisi byte yang mau diubah, aman-nya di tengah file
#    (hindari 200 byte pertama, biasanya itu header PDF yang sensitif)
posisi = len(data) // 2
data[posisi] = data[posisi] ^ 0xFF   # balik semua bit di byte itu

# 4. Simpan hasil tamper-nya
with open(file_tamper, "wb") as f:
    f.write(data)

print(f"Selesai. 1 byte diubah di posisi {posisi} dari total {len(data)} byte.")
print(f"File hasil tamper: {file_tamper}")
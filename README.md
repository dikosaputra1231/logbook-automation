# ISPLA - IPB Student Portal Logbook Automation

ISPLA (IPB Student Portal Logbook Automation) adalah skrip berbasis Python dan Selenium yang berfungsi untuk mengotomatisasi pengisian Logbook Aktivitas (seperti MBKM, Kampus Merdeka, dll.) di situs Student Portal IPB.

Dengan menggunakan ISPLA, Anda hanya perlu merapikan data kegiatan Anda di dalam file Excel/CSV, dan membiarkan bot secara otomatis mengisi form satu per satu di website, termasuk mengunggah file dokumentasi/sertifikat kegiatan.

##  Fitur Utama
- **Automasi Pengisian Form:** Otomatis mengisi tanggal, jam, jenis kegiatan, tipe penyelenggaraan, lokasi, dan keterangan.
- **Auto Upload Bukti:** Mendukung pengunggahan file bukti/dokumentasi (gambar/jpg/jpeg) yang sesuai dengan kegiatan.
- **Manual Login:** Skrip akan membuka browser dan mempersilakan Anda login menggunakan SSO IPB dengan aman, setelah itu skrip akan mengambil alih untuk pengisian form.
- **Filter Baris (CLI):** Anda bisa memilih untuk hanya memproses baris tertentu di CSV atau melanjutkan dari baris yang terputus.

---

##  Prasyarat (Prerequisites)
Sebelum menjalankan proyek ini, pastikan Anda telah memiliki:
1. **Python 3.8+** terinstal di komputer.
2. Browser **Google Chrome** versi terbaru.
3. Git (Opsional, untuk clone repository).

---

##  Cara Instalasi & Persiapan

1. **Clone Repository (Atau Download ZIP)**
   ```bash
   git clone https://github.com/USERNAME_ANDA/ipb-logbook-automation.git
   cd "ipb-logbook-automation"
   ```

2. **Buat Virtual Environment (Sangat Disarankan)**
   ```bash
   python -m venv .venv
   
   # Untuk pengguna Windows:
   .venv\Scripts\activate
   # Untuk pengguna Mac/Linux:
   source .venv/bin/activate
   ```

3. **Install Dependensi Library**
   ```bash
   pip install -r requirements.txt
   ```

4. **Siapkan Konfigurasi `.env`**
   Salin file template konfigurasi menjadi `.env`:
   *(File `.env` otomatis disembunyikan oleh `.gitignore` sehingga tidak akan ter-upload ke publik)*
   - Ubah nama file `.env.example` menjadi `.env`.
   - Buka `.env` lalu sesuaikan `CSV_FILE` dengan nama file CSV logbook Anda.
   - Sesuaikan `LOGBOOK_URL` dengan link/URL halaman form input logbook Anda di portal.

---

##  Persiapan Data CSV

Skrip ini membaca data dari file CSV. Anda harus membuat file CSV (atau menyimpannya dari Microsoft Excel/Google Sheets) di dalam folder `data logbook/`.

Pastikan header/nama kolom di baris pertama **sama persis** dengan ketentuan berikut (penulisan header pada CSV bebas besar/kecil):
- `no`: Nomor urut baris.
- `tanggal`: Tanggal kegiatan (Format: `DD/MM/YYYY`, misal: `25/08/2024`).
- `waktu_mulai`: Waktu mulai (Format: `HH:MM`, misal: `08:00`).
- `waktu_selesai`: Waktu selesai (Format: `HH:MM`, misal: `16:00`).
- `jenis_kegiatan`: ID/Teks Jenis kegiatan.
- `tipe`: "Online" atau "Offline".
- `lokasi`: Tempat kegiatan berlangsung.
- `keterangan`: Rangkuman/deskripsi aktivitas.
- `doc_path`: (Opsional) Nama file foto/bukti. Harus berada di folder yang sama (`data logbook`). Biarkan kosong jika tidak ada bukti.

*(Lihat contoh file excel yang ada di folder data logbook jika Anda bingung).*

---

##  Cara Menggunakan

1. **Jalankan Skrip Utama:**
   ```bash
   python main.py
   ```
2. **Login Mandiri:** Browser Chrome akan terbuka secara otomatis. Lakukan Login SSO IPB dan navigasikan ke halaman logbook Anda.
3. **Konfirmasi Lanjut:** Setelah halaman logbook siap, kembali ke layar terminal/command prompt, lalu tekan **ENTER**.
4. **Otomatisasi Berjalan:** Bot akan mulai mengisikan seluruh form sesuai isi file CSV Anda. Biarkan bot bekerja.

###  Mode CLI (Advanced)
Jika Anda hanya ingin mencoba-coba atau meneruskan data yang sempat terputus, Anda bisa menggunakan perintah tambahan berikut:

- **Tes baca data tanpa buka browser (Dry Run):**
  ```bash
  python main.py --dry-run
  ```
- **Hanya memproses baris tertentu (misal baris 1, 3, dan 5):**
  ```bash
  python main.py --rows 1,3,5
  ```
- **Melanjutkan proses mulai dari baris ke-10:**
  ```bash
  python main.py --start 10
  ```
- **Menggunakan CSV logbook lain (tanpa ubah `.env`):**
  ```bash
  python main.py --csv "data logbook/logbook2.csv"
  ```

---

## Keamanan & Privasi
- File konfigurasi rahasia (`.env`) dan folder penyimpan data pribadi (`data logbook/`) sudah diatur di `.gitignore` agar tidak ikut terunggah (ter-push) ke GitHub.
- Pastikan Anda tidak pernah meng-commit file kredensial atau foto data pribadi ke dalam repository publik.

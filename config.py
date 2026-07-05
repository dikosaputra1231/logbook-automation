# ============================================================
#  config.py — Konfigurasi global dan konstanta proyek ISPLA
#
#  PANDUAN KONFIGURASI:
#  1. Salin ".env.example" menjadi ".env"
#  2. Isi nilai di ".env" sesuai akun dan portal Anda
#  3. Sesuaikan MAPPING di bawah ini jika elemen form berbeda
# ============================================================

import os
from pathlib import Path
from dotenv import load_dotenv

# Muat variabel dari file .env
load_dotenv()

# ===========================================================
# SECTION 1: PATHS
# ===========================================================

# Root folder proyek (folder tempat config.py berada)
PROJECT_ROOT = Path(__file__).parent.resolve()

# Folder file dokumentasi (relatif ke PROJECT_ROOT atau path absolut)
_docs_folder_env = os.getenv("DOCS_FOLDER", "data logbook")
DOCS_FOLDER = Path(_docs_folder_env) if Path(_docs_folder_env).is_absolute() else PROJECT_ROOT / _docs_folder_env

# File CSV logbook
_csv_file_env = os.getenv("CSV_FILE", "Logbook GAN 2024 V2 - Sheet1.csv")
CSV_FILE = Path(_csv_file_env) if Path(_csv_file_env).is_absolute() else DOCS_FOLDER / _csv_file_env

# File log output
LOG_FILE = PROJECT_ROOT / "automation.log"

# ===========================================================
# SECTION 2: KREDENSIAL
# ===========================================================

IPB_USERNAME = os.getenv("IPB_USERNAME", "")
IPB_PASSWORD = os.getenv("IPB_PASSWORD", "")

# ===========================================================
# SECTION 3: URL PORTAL
# ===========================================================

PORTAL_BASE_URL = os.getenv("PORTAL_URL", "https://studentportal.ipb.ac.id")

# URL halaman login (sesuaikan jika pakai SSO/CAS)
LOGIN_URL = f"{PORTAL_BASE_URL}/Account/Login"

# URL halaman logbook aktivitas kampus merdeka — bisa diatur via .env (LOGBOOK_URL)
LOGBOOK_URL = os.getenv("LOGBOOK_URL", f"{PORTAL_BASE_URL}/Kegiatan/LogAktivitasKampusMerdeka")

# ===========================================================
# SECTION 4: PENGATURAN BROWSER
# ===========================================================

# True = browser berjalan di background (tanpa tampilan)
HEADLESS = os.getenv("HEADLESS", "false").lower() == "true"

# Timeout (detik) untuk Explicit Waits
WAIT_TIMEOUT = int(os.getenv("WAIT_TIMEOUT", "20"))

# ===========================================================
# SECTION 5: MAPPING DATA CSV → FORM PORTAL
# ===========================================================

# --- Jenis Kegiatan ---
# Kunci = nilai di kolom CSV, Nilai = teks opsi di dropdown portal
# ⚠️  PERLU DIKONFIRMASI: Sesuaikan dengan opsi dropdown aktual
JENIS_KEGIATAN_MAP = {
    "1": "Berita Acara Pembimbingan (Konsultasi/Mentoring/Coaching)",
    "2": "Berita Acara Ujian",
    "3": "Berita Acara Kegiatan",
}
# --- Tipe Penyelenggaraan ---
# Nilai di CSV: "Offline" atau "Online"
# Sesuaikan dengan label radio button/dropdown di portal
TIPE_PENYELENGGARAAN_MAP = {
    "Offline": "Offline",
    "Online":  "Online",
    "Daring":  "Online",
    "Luring":  "Offline",
}

# ===========================================================
# SECTION 6: PENGATURAN FORM
# ===========================================================

# Apakah checkbox "Dosen Penggerak" selalu dicentang?
DOSEN_PENGGERAK_CHECKED = True

# Format tanggal yang diterima oleh input form portal
DATE_FORMAT_OUTPUT = "%d/%m/%Y"

# Format waktu yang diterima oleh input form portal ("HH:MM")
TIME_FORMAT_OUTPUT = "%H:%M"

# ===========================================================
# SECTION 7: SELECTOR HTML (CSS/XPath)
# ===========================================================

SELECTORS = {
    # Halaman Login
    "login_username":       'input[name="Username"], input[id="Username"]',
    "login_password":       'input[name="Password"], input[id="Password"]',
    "login_submit":         'button[type="submit"], input[type="submit"]',

    # Indikator login berhasil (elemen yang muncul setelah login)
    "post_login_indicator": '.navbar-user, .user-info, #user-menu',

    # Tombol "Tambah" untuk membuka form baru
    # HTML: <a class="btn btn-default btn-tool" onclick="OpenModal(...)">
    "btn_tambah":           'a.btn-tool, a.btn-default.btn-tool',

    # Field form logbook (Berdasarkan HTML Inspect)
    "field_tanggal":        'input[id="Waktu"]',
    "field_waktu_mulai":    'input[id="Tmw"]',
    "field_waktu_selesai":  'input[id="Tsw"]',
    "field_lokasi":         'input[name="Lokasi"], input[id="Lokasi"], input[name="lokasi"]',
    "field_keterangan":     'textarea[name="Keterangan"], textarea[id="Keterangan"], textarea[name="Topik"], input[name="Keterangan"]',

    # Dropdown Jenis Kegiatan
    "dropdown_jenis":       'select[id="JenisLogbookKegiatanKampusMerdekaId"]',

    # Radio/Dropdown Tipe Penyelenggaraan
    "radio_tipe":           'input[type="radio"][name="TipePenyelenggaraan"], input[type="radio"][name*="Tipe"]',
    "dropdown_tipe":        'select[name="TipePenyelenggaraan"]',

    # Checkbox Dosen Penggerak
    "checkbox_dosen":       'input[id="ListDosenPembimbing_0__Value"], input[name="ListDosenPembimbing[0].Value"]',

    # Upload file Bukti Aktivitas
    "input_file":           'input[type="file"]',

    # Tombol Simpan
    # HTML: <input type="submit" value="Simpan" class="btn btn-primary btn-flat">
    "btn_simpan":           'input[type="submit"][value="Simpan"], input[type="submit"].btn-primary',

    # Konfirmasi sukses
    "success_indicator":    '.alert-success, .toast-success, .swal2-success',
}

# ===========================================================
# SECTION 8: VALIDASI KONFIGURASI
# ===========================================================

def validate_config() -> list[str]:
    """
    Validasi konfigurasi sebelum skrip dijalankan.
    Mengembalikan list pesan error (kosong = semua OK).
    """
    errors = []

    if not IPB_USERNAME:
        errors.append("IPB_USERNAME belum diisi di file .env")
    if not IPB_PASSWORD:
        errors.append("IPB_PASSWORD belum diisi di file .env")
    if not DOCS_FOLDER.exists():
        errors.append(f"Folder dokumentasi tidak ditemukan: {DOCS_FOLDER}")
    if not CSV_FILE.exists():
        errors.append(f"File CSV tidak ditemukan: {CSV_FILE}")

    return errors

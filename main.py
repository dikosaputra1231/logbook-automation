# ============================================================
#  main.py — Entry point & orkestrasi alur kerja ISPLA
#
#  Cara penggunaan:
#    python main.py              → Jalankan automasi penuh
#    python main.py --dry-run    → Hanya parsing CSV, tanpa buka browser
#    python main.py --rows 1,3   → Hanya proses baris nomor 1 dan 3
# ============================================================

from __future__ import annotations

import sys
import time
import argparse
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from webdriver_manager.chrome import ChromeDriverManager

from config import (
    HEADLESS,
    WAIT_TIMEOUT,
    validate_config,
    PROJECT_ROOT,
)
from logger_setup import logger
from data_parser import load_records

from form_handler import navigate_to_logbook, submit_record


# ===========================================================
# INISIALISASI BROWSER
# ===========================================================

def init_driver() -> webdriver.Chrome:
    """
    Inisialisasi Chrome WebDriver dengan pengaturan optimal.

    webdriver-manager otomatis mengunduh ChromeDriver yang sesuai
    dengan versi Chrome yang terinstall — tidak perlu download manual.

    Returns:
        Objek WebDriver Chrome yang siap digunakan
    """
    options = ChromeOptions()

    if HEADLESS:
        options.add_argument("--headless=new")
        logger.info("Mode: Headless (browser tersembunyi)")
    else:
        logger.info("Mode: Headed (browser terlihat)")

    # Pengaturan umum untuk stabilitas
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--window-size=1366,768")
    options.add_argument("--lang=id-ID")

    # Sembunyikan tanda "otomatis dikontrol" dari browser
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    # Set folder download default (untuk keperluan masa depan)
    prefs = {
        "download.default_directory": str(PROJECT_ROOT / "downloads"),
        "profile.default_content_setting_values.notifications": 2,
    }
    options.add_experimental_option("prefs", prefs)

    logger.info("Menginisialisasi Chrome WebDriver...")
    driver = webdriver.Chrome(
        service=ChromeService(ChromeDriverManager().install()),
        options=options,
    )
    driver.implicitly_wait(3)  # Implicit wait dasar (Explicit Wait dipakai di modul lain)
    return driver


# ===========================================================
# ARGUMENT PARSER
# ===========================================================

def parse_args() -> argparse.Namespace:
    """Parse argumen command line."""
    parser = argparse.ArgumentParser(
        description="ISPLA — IPB Student Portal Logbook Automation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Contoh penggunaan:
  python main.py                          Jalankan semua baris di CSV default
  python main.py --dry-run                Hanya tampilkan data CSV tanpa buka browser
  python main.py --rows 1,2,3             Hanya proses baris No. 1, 2, dan 3
  python main.py --start 3               Mulai dari baris No. 3 hingga selesai
  python main.py --csv "data logbook/Logbook2.csv"  Ganti file CSV
  python main.py --url "https://..."      Ganti URL halaman logbook
        """,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse CSV dan tampilkan data tanpa membuka browser",
    )
    parser.add_argument(
        "--rows",
        type=str,
        default=None,
        help="Proses hanya nomor baris tertentu (dipisah koma). Contoh: --rows 1,3,5",
    )
    parser.add_argument(
        "--start",
        type=int,
        default=None,
        help="Mulai dari nomor baris ini (inklusif). Contoh: --start 3",
    )
    parser.add_argument(
        "--csv",
        type=str,
        default=None,
        help="Path ke file CSV logbook. Contoh: --csv \"data logbook/Logbook2.csv\"",
    )
    parser.add_argument(
        "--url",
        type=str,
        default=None,
        help="URL halaman logbook di portal IPB. Contoh: --url \"https://studentportal.ipb.ac.id/...\"",
    )
    return parser.parse_args()


# ===========================================================
# FILTER RECORDS
# ===========================================================

def filter_records(records: list[dict], args: argparse.Namespace) -> list[dict]:
    """
    Filter record berdasarkan argumen --rows atau --start.

    Args:
        records: Semua record dari data_parser
        args:    Parsed argumen dari command line

    Returns:
        List record yang sudah difilter
    """
    if args.rows:
        target_nos = {no.strip() for no in args.rows.split(",")}
        filtered = [r for r in records if str(r["no"]) in target_nos]
        logger.info(f"Filter --rows: {len(filtered)} dari {len(records)} record dipilih")
        return filtered

    if args.start is not None:
        filtered = [r for r in records if int(r["no"]) >= args.start]
        logger.info(f"Filter --start {args.start}: {len(filtered)} dari {len(records)} record dipilih")
        return filtered

    return records


# ===========================================================
# ENTRY POINT UTAMA
# ===========================================================

def main() -> None:
    args = parse_args()

    # --- Override CSV/URL dari argumen command line jika diberikan ---
    import config
    if args.csv:
        csv_path = Path(args.csv)
        if not csv_path.is_absolute():
            csv_path = config.PROJECT_ROOT / args.csv
        config.CSV_FILE = csv_path
        logger.info(f"[Override] File CSV: {csv_path}")
    if args.url:
        config.LOGBOOK_URL = args.url
        logger.info(f"[Override] URL Logbook: {args.url}")

    # --- Banner ---
    print("\n" + "="*65)
    print("  [ISPLA] - IPB Student Portal Logbook Automation")
    print(f"  CSV : {config.CSV_FILE.name}")
    print("="*65 + "\n")

    # --- Validasi konfigurasi (kecuali dry-run) ---
    if not args.dry_run:
        errors = validate_config()
        if errors:
            logger.error("Konfigurasi tidak valid:")
            for e in errors:
                logger.error(f"  ✗ {e}")
            logger.error("\nSilakan periksa file .env dan config.py, lalu coba lagi.")
            sys.exit(1)

    # --- Baca & parse CSV ---
    records = load_records()
    if not records:
        logger.error("Tidak ada record valid untuk diproses. Program berhenti.")
        sys.exit(1)

    # --- Filter records ---
    records = filter_records(records, args)
    if not records:
        logger.error("Tidak ada record yang sesuai filter. Program berhenti.")
        sys.exit(1)

    # ===========================================================
    # MODE DRY-RUN: Hanya tampilkan data, tanpa browser
    # ===========================================================
    if args.dry_run:
        print(f"\n{'-'*65}")
        print(f"  DRY-RUN: {len(records)} record akan diproses")
        print(f"{'-'*65}\n")
        for i, rec in enumerate(records, 1):
            print(f"  [{i:02d}] No.{rec['no']:>3} | {rec['tanggal']} | "
                  f"{rec['waktu_mulai']}-{rec['waktu_selesai']}")
            print(f"        Jenis: {rec['jenis_kegiatan']} | "
                  f"Tipe: {rec['tipe']} | Lokasi: {rec['lokasi']}")
            print(f"        Ket  : {rec['keterangan'][:60]}"
                  f"{'...' if len(rec['keterangan']) > 60 else ''}")
            print(f"        File : {rec['doc_path'] or '(tidak ada)'}")
            print()
        print("\n  [OK] Dry-run selesai. Tidak ada data yang dikirim ke portal.")
        return

    # ===========================================================
    # MODE AUTOMASI PENUH
    # ===========================================================
    driver = None
    results = {"success": [], "failed": [], "skipped": []}

    try:
        # --- Inisialisasi browser ---
        driver = init_driver()
        
        # Buka halaman awal portal agar pengguna tidak perlu mengetik URL
        from config import LOGBOOK_URL, PORTAL_BASE_URL
        driver.get(LOGBOOK_URL)

        # --- Login & Navigasi Manual ---
        logger.info("\n" + "="*50)
        logger.info("BROWSER TELAH DIBUKA. SILAKAN LAKUKAN MANUAL:")
        logger.info(f"1. Login ke Student Portal di Chrome.")
        logger.info("2. Navigasi / klik menu menuju halaman Logbook.")
        logger.info("3. Jika Anda SUDAH berada di halaman Logbook, kembali ke terminal ini.")
        logger.info("="*50 + "\n")
        
        input("[TEKAN ENTER DI SINI JIKA HALAMAN LOGBOOK SUDAH TERBUKA]...")
        
        logger.info("\nMelanjutkan skrip otomatis...")

        # --- Loop setiap record ---
        logger.info(f"\nMemulai pengisian {len(records)} logbook...\n")
        print(f"{'-'*65}")

        for i, record in enumerate(records, 1):
            row_no = record["no"]
            logger.info(f"[{i}/{len(records)}] Memproses No. {row_no}...")

            try:
                success = submit_record(driver, record)
                if success:
                    results["success"].append(row_no)
                else:
                    results["failed"].append(row_no)
                    logger.error(
                        f"[No. {row_no}] Gagal submit — melanjutkan ke record berikutnya"
                    )

            except Exception as exc:
                # Tangkap error tak terduga — log dan lanjutkan (tidak crash)
                results["failed"].append(row_no)
                logger.error(
                    f"[No. {row_no}] Error tidak terduga: {type(exc).__name__}: {exc} "
                    f"— melanjutkan ke record berikutnya"
                )
                # Muat ulang halaman logbook sebelum record berikutnya
                try:
                    navigate_to_logbook(driver, None)
                    time.sleep(2)
                except Exception:
                    pass

            # Jeda kecil antar record
            time.sleep(1)

    except KeyboardInterrupt:
        logger.warning("\n[!] Program dihentikan oleh pengguna (Ctrl+C)")
    finally:
        # --- Tutup browser ---
        if driver:
            driver.quit()
            logger.debug("Browser ditutup")

    # ===========================================================
    # LAPORAN AKHIR
    # ===========================================================
    total = len(records)
    ok    = len(results["success"])
    fail  = len(results["failed"])

    print(f"\n{'='*65}")
    print(f"  [LAPORAN AKHIR]")
    print(f"{'='*65}")
    print(f"  Total diproses  : {total}")
    print(f"  [OK] Berhasil   : {ok}")
    print(f"  [X] Gagal       : {fail}")

    if results["success"]:
        print(f"\n  Berhasil  -> No. {', '.join(str(n) for n in results['success'])}")
    if results["failed"]:
        print(f"  Gagal     -> No. {', '.join(str(n) for n in results['failed'])}")

    print(f"\n  Detail log tersimpan di: {PROJECT_ROOT / 'automation.log'}")
    print(f"{'='*65}\n")

    if fail > 0:
        sys.exit(1)  # Exit code 1 jika ada yang gagal


if __name__ == "__main__":
    main()

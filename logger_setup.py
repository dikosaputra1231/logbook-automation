# ============================================================
#  logger_setup.py — Konfigurasi logging untuk proyek ISPLA
#
#  Output:
#  - Terminal: pesan berwarna dengan timestamp
#  - File: automation.log (di folder proyek)
# ============================================================

import logging
import sys
from pathlib import Path
from config import LOG_FILE

# ===========================================================
# ANSI Color Codes untuk terminal (Windows 10+ mendukung ini)
# ===========================================================

class ColorFormatter(logging.Formatter):
    """Formatter dengan warna ANSI untuk output terminal."""

    COLORS = {
        logging.DEBUG:    "\033[0;36m",   # Cyan
        logging.INFO:     "\033[0;32m",   # Hijau
        logging.WARNING:  "\033[0;33m",   # Kuning
        logging.ERROR:    "\033[0;31m",   # Merah
        logging.CRITICAL: "\033[1;31m",   # Merah tebal
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelno, self.RESET)
        record.levelname = f"{color}{record.levelname:<8}{self.RESET}"
        return super().format(record)


def setup_logger(name: str = "ISPLA") -> logging.Logger:
    """
    Membuat dan mengkonfigurasi logger dengan dua handler:
    - StreamHandler → terminal (dengan warna)
    - FileHandler   → automation.log (tanpa warna)

    Args:
        name: Nama logger (default: "ISPLA")

    Returns:
        Logger yang sudah dikonfigurasi
    """
    logger = logging.getLogger(name)

    # Hindari duplikasi handler jika setup_logger dipanggil berkali-kali
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    fmt_str      = "[%(asctime)s] %(levelname)s %(message)s"
    date_fmt_str = "%Y-%m-%d %H:%M:%S"

    # --- Handler 1: Terminal (berwarna) ---
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(logging.INFO)
    stream_handler.setFormatter(
        ColorFormatter(fmt=fmt_str, datefmt=date_fmt_str)
    )

    # --- Handler 2: File log (tanpa warna) ---
    log_path = Path(LOG_FILE)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        logging.Formatter(fmt=fmt_str, datefmt=date_fmt_str)
    )

    logger.addHandler(stream_handler)
    logger.addHandler(file_handler)

    return logger


# Logger siap pakai — import dari modul lain
logger = setup_logger()

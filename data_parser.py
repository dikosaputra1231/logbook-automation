# ============================================================
#  data_parser.py — Pembaca & validator file CSV logbook
#
#  Fungsi utama:
#  - Membaca file CSV dengan pandas
#  - Membersihkan dan memvalidasi setiap baris
#  - Konversi format tanggal dan waktu
#  - Mengembalikan list of dict siap pakai untuk form_handler
# ============================================================

from __future__ import annotations

import re
from pathlib import Path
from datetime import datetime
from typing import Optional

import pandas as pd

from config import (
    CSV_FILE,
    DOCS_FOLDER,
    DATE_FORMAT_OUTPUT,
    TIME_FORMAT_OUTPUT,
    JENIS_KEGIATAN_MAP,
    TIPE_PENYELENGGARAAN_MAP,
)
from logger_setup import logger


# ===========================================================
# INTERNAL HELPERS
# ===========================================================

def _parse_time(raw: str, row_num: int, field_name: str) -> Optional[str]:
    """
    Konversi waktu dari format CSV ("HH.MM" atau "HH:MM")
    ke format yang diterima form ("HH:MM").

    Args:
        raw:        Nilai mentah dari CSV
        row_num:    Nomor baris untuk pesan error
        field_name: Nama field untuk pesan error

    Returns:
        String waktu "HH:MM" atau None jika gagal diparse
    """
    raw = str(raw).strip()
    # Ganti titik dengan titik dua: "19.00" → "19:00"
    normalized = re.sub(r'[.\-]', ':', raw)

    for fmt in ("%H:%M", "%H:%M:%S"):
        try:
            t = datetime.strptime(normalized, fmt)
            return t.strftime(TIME_FORMAT_OUTPUT)
        except ValueError:
            continue

    logger.warning(
        f"[Baris {row_num}] Gagal parse {field_name}: '{raw}' — baris dilewati untuk field ini"
    )
    return None


def _parse_date(raw: str, row_num: int) -> Optional[str]:
    """
    Konversi tanggal dari format CSV ke format output yang dikonfigurasi.

    Mendukung format input:
    - "DD/MM/YYYY"  (contoh: "09/09/2024")
    - "DD-MM-YYYY"
    - "YYYY-MM-DD"
    - "D/M/YYYY" (tanpa leading zero)

    Args:
        raw:     Nilai mentah dari CSV
        row_num: Nomor baris untuk pesan error

    Returns:
        String tanggal terformat atau None jika gagal
    """
    raw = str(raw).strip().replace("//", "/")
    input_formats = [
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%Y-%m-%d",
        "%d/%m/%y",
        "%d-%m-%y",
        "%m/%d/%Y",
        "%m-%d-%Y",
    ]
    for fmt in input_formats:
        try:
            d = datetime.strptime(raw, fmt)
            return d.strftime(DATE_FORMAT_OUTPUT)
        except ValueError:
            continue

    logger.warning(
        f"[Baris {row_num}] Gagal parse tanggal: '{raw}' — baris dilewati"
    )
    return None


def _resolve_doc_path(filename: str, row_num: int) -> Optional[Path]:
    """
    Temukan path absolut file dokumentasi.

    Args:
        filename: Nama file dari CSV (contoh: "Sertif_GAN.jpeg")
        row_num:  Nomor baris untuk pesan error

    Returns:
        Path absolut jika file ditemukan, None jika tidak ada
    """
    if not filename or str(filename).strip().lower() in ("", "nan", "none"):
        logger.warning(f"[Baris {row_num}] Tidak ada file dokumentasi — upload dilewati")
        return None

    filename = str(filename).strip()
    candidate = DOCS_FOLDER / filename

    if candidate.exists():
        return candidate.resolve()

    # Coba case-insensitive search di folder yang sama
    try:
        # Coba cocokkan nama dengan ekstensi terlebih dahulu (case-insensitive)
        matches = [
            f for f in DOCS_FOLDER.iterdir()
            if f.name.lower() == filename.lower()
        ]
        
        # Jika gagal, coba cocokkan HANYA nama tanpa ekstensi (Sertif_GAN.jpeg vs Sertif_GAN.jpg)
        if not matches:
            filename_stem = Path(filename).stem.lower()
            matches = [
                f for f in DOCS_FOLDER.iterdir()
                if f.is_file() and f.stem.lower() == filename_stem
            ]

        if matches:
            logger.warning(
                f"[Baris {row_num}] File ditemukan dengan nama/ekstensi berbeda: '{matches[0].name}'"
            )
            return matches[0].resolve()
    except OSError:
        pass

    logger.warning(
        f"[Baris {row_num}] File dokumentasi tidak ditemukan: '{candidate}' "
        f"— pastikan file sudah diletakkan di folder '{DOCS_FOLDER}'"
    )
    return None


def _map_jenis_kegiatan(raw: str, row_num: int) -> str:
    """
    Peta nilai kolom Jenis Kegiatan (angka/string) ke label dropdown.
    """
    key = str(raw).strip()
    mapped = JENIS_KEGIATAN_MAP.get(key)
    if mapped is None:
        logger.warning(
            f"[Baris {row_num}] Jenis Kegiatan '{key}' tidak ada di JENIS_KEGIATAN_MAP. "
            f"Menggunakan nilai asli: '{key}'"
        )
        return key
    return mapped


def _map_tipe_penyelenggaraan(raw: str, row_num: int) -> str:
    """
    Peta nilai kolom Tipe Penyelenggaraan ke label form.
    """
    key = str(raw).strip().capitalize()
    # Coba exact match, lalu case-insensitive
    mapped = TIPE_PENYELENGGARAAN_MAP.get(key) or TIPE_PENYELENGGARAAN_MAP.get(raw.strip())
    if mapped is None:
        logger.warning(
            f"[Baris {row_num}] Tipe Penyelenggaraan '{raw}' tidak ada di map. "
            f"Menggunakan nilai asli."
        )
        return raw.strip()
    return mapped


# ===========================================================
# PUBLIC API
# ===========================================================

def load_records(csv_path: Path = CSV_FILE) -> list[dict]:
    """
    Baca file CSV dan kembalikan list of dict yang sudah divalidasi.

    Setiap dict memiliki key:
    - no            (int)    : Nomor urut dari CSV
    - tanggal       (str)    : Tanggal terformat
    - waktu_mulai   (str)    : Waktu mulai "HH:MM"
    - waktu_selesai (str)    : Waktu selesai "HH:MM"
    - jenis_kegiatan (str)   : Label dropdown (sudah di-mapping)
    - lokasi        (str)    : Lokasi kegiatan
    - tipe          (str)    : "Offline" atau "Online"
    - keterangan    (str)    : Uraian kegiatan
    - doc_path      (Path|None): Path absolut file dokumentasi

    Baris yang gagal validasi field wajib akan di-skip dengan log ERROR.
    Baris yang kehilangan field opsional akan di-log WARNING dan tetap diproses.

    Returns:
        List of dicts siap pakai untuk form_handler
    """
    logger.info(f"Membaca CSV: {csv_path}")

    if not csv_path.exists():
        logger.error(f"File CSV tidak ditemukan: {csv_path}")
        return []

    try:
        df = pd.read_csv(
            csv_path,
            dtype=str,           # Baca semua kolom sebagai string
            keep_default_na=False,  # Jangan ubah kosong jadi NaN otomatis
            skipinitialspace=True,
        )
    except Exception as exc:
        logger.error(f"Gagal membaca CSV: {exc}")
        return []

    # Normalisasi nama kolom: lowercase + strip spasi
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    logger.info(f"Total baris ditemukan: {len(df)}")

    # Kolom wajib yang harus ada di CSV
    # Kita tidak wajibkan kolom spesifik lagi karena pencarian sekarang fleksibel
    # missing = required_cols - set(df.columns)

    records: list[dict] = []

    # --- Fungsi bantu untuk mencari kolom berdasarkan alias ---
    def _get_val(r, aliases: list) -> str:
        for k, v in r.items():
            k_lower = k.lower().replace(" ", "_").replace("-", "_")
            if any(a in k_lower for a in aliases):
                return str(v).strip()
        return ""

    for idx, row in df.iterrows():
        # --- Nomor Baris Asli CSV ---
        row_num = idx + 2

        # Lewati baris kosong
        if not any(str(v).strip() for v in row.values):
            continue

        raw_tanggal = _get_val(row, ["tanggal", "waktu", "date", "hari"])
        if not raw_tanggal:
            logger.error(f"[Baris {row_num}] Kolom Tanggal tidak ditemukan atau kosong — baris dilewati")
            continue

        tanggal = _parse_date(raw_tanggal, row_num)
        if tanggal is None:
            continue  # Error sudah di-log di _parse_date

        # --- Validasi & konversi Waktu ---
        waktu_mulai   = _parse_time(_get_val(row, ["mulai", "start"]),   row_num, "Waktu Mulai")
        waktu_selesai = _parse_time(_get_val(row, ["selesai", "end"]), row_num, "Waktu Selesai")

        if waktu_mulai is None or waktu_selesai is None:
            logger.error(f"[Baris {row_num}] Waktu tidak valid — baris dilewati")
            continue

        # --- Keterangan ---
        keterangan = _get_val(row, ["keterangan", "uraian", "deskripsi", "topik", "description"])
        if not keterangan:
            logger.warning(f"[Baris {row_num}] Keterangan kosong — tetap diproses")

        # --- Lokasi ---
        lokasi = _get_val(row, ["lokasi", "tempat", "location"])
        if not lokasi:
            logger.warning(f"[Baris {row_num}] Lokasi kosong — tetap diproses")

        # --- Jenis Kegiatan ---
        jenis_kegiatan = _map_jenis_kegiatan(
            _get_val(row, ["jenis_kegiatan", "jenis", "tipe_kegiatan"]), row_num
        )

        # --- Tipe Penyelenggaraan ---
        tipe_raw = _get_val(row, ["tipe_penyelenggaraan", "kehadiran", "metode", "tipe"])
        if not tipe_raw:
            tipe_raw = "Offline"
        tipe = _map_tipe_penyelenggaraan(tipe_raw, row_num)

        # --- File Dokumentasi ---
        doc_filename = _get_val(row, ["dokumentasi", "bukti", "foto", "file"])
        doc_path     = _resolve_doc_path(doc_filename, row_num)

        # --- Nomor urut ---
        no_val = _get_val(row, ["no.", "no", "nomor", "id"])
        no = str(no_val).strip() if no_val else str(row_num - 1)

        record = {
            "no":             no,
            "tanggal":        tanggal,
            "waktu_mulai":    waktu_mulai,
            "waktu_selesai":  waktu_selesai,
            "jenis_kegiatan": jenis_kegiatan,
            "lokasi":         lokasi,
            "tipe":           tipe,
            "keterangan":     keterangan,
            "doc_path":       doc_path,
        }
        records.append(record)
        logger.debug(f"[Baris {row_num}] [OK] Record parsed: {tanggal} | {waktu_mulai}-{waktu_selesai} | {lokasi}")

    logger.info(f"Total record valid: {len(records)} dari {len(df)} baris")
    return records


# ===========================================================
# MODE STANDALONE — Jalankan langsung untuk debug/dry-run
# ===========================================================

if __name__ == "__main__":
    print("\n" + "="*60)
    print("  DATA PARSER — Dry Run")
    print("="*60 + "\n")

    records = load_records()

    if not records:
        print("[!] Tidak ada record yang berhasil diparsing.")
    else:
        print(f"\n[OK] {len(records)} record berhasil diparsing:\n")
        for i, rec in enumerate(records, 1):
            print(f"  [{i:02d}] {rec['tanggal']} | {rec['waktu_mulai']}-{rec['waktu_selesai']}")
            print(f"       Jenis   : {rec['jenis_kegiatan']}")
            print(f"       Lokasi  : {rec['lokasi']} ({rec['tipe']})")
            print(f"       Ket.    : {rec['keterangan'][:60]}{'...' if len(rec['keterangan']) > 60 else ''}")
            print(f"       Dok.    : {rec['doc_path'] or '(belum ada - taruh file di folder data logbook)'}")
            print()

# ============================================================
#  form_handler.py — Navigasi ke form logbook & pengisian data
#
#  Fungsi utama:
#  - Navigasi ke halaman logbook
#  - Membuka form "Tambah" baru
#  - Mengisi semua field sesuai data dari data_parser
#  - Upload file dokumentasi
#  - Submit dan verifikasi sukses
# ============================================================

from __future__ import annotations

import time
from pathlib import Path
from typing import Optional

from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    ElementNotInteractableException,
    ElementClickInterceptedException,
)

from config import (
    LOGBOOK_URL,
    WAIT_TIMEOUT,
    SELECTORS,
    DOSEN_PENGGERAK_CHECKED,
    TIPE_PENYELENGGARAAN_MAP,
)
from logger_setup import logger


# ===========================================================
# HELPERS INTERNAL
# ===========================================================

def _wait_and_find(
    driver: WebDriver,
    wait: WebDriverWait,
    selector: str,
    description: str = "elemen",
    clickable: bool = False,
) -> Optional[object]:
    """
    Tunggu elemen muncul dan kembalikan referensinya.

    Args:
        driver:       WebDriver aktif
        wait:         WebDriverWait
        selector:     CSS selector atau XPath target elemen
        description:  Label untuk pesan log
        clickable:    Jika True, tunggu hingga elemen bisa diklik

    Returns:
        WebElement atau None jika timeout
    """
    by_type = By.XPATH if selector.startswith("//") or selector.startswith("(") else By.CSS_SELECTOR
    condition = EC.element_to_be_clickable if clickable else EC.visibility_of_element_located
    try:
        element = wait.until(condition((by_type, selector)))
        return element
    except TimeoutException:
        logger.error(f"Timeout menunggu {description}: '{selector}'")
        return None


def _safe_click(driver: WebDriver, element, description: str = "elemen") -> bool:
    """
    Klik elemen dengan aman. Coba native click, fallback ke JavaScript jika terhalang.
    """
    try:
        # Pastikan elemen ada di area layar yang terlihat
        driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'center'});", element)
        time.sleep(0.5)
        
        element.click()
        return True
    except ElementClickInterceptedException:
        logger.warning(f"Klik biasa gagal untuk {description} — mencoba via JavaScript")
        try:
            driver.execute_script("arguments[0].click();", element)
            return True
        except Exception as exc:
            logger.error(f"JavaScript click juga gagal untuk {description}: {exc}")
            return False


def _fill_text_field(driver: WebDriver, element, value: str, clear_first: bool = True) -> None:
    """Isi field teks, dengan opsional clear terlebih dahulu."""
    
    # Deteksi jika ini adalah input time/date
    is_time_input = False
    try:
        if element.get_attribute("type") == "time":
            is_time_input = True
    except:
        pass

    if not is_time_input and clear_first:
        try:
            # Cara paling ampuh menghapus isi text field biasa
            element.send_keys(Keys.CONTROL + "a")
            element.send_keys(Keys.BACKSPACE)
            time.sleep(0.1)
        except:
            pass
    
    try:
        if not is_time_input:
            # Coba ketik normal jika bukan time input
            element.send_keys(value)
            time.sleep(0.1)
    except:
        pass
        
    # Pastikan value terset secara paksa melalui JavaScript
    driver.execute_script('''
        var el = arguments[0];
        el.value = arguments[1];
        el.setAttribute('value', arguments[1]);
        el.dispatchEvent(new Event('input', { bubbles: true }));
        el.dispatchEvent(new Event('change', { bubbles: true }));
        el.dispatchEvent(new Event('blur', { bubbles: true }));
    ''', element, value)


def _select_dropdown_by_text(
    driver: WebDriver,
    wait: WebDriverWait,
    selector: str,
    text: str,
    row_no: str,
    field_name: str,
) -> bool:
    """
    Pilih opsi dropdown berdasarkan teks yang terlihat.

    Returns:
        True jika berhasil memilih
    """
    element = _wait_and_find(driver, wait, selector, f"dropdown {field_name}")
    if element is None:
        return False
    try:
        sel = Select(element)
        # Coba exact match dulu
        try:
            sel.select_by_visible_text(text)
            return True
        except Exception:
            pass
        # Coba partial match
        for option in sel.options:
            if text.lower() in option.text.lower():
                sel.select_by_visible_text(option.text)
                logger.warning(
                    f"[No. {row_no}] {field_name}: partial match '{option.text}' untuk '{text}'"
                )
                return True
        logger.error(
            f"[No. {row_no}] {field_name}: opsi '{text}' tidak ditemukan di dropdown. "
            f"Opsi tersedia: {[o.text for o in sel.options]}"
        )
        return False
    except Exception as exc:
        logger.error(f"[No. {row_no}] Gagal memilih dropdown {field_name}: {exc}")
        return False


def _handle_radio_or_dropdown(
    driver: WebDriver,
    wait: WebDriverWait,
    value: str,
    row_no: str,
) -> bool:
    """
    Tangani field Tipe Penyelenggaraan yang bisa berupa radio button ATAU dropdown.
    Mencoba radio button dulu, lalu fallback ke dropdown.

    Returns:
        True jika berhasil
    """
    # --- Coba Radio Button ---
    try:
        radios = driver.find_elements(By.CSS_SELECTOR, SELECTORS["radio_tipe"])
        if radios:
            for radio in radios:
                radio_val = (radio.get_attribute("value") or "").strip()
                radio_lbl = ""
                # Coba ambil label terkait
                try:
                    label = driver.find_element(
                        By.CSS_SELECTOR, f'label[for="{radio.get_attribute("id")}"]'
                    )
                    radio_lbl = label.text.strip()
                except NoSuchElementException:
                    radio_lbl = radio_val

                if value.lower() in radio_val.lower() or value.lower() in radio_lbl.lower():
                    _safe_click(driver, radio, f"radio tipe '{value}'")
                    logger.debug(f"[No. {row_no}] Radio Tipe Penyelenggaraan: '{value}' dipilih")
                    return True
            logger.warning(f"[No. {row_no}] Radio button tipe '{value}' tidak cocok")
    except Exception:
        pass

    # --- Fallback: Dropdown ---
    return _select_dropdown_by_text(
        driver, wait,
        selector=SELECTORS["dropdown_tipe"],
        text=value,
        row_no=row_no,
        field_name="Tipe Penyelenggaraan",
    )


def _upload_file(
    driver: WebDriver,
    wait: WebDriverWait,
    doc_path: Optional[Path],
    row_no: str,
) -> bool:
    """
    Upload file dokumentasi ke input[type=file].

    Returns:
        True jika berhasil atau tidak ada file (skip),
        False jika file ada tapi gagal diupload
    """
    if doc_path is None:
        logger.warning(f"[No. {row_no}] Tidak ada file dokumentasi — upload dilewati")
        return True  # Bukan error fatal, lanjut proses

    file_input = _wait_and_find(
        driver, wait, SELECTORS["input_file"], "input file upload"
    )
    if file_input is None:
        return False

    try:
        # send_keys dengan path absolut adalah cara standar upload di Selenium
        file_input.send_keys(str(doc_path))
        logger.debug(f"[No. {row_no}] File diupload: {doc_path.name}")
        time.sleep(1)  # Beri waktu untuk UI memproses file
        return True
    except Exception as exc:
        logger.error(f"[No. {row_no}] Gagal upload file '{doc_path}': {exc}")
        return False


def _handle_dosen_penggerak(driver: WebDriver, wait: WebDriverWait, row_no: str) -> None:
    """
    Centang checkbox Dosen Penggerak jika konfigurasi mengharuskan.
    """
    if not DOSEN_PENGGERAK_CHECKED:
        return

    try:
        checkbox = _wait_and_find(
            driver, wait, SELECTORS["checkbox_dosen"], "checkbox Dosen Penggerak"
        )
        if checkbox is None:
            return
        if not checkbox.is_selected():
            _safe_click(driver, checkbox, "checkbox Dosen Penggerak")
            logger.debug(f"[No. {row_no}] Checkbox Dosen Penggerak: ✓ dicentang")
        else:
            logger.debug(f"[No. {row_no}] Checkbox Dosen Penggerak sudah tercentang")
    except Exception as exc:
        logger.warning(f"[No. {row_no}] Gagal mencentang Dosen Penggerak: {exc}")


def _verify_success(driver: WebDriver, wait: WebDriverWait, row_no: str) -> bool:
    """
    Cek apakah penyimpanan berhasil (muncul indikator sukses).

    Returns:
        True jika sukses terdeteksi
    """
    # Tunggu sebentar agar jika ada alert sukses lama, ia terganti atau animasi submit selesai
    time.sleep(1.5)
    
    try:
        wait.until(
            EC.visibility_of_element_located(
                (By.CSS_SELECTOR, SELECTORS["success_indicator"])
            )
        )
        logger.info(f"[No. {row_no}] ✓ Logbook berhasil disimpan")
        return True
    except TimeoutException:
        logger.warning(
            f"[No. {row_no}] Indikator sukses tidak terdeteksi — "
            f"periksa halaman secara manual. URL: {driver.current_url}"
        )
        return False


# ===========================================================
# NAVIGASI
# ===========================================================

def navigate_to_logbook(driver: WebDriver, wait: WebDriverWait) -> bool:
    """
    Navigasi ke halaman logbook aktivitas.

    Returns:
        True jika berhasil membuka halaman
    """
    logger.info(f"Navigasi ke halaman logbook: {LOGBOOK_URL}")
    try:
        driver.get(LOGBOOK_URL)
        time.sleep(2)
        logger.debug(f"URL saat ini: {driver.current_url}")
        return True
    except Exception as exc:
        logger.error(f"Gagal navigasi ke halaman logbook: {exc}")
        return False


# ===========================================================
# PUBLIC API — SUBMIT SATU RECORD
# ===========================================================

def submit_record(driver: WebDriver, record: dict) -> bool:
    """
    Submit satu record logbook ke form portal.

    Alur:
    1. Klik tombol "Tambah" untuk buka form
    2. Isi semua field form
    3. Upload dokumentasi
    4. Klik "Simpan" & verifikasi

    Args:
        driver: WebDriver aktif (sudah login)
        record: Dict dari data_parser.load_records()

    Returns:
        True jika seluruh proses berhasil
    """
    row_no = record.get("no", "?")
    wait   = WebDriverWait(driver, WAIT_TIMEOUT)

    logger.info(
        f"[No. {row_no}] Memulai submit: {record['tanggal']} | "
        f"{record['waktu_mulai']}–{record['waktu_selesai']} | {record['lokasi']}"
    )

    # --- Step 1: Cek apakah form sudah terbuka (opsional klik Tambah) ---
    # Cek cepat (2 detik) apakah field tanggal sudah ada di layar
    form_already_open = False
    try:
        quick_wait = WebDriverWait(driver, 2)
        quick_wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, SELECTORS["field_tanggal"])))
        form_already_open = True
        logger.debug(f"[No. {row_no}] Form popup sudah terbuka (dilakukan manual oleh user).")
    except TimeoutException:
        pass

    if not form_already_open:
        # Jika form belum terbuka, skrip yang akan mengklik tombol Tambah
        btn_tambah = _wait_and_find(
            driver, wait, SELECTORS["btn_tambah"], "tombol Tambah", clickable=True
        )
        if btn_tambah is None:
            return False
        if not _safe_click(driver, btn_tambah, "tombol Tambah"):
            return False
        logger.debug(f"[No. {row_no}] Tombol Tambah diklik oleh skrip")
        time.sleep(1.5)  # Tunggu modal/form muncul

    # --- Step 2: Isi field Tanggal ---
    field_tanggal = _wait_and_find(
        driver, wait, SELECTORS["field_tanggal"], "field Tanggal"
    )
    if field_tanggal is None:
        return False
    _fill_text_field(driver, field_tanggal, record["tanggal"])
    logger.debug(f"[No. {row_no}] Tanggal: {record['tanggal']}")

    # --- Step 3: Isi Waktu Selesai (Diisi lebih dulu agar validasi front-end tidak me-revert Waktu Mulai) ---
    field_waktu_selesai = _wait_and_find(
        driver, wait, SELECTORS["field_waktu_selesai"], "field Waktu Selesai"
    )
    if field_waktu_selesai is None:
        return False
    _fill_text_field(driver, field_waktu_selesai, record["waktu_selesai"])
    logger.debug(f"[No. {row_no}] Waktu Selesai: {record['waktu_selesai']}")

    # --- Step 4: Isi Waktu Mulai ---
    field_waktu_mulai = _wait_and_find(
        driver, wait, SELECTORS["field_waktu_mulai"], "field Waktu Mulai"
    )
    if field_waktu_mulai is None:
        return False
    _fill_text_field(driver, field_waktu_mulai, record["waktu_mulai"])
    logger.debug(f"[No. {row_no}] Waktu Mulai: {record['waktu_mulai']}")

    # --- Step 5: Dropdown Jenis Kegiatan ---
    ok = _select_dropdown_by_text(
        driver, wait,
        selector=SELECTORS["dropdown_jenis"],
        text=record["jenis_kegiatan"],
        row_no=row_no,
        field_name="Jenis Kegiatan",
    )
    if not ok:
        logger.warning(f"[No. {row_no}] Jenis Kegiatan gagal dipilih — lanjut ke field berikutnya")

    # --- Step 6: Isi Lokasi ---
    field_lokasi = _wait_and_find(
        driver, wait, SELECTORS["field_lokasi"], "field Lokasi"
    )
    if field_lokasi is not None:
        _fill_text_field(driver, field_lokasi, record["lokasi"])
        logger.debug(f"[No. {row_no}] Lokasi: {record['lokasi']}")

    # --- Step 7: Radio Tipe Penyelenggaraan ---
    # Coba temukan semua radio button di form dan klik yang value/teks-nya cocok
    radio_success = False
    try:
        radios = driver.find_elements(By.CSS_SELECTOR, 'input[type="radio"]')
        target_val = record["tipe"].lower()
        for r in radios:
            r_val = (r.get_attribute("value") or "").lower()
            parent_text = ""
            try:
                # Cari label pembungkus jika ada
                parent_text = (r.find_element(By.XPATH, "..").text or "").lower()
            except:
                pass
            
            if target_val in r_val or target_val in parent_text:
                _safe_click(driver, r, f"radio tipe '{record['tipe']}'")
                logger.debug(f"[No. {row_no}] Radio Tipe Penyelenggaraan dipilih via HTML/Label: '{record['tipe']}'")
                radio_success = True
                break
    except Exception as e:
        logger.debug(f"[No. {row_no}] Pencarian radio gagal: {e}")

    if not radio_success:
        # --- Fallback lama jika gagal ---
        ok = _select_radio_by_text(
            driver, wait,
            selector=SELECTORS["radio_tipe"],
            value=record["tipe"],
            row_no=row_no,
        )
        if not ok:
            logger.warning(f"[No. {row_no}] Tipe Penyelenggaraan radio gagal dipilih")

    # --- Step 8: Checkbox Dosen Penggerak ---
    _handle_dosen_penggerak(driver, wait, row_no)

    # --- Step 9: Isi Keterangan ---
    field_keterangan = _wait_and_find(
        driver, wait, SELECTORS["field_keterangan"], "field Keterangan"
    )
    if field_keterangan is not None:
        _fill_text_field(driver, field_keterangan, record["keterangan"])
        logger.debug(f"[No. {row_no}] Keterangan: {record['keterangan'][:30]}...")

    # --- Step 10: Upload Dokumentasi ---
    upload_ok = _upload_file(driver, wait, record.get("doc_path"), row_no)
    if not upload_ok:
        logger.warning(f"[No. {row_no}] Upload gagal — lanjut submit tanpa file")

    # --- Step 11: Klik Simpan ---
    btn_simpan = _wait_and_find(
        driver, wait, SELECTORS["btn_simpan"], "tombol Simpan", clickable=True
    )
    if btn_simpan is None:
        return False
    if not _safe_click(driver, btn_simpan, "tombol Simpan"):
        return False
    logger.debug(f"[No. {row_no}] Tombol Simpan diklik")

    # --- Step 12: Verifikasi sukses ---
    time.sleep(1.5)
    success = _verify_success(driver, wait, row_no)

    # --- Step 13: Tunggu hingga modal tertutup (backdrop hilang) ---
    # Penting agar record berikutnya bisa langsung mengklik tombol Tambah
    if success:
        try:
            WebDriverWait(driver, 10).until(
                EC.invisibility_of_element_located((By.CSS_SELECTOR, '.modal-backdrop, .modal.show, .modal.fade.show'))
            )
            logger.debug(f"[No. {row_no}] Modal sudah tertutup")
        except TimeoutException:
            # Jika backdrop tidak hilang sendiri, tutup paksa via JS
            driver.execute_script("""
                document.querySelectorAll('.modal-backdrop').forEach(el => el.remove());
                document.querySelectorAll('.modal.show').forEach(el => el.classList.remove('show'));
                document.body.classList.remove('modal-open');
                document.body.style.overflow = '';
                document.body.style.paddingRight = '';
            """)
            logger.debug(f"[No. {row_no}] Modal ditutup paksa via JS")
        time.sleep(1)

    # Beri jeda antar submit
    time.sleep(1.5)

    return success

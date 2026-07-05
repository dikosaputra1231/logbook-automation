# ============================================================
#  auth_module.py — Login & session management Student Portal IPB
#
#  Mendukung dua pola login:
#  1. Login form standar (langsung isi username/password)
#  2. SSO / CAS redirect (detect redirect, isi form CAS)
# ============================================================

from __future__ import annotations

import time

from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    WebDriverException,
)

from config import (
    LOGIN_URL,
    PORTAL_BASE_URL,
    WAIT_TIMEOUT,
    SELECTORS,
)
from logger_setup import logger

import os
IPB_USERNAME = os.getenv("IPB_USERNAME", "")
IPB_PASSWORD = os.getenv("IPB_PASSWORD", "")


# ===========================================================
# KONSTANTA INTERNAL
# ===========================================================

# Indikator bahwa halaman yang sedang terbuka adalah halaman CAS/SSO
CAS_URL_KEYWORDS = ["cas", "sso", "auth", "login.ipb", "oauth"]

# Selector tambahan khusus SSO CAS IPB (sesuaikan jika berbeda)
CAS_SELECTORS = {
    "username": 'input#username, input[name="username"]',
    "password": 'input#password, input[name="password"]',
    "submit":   'input[name="submit"], button[type="submit"]',
}


# ===========================================================
# HELPERS
# ===========================================================

def _is_on_cas_page(driver: WebDriver) -> bool:
    """Cek apakah browser saat ini berada di halaman CAS/SSO."""
    current_url = driver.current_url.lower()
    return any(kw in current_url for kw in CAS_URL_KEYWORDS)


def _fill_login_form(
    driver: WebDriver,
    wait: WebDriverWait,
    username_sel: str,
    password_sel: str,
    submit_sel: str,
) -> None:
    """
    Isi dan submit form login generik.

    Args:
        driver:       WebDriver aktif
        wait:         WebDriverWait dengan timeout
        username_sel: CSS selector field username
        password_sel: CSS selector field password
        submit_sel:   CSS selector tombol submit
    """
    # Tunggu field username muncul
    username_field = wait.until(
        EC.presence_of_element_located((By.CSS_SELECTOR, username_sel))
    )
    username_field.clear()
    username_field.send_keys(IPB_USERNAME)
    logger.debug(f"Username '{IPB_USERNAME}' diisi")

    # Isi password
    password_field = driver.find_element(By.CSS_SELECTOR, password_sel)
    password_field.clear()
    password_field.send_keys(IPB_PASSWORD)
    logger.debug("Password diisi")

    # Klik submit
    submit_btn = driver.find_element(By.CSS_SELECTOR, submit_sel)
    submit_btn.click()
    logger.debug("Form login di-submit")


def _wait_for_post_login(driver: WebDriver, wait: WebDriverWait) -> bool:
    """
    Tunggu indikator halaman berhasil login.

    Returns:
        True jika login berhasil, False jika timeout
    """
    # Strategi 1: Cek elemen indikator login dari config
    try:
        wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, SELECTORS["post_login_indicator"])
            )
        )
        return True
    except TimeoutException:
        pass

    # Strategi 2: Cek apakah URL sudah bukan halaman login
    try:
        wait.until(lambda d: "login" not in d.current_url.lower())
        return True
    except TimeoutException:
        pass

    return False


# ===========================================================
# PUBLIC API
# ===========================================================

def login(driver: WebDriver) -> bool:
    """
    Login ke Student Portal IPB menggunakan kredensial dari .env.

    Alur:
    1. Navigasi ke LOGIN_URL
    2. Deteksi apakah halaman di-redirect ke CAS/SSO
    3. Isi form login sesuai jenis halaman
    4. Tunggu konfirmasi login berhasil

    Args:
        driver: WebDriver Chrome yang sudah diinisialisasi

    Returns:
        True jika login berhasil, False jika gagal
    """
    if not IPB_USERNAME or not IPB_PASSWORD:
        logger.error("Kredensial belum diisi! Pastikan IPB_USERNAME dan IPB_PASSWORD ada di .env")
        return False

    wait = WebDriverWait(driver, WAIT_TIMEOUT)

    logger.info(f"Navigasi ke halaman login: {LOGIN_URL}")
    try:
        driver.get(LOGIN_URL)
    except WebDriverException as exc:
        logger.error(f"Gagal membuka URL login: {exc}")
        return False

    # Tunggu sebentar untuk redirect SSO selesai
    time.sleep(2)

    current_url = driver.current_url
    logger.debug(f"URL saat ini: {current_url}")

    # ===========================================================
    # SKENARIO A: Halaman CAS / SSO
    # ===========================================================
    if _is_on_cas_page(driver):
        logger.info("Terdeteksi halaman SSO/CAS — menggunakan alur SSO")
        try:
            _fill_login_form(
                driver, wait,
                username_sel=CAS_SELECTORS["username"],
                password_sel=CAS_SELECTORS["password"],
                submit_sel=CAS_SELECTORS["submit"],
            )
        except (TimeoutException, NoSuchElementException) as exc:
            logger.error(f"Gagal mengisi form SSO/CAS: {exc}")
            return False

    # ===========================================================
    # SKENARIO B: Form login standar di portal langsung
    # ===========================================================
    else:
        logger.info("Menggunakan form login standar")
        try:
            _fill_login_form(
                driver, wait,
                username_sel=SELECTORS["login_username"],
                password_sel=SELECTORS["login_password"],
                submit_sel=SELECTORS["login_submit"],
            )
        except (TimeoutException, NoSuchElementException) as exc:
            logger.error(f"Gagal mengisi form login: {exc}")
            return False

    # ===========================================================
    # Verifikasi login berhasil
    # ===========================================================
    logger.info("Menunggu konfirmasi login...")
    success = _wait_for_post_login(driver, wait)

    if success:
        logger.info(f"✓ Login berhasil! URL: {driver.current_url}")
    else:
        logger.error(
            "✗ Login gagal atau timeout. Kemungkinan penyebab:\n"
            "  - Kredensial salah\n"
            "  - Halaman memerlukan verifikasi tambahan (Captcha/OTP)\n"
            "  - Selector post_login_indicator tidak cocok\n"
            f"  URL saat ini: {driver.current_url}"
        )

    return success

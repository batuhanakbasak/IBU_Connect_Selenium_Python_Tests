import time

import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

from config import (
    ADMIN_DASHBOARD_PATH,
    ADMIN_EMAIL,
    ADMIN_PASSWORD,
    BASE_URL,
    ORGANIZER_DASHBOARD_PATH,
    ORGANIZER_EMAIL,
    ORGANIZER_PASSWORD,
    STUDENT_DASHBOARD_PATH,
    STUDENT_EMAIL,
    STUDENT_PASSWORD,
)
from helpers import email_input, password_input, submit_button, wait_for_page_contains


# `@pytest.mark.parametrize` ayni test body'yi birden fazla veriyle kosar.
@pytest.mark.parametrize(
    "path,expected_text",
    [
        ("/student/login", "student login"),
        ("/organizer/organizer-login", "organizer"),
        ("/admin/login", "admin"),
    ],
)
def test_login_pages_have_core_fields(driver, path, expected_text):
    # Her login sayfasinda temel alanlar gorunmeli.
    # `driver` fixture olarak conftest.py'den gelir.
    # Asil test body bu fonksiyonun govdesidir.
    driver.get(BASE_URL + path)
    wait_for_page_contains(driver, expected_text)
    assert email_input(driver).is_displayed()
    assert password_input(driver).is_displayed()
    assert submit_button(driver).is_displayed()


def test_student_page_has_registration_hint(driver):
    # Student login ekraninda kayit yonlendirmesi olmali.
    driver.get(BASE_URL + "/student/login")
    wait_for_page_contains(driver, "create")
    assert "create one here" in driver.page_source.lower() or "need an account" in driver.page_source.lower()


def _fill_login_form(driver, email, password):
    # Tum login senaryolari ayni doldurma akisini kullansin.
    email_field = email_input(driver)
    password_field = password_input(driver)

    email_field.clear()
    password_field.clear()

    if email is not None:
        email_field.send_keys(email)
    if password:
        password_field.send_keys(password)

    return email_field, password_field


def _login_feedback_text(driver):
    # Roller farkli mesaj kutulari kullanabiliyor.
    for selector in ("[data-login-message]", ".auth-message", ".inline-message"):
        for element in driver.find_elements(By.CSS_SELECTOR, selector):
            text = element.text.strip()
            if text:
                return text
    return ""


def _open_login_page(driver, path):
    # Onceki login state'i bu testi etkilemesin diye temizlik yapiyoruz.
    login_url = BASE_URL + path
    driver.get(login_url)
    driver.delete_all_cookies()
    driver.execute_script("window.localStorage.clear(); window.sessionStorage.clear();")
    driver.get(login_url)
    wait_for_page_contains(driver, "email")


def _field_validation_message(driver, field):
    # Inline mesaj yoksa tarayici validation mesajini okuyalim.
    return driver.execute_script("return arguments[0].validationMessage || '';", field).strip()


def _login_should_succeed(driver, path, expected_path, email, password):
    # Pozitif senaryoda dashboard yonlendirmesini bekliyoruz.
    _open_login_page(driver, path)
    _fill_login_form(driver, email, password)
    submit_button(driver).click()

    expected_fragment = expected_path.lower()
    generic_dashboard_fragment = "dashboard"
    deadline = time.monotonic() + 20
    last_url = driver.current_url
    rendered_message = ""

    while time.monotonic() < deadline:
        last_url = driver.current_url
        rendered_message = _login_feedback_text(driver)
        lowered_url = last_url.lower()

        if expected_fragment in lowered_url or generic_dashboard_fragment in lowered_url:
            return
        if rendered_message:
            break

        time.sleep(0.5)

    if expected_fragment not in driver.current_url.lower() and generic_dashboard_fragment not in driver.current_url.lower():
        rendered_message = _login_feedback_text(driver) or "No login error message was rendered."
        pytest.fail(
            f"Login did not reach {expected_path!r}. Stayed on {last_url!r}. "
            f"Rendered message: {rendered_message}"
        )


# Bu test body de ayni sekilde 3 rol icin tekrar kosar.
@pytest.mark.parametrize(
    "path,email,password,expected_login_path",
    [
        ("/student/login", STUDENT_EMAIL, "", "/student/login"),
        ("/organizer/organizer-login", ORGANIZER_EMAIL, "", "/organizer/organizer-login"),
        ("/admin/login", ADMIN_EMAIL, "", "/admin/login"),
    ],
)
def test_login_with_empty_password_stays_on_login_page(driver, path, email, password, expected_login_path):
    # Bos sifrede kullanici login sayfasinda kalmali.
    _open_login_page(driver, path)
    _, password_field = _fill_login_form(driver, email, password)
    submit_button(driver).click()

    validation_message = _field_validation_message(driver, password_field).lower()
    feedback = _login_feedback_text(driver).lower()

    assert expected_login_path in driver.current_url.lower()
    assert validation_message or feedback
    assert (
        "fill out this field" in validation_message
        or "lutfen bu alani doldurun" in validation_message
        or "required" in validation_message
        or "password" in feedback
        or "required" in feedback
    )


def test_student_login_empty_password_shows_inline_app_error_message(driver):
    # Bu test bilerek bug yakalamak icin tutuluyor.
    _open_login_page(driver, "/student/login")
    _, password_field = _fill_login_form(driver, STUDENT_EMAIL, "")
    submit_button(driver).click()

    validation_message = _field_validation_message(driver, password_field)
    feedback = _login_feedback_text(driver)

    assert "/student/login" in driver.current_url.lower()
    assert feedback, (
        "No inline application error message was rendered for empty password submission. "
        f"Browser-native validation handled it instead: {validation_message!r}"
    )


# Bu negatif test de 3 rol icin tekrar edilir.
@pytest.mark.parametrize(
    "path,email,wrong_password,expected_login_path",
    [
        ("/student/login", STUDENT_EMAIL, "wrong-password-123", "/student/login"),
        ("/organizer/organizer-login", ORGANIZER_EMAIL, "wrong-password-123", "/organizer/organizer-login"),
        ("/admin/login", ADMIN_EMAIL, "wrong-password-123", "/admin/login"),
    ],
)
def test_login_with_wrong_password_shows_error(driver, path, email, wrong_password, expected_login_path):
    # Yanlis sifre login'i reddetmeli ve hata gostermeli.
    _open_login_page(driver, path)
    _fill_login_form(driver, email, wrong_password)
    submit_button(driver).click()

    WebDriverWait(driver, 15).until(
        lambda d: bool(_login_feedback_text(d)) or "invalid credentials" in d.page_source.lower()
    )
    feedback = (_login_feedback_text(driver) or driver.page_source).lower()

    assert expected_login_path in driver.current_url.lower()
    assert any(
        phrase in feedback
        for phrase in ("invalid credentials", "wrong email or password", "login failed", "invalid")
    )


def test_student_login_success(driver):
    # Dogru ogrenci bilgisi dashboard'a goturmeli.
    _login_should_succeed(driver, "/student/login", STUDENT_DASHBOARD_PATH, STUDENT_EMAIL, STUDENT_PASSWORD)


def test_organizer_login_success(driver):
    # Dogru organizer bilgisi dashboard'a goturmeli.
    _login_should_succeed(
        driver,
        "/organizer/organizer-login",
        ORGANIZER_DASHBOARD_PATH,
        ORGANIZER_EMAIL,
        ORGANIZER_PASSWORD,
    )


def test_admin_login_success(driver):
    # Dogru admin bilgisi dashboard'a goturmeli.
    _login_should_succeed(driver, "/admin/login", ADMIN_DASHBOARD_PATH, ADMIN_EMAIL, ADMIN_PASSWORD)

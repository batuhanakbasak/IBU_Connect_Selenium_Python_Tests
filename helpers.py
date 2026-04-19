from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def wait_for_page_contains(driver, text, timeout=10):
    WebDriverWait(driver, timeout).until(lambda d: text.lower() in d.page_source.lower())


def wait_for_elements_count(driver, by, value, count=1, timeout=10):
    WebDriverWait(driver, timeout).until(lambda d: len(d.find_elements(by, value)) >= count)


def first_existing(driver, selectors):
    for by, value in selectors:
        elems = driver.find_elements(by, value)
        if elems:
            return elems[0]
    raise AssertionError(f"No matching selector found: {selectors}")


def visible_text_contains(driver, text):
    return text.lower() in driver.page_source.lower()


def email_input(driver):
    selectors = [
        (By.CSS_SELECTOR, 'input[type="email"]'),
        (By.NAME, 'email'),
        (By.CSS_SELECTOR, 'input[placeholder*="mail" i]'),
    ]
    return first_existing(driver, selectors)


def password_input(driver):
    selectors = [
        (By.CSS_SELECTOR, 'input[type="password"]'),
        (By.NAME, 'password'),
    ]
    return first_existing(driver, selectors)


def submit_button(driver):
    selectors = [
        (By.CSS_SELECTOR, 'button[type="submit"]'),
        (
            By.XPATH,
            "//button[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'sign in')]",
        ),
        (By.XPATH, "//input[@type='submit']"),
    ]
    return first_existing(driver, selectors)

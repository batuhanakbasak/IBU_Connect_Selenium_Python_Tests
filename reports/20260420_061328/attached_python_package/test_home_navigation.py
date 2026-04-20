from selenium.webdriver.common.by import By
from config import BASE_URL
from helpers import wait_for_elements_count, wait_for_page_contains


def _link_label(anchor):
    # Some anchors render empty `.text`, so we fall back to raw textContent.
    return (
        anchor.text
        or anchor.get_attribute('textContent')
        or anchor.get_attribute('aria-label')
        or ''
    ).strip().lower()


def test_homepage_loads_and_shows_role_panels(driver):
    driver.get(BASE_URL)
    wait_for_page_contains(driver, 'Multimedia Web Design Project')
    page = driver.page_source.lower()
    assert 'student login' in page
    assert 'organizer login' in page
    assert 'admin login' in page


def test_homepage_links_navigate_to_expected_pages(driver):
    driver.get(BASE_URL)
    wait_for_page_contains(driver, 'student login')
    wait_for_elements_count(driver, By.TAG_NAME, 'a', count=3)
    # Build a label -> href map so the assertions stay easy to read.
    links = {}
    for anchor in driver.find_elements(By.TAG_NAME, 'a'):
        label = _link_label(anchor)
        if label:
            links[label] = anchor.get_attribute('href')

    assert 'student login' in links
    assert 'organizer login' in links
    assert 'admin login' in links
    assert '/student/' in links['student login']
    assert '/organizer/' in links['organizer login']
    assert '/admin/' in links['admin login']

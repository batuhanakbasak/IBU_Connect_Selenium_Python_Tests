from pathlib import Path

import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

from reporting import (
    build_actual_result,
    build_attachment_package,
    build_run_state,
    display_time,
    finalize_summary,
    safe_name,
    status_from_pytest_outcome,
    update_browser_metadata,
    write_run_artifacts,
)

# Pytest bu isimdeki fonksiyonu otomatik cagirir.
def pytest_configure(config):
    # Tum kosu boyunca kullanilacak ortak rapor state'i.
    config._execution_report_state = build_run_state(config.rootpath, config.invocation_params.args)

# Her testten hemen once pytest bunu otomatik cagirir.
def pytest_runtest_setup(item):
    # Her test icin bos bir execution kaydi aciyoruz.
    item._execution_record = {
        "nodeid": item.nodeid,
        "status": "Blocked",
        "pytest_outcome": "skipped",
        "actual_result": "Test execution did not reach its verification steps.",
        "execution_date": "",
        "evidence_reference": "N/A",
        "current_url": "",
        "page_title": "",
    }

# Hook = pytest'in kendi olaylarina baglanan ozel fonksiyon.
@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    # Pytest setup/call/teardown sonucunu burada yakaliyor.
    # `yield` sonrasi pytest'in olusturdugu report nesnesi geri geliyor.
    outcome = yield
    report = outcome.get_result()
    setattr(item, f"rep_{report.when}", report)

    record = getattr(item, "_execution_record", None)
    if record is None:
        return

    if report.when == "setup" and report.outcome in {"failed", "skipped"}:
        record["status"] = status_from_pytest_outcome(report.outcome)
        record["pytest_outcome"] = report.outcome
        record["actual_result"] = build_actual_result(report)
        record["execution_date"] = display_time()

    if report.when == "call":
        record["status"] = status_from_pytest_outcome(report.outcome)
        record["pytest_outcome"] = report.outcome
        record["actual_result"] = build_actual_result(report)
        record["execution_date"] = display_time()

    if report.when == "teardown":
        # Test body gecti ama teardown patlarsa sonucu fail'e cekiyoruz.
        if report.failed and record["status"] == "Pass":
            record["status"] = "Fail"
            record["pytest_outcome"] = "failed"
            record["actual_result"] = build_actual_result(report)
            record["execution_date"] = display_time()

        state = item.config._execution_report_state
        state["tests"].append(record)

# Tum testler bittikten sonra pytest bunu otomatik cagirir.
def pytest_sessionfinish(session, exitstatus):
    # Tum testler bitince rapor dosyalari uretiliyor.
    state = session.config._execution_report_state
    finalize_summary(state)
    build_attachment_package(state)
    _, markdown_path = write_run_artifacts(state)
    session.config._execution_report_markdown = markdown_path

# Terminal ozeti basilirken pytest bu fonksiyona ugrar.
def pytest_terminal_summary(terminalreporter, exitstatus, config):
    # Raporun nereye yazildigini terminalde goster.
    markdown_path = getattr(config, "_execution_report_markdown", None)
    if markdown_path:
        terminalreporter.write_sep("-", f"execution report written to {markdown_path}")


# Fixture = test fonksiyonuna isimle enjekte edilen yardimci kaynak.
@pytest.fixture
def driver(request):
    # Her test temiz Chrome ile baslar; state sizmasi azalir.
    options = Options()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-notifications")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.implicitly_wait(8)

    state = request.config._execution_report_state
    update_browser_metadata(state, driver.capabilities)

    # `yield` oncesi setup, sonrasi teardown gibi calisir.
    yield driver

    record = getattr(request.node, "_execution_record", None)
    if record is not None:
        # Son ekran goruntusunu kanit olarak sakliyoruz.
        evidence_dir = Path(state["evidence_dir"])
        screenshot_name = f"{safe_name(request.node.nodeid)}.png"
        screenshot_path = evidence_dir / screenshot_name

        try:
            driver.save_screenshot(str(screenshot_path))
            record["evidence_reference"] = f"evidence/{screenshot_name}"
        except Exception as error:
            record["evidence_reference"] = f"Screenshot unavailable: {error}"

        try:
            record["current_url"] = driver.current_url
        except Exception:
            record["current_url"] = ""

        try:
            record["page_title"] = driver.title
        except Exception:
            record["page_title"] = ""

        if record["current_url"] and record["status"] == "Pass":
            record["actual_result"] = (
                f"Expected behavior was observed during execution. Final URL: {record['current_url']}"
            )

    driver.quit()

from pathlib import Path

import pytest
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
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


def pytest_configure(config):
    # Create one shared reporting state for the whole pytest session.
    config._execution_report_state = build_run_state(config.rootpath, config.invocation_params.args)


def pytest_runtest_setup(item):
    # Start each test as "Blocked" until pytest tells us the real outcome.
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


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    # Capture setup/call/teardown results so we can build the final execution log.
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
        if report.failed and record["status"] == "Pass":
            record["status"] = "Fail"
            record["pytest_outcome"] = "failed"
            record["actual_result"] = build_actual_result(report)
            record["execution_date"] = display_time()

        state = item.config._execution_report_state
        state["tests"].append(record)


def pytest_sessionfinish(session, exitstatus):
    # When the run ends, generate the summary, zip package, and markdown/json reports.
    state = session.config._execution_report_state
    finalize_summary(state)
    build_attachment_package(state)
    _, markdown_path = write_run_artifacts(state)
    session.config._execution_report_markdown = markdown_path


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    #nereye yazıldığını terminalde gösterelim
    markdown_path = getattr(config, "_execution_report_markdown", None)
    if markdown_path:
        terminalreporter.write_sep("-", f"execution report written to {markdown_path}")


@pytest.fixture
def driver(request):
    # Every test gets a fresh Chrome session to reduce state leakage between scenarios.
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

    yield driver

    record = getattr(request.node, "_execution_record", None)
    if record is not None:
        # Save the final browser state as evidence for the generated test report.
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

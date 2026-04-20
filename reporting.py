from __future__ import annotations

import getpass
import json
import os
import platform
import re
import shutil
from collections import Counter
from datetime import datetime
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import selenium


PLANNED_NEGATIVE_TESTS = [
    {
        "id": "TC-11",
        "title": "Empty password login attempt",
        "description": "Attempt login with a valid-looking email and an empty password field.",
    },
    {
        "id": "TC-12",
        "title": "Invalid email format during registration",
        "description": "Attempt registration with an invalid email format such as `mehmet@com`.",
    },
    {
        "id": "TC-13",
        "title": "Overlong name input validation",
        "description": "Attempt registration with an excessively long full name value to validate field limits.",
    },
    {
        "id": "TC-14",
        "title": "Basic SQL injection payload attempt",
        "description": "Attempt authentication with a payload such as `' OR 1=1` to confirm defensive validation.",
    },
]


def current_timestamp():
    return datetime.now().astimezone()


def iso_now():
    return current_timestamp().isoformat(timespec="seconds")


def display_time(value=None):
    timestamp = value or current_timestamp()
    return timestamp.strftime("%Y-%m-%d %H:%M:%S %z")


def build_run_state(project_root, invocation_args):
    started_at = current_timestamp()
    run_id = started_at.strftime("%Y%m%d_%H%M%S")
    reports_dir = Path(project_root) / "reports"
    run_dir = reports_dir / run_id
    evidence_dir = run_dir / "evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)

    return {
        "run_id": run_id,
        "project_root": str(project_root),
        "report_dir": str(run_dir),
        "evidence_dir": str(evidence_dir),
        "tester_name": os.getenv("TESTER_NAME", getpass.getuser()),
        "execution_started_at": started_at.isoformat(timespec="seconds"),
        "execution_finished_at": "",
        "execution_date": display_time(started_at),
        "execution_command": os.getenv("PYTEST_EXECUTION_COMMAND") or format_command(invocation_args),
        "environment": {
            "operating_system": platform.platform(),
            "python_version": platform.python_version(),
            "selenium_version": selenium.__version__,
            "browser_name": "Chrome",
            "browser_version": "Unknown",
            "driver_version": "Unknown",
        },
        "planned_negative_tests": PLANNED_NEGATIVE_TESTS,
        "bug_report": {},
        "automation_package": {},
        "tests": [],
        "summary": {
            "collected": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "blocked": 0,
        },
    }


def format_command(invocation_args):
    args = " ".join(invocation_args).strip()
    return f"pytest {args}".strip()


def safe_name(nodeid):
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", nodeid).strip("._") or "test"


def status_from_pytest_outcome(outcome):
    mapping = {
        "passed": "Pass",
        "failed": "Fail",
        "skipped": "Blocked",
    }
    return mapping.get(outcome, outcome.title())


def extract_reason(longrepr_text):
    if not longrepr_text:
        return ""
    raw_text = str(longrepr_text)
    if "Skipped:" in raw_text:
        return raw_text.split("Skipped:", 1)[1].strip(" '()")

    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    if not lines:
        return ""
    return lines[-1]


def build_actual_result(report):
    reason = extract_reason(getattr(report, "longreprtext", ""))

    if report.outcome == "passed":
        return "Expected behavior was observed during execution."
    if report.outcome == "skipped":
        if reason:
            return f"Execution was blocked: {reason}"
        return "Execution was blocked before the test steps could complete."
    if reason:
        return f"Observed result diverged from expectation: {reason}"
    return "Observed result diverged from expectation. Review the pytest traceback for details."


def update_browser_metadata(run_state, capabilities):
    capabilities = capabilities or {}
    environment = run_state["environment"]

    browser_name = capabilities.get("browserName")
    if browser_name:
        environment["browser_name"] = str(browser_name).title()

    browser_version = capabilities.get("browserVersion")
    if browser_version:
        environment["browser_version"] = str(browser_version)

    chrome_data = capabilities.get("chrome", {})
    driver_version = chrome_data.get("chromedriverVersion", "")
    if driver_version:
        environment["driver_version"] = driver_version.split(" ", 1)[0]


def finalize_summary(run_state):
    counts = Counter(test["status"] for test in run_state["tests"])
    raw_counts = Counter(test["pytest_outcome"] for test in run_state["tests"])

    run_state["execution_finished_at"] = iso_now()
    run_state["summary"] = {
        "collected": len(run_state["tests"]),
        "executed": counts.get("Pass", 0) + counts.get("Fail", 0),
        "passed": counts.get("Pass", 0),
        "failed": counts.get("Fail", 0),
        "skipped": raw_counts.get("skipped", 0),
        "blocked": counts.get("Blocked", 0),
    }
    run_state["bug_report"] = build_bug_report(run_state)


def build_bug_report(run_state):
    failed_tests = [test for test in run_state["tests"] if test["status"] == "Fail"]
    environment = run_state["environment"]

    inline_validation_bug = next(
        (test for test in failed_tests if "test_student_login_empty_password_shows_inline_app_error_message" in test["nodeid"]),
        None,
    )
    if inline_validation_bug:
        return {
            "bug_id": "BUG-01",
            "title": "Student login does not render an inline validation error for empty password submission",
            "severity": "Medium",
            "environment": (
                f"{environment['operating_system']}, {environment['browser_name']} {environment['browser_version']}, "
                f"Python {environment['python_version']}, Selenium {environment['selenium_version']}"
            ),
            "steps_to_reproduce": [
                "Open `https://batuhanakbasak.com/student/login`.",
                "Enter a valid student email such as `ahmet@gmail.com`.",
                "Leave the password field empty and click `Sign In`.",
            ],
            "expected_result": (
                "The application should render a clear inline validation message inside the form, consistent with the page's UI language and styling."
            ),
            "actual_result": (
                "No application-level inline error message is shown. The browser's native required-field validation blocks submission instead."
            ),
        }

    blocked_tests = [test for test in run_state["tests"] if test["status"] == "Blocked"]
    if not blocked_tests:
        return {}

    blocked_case_list = ", ".join(test["nodeid"] for test in blocked_tests)

    return {
        "bug_id": "BUG-01",
        "title": "Shared positive-login test credentials are not provisioned in the execution environment",
        "severity": "Medium",
        "environment": (
            f"{environment['operating_system']}, {environment['browser_name']} {environment['browser_version']}, "
            f"Python {environment['python_version']}, Selenium {environment['selenium_version']}"
        ),
        "steps_to_reproduce": [
            "Open the automation package in a clean environment without setting STUDENT_EMAIL, ORGANIZER_EMAIL, and ADMIN_EMAIL variables.",
            "Run `python run_tests_with_report.py -v`.",
            f"Observe the credential-dependent tests: {blocked_case_list}.",
        ],
        "expected_result": (
            "The shared QA or UAT environment should provide stable non-production credentials or an equivalent secrets source "
            "so that positive-login smoke tests can execute end-to-end."
        ),
        "actual_result": (
            f"{len(blocked_tests)} positive-login scenarios were blocked with the message "
            "`Credentials not provided via environment variables.`"
        ),
    }


def build_attachment_package(run_state):
    project_root = Path(run_state["project_root"])
    run_dir = Path(run_state["report_dir"])
    package_dir = run_dir / "attached_python_package"
    package_dir.mkdir(parents=True, exist_ok=True)

    files_to_copy = [
        "test_home_navigation.py",
        "test_login_forms.py",
        "helpers.py",
        "config.py",
        "conftest.py",
    ]

    for relative_path in files_to_copy:
        source = project_root / relative_path
        if source.exists():
            shutil.copy2(source, package_dir / source.name)

    requirements_path = package_dir / "requirements.txt"
    requirements_path.write_text("selenium\npytest\n", encoding="utf-8")

    readme_path = package_dir / "README.txt"
    readme_path.write_text(build_package_readme_text(), encoding="utf-8")

    zip_path = run_dir / "attached_python_package.zip"
    with ZipFile(zip_path, "w", compression=ZIP_DEFLATED) as archive:
        for file_path in sorted(package_dir.rglob("*")):
            if file_path.is_file():
                archive.write(file_path, arcname=file_path.relative_to(package_dir))

    run_state["automation_package"] = {
        "folder": str(package_dir),
        "zip_path": str(zip_path),
        "zip_name": zip_path.name,
        "contents": sorted(path.name for path in package_dir.iterdir() if path.is_file()),
    }


def build_package_readme_text():
    return "\n".join(
        [
            "IBU Connect Selenium Smoke Tests",
            "",
            "How to run:",
            "1. Install dependencies with `pip install -r requirements.txt`.",
            "2. Run the tests with `pytest -v`.",
            "3. Optional positive-login tests require environment variables for credentials.",
            "",
            "Included files:",
            "- test_home_navigation.py",
            "- test_login_forms.py",
            "- helpers.py",
            "- config.py",
            "- conftest.py",
            "- requirements.txt",
            "- README.txt",
        ]
    )


def write_run_artifacts(run_state):
    run_dir = Path(run_state["report_dir"])
    json_path = run_dir / "execution_artifacts.json"
    markdown_path = run_dir / "test_execution_report.md"

    json_path.write_text(json.dumps(run_state, indent=2, ensure_ascii=True), encoding="utf-8")
    markdown_path.write_text(render_markdown_report(run_state), encoding="utf-8")

    return json_path, markdown_path


def render_markdown_report(run_state):
    summary = run_state["summary"]
    environment = run_state["environment"]
    bug_report = run_state.get("bug_report", {})
    automation_package = run_state.get("automation_package", {})
    package_display_path = automation_package.get("zip_name") or automation_package.get("zip_path", "Not generated")

    lines = [
        "# Test Execution Report",
        "",
        "## 4. Test Environment and Tools",
        "",
        "| Item | Value |",
        "| --- | --- |",
        f"| Tester Name | {escape_pipe(run_state['tester_name'])} |",
        f"| Execution Date | {escape_pipe(run_state['execution_date'])} |",
        f"| Operating System | {escape_pipe(environment['operating_system'])} |",
        f"| Browser | {escape_pipe(environment['browser_name'])} |",
        f"| Browser Version | {escape_pipe(environment['browser_version'])} |",
        f"| Python Version | {escape_pipe(environment['python_version'])} |",
        f"| Selenium Version | {escape_pipe(environment['selenium_version'])} |",
        "",
        "## 6. Functional Test Cases",
        "",
        "The functional test cases remain unchanged and are executed from the current automation package.",
        "",
        "### Automated Test Scope",
        "",
    ]

    for test in run_state["tests"]:
        lines.append(f"- `{test['nodeid']}`")

    lines.extend(
        [
            "",
            "### Additional Negative Test Cases (Documentation Only)",
            "",
        ]
    )

    for test_case in run_state["planned_negative_tests"]:
        lines.append(
            f"- `{test_case['id']}` {test_case['title']}: {test_case['description']} Not automated in this execution."
        )

    lines.extend(
        [
            "",
            "### Execution Log Appendix",
            "",
            "| Test Case | Actual Result | Status | Execution Date | Evidence Reference |",
            "| --- | --- | --- | --- | --- |",
        ]
    )

    for test in run_state["tests"]:
        lines.append(
            "| {nodeid} | {actual_result} | {status} | {execution_date} | {evidence_reference} |".format(
                nodeid=escape_pipe(test["nodeid"]),
                actual_result=escape_pipe(test["actual_result"]),
                status=escape_pipe(test["status"]),
                execution_date=escape_pipe(test["execution_date"]),
                evidence_reference=escape_pipe(test["evidence_reference"]),
            )
        )

    lines.extend(
        [
            "",
            "## 8. Bug Report",
            "",
        ]
    )

    if bug_report:
        lines.extend(
            [
                f"- Bug ID: {bug_report['bug_id']}",
                f"- Title: {bug_report['title']}",
                f"- Severity: {bug_report['severity']}",
                f"- Environment: {bug_report['environment']}",
                "- Steps to Reproduce:",
            ]
        )
        for index, step in enumerate(bug_report["steps_to_reproduce"], start=1):
            lines.append(f"{index}. {step}")
        lines.extend(
            [
                f"- Expected Result: {bug_report['expected_result']}",
                f"- Actual Result: {bug_report['actual_result']}",
            ]
        )
    else:
        lines.extend(
            [
                "No confirmed bugs were documented during this execution. Use the template below only when a validated defect is found.",
                "",
                "- Bug ID:",
                "- Title:",
                "- Severity:",
                "- Environment:",
                "- Steps to Reproduce:",
                "- Expected Result:",
                "- Actual Result:",
            ]
        )

    lines.extend(
        [
            "",
            "## 9. Automation Package Included",
            "",
            "| Item | Value |",
            "| --- | --- |",
            f"| Executed Command | {escape_pipe(run_state['execution_command'])} |",
            f"| Execution Date | {escape_pipe(run_state['execution_date'])} |",
            f"| Browser / Driver Version | {escape_pipe(environment['browser_version'])} / {escape_pipe(environment['driver_version'])} |",
            f"| Total Tests | {summary['collected']} |",
            f"| Passed | {summary['passed']} |",
            f"| Failed | {summary['failed']} |",
            f"| Skipped | {summary['skipped']} |",
            f"| Attached Python Package | {escape_pipe(package_display_path)} |",
            "",
            "### Package Contents",
            "",
        ]
    )

    for filename in automation_package.get("contents", []):
        lines.append(f"- `{filename}`")

    lines.extend(
        [
            "",
            "## 10. Final Evaluation Notes",
            "",
            f"- Total executed tests: {summary['executed']} out of {summary['collected']} collected tests.",
            f"- Pass/Fail/Blocked summary: {summary['passed']} passed, {summary['failed']} failed, {summary['blocked']} blocked.",
            f"- Defects by severity: {build_defect_summary(bug_report)}",
            f"- Key observations: {build_key_observations(summary)}",
            f"- Limitations: {build_limitations(summary)}",
            "- Follow-up improvements: Provide stable test credentials for all roles, keep dashboard routes configurable, and review evidence files when triaging blocked or failed runs.",
            "",
        ]
    )

    return "\n".join(lines)


def build_key_observations(summary):
    if summary["failed"]:
        return "At least one automated scenario failed and requires functional triage before release confidence is claimed."
    if summary["blocked"]:
        return "Core smoke coverage passed, but some positive-login scenarios were blocked because required prerequisites were not available."
    return "All executed automated scenarios passed during this run."


def build_limitations(summary):
    if summary["blocked"]:
        return "Blocked scenarios reduce end-to-end confidence for credential-dependent flows."
    if summary["failed"]:
        return "Failed scenarios indicate the current build needs additional investigation."
    return "This run is smoke-level coverage and does not replace broader regression, performance, or security testing."


def build_defect_summary(bug_report):
    if not bug_report:
        return "No confirmed defects were logged in this execution."
    return f"1 {bug_report['severity']} severity defect documented ({bug_report['bug_id']})."


def escape_pipe(value):
    return str(value).replace("|", "\\|")

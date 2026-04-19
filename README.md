# IBU Connect Selenium Smoke Tests

This package contains Python + Selenium smoke tests for the public IBU Connect website.

## 1) Install
```bash
pip install -r requirements.txt
```

## 2) Run all tests
```bash
pytest -v
```

To run tests and explicitly capture the executed command in the generated report:

```bash
python run_tests_with_report.py -v
```

## 3) Optional credentials for positive login tests
Set environment variables before running. In PowerShell:

```powershell
$env:STUDENT_EMAIL="your_student_email"
$env:STUDENT_PASSWORD="your_student_password"
$env:ORGANIZER_EMAIL="your_organizer_email"
$env:ORGANIZER_PASSWORD="your_organizer_password"
$env:ADMIN_EMAIL="your_admin_email"
$env:ADMIN_PASSWORD="your_admin_password"
```

You can also override the target URL and expected dashboard routes:

```powershell
$env:BASE_URL="https://batuhanakbasak.com"
$env:STUDENT_DASHBOARD_PATH="/student/dashboard"
$env:ORGANIZER_DASHBOARD_PATH="/organizer/dashboard"
$env:ADMIN_DASHBOARD_PATH="/admin/dashboard"
```

## 4) Run a single file
```bash
pytest -v test_home_navigation.py
pytest -v test_login_forms.py
```

## Notes
- The tests are intentionally smoke-level and non-destructive.
- Positive login tests automatically skip if credentials are not supplied.
- The selectors are written to be fairly tolerant, but if the frontend changes a lot, update the locators in `helpers.py`.
- Each pytest run generates `reports/<timestamp>/test_execution_report.md`, `execution_artifacts.json`, and per-test evidence screenshots.

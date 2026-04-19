# Test Execution Report

## 4. Test Environment and Tools

| Item | Value |
| --- | --- |
| Tester Name | batuh |
| Execution Date | 2026-04-19 19:34:07 +0200 |
| Operating System | Windows-11-10.0.26200-SP0 |
| Browser | Chrome |
| Browser Version | 147.0.7727.57 |
| Python Version | 3.12.10 |
| Selenium Version | 4.43.0 |

## 6. Functional Test Cases

The functional test cases remain unchanged and are executed from the current automation package.

### Automated Test Scope

- `test_home_navigation.py::test_homepage_loads_and_shows_role_panels`
- `test_home_navigation.py::test_homepage_links_navigate_to_expected_pages`
- `test_login_forms.py::test_login_pages_have_core_fields[/student/login-student login]`
- `test_login_forms.py::test_login_pages_have_core_fields[/organizer/organizer-login-organizer]`
- `test_login_forms.py::test_login_pages_have_core_fields[/admin/login-admin]`
- `test_login_forms.py::test_student_page_has_registration_hint`
- `test_login_forms.py::test_login_with_empty_password_stays_on_login_page[/student/login-ahmet@gmail.com--/student/login]`
- `test_login_forms.py::test_login_with_empty_password_stays_on_login_page[/organizer/organizer-login-mehmetali@gmail.com--/organizer/organizer-login]`
- `test_login_forms.py::test_login_with_empty_password_stays_on_login_page[/admin/login-admin1@example.com--/admin/login]`
- `test_login_forms.py::test_login_with_wrong_password_shows_error[/student/login-ahmet@gmail.com-wrong-password-123-/student/login]`
- `test_login_forms.py::test_login_with_wrong_password_shows_error[/organizer/organizer-login-mehmetali@gmail.com-wrong-password-123-/organizer/organizer-login]`
- `test_login_forms.py::test_login_with_wrong_password_shows_error[/admin/login-admin1@example.com-wrong-password-123-/admin/login]`
- `test_login_forms.py::test_student_login_success`
- `test_login_forms.py::test_organizer_login_success`
- `test_login_forms.py::test_admin_login_success`

### Additional Negative Test Cases (Documentation Only)

- `TC-11` Empty password login attempt: Attempt login with a valid-looking email and an empty password field. Not automated in this execution.
- `TC-12` Invalid email format during registration: Attempt registration with an invalid email format such as `mehmet@com`. Not automated in this execution.
- `TC-13` Overlong name input validation: Attempt registration with an excessively long full name value to validate field limits. Not automated in this execution.
- `TC-14` Basic SQL injection payload attempt: Attempt authentication with a payload such as `' OR 1=1` to confirm defensive validation. Not automated in this execution.

### Execution Log Appendix

| Test Case | Actual Result | Status | Execution Date | Evidence Reference |
| --- | --- | --- | --- | --- |
| test_home_navigation.py::test_homepage_loads_and_shows_role_panels | Expected behavior was observed during execution. Final URL: https://batuhanakbasak.com/ | Pass | 2026-04-19 19:34:12 +0200 | evidence/test_home_navigation.py_test_homepage_loads_and_shows_role_panels.png |
| test_home_navigation.py::test_homepage_links_navigate_to_expected_pages | Expected behavior was observed during execution. Final URL: https://batuhanakbasak.com/ | Pass | 2026-04-19 19:34:18 +0200 | evidence/test_home_navigation.py_test_homepage_links_navigate_to_expected_pages.png |
| test_login_forms.py::test_login_pages_have_core_fields[/student/login-student login] | Expected behavior was observed during execution. Final URL: https://batuhanakbasak.com/student/login | Pass | 2026-04-19 19:34:24 +0200 | evidence/test_login_forms.py_test_login_pages_have_core_fields_student_login-student_login.png |
| test_login_forms.py::test_login_pages_have_core_fields[/organizer/organizer-login-organizer] | Expected behavior was observed during execution. Final URL: https://batuhanakbasak.com/organizer/organizer-login | Pass | 2026-04-19 19:34:30 +0200 | evidence/test_login_forms.py_test_login_pages_have_core_fields_organizer_organizer-login-organizer.png |
| test_login_forms.py::test_login_pages_have_core_fields[/admin/login-admin] | Expected behavior was observed during execution. Final URL: https://batuhanakbasak.com/admin/login | Pass | 2026-04-19 19:34:36 +0200 | evidence/test_login_forms.py_test_login_pages_have_core_fields_admin_login-admin.png |
| test_login_forms.py::test_student_page_has_registration_hint | Expected behavior was observed during execution. Final URL: https://batuhanakbasak.com/student/login | Pass | 2026-04-19 19:34:42 +0200 | evidence/test_login_forms.py_test_student_page_has_registration_hint.png |
| test_login_forms.py::test_login_with_empty_password_stays_on_login_page[/student/login-ahmet@gmail.com--/student/login] | Expected behavior was observed during execution. Final URL: https://batuhanakbasak.com/student/login | Pass | 2026-04-19 19:34:57 +0200 | evidence/test_login_forms.py_test_login_with_empty_password_stays_on_login_page_student_login-ahmet_gmail.com--_student_login.png |
| test_login_forms.py::test_login_with_empty_password_stays_on_login_page[/organizer/organizer-login-mehmetali@gmail.com--/organizer/organizer-login] | Expected behavior was observed during execution. Final URL: https://batuhanakbasak.com/organizer/organizer-login | Pass | 2026-04-19 19:35:12 +0200 | evidence/test_login_forms.py_test_login_with_empty_password_stays_on_login_page_organizer_organizer-login-mehmetali_gmail.com--_organizer_organizer-login.png |
| test_login_forms.py::test_login_with_empty_password_stays_on_login_page[/admin/login-admin1@example.com--/admin/login] | Expected behavior was observed during execution. Final URL: https://batuhanakbasak.com/admin/login | Pass | 2026-04-19 19:35:26 +0200 | evidence/test_login_forms.py_test_login_with_empty_password_stays_on_login_page_admin_login-admin1_example.com--_admin_login.png |
| test_login_forms.py::test_login_with_wrong_password_shows_error[/student/login-ahmet@gmail.com-wrong-password-123-/student/login] | Expected behavior was observed during execution. Final URL: https://batuhanakbasak.com/student/login | Pass | 2026-04-19 19:35:41 +0200 | evidence/test_login_forms.py_test_login_with_wrong_password_shows_error_student_login-ahmet_gmail.com-wrong-password-123-_student_login.png |
| test_login_forms.py::test_login_with_wrong_password_shows_error[/organizer/organizer-login-mehmetali@gmail.com-wrong-password-123-/organizer/organizer-login] | Expected behavior was observed during execution. Final URL: https://batuhanakbasak.com/organizer/organizer-login | Pass | 2026-04-19 19:35:56 +0200 | evidence/test_login_forms.py_test_login_with_wrong_password_shows_error_organizer_organizer-login-mehmetali_gmail.com-wrong-password-123-_organizer_organizer-login.png |
| test_login_forms.py::test_login_with_wrong_password_shows_error[/admin/login-admin1@example.com-wrong-password-123-/admin/login] | Expected behavior was observed during execution. Final URL: https://batuhanakbasak.com/admin/login | Pass | 2026-04-19 19:36:11 +0200 | evidence/test_login_forms.py_test_login_with_wrong_password_shows_error_admin_login-admin1_example.com-wrong-password-123-_admin_login.png |
| test_login_forms.py::test_student_login_success | Expected behavior was observed during execution. Final URL: https://batuhanakbasak.com/student/dashboard.html | Pass | 2026-04-19 19:36:58 +0200 | evidence/test_login_forms.py_test_student_login_success.png |
| test_login_forms.py::test_organizer_login_success | Expected behavior was observed during execution. Final URL: https://batuhanakbasak.com/organizer/dashboard.html | Pass | 2026-04-19 19:37:38 +0200 | evidence/test_login_forms.py_test_organizer_login_success.png |
| test_login_forms.py::test_admin_login_success | Expected behavior was observed during execution. Final URL: https://batuhanakbasak.com/admin/dashboard.html | Pass | 2026-04-19 19:38:18 +0200 | evidence/test_login_forms.py_test_admin_login_success.png |

## 8. Bug Report

No confirmed bugs were documented during this execution. Use the template below only when a validated defect is found.

- Bug ID:
- Title:
- Severity:
- Environment:
- Steps to Reproduce:
- Expected Result:
- Actual Result:

## 9. Automation Package Included

| Item | Value |
| --- | --- |
| Executed Command | python -m pytest -v |
| Execution Date | 2026-04-19 19:34:07 +0200 |
| Browser / Driver Version | 147.0.7727.57 / 147.0.7727.57 |
| Total Tests | 15 |
| Passed | 15 |
| Failed | 0 |
| Skipped | 0 |
| Attached Python Package | attached_python_package.zip |

### Package Contents

- `README.txt`
- `config.py`
- `conftest.py`
- `helpers.py`
- `requirements.txt`
- `test_home_navigation.py`
- `test_login_forms.py`

## 10. Final Evaluation Notes

- Total executed tests: 15 out of 15 collected tests.
- Pass/Fail/Blocked summary: 15 passed, 0 failed, 0 blocked.
- Defects by severity: No confirmed defects were logged in this execution.
- Key observations: All executed automated scenarios passed during this run.
- Limitations: This run is smoke-level coverage and does not replace broader regression, performance, or security testing.
- Follow-up improvements: Provide stable test credentials for all roles, keep dashboard routes configurable, and review evidence files when triaging blocked or failed runs.

import os


def _env(name, default=""):
    # Env varsa onu kullan, yoksa default degeri donsun.
    return os.getenv(name, default).strip()


# Testlerin hedef sitesi.
BASE_URL = _env("BASE_URL", "https://batuhanakbasak.com").rstrip("/")

# Bu hesaplar terminalden env ile degistirilebilir.
STUDENT_EMAIL = _env("STUDENT_EMAIL", "ahmet@gmail.com")
STUDENT_PASSWORD = _env("STUDENT_PASSWORD", "12345678")
ORGANIZER_EMAIL = _env("ORGANIZER_EMAIL", "mehmetali@gmail.com")
ORGANIZER_PASSWORD = _env("ORGANIZER_PASSWORD", "12345678")
ADMIN_EMAIL = _env("ADMIN_EMAIL", "admin1@example.com")
ADMIN_PASSWORD = _env("ADMIN_PASSWORD", "12345678")

# Basarili login sonrasi beklenen yonlendirme adresleri.
STUDENT_DASHBOARD_PATH = _env("STUDENT_DASHBOARD_PATH", "/student/dashboard")
ORGANIZER_DASHBOARD_PATH = _env("ORGANIZER_DASHBOARD_PATH", "/organizer/dashboard")
ADMIN_DASHBOARD_PATH = _env("ADMIN_DASHBOARD_PATH", "/admin/dashboard")

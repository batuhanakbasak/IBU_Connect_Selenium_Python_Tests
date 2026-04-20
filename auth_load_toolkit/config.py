from __future__ import annotations

import importlib.util
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

from dotenv import load_dotenv


ToolkitMode = Literal["off", "page", "api", "auto"]


@dataclass(frozen=True)
class RoleCredentials:
    email: str
    password: str


@dataclass(frozen=True)
class RoleConfig:
    name: str
    login_page_path: str
    login_api_path: str
    dashboard_page_path: str
    dashboard_api_path: str
    credentials: RoleCredentials


@dataclass(frozen=True)
class StageConfig:
    users: int
    duration_seconds: int

    @property
    def name(self) -> str:
        return f"{self.users}u_{self.duration_seconds}s"


@dataclass(frozen=True)
class LoadTestConfig:
    toolkit_root: Path
    results_root: Path
    base_url: str
    api_base_url: str
    enabled_roles: tuple[RoleConfig, ...]
    stages: tuple[StageConfig, ...]
    include_login_page_get: bool
    include_dashboard_request: bool
    dashboard_request_mode: ToolkitMode
    request_timeout_seconds: float
    request_delay_seconds: float
    verify_tls: bool
    user_agent: str
    max_connections_multiplier: int
    high_stress_warning_users: int
    hard_concurrency_cap: int
    warnings: tuple[str, ...]


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _env_bool(name: str, default: bool) -> bool:
    raw_value = _env(name, str(default)).lower()
    return raw_value in {"1", "true", "yes", "y", "on"}


def _env_int(name: str, default: int) -> int:
    try:
        return int(_env(name, str(default)))
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(_env(name, str(default)))
    except ValueError:
        return default


def _normalize_url(value: str) -> str:
    return value.rstrip("/")


def _derive_api_base_url(base_url: str) -> str:
    parsed = urlparse(base_url)
    hostname = parsed.hostname or ""
    if not hostname:
        return "http://localhost:3000/api"
    if hostname.startswith("api."):
        api_host = hostname
    elif hostname.startswith("www."):
        api_host = f"api.{hostname[4:]}"
    else:
        api_host = f"api.{hostname}"
    return f"{parsed.scheme or 'https'}://{api_host}/api"


def _parse_stage_token(token: str) -> StageConfig:
    cleaned = token.strip().lower()
    if "x" not in cleaned:
        raise ValueError(f"Invalid stage token: {token!r}. Use the form usersxduration, e.g. 5x30.")
    users_text, duration_text = cleaned.split("x", 1)
    users = int(users_text)
    duration_seconds = int(duration_text)
    if users <= 0 or duration_seconds <= 0:
        raise ValueError(f"Stage values must be positive: {token!r}")
    return StageConfig(users=users, duration_seconds=duration_seconds)


def _parse_stages(raw_value: str) -> tuple[StageConfig, ...]:
    return tuple(_parse_stage_token(token) for token in raw_value.split(",") if token.strip())


def _load_root_project_defaults(toolkit_root: Path) -> dict[str, str]:
    root_config_path = toolkit_root.parent / "config.py"
    if not root_config_path.exists():
        return {}

    spec = importlib.util.spec_from_file_location("root_project_config", root_config_path)
    if spec is None or spec.loader is None:
        return {}

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    defaults = {
        "TARGET_BASE_URL": getattr(module, "BASE_URL", ""),
        "STUDENT_EMAIL": getattr(module, "STUDENT_EMAIL", ""),
        "STUDENT_PASSWORD": getattr(module, "STUDENT_PASSWORD", ""),
        "ORGANIZER_EMAIL": getattr(module, "ORGANIZER_EMAIL", ""),
        "ORGANIZER_PASSWORD": getattr(module, "ORGANIZER_PASSWORD", ""),
        "ADMIN_EMAIL": getattr(module, "ADMIN_EMAIL", ""),
        "ADMIN_PASSWORD": getattr(module, "ADMIN_PASSWORD", ""),
    }
    return {key: str(value).strip() for key, value in defaults.items() if str(value).strip()}


def _apply_root_project_fallbacks(toolkit_root: Path) -> list[str]:
    fallback_values = _load_root_project_defaults(toolkit_root)
    applied_messages: list[str] = []

    for key, value in fallback_values.items():
        if not os.getenv(key):
            os.environ[key] = value
            applied_messages.append(f"{key} was not set, so the toolkit reused the root project config default.")

    return applied_messages


def _build_role(
    *,
    name: str,
    login_page_path: str,
    login_api_path: str,
    dashboard_page_path: str,
    dashboard_api_path: str,
    email_env: str,
    password_env: str,
) -> RoleConfig | None:
    email = _env(email_env)
    password = _env(password_env)
    if not email or not password:
        return None
    return RoleConfig(
        name=name,
        login_page_path=login_page_path,
        login_api_path=login_api_path,
        dashboard_page_path=dashboard_page_path,
        dashboard_api_path=dashboard_api_path,
        credentials=RoleCredentials(email=email, password=password),
    )


def load_config() -> LoadTestConfig:
    toolkit_root = Path(__file__).resolve().parent
    load_dotenv(toolkit_root / ".env", override=False)
    fallback_messages = _apply_root_project_fallbacks(toolkit_root)

    base_url = _normalize_url(_env("TARGET_BASE_URL", "https://batuhanakbasak.com"))
    api_base_url = _normalize_url(_env("TARGET_API_BASE_URL", _derive_api_base_url(base_url)))

    stages = _parse_stages(_env("LOAD_STAGES", "2x15,5x20,10x30"))
    include_login_page_get = _env_bool("INCLUDE_LOGIN_PAGE_GET", True)
    include_dashboard_request = _env_bool("INCLUDE_DASHBOARD_REQUEST", False)
    dashboard_request_mode: ToolkitMode = _env("DASHBOARD_REQUEST_MODE", "off").lower() or "off"  # type: ignore[assignment]
    request_timeout_seconds = _env_float("REQUEST_TIMEOUT_SECONDS", 15.0)
    request_delay_seconds = _env_float("REQUEST_DELAY_SECONDS", 0.25)
    verify_tls = _env_bool("VERIFY_TLS", True)
    user_agent = _env("LOAD_TEST_USER_AGENT", "IBU-Auth-Load-Toolkit/1.0")
    max_connections_multiplier = _env_int("MAX_CONNECTIONS_MULTIPLIER", 4)
    high_stress_warning_users = _env_int("HIGH_STRESS_WARNING_USERS", 25)
    hard_concurrency_cap = _env_int("HARD_CONCURRENCY_CAP", 50)
    allow_high_stress = _env_bool("ALLOW_HIGH_STRESS", False)

    requested_roles = [role.strip().lower() for role in _env("ENABLED_ROLES", "student,organizer,admin").split(",") if role.strip()]

    known_roles: dict[str, RoleConfig | None] = {
        "student": _build_role(
            name="student",
            login_page_path="/student/login",
            login_api_path="/auth/login/student",
            dashboard_page_path=_env("STUDENT_DASHBOARD_PAGE_PATH", "/student/dashboard.html"),
            dashboard_api_path=_env("STUDENT_DASHBOARD_API_PATH", ""),
            email_env="STUDENT_EMAIL",
            password_env="STUDENT_PASSWORD",
        ),
        "organizer": _build_role(
            name="organizer",
            login_page_path="/organizer/organizer-login",
            login_api_path="/auth/login/organizer",
            dashboard_page_path=_env("ORGANIZER_DASHBOARD_PAGE_PATH", "/organizer/dashboard.html"),
            dashboard_api_path=_env("ORGANIZER_DASHBOARD_API_PATH", ""),
            email_env="ORGANIZER_EMAIL",
            password_env="ORGANIZER_PASSWORD",
        ),
        "admin": _build_role(
            name="admin",
            login_page_path="/admin/login",
            login_api_path="/admin/auth/login",
            dashboard_page_path=_env("ADMIN_DASHBOARD_PAGE_PATH", "/admin/dashboard.html"),
            dashboard_api_path=_env("ADMIN_DASHBOARD_API_PATH", ""),
            email_env="ADMIN_EMAIL",
            password_env="ADMIN_PASSWORD",
        ),
    }

    warnings: list[str] = [
        "Use modest defaults first. This toolkit is designed for staged testing, not aggressive production flooding.",
    ]
    warnings.extend(fallback_messages)

    enabled_roles: list[RoleConfig] = []
    for role_name in requested_roles:
        role = known_roles.get(role_name)
        if role is None:
            warnings.append(
                f"Role {role_name!r} is disabled because its credentials were not found in environment variables."
            )
            continue
        enabled_roles.append(role)

    if not enabled_roles:
        raise ValueError(
            "No enabled roles are ready to run. Set STUDENT_EMAIL/STUDENT_PASSWORD, "
            "ORGANIZER_EMAIL/ORGANIZER_PASSWORD, and/or ADMIN_EMAIL/ADMIN_PASSWORD."
        )

    peak_users = max(stage.users for stage in stages)
    if peak_users > high_stress_warning_users:
        warnings.append(
            f"Highest configured concurrency is {peak_users}, which is above the soft warning threshold "
            f"of {high_stress_warning_users} users."
        )

    if peak_users > hard_concurrency_cap and not allow_high_stress:
        raise ValueError(
            f"Configured peak concurrency ({peak_users}) exceeds HARD_CONCURRENCY_CAP ({hard_concurrency_cap}). "
            "Set ALLOW_HIGH_STRESS=true only when you have explicit permission to push harder."
        )

    if include_dashboard_request and dashboard_request_mode == "off":
        warnings.append(
            "INCLUDE_DASHBOARD_REQUEST is enabled but DASHBOARD_REQUEST_MODE is off. Dashboard calls will be skipped."
        )

    if include_dashboard_request and dashboard_request_mode in {"api", "auto"}:
        for role in enabled_roles:
            if not role.dashboard_api_path:
                warnings.append(
                    f"{role.name.title()} dashboard API path is empty. Set {role.name.upper()}_DASHBOARD_API_PATH "
                    "to exercise authenticated API requests after login."
                )

    return LoadTestConfig(
        toolkit_root=toolkit_root,
        results_root=toolkit_root / "results",
        base_url=base_url,
        api_base_url=api_base_url,
        enabled_roles=tuple(enabled_roles),
        stages=stages,
        include_login_page_get=include_login_page_get,
        include_dashboard_request=include_dashboard_request,
        dashboard_request_mode=dashboard_request_mode,
        request_timeout_seconds=request_timeout_seconds,
        request_delay_seconds=request_delay_seconds,
        verify_tls=verify_tls,
        user_agent=user_agent,
        max_connections_multiplier=max_connections_multiplier,
        high_stress_warning_users=high_stress_warning_users,
        hard_concurrency_cap=hard_concurrency_cap,
        warnings=tuple(warnings),
    )

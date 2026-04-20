from __future__ import annotations

import argparse
import asyncio
import sys
import time
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx

from config import LoadTestConfig, RoleConfig, StageConfig, load_config
from report_generator import write_reports


def iso_now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def snapshot_config(config: LoadTestConfig) -> dict[str, Any]:
    return {
        "base_url": config.base_url,
        "api_base_url": config.api_base_url,
        "enabled_roles": [role.name for role in config.enabled_roles],
        "stage_plan": ", ".join(f"{stage.users}x{stage.duration_seconds}" for stage in config.stages),
        "include_login_page_get": config.include_login_page_get,
        "include_dashboard_request": config.include_dashboard_request,
        "dashboard_request_mode": config.dashboard_request_mode,
        "request_timeout_seconds": config.request_timeout_seconds,
        "request_delay_seconds": config.request_delay_seconds,
        "verify_tls": config.verify_tls,
    }


def extract_message(payload: Any) -> str:
    if isinstance(payload, dict):
        if isinstance(payload.get("message"), str):
            return payload["message"]
        errors = payload.get("errors")
        if isinstance(errors, list):
            messages = [str(item.get("message")) for item in errors if isinstance(item, dict) and item.get("message")]
            if messages:
                return "; ".join(messages)
    return ""


def extract_token(payload: Any) -> str:
    candidates = [
        ("data", "access_token"),
        ("data", "token"),
        ("access_token",),
        ("token",),
    ]
    for candidate in candidates:
        value: Any = payload
        for key in candidate:
            if not isinstance(value, dict):
                value = None
                break
            value = value.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def ensure_status_and_payload(response: httpx.Response, payload: Any) -> tuple[bool, str]:
    if response.status_code >= 400:
        return False, extract_message(payload) or f"HTTP {response.status_code}"
    if isinstance(payload, dict) and payload.get("success") is False:
        return False, extract_message(payload) or "API returned success=false"
    return True, ""


class AuthLoadRunner:
    def __init__(self, config: LoadTestConfig) -> None:
        self.config = config
        self.records: list[dict[str, Any]] = []
        self.stage_runs: list[dict[str, Any]] = []
        self.runtime_warnings = list(config.warnings)

    async def run(self) -> dict[str, Path]:
        started_at = iso_now()
        for index, stage in enumerate(self.config.stages, start=1):
            await self.run_stage(index, stage)
        finished_at = iso_now()

        run_dir = self.config.results_root / datetime.now().strftime("%Y%m%d_%H%M%S")
        return write_reports(
            run_dir=run_dir,
            config_snapshot=snapshot_config(self.config),
            stage_runs=self.stage_runs,
            records=self.records,
            warnings=self.runtime_warnings,
            started_at=started_at,
            finished_at=finished_at,
        )

    async def run_stage(self, stage_index: int, stage: StageConfig) -> None:
        print(f"[stage {stage_index}] starting {stage.users} users for {stage.duration_seconds}s")
        limits = httpx.Limits(
            max_connections=max(stage.users * self.config.max_connections_multiplier, 20),
            max_keepalive_connections=max(stage.users, 10),
        )
        headers = {"User-Agent": self.config.user_agent}
        timeout = httpx.Timeout(self.config.request_timeout_seconds)

        stage_name = f"stage_{stage_index}_{stage.name}"
        stage_started = time.perf_counter()
        deadline = stage_started + stage.duration_seconds

        async with httpx.AsyncClient(
            timeout=timeout,
            verify=self.config.verify_tls,
            headers=headers,
            follow_redirects=True,
            limits=limits,
        ) as client:
            tasks = [
                asyncio.create_task(self.worker(client=client, worker_id=worker_id, stage=stage, stage_name=stage_name, deadline=deadline))
                for worker_id in range(stage.users)
            ]
            await asyncio.gather(*tasks)

        actual_duration = round(time.perf_counter() - stage_started, 2)
        self.stage_runs.append(
            {
                "stage_name": stage_name,
                "users": stage.users,
                "planned_duration_seconds": stage.duration_seconds,
                "actual_duration_seconds": actual_duration,
            }
        )
        print(f"[stage {stage_index}] completed in {actual_duration}s")

    async def worker(
        self,
        *,
        client: httpx.AsyncClient,
        worker_id: int,
        stage: StageConfig,
        stage_name: str,
        deadline: float,
    ) -> None:
        iteration = 0
        roles = self.config.enabled_roles

        while time.perf_counter() < deadline:
            role = roles[(worker_id + iteration) % len(roles)]
            iteration += 1
            await self.run_role_flow(
                client=client,
                role=role,
                stage=stage,
                stage_name=stage_name,
                iteration=iteration,
            )
            if self.config.request_delay_seconds > 0:
                await asyncio.sleep(self.config.request_delay_seconds)

    async def run_role_flow(
        self,
        *,
        client: httpx.AsyncClient,
        role: RoleConfig,
        stage: StageConfig,
        stage_name: str,
        iteration: int,
    ) -> None:
        if self.config.include_login_page_get:
            await self.perform_request(
                client=client,
                stage=stage,
                stage_name=stage_name,
                role=role.name,
                request_name=f"{role.name}_login_page",
                method="GET",
                url=f"{self.config.base_url}{role.login_page_path}",
                iteration=iteration,
            )

        login_record, response, payload = await self.perform_request(
            client=client,
            stage=stage,
            stage_name=stage_name,
            role=role.name,
            request_name=f"{role.name}_login_api",
            method="POST",
            url=f"{self.config.api_base_url}{role.login_api_path}",
            json_body={
                "email": role.credentials.email,
                "password": role.credentials.password,
            },
            iteration=iteration,
        )

        if response is None:
            return

        valid, error_message = ensure_status_and_payload(response, payload)
        if not valid:
            login_record["success"] = False
            login_record["error"] = error_message
            return

        token = extract_token(payload)

        if self.config.include_dashboard_request and self.config.dashboard_request_mode != "off":
            await self.request_dashboard(
                client=client,
                role=role,
                stage=stage,
                stage_name=stage_name,
                iteration=iteration,
                token=token,
            )

    async def request_dashboard(
        self,
        *,
        client: httpx.AsyncClient,
        role: RoleConfig,
        stage: StageConfig,
        stage_name: str,
        iteration: int,
        token: str,
    ) -> None:
        mode = self.config.dashboard_request_mode
        if mode == "api":
            await self.request_dashboard_api(
                client=client,
                role=role,
                stage=stage,
                stage_name=stage_name,
                iteration=iteration,
                token=token,
            )
            return

        if mode == "page":
            await self.request_dashboard_page(
                client=client,
                role=role,
                stage=stage,
                stage_name=stage_name,
                iteration=iteration,
            )
            return

        if mode == "auto":
            if role.dashboard_api_path and token:
                await self.request_dashboard_api(
                    client=client,
                    role=role,
                    stage=stage,
                    stage_name=stage_name,
                    iteration=iteration,
                    token=token,
                )
            else:
                await self.request_dashboard_page(
                    client=client,
                    role=role,
                    stage=stage,
                    stage_name=stage_name,
                    iteration=iteration,
                )

    async def request_dashboard_api(
        self,
        *,
        client: httpx.AsyncClient,
        role: RoleConfig,
        stage: StageConfig,
        stage_name: str,
        iteration: int,
        token: str,
    ) -> None:
        if not role.dashboard_api_path:
            self.runtime_warnings.append(
                f"{role.name.title()} dashboard API request was requested but no dashboard API path is configured."
            )
            return
        if not token:
            self.records.append(
                self.build_record(
                    stage=stage,
                    stage_name=stage_name,
                    role=role.name,
                    request_name=f"{role.name}_dashboard_api",
                    method="GET",
                    url=f"{self.config.api_base_url}{role.dashboard_api_path}",
                    status_code=0,
                    success=False,
                    latency_ms=0.0,
                    bytes_received=0,
                    error="Dashboard API request skipped because no auth token was found in the login response.",
                    iteration=iteration,
                )
            )
            return

        await self.perform_request(
            client=client,
            stage=stage,
            stage_name=stage_name,
            role=role.name,
            request_name=f"{role.name}_dashboard_api",
            method="GET",
            url=f"{self.config.api_base_url}{role.dashboard_api_path}",
            headers={"Authorization": f"Bearer {token}"},
            iteration=iteration,
        )

    async def request_dashboard_page(
        self,
        *,
        client: httpx.AsyncClient,
        role: RoleConfig,
        stage: StageConfig,
        stage_name: str,
        iteration: int,
    ) -> None:
        if not role.dashboard_page_path:
            self.runtime_warnings.append(
                f"{role.name.title()} dashboard page request was requested but no dashboard page path is configured."
            )
            return
        await self.perform_request(
            client=client,
            stage=stage,
            stage_name=stage_name,
            role=role.name,
            request_name=f"{role.name}_dashboard_page",
            method="GET",
            url=f"{self.config.base_url}{role.dashboard_page_path}",
            iteration=iteration,
        )

    async def perform_request(
        self,
        *,
        client: httpx.AsyncClient,
        stage: StageConfig,
        stage_name: str,
        role: str,
        request_name: str,
        method: str,
        url: str,
        iteration: int,
        headers: dict[str, str] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> tuple[dict[str, Any], httpx.Response | None, Any]:
        started = time.perf_counter()
        timestamp = iso_now()
        response: httpx.Response | None = None
        payload: Any = None
        status_code = 0
        error = ""
        bytes_received = 0
        success = False

        try:
            response = await client.request(method, url, headers=headers, json=json_body)
            status_code = response.status_code
            bytes_received = len(response.content)
            try:
                payload = response.json()
            except ValueError:
                payload = None
            success, error = ensure_status_and_payload(response, payload)
        except httpx.HTTPError as exc:
            error = str(exc)

        latency_ms = round((time.perf_counter() - started) * 1000, 2)
        record = self.build_record(
            stage=stage,
            stage_name=stage_name,
            role=role,
            request_name=request_name,
            method=method,
            url=url,
            status_code=status_code,
            success=success,
            latency_ms=latency_ms,
            bytes_received=bytes_received,
            error=error,
            iteration=iteration,
            timestamp=timestamp,
        )
        self.records.append(record)
        return record, response, payload

    def build_record(
        self,
        *,
        stage: StageConfig,
        stage_name: str,
        role: str,
        request_name: str,
        method: str,
        url: str,
        status_code: int,
        success: bool,
        latency_ms: float,
        bytes_received: int,
        error: str,
        iteration: int,
        timestamp: str | None = None,
    ) -> dict[str, Any]:
        return {
            "timestamp": timestamp or iso_now(),
            "stage_name": stage_name,
            "stage_users": stage.users,
            "role": role,
            "request_name": request_name,
            "method": method,
            "url": url,
            "status_code": status_code,
            "success": success,
            "latency_ms": latency_ms,
            "bytes_received": bytes_received,
            "error": error,
            "iteration": iteration,
        }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Async Python load/stress toolkit for Student / Organizer / Admin authentication flows."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Load and print the resolved configuration without sending any requests.",
    )
    return parser.parse_args()


async def async_main() -> int:
    args = parse_args()
    config = load_config()

    print("Resolved configuration:")
    print(f"  Base URL: {config.base_url}")
    print(f"  API Base URL: {config.api_base_url}")
    print(f"  Enabled roles: {', '.join(role.name for role in config.enabled_roles)}")
    print(f"  Stages: {', '.join(stage.name for stage in config.stages)}")
    print(f"  Dashboard mode: {config.dashboard_request_mode}")
    if config.warnings:
        print("Warnings:")
        for warning in config.warnings:
            print(f"  - {warning}")

    if args.dry_run:
        return 0

    runner = AuthLoadRunner(config)
    report_paths = await runner.run()

    print("\nArtifacts written:")
    for label, path in report_paths.items():
        print(f"  {label}: {path}")
    return 0


def main() -> int:
    try:
        return asyncio.run(async_main())
    except KeyboardInterrupt:
        print("\nRun cancelled by user.", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"\nLoad test toolkit failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

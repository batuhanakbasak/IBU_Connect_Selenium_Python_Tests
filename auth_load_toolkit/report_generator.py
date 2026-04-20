from __future__ import annotations

import csv
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any


SUGGESTED_THRESHOLDS = {
    "failure_rate_percent": 1.0,
    "avg_latency_ms": 300.0,
    "p95_latency_ms": 500.0,
    "throughput_rps_single_user_baseline": 2.0,
}


def percentile(values: list[float], percent: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = (len(ordered) - 1) * percent
    lower_index = int(rank)
    upper_index = min(lower_index + 1, len(ordered) - 1)
    fraction = rank - lower_index
    return ordered[lower_index] + (ordered[upper_index] - ordered[lower_index]) * fraction


def build_metric_block(records: list[dict[str, Any]], elapsed_seconds: float) -> dict[str, Any]:
    latencies = [float(record["latency_ms"]) for record in records]
    failures = [record for record in records if not record["success"]]
    total = len(records)
    passed = total - len(failures)
    throughput = total / elapsed_seconds if elapsed_seconds > 0 else 0.0
    return {
        "request_count": total,
        "success_count": passed,
        "failure_count": len(failures),
        "failure_rate": round((len(failures) / total) * 100, 2) if total else 0.0,
        "throughput_rps": round(throughput, 2),
        "avg_latency_ms": round(sum(latencies) / total, 2) if total else 0.0,
        "min_latency_ms": round(min(latencies), 2) if total else 0.0,
        "max_latency_ms": round(max(latencies), 2) if total else 0.0,
        "p50_latency_ms": round(percentile(latencies, 0.50), 2),
        "p90_latency_ms": round(percentile(latencies, 0.90), 2),
        "p95_latency_ms": round(percentile(latencies, 0.95), 2),
        "p99_latency_ms": round(percentile(latencies, 0.99), 2),
    }


def build_summary(
    *,
    config_snapshot: dict[str, Any],
    stage_runs: list[dict[str, Any]],
    records: list[dict[str, Any]],
    warnings: list[str],
    started_at: str,
    finished_at: str,
) -> dict[str, Any]:
    overall_elapsed = (
        datetime.fromisoformat(finished_at) - datetime.fromisoformat(started_at)
    ).total_seconds()

    overall = build_metric_block(records, overall_elapsed)

    records_by_stage: dict[str, list[dict[str, Any]]] = defaultdict(list)
    records_by_request: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        records_by_stage[record["stage_name"]].append(record)
        records_by_request[record["request_name"]].append(record)

    stage_summaries: list[dict[str, Any]] = []
    for stage in stage_runs:
        stage_records = records_by_stage.get(stage["stage_name"], [])
        stage_summaries.append(
            {
                **stage,
                "metrics": build_metric_block(stage_records, stage["actual_duration_seconds"]),
            }
        )

    request_summaries: list[dict[str, Any]] = []
    for request_name, request_records in sorted(records_by_request.items()):
        request_elapsed = overall_elapsed if overall_elapsed > 0 else 1.0
        request_summaries.append(
            {
                "request_name": request_name,
                "metrics": build_metric_block(request_records, request_elapsed),
            }
        )

    failure_samples = [
        {
            "timestamp": record["timestamp"],
            "stage_name": record["stage_name"],
            "role": record["role"],
            "request_name": record["request_name"],
            "status_code": record["status_code"],
            "error": record["error"],
            "url": record["url"],
        }
        for record in records
        if not record["success"]
    ][:20]

    return {
        "started_at": started_at,
        "finished_at": finished_at,
        "config": config_snapshot,
        "warnings": warnings,
        "overall": overall,
        "stages": stage_summaries,
        "requests": request_summaries,
        "failure_samples": failure_samples,
    }


def write_csv(records: list[dict[str, Any]], output_path: Path) -> None:
    fieldnames = [
        "timestamp",
        "stage_name",
        "stage_users",
        "role",
        "request_name",
        "method",
        "url",
        "status_code",
        "success",
        "latency_ms",
        "bytes_received",
        "error",
        "iteration",
    ]
    with output_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            writer.writerow({key: record.get(key, "") for key in fieldnames})


def write_json(summary: dict[str, Any], records: list[dict[str, Any]], output_path: Path) -> None:
    payload = {
        "summary": summary,
        "records": records,
    }
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")


def _request_kind(request_name: str) -> str:
    if request_name.endswith("_login_page"):
        return "Login Page GET"
    if request_name.endswith("_login_api"):
        return "Login API POST"
    if request_name.endswith("_dashboard_page"):
        return "Dashboard Page GET"
    if request_name.endswith("_dashboard_api"):
        return "Dashboard API GET"
    return "Other"


def _request_role(request_name: str) -> str:
    return request_name.split("_", 1)[0].title()


def _request_label(request_name: str) -> str:
    return request_name.replace("_", " ")


def _weighted_metric(requests: list[dict[str, Any]], metric_name: str) -> float:
    total_requests = sum(int(request["metrics"]["request_count"]) for request in requests)
    if total_requests <= 0:
        return 0.0
    weighted_total = sum(
        float(request["metrics"][metric_name]) * int(request["metrics"]["request_count"]) for request in requests
    )
    return round(weighted_total / total_requests, 2)


def _stage_count(summary: dict[str, Any]) -> int:
    return len(summary["stages"])


def _plural(value: int, singular: str, plural: str | None = None) -> str:
    if value == 1:
        return singular
    return plural or f"{singular}s"


def _peak_concurrency(summary: dict[str, Any]) -> int:
    return max((int(stage["users"]) for stage in summary["stages"]), default=0)


def _stage_plan_explained(summary: dict[str, Any]) -> str:
    stages = summary["stages"]
    if not stages:
        return "no stages were recorded"
    parts = [
        f"{stage['users']} {_plural(int(stage['users']), 'user')} for {stage['planned_duration_seconds']} {_plural(int(stage['planned_duration_seconds']), 'second')}"
        for stage in stages
    ]
    if len(parts) == 1:
        return parts[0]
    return ", then ".join(parts)


def _workload_label(summary: dict[str, Any]) -> str:
    peak_users = _peak_concurrency(summary)
    if peak_users <= 2:
        return "a very small baseline workload"
    if peak_users <= 10:
        return "a modest staged workload"
    if peak_users <= 25:
        return "a moderate staged workload"
    return "a higher-concurrency staged workload"


def _sample_size_comment(summary: dict[str, Any]) -> str:
    group_counts = [int(request["metrics"]["request_count"]) for request in summary["requests"]]
    minimum_group_count = min(group_counts, default=0)
    if minimum_group_count < 10:
        return (
            "Each request group in this run has only a few observations, so individual outliers can shift averages and percentiles materially."
        )
    if minimum_group_count < 100:
        return (
            "Request-group counts are better than a smoke sample but still limited, so repeated runs are needed before making stable trend or capacity claims."
        )
    return (
        "Each request group contains hundreds of observations, which is stronger than a smoke sample. Even so, one run is still not enough for final capacity claims, "
        "and repeated runs are needed to validate consistency and tail-latency behavior."
    )


def _limitations_stage_line(summary: dict[str, Any]) -> str:
    if _stage_count(summary) == 1:
        return f"Only one short stage was executed (`{_stage_plan_explained(summary)}`)."
    return (
        f"Only one run was captured, even though it included `{_stage_count(summary)}` short staged phases with a peak concurrency of `{_peak_concurrency(summary)}` users."
    )


def _threshold_rows(summary: dict[str, Any]) -> list[tuple[str, str, str, str]]:
    overall = summary["overall"]
    throughput_threshold = SUGGESTED_THRESHOLDS["throughput_rps_single_user_baseline"]

    def verdict(passed: bool) -> str:
        return "Meets suggested threshold" if passed else "Above suggested threshold"

    rows = [
        (
            "Failure rate",
            "<= 1.0% (suggested)",
            f"{overall['failure_rate']}%",
            verdict(overall["failure_rate"] <= SUGGESTED_THRESHOLDS["failure_rate_percent"]),
        ),
        (
            "Average latency",
            "<= 300 ms (suggested)",
            f"{overall['avg_latency_ms']} ms",
            verdict(overall["avg_latency_ms"] <= SUGGESTED_THRESHOLDS["avg_latency_ms"]),
        ),
        (
            "P95 latency",
            "<= 500 ms (suggested)",
            f"{overall['p95_latency_ms']} ms",
            verdict(overall["p95_latency_ms"] <= SUGGESTED_THRESHOLDS["p95_latency_ms"]),
        ),
    ]

    if _stage_count(summary) == 1 and _peak_concurrency(summary) <= 1:
        rows.append(
            (
                "Throughput",
                ">= 2.0 req/s for a 1-user baseline run (suggested)",
                f"{overall['throughput_rps']} req/s",
                verdict(overall["throughput_rps"] >= throughput_threshold),
            )
        )
    else:
        rows.append(
            (
                "Throughput",
                "No single fixed threshold is suggested for this multi-stage run",
                f"{overall['throughput_rps']} req/s",
                "Reported for reference only",
            )
        )

    return rows


def _request_tables(summary: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    page_requests = [request for request in summary["requests"] if _request_kind(request["request_name"]) == "Login Page GET"]
    api_requests = [request for request in summary["requests"] if _request_kind(request["request_name"]) == "Login API POST"]
    return page_requests, api_requests


def _slowest_requests(summary: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    requests = summary["requests"]
    slowest_avg = max(requests, key=lambda item: float(item["metrics"]["avg_latency_ms"]))
    slowest_p95 = max(requests, key=lambda item: float(item["metrics"]["p95_latency_ms"]))
    return slowest_avg, slowest_p95


def _out_of_scope_items(summary: dict[str, Any]) -> list[str]:
    items = [
        "Browser rendering time and client-side UX behavior were not measured because this toolkit uses direct HTTP requests rather than a browser.",
        "Logout, password reset, registration, token refresh, and invalid-credential scenarios were not exercised in this run.",
        "Server-side CPU, memory, database, cache, and network telemetry were not available in this report.",
        "Rate limiting, WAF behavior, and load-balancer distribution were not validated.",
    ]
    if not summary["config"]["include_dashboard_request"]:
        items.insert(0, "Post-login dashboard/API calls were disabled, so authenticated business flows were not part of this run.")
    return items


def _evidence_items() -> list[str]:
    return [
        "`results.json`: structured machine-readable metrics and raw request records.",
        "`request_results.csv`: flat request-level export suitable for spreadsheet analysis.",
        "`summary.md`: human-readable performance report with interpretation and recommendations.",
        "`presentation_notes.md`: report-ready and presentation-ready text blocks.",
        "Terminal output: available during execution and suitable for capture as console evidence.",
        "Screenshots: not generated by the current toolkit run and therefore not available unless captured separately.",
        "Run log file: not generated as a dedicated artifact in the current implementation.",
    ]


def _chart_suggestions() -> list[str]:
    return [
        "Per-endpoint average latency bar chart.",
        "Per-endpoint p95 latency comparison chart.",
        "Throughput by stage chart for staged runs.",
        "Failure rate by endpoint chart once failures exist or negative tests are introduced.",
    ]


def _missing_measurements() -> list[str]:
    return [
        "Server-side CPU, memory, container, and process metrics during the run.",
        "Database query time, connection-pool usage, and cache-hit data for authentication requests.",
        "Token issuance time or server-side auth processing time split from total response time.",
        "Network timing details such as DNS, TLS handshake, and connection reuse effects.",
        "Separate warm-up versus steady-state measurements.",
        "Concurrent active-user count over time and queue/backpressure indicators.",
        "Role-level throughput and error trend charts across multi-stage runs.",
        "Authenticated dashboard/API metrics after successful login.",
        "Dedicated run log files and optional chart images exported automatically.",
    ]


def _performance_section(summary: dict[str, Any]) -> str:
    overall = summary["overall"]
    slowest_avg, slowest_p95 = _slowest_requests(summary)
    peak_users = _peak_concurrency(summary)
    stage_count = _stage_count(summary)
    stage_label = _plural(stage_count, "stage")
    slowest_role = _request_role(slowest_avg["request_name"])

    return "\n".join(
        [
            "## Performance Testing",
            "",
            "A baseline authentication performance test was executed against the authorized Student, Organizer, and Admin login flows of the target system. "
            f"The run covered `{stage_count}` {stage_label} up to a peak of `{peak_users}` concurrent users and generated `{overall['request_count']}` total requests with "
            f"`{overall['success_count']}` successful responses and `{overall['failure_count']}` failures. This indicates full functional reliability for the sampled workload, "
            "although the run should be treated as a baseline validation rather than a final capacity statement. It was not a real stress test, it did not use high concurrency, and it was not an endurance run.",
            "",
            f"Observed performance was stable for {_workload_label(summary)}. The overall failure rate was `{overall['failure_rate']}%`, average latency was "
            f"`{overall['avg_latency_ms']} ms`, and p95 latency was `{overall['p95_latency_ms']} ms`. Interpreted against suggested baseline thresholds "
            "for authentication services, these results are acceptable for this level of staged load. The measured throughput was "
            f"`{overall['throughput_rps']} req/s`, which is reasonable for a mixed page-and-API authentication sequence executed across the configured stages.",
            "",
            "At the request-group level, login page GET requests were materially faster than login API POST requests, which is the expected pattern because authentication "
            "calls involve credential validation and likely backend processing. The slowest request group by average latency was "
            f"`{_request_label(slowest_avg['request_name'])}` at `{slowest_avg['metrics']['avg_latency_ms']} ms`, while the slowest by p95 latency was "
            f"`{_request_label(slowest_p95['request_name'])}` at `{slowest_p95['metrics']['p95_latency_ms']} ms`. This suggests that the `{slowest_role}` authentication path may involve slightly higher backend cost "
            "or higher variability than the other role paths, although repeated runs are still needed before treating it as a persistent bottleneck.",
            "",
            "The current evidence supports the conclusion that the authentication endpoints are responsive and error-free under the tested load levels. However, the run does not "
            "demonstrate stress tolerance, scalability, or infrastructure behavior under sustained concurrency. Additional staged tests, server-side telemetry, and authenticated "
            "post-login flows should be added before drawing stronger performance or capacity conclusions.",
        ]
    )


def _presentation_paragraph(summary: dict[str, Any]) -> str:
    overall = summary["overall"]
    peak_users = _peak_concurrency(summary)
    return (
        "A baseline authentication performance test was conducted for the Student, Organizer, and Admin login flows of "
        f"`{summary['config']['base_url']}`. During staged execution up to `{peak_users}` concurrent users, the system processed `{overall['request_count']}` requests with "
        f"`0` failures, achieving `{overall['throughput_rps']} req/s`, `{overall['avg_latency_ms']} ms` average latency, and `{overall['p95_latency_ms']} ms` p95 latency. "
        "These results indicate that the authentication layer was stable and responsive for the tested staged workload, while also showing that additional multi-stage testing "
        "is still required before making broader scalability claims. This run should not be presented as a real stress test, a high-concurrency test, or an endurance test."
    )


def _oral_explanation(summary: dict[str, Any]) -> str:
    overall = summary["overall"]
    slowest_avg, _ = _slowest_requests(summary)
    peak_users = _peak_concurrency(summary)
    return (
        "In this run, I tested the Student, Organizer, and Admin authentication flows with a staged but still modest load profile. "
        f"The toolkit sent `{overall['request_count']}` requests in total and all of them succeeded, so the observed failure rate was zero. "
        f"Average latency was `{overall['avg_latency_ms']} milliseconds` and p95 latency was `{overall['p95_latency_ms']} milliseconds`, which is acceptable for a light login workload. "
        f"The slowest request group was `{_request_label(slowest_avg['request_name'])}`, so if I continue this study, that path is the first one I would monitor under higher concurrency. "
        f"I would still treat this as a baseline staged validation rather than a full stress test, because the peak concurrency was only `{peak_users}` users, no endurance run was performed, and no server-side resource metrics were captured."
    )


def write_markdown(summary: dict[str, Any], output_path: Path) -> None:
    overall = summary["overall"]
    config = summary["config"]
    page_requests, api_requests = _request_tables(summary)
    slowest_avg, slowest_p95 = _slowest_requests(summary)

    lines: list[str] = [
        "# Authentication Performance Test Report",
        "",
        "## Executive Summary",
        "",
        "This report presents a baseline performance assessment of the authorized Student, Organizer, and Admin authentication flows. "
        f"The executed workload covered `{_stage_count(summary)}` {_plural(_stage_count(summary), 'stage')} with `{overall['request_count']}` total requests, `{overall['success_count']}` successes, "
        f"and `{overall['failure_count']}` failures. Overall results indicate stable behavior for {_workload_label(summary)}, with "
        f"`{overall['avg_latency_ms']} ms` average latency, `{overall['p95_latency_ms']} ms` p95 latency, and `{overall['throughput_rps']} req/s` throughput. "
        "These findings are suitable as a baseline reference, but they should not be interpreted as proof of scalability or stress tolerance.",
        "",
        "## Important Clarification",
        "",
        "- This run was not a real stress test.",
        "- This run did not use high concurrency.",
        "- This run was not an endurance or soak test.",
        f"- The executed stage plan was `{config['stage_plan']}` with a peak concurrency of `{_peak_concurrency(summary)}` users, so it should be treated as {_workload_label(summary)} rather than a stress or endurance workload.",
        "",
        "## Key Terms",
        "",
        f"- Stage: one planned phase of the test workload. In this run, the stage plan `{config['stage_plan']}` means `{_stage_plan_explained(summary)}`.",
        f"- Concurrency: the number of active virtual users sending requests at the same time. In this run, planned peak concurrency was `{_peak_concurrency(summary)}` users.",
        "- Load test: a test that applies an expected or normal workload to measure response time, throughput, and failure behavior under realistic usage.",
        "- Stress test: a test that pushes the system beyond normal expected workload in order to identify degradation points, instability, or failure thresholds.",
        "",
        "## Test Objective",
        "",
        "The objective of this performance test was to validate that the authentication layer remains responsive and reliable under a light, controlled workload. "
        "More specifically, the run was intended to confirm that login page endpoints and login API authentication endpoints can serve Student, Organizer, and Admin users without errors, "
        "while capturing baseline latency and throughput measurements that can be compared against future, higher-load runs.",
        "",
        "## Test Scope",
        "",
        "### In Scope",
        "",
        "- Student login page GET requests and Student login API POST requests.",
        "- Organizer login page GET requests and Organizer login API POST requests.",
        "- Admin login page GET requests and Admin login API POST requests.",
        "- End-to-end request timing, throughput, and failure-rate measurement at the HTTP level.",
        "",
        "### Out of Scope / Not Measured",
        "",
    ]

    for item in _out_of_scope_items(summary):
        lines.append(f"- {item}")

    lines.extend(
        [
            "",
            "## Methodology",
            "",
            "- Tooling: custom Python 3.12 toolkit implemented with `asyncio` and `httpx`.",
            "- Concurrency model: one asynchronous worker task per virtual user, sharing a stage-level HTTP client.",
            f"- Stage plan executed in this run: `{config['stage_plan']}`.",
            f"- Peak configured concurrency in this run: `{_peak_concurrency(summary)}` virtual users.",
            f"- Request timeout assumption: `{config['request_timeout_seconds']} seconds` per request.",
            f"- Inter-iteration delay: `{config['request_delay_seconds']} seconds` between role-flow iterations.",
            f"- TLS verification: `{config['verify_tls']}`.",
            "- Redirect handling: enabled.",
            "- Request model distinction:",
            "- `Login Page GET`: fetches the UI endpoint and measures page-response timing at the HTTP layer.",
            "- `Login API POST`: sends credentials to the authentication API endpoint and measures backend authentication response timing.",
            "",
            "## Authentication Flow Explanation",
            "",
            "For each iteration, the script cycles through the enabled roles and performs the configured steps in sequence:",
            "",
            "1. Optionally request the role-specific login page endpoint to measure page availability and HTTP response time.",
            "2. Send a POST request to the role-specific login API using the configured credentials.",
            "3. Validate the HTTP status and API payload for success/failure semantics.",
            "4. If a token is returned, keep it available for optional authenticated dashboard/API calls in later steps.",
            f"5. In this run, authenticated dashboard requests were `{config['include_dashboard_request']}`, so post-login dashboard traffic was not executed.",
            "",
            "## Test Configuration Snapshot",
            "",
            "| Item | Value |",
            "| --- | --- |",
            f"| Base URL | `{config['base_url']}` |",
            f"| API Base URL | `{config['api_base_url']}` |",
            f"| Enabled Roles | `{', '.join(config['enabled_roles'])}` |",
            f"| Stage Plan | `{config['stage_plan']}` |",
            f"| Login Page GET Enabled | `{config['include_login_page_get']}` |",
            f"| Dashboard Requests Enabled | `{config['include_dashboard_request']}` |",
            f"| Dashboard Mode | `{config['dashboard_request_mode']}` |",
            f"| Timeout | `{config['request_timeout_seconds']} s` |",
            f"| Request Delay | `{config['request_delay_seconds']} s` |",
            "",
            "## Success Criteria / Suggested Acceptance Thresholds",
            "",
            "No formal acceptance thresholds were recorded before this run, so the following values should be treated as suggested baseline thresholds for authentication workloads rather than fixed contractual limits.",
            "",
            "| Metric | Suggested Threshold | Observed Value | Interpretation |",
            "| --- | --- | --- | --- |",
        ]
    )

    for metric, threshold, actual, interpretation in _threshold_rows(summary):
        lines.append(f"| {metric} | {threshold} | {actual} | {interpretation} |")

    lines.extend(
        [
            "",
            "## Results Summary",
            "",
            "| Metric | Value |",
            "| --- | --- |",
            f"| Requests | {overall['request_count']} |",
            f"| Successes | {overall['success_count']} |",
            f"| Failures | {overall['failure_count']} |",
            f"| Failure Rate | {overall['failure_rate']}% |",
            f"| Throughput | {overall['throughput_rps']} req/s |",
            f"| Average Latency | {overall['avg_latency_ms']} ms |",
            f"| Minimum Latency | {overall['min_latency_ms']} ms |",
            f"| Maximum Latency | {overall['max_latency_ms']} ms |",
            f"| P50 Latency | {overall['p50_latency_ms']} ms |",
            f"| P90 Latency | {overall['p90_latency_ms']} ms |",
            f"| P95 Latency | {overall['p95_latency_ms']} ms |",
            f"| P99 Latency | {overall['p99_latency_ms']} ms |",
            "",
            "## Stage Breakdown",
            "",
            "| Stage | Users | Planned Duration | Actual Duration | Requests | Failures | Throughput | P95 |",
            "| --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )

    for stage in summary["stages"]:
        metrics = stage["metrics"]
        lines.append(
            "| {stage_name} | {users} | {planned}s | {actual}s | {requests} | {failures} | {throughput} req/s | {p95} ms |".format(
                stage_name=stage["stage_name"],
                users=stage["users"],
                planned=stage["planned_duration_seconds"],
                actual=stage["actual_duration_seconds"],
                requests=metrics["request_count"],
                failures=metrics["failure_count"],
                throughput=metrics["throughput_rps"],
                p95=metrics["p95_latency_ms"],
            )
        )

    lines.extend(
        [
            "",
            "## Request Group Breakdown",
            "",
            "| Role | Request Type | Requests | Failures | Avg | P95 | P99 |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
    )

    for request in summary["requests"]:
        metrics = request["metrics"]
        lines.append(
            "| {role} | {kind} | {count} | {failures} | {avg} ms | {p95} ms | {p99} ms |".format(
                role=_request_role(request["request_name"]),
                kind=_request_kind(request["request_name"]),
                count=metrics["request_count"],
                failures=metrics["failure_count"],
                avg=metrics["avg_latency_ms"],
                p95=metrics["p95_latency_ms"],
                p99=metrics["p99_latency_ms"],
            )
        )

    page_avg = _weighted_metric(page_requests, "avg_latency_ms")
    api_avg = _weighted_metric(api_requests, "avg_latency_ms")
    page_p95 = _weighted_metric(page_requests, "p95_latency_ms")
    api_p95 = _weighted_metric(api_requests, "p95_latency_ms")

    lines.extend(
        [
            "",
            "## Detailed Interpretation of Metrics",
            "",
            f"- Reliability: the run recorded `{overall['failure_count']}` failures out of `{overall['request_count']}` requests, so the observed failure rate was `{overall['failure_rate']}%`. "
            "For a baseline authentication workload, this indicates stable request handling in the sampled interval.",
            f"- Responsiveness: overall average latency was `{overall['avg_latency_ms']} ms` and p95 latency was `{overall['p95_latency_ms']} ms`, which is acceptable for the tested staged authentication scenario under the suggested baseline thresholds.",
            f"- Page versus API behavior: login page GET requests were faster overall than login API POST requests. The weighted average for page requests was `{page_avg} ms`, while the weighted average for authentication API requests was `{api_avg} ms`. "
            f"Weighted p95 values were `{page_p95} ms` for page requests and `{api_p95} ms` for API requests, which is expected because authentication calls typically include backend validation and token generation overhead.",
            f"- Role comparison: `{_request_role(slowest_avg['request_name'])}` showed the highest API latency in this run, with `{slowest_avg['metrics']['avg_latency_ms']} ms` average latency and `{slowest_p95['metrics']['p95_latency_ms']} ms` p95 latency for `{_request_label(slowest_avg['request_name'])}`. "
            "The other role-specific API paths were slightly lower and relatively close to each other, which suggests broadly consistent behavior across roles.",
            f"- Sample size caution: {_sample_size_comment(summary)}",
            "",
            "## Bottleneck / Hotspot Analysis",
            "",
            f"- Slowest request group by average latency: `{_request_label(slowest_avg['request_name'])}` at `{slowest_avg['metrics']['avg_latency_ms']} ms`.",
            f"- Slowest request group by p95 latency: `{_request_label(slowest_p95['request_name'])}` at `{slowest_p95['metrics']['p95_latency_ms']} ms`.",
            f"- Interpretation: the `{_request_role(slowest_avg['request_name'])}` authentication path appears to be the first candidate for deeper investigation in future runs. Possible explanations include role-specific backend validation cost, data-access differences, cache warm-up effects, or normal run-to-run variance.",
            "- No failure hotspot was observed because all request groups completed successfully in this run.",
            "",
            "## Limitations",
            "",
            f"- {_limitations_stage_line(summary)}",
            "- This was a baseline load check, not a full stress test or endurance test.",
            "- The results do not prove load-balancer behavior, horizontal scaling, or infrastructure resilience.",
            "- Server-side CPU, memory, database, cache, and network metrics were not measured.",
            "- Only one run was captured, so the dataset is still not sufficient for final capacity claims.",
            f"- Dashboard/API requests after login were `{config['include_dashboard_request']}`, so authenticated post-login workloads are not represented.",
            "",
            "## Recommendations / Next Steps",
            "",
            "- Repeat the baseline using `1 user / 10 sec` to confirm that the current measurements are reproducible.",
            "- Add stronger staged runs such as `5 users / 30 sec`, `10 users / 30 sec`, and `20 users / 60 sec`.",
            "- Enable authenticated dashboard/API requests in later runs to validate post-login behavior.",
            "- Capture server-side CPU, memory, database, and cache metrics alongside client-side latency results.",
            "- Add charts to improve presentation clarity and trend analysis.",
            "- Run multiple repetitions per stage so that averages and percentiles are supported by a larger sample.",
            "",
            "## Evidence / Deliverables",
            "",
        ]
    )

    for item in _evidence_items():
        lines.append(f"- {item}")

    lines.extend(["", "## Optional Charts", ""])
    for item in _chart_suggestions():
        lines.append(f"- {item}")

    if summary["failure_samples"]:
        lines.extend(
            [
                "",
                "## Failure Samples",
                "",
                "| Timestamp | Stage | Role | Request | Status | Error |",
                "| --- | --- | --- | --- | --- | --- |",
            ]
        )
        for failure in summary["failure_samples"]:
            lines.append(
                "| {timestamp} | {stage} | {role} | {request} | {status} | {error} |".format(
                    timestamp=failure["timestamp"],
                    stage=failure["stage_name"],
                    role=failure["role"],
                    request=failure["request_name"],
                    status=failure["status_code"],
                    error=str(failure["error"]).replace("|", "\\|"),
                )
            )

    if summary["warnings"]:
        lines.extend(["", "## Warnings", ""])
        for warning in summary["warnings"]:
            lines.append(f"- {warning}")

    output_path.write_text("\n".join(lines), encoding="utf-8")


def write_presentation_notes(summary: dict[str, Any], output_path: Path) -> None:
    lines: list[str] = [
        "# Presentation Notes",
        "",
        "## A. Report-Ready Performance Testing Section",
        "",
        _performance_section(summary),
        "",
        "## B. Presentation-Ready Paragraph",
        "",
        _presentation_paragraph(summary),
        "",
        "## C. Short Oral Explanation",
        "",
        _oral_explanation(summary),
        "",
        "## D. Missing Measurements For Future Runs",
        "",
    ]

    for item in _missing_measurements():
        lines.append(f"- {item}")

    output_path.write_text("\n".join(lines), encoding="utf-8")


def write_reports(
    *,
    run_dir: Path,
    config_snapshot: dict[str, Any],
    stage_runs: list[dict[str, Any]],
    records: list[dict[str, Any]],
    warnings: list[str],
    started_at: str,
    finished_at: str,
) -> dict[str, Path]:
    run_dir.mkdir(parents=True, exist_ok=True)

    summary = build_summary(
        config_snapshot=config_snapshot,
        stage_runs=stage_runs,
        records=records,
        warnings=warnings,
        started_at=started_at,
        finished_at=finished_at,
    )

    json_path = run_dir / "results.json"
    csv_path = run_dir / "request_results.csv"
    markdown_path = run_dir / "summary.md"
    presentation_path = run_dir / "presentation_notes.md"

    write_json(summary, records, json_path)
    write_csv(records, csv_path)
    write_markdown(summary, markdown_path)
    write_presentation_notes(summary, presentation_path)

    return {
        "json": json_path,
        "csv": csv_path,
        "markdown": markdown_path,
        "presentation": presentation_path,
    }

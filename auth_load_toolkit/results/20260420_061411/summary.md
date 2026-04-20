# Authentication Performance Test Report

## Executive Summary

This report presents a baseline performance assessment of the authorized Student, Organizer, and Admin authentication flows. The executed workload covered `3` stages with `1582` total requests, `1582` successes, and `0` failures. Overall results indicate stable behavior for a modest staged workload, with `144.85 ms` average latency, `272.6 ms` p95 latency, and `23.97 req/s` throughput. These findings are suitable as a baseline reference, but they should not be interpreted as proof of scalability or stress tolerance.

## Important Clarification

- This run was not a real stress test.
- This run did not use high concurrency.
- This run was not an endurance or soak test.
- The executed stage plan was `2x15, 5x20, 10x30` with a peak concurrency of `10` users, so it should be treated as a modest staged workload rather than a stress or endurance workload.

## Key Terms

- Stage: one planned phase of the test workload. In this run, the stage plan `2x15, 5x20, 10x30` means `2 users for 15 seconds, then 5 users for 20 seconds, then 10 users for 30 seconds`.
- Concurrency: the number of active virtual users sending requests at the same time. In this run, planned peak concurrency was `10` users.
- Load test: a test that applies an expected or normal workload to measure response time, throughput, and failure behavior under realistic usage.
- Stress test: a test that pushes the system beyond normal expected workload in order to identify degradation points, instability, or failure thresholds.

## Test Objective

The objective of this performance test was to validate that the authentication layer remains responsive and reliable under a light, controlled workload. More specifically, the run was intended to confirm that login page endpoints and login API authentication endpoints can serve Student, Organizer, and Admin users without errors, while capturing baseline latency and throughput measurements that can be compared against future, higher-load runs.

## Test Scope

### In Scope

- Student login page GET requests and Student login API POST requests.
- Organizer login page GET requests and Organizer login API POST requests.
- Admin login page GET requests and Admin login API POST requests.
- End-to-end request timing, throughput, and failure-rate measurement at the HTTP level.

### Out of Scope / Not Measured

- Post-login dashboard/API calls were disabled, so authenticated business flows were not part of this run.
- Browser rendering time and client-side UX behavior were not measured because this toolkit uses direct HTTP requests rather than a browser.
- Logout, password reset, registration, token refresh, and invalid-credential scenarios were not exercised in this run.
- Server-side CPU, memory, database, cache, and network telemetry were not available in this report.
- Rate limiting, WAF behavior, and load-balancer distribution were not validated.

## Methodology

- Tooling: custom Python 3.12 toolkit implemented with `asyncio` and `httpx`.
- Concurrency model: one asynchronous worker task per virtual user, sharing a stage-level HTTP client.
- Stage plan executed in this run: `2x15, 5x20, 10x30`.
- Peak configured concurrency in this run: `10` virtual users.
- Request timeout assumption: `15.0 seconds` per request.
- Inter-iteration delay: `0.25 seconds` between role-flow iterations.
- TLS verification: `True`.
- Redirect handling: enabled.
- Request model distinction:
- `Login Page GET`: fetches the UI endpoint and measures page-response timing at the HTTP layer.
- `Login API POST`: sends credentials to the authentication API endpoint and measures backend authentication response timing.

## Authentication Flow Explanation

For each iteration, the script cycles through the enabled roles and performs the configured steps in sequence:

1. Optionally request the role-specific login page endpoint to measure page availability and HTTP response time.
2. Send a POST request to the role-specific login API using the configured credentials.
3. Validate the HTTP status and API payload for success/failure semantics.
4. If a token is returned, keep it available for optional authenticated dashboard/API calls in later steps.
5. In this run, authenticated dashboard requests were `False`, so post-login dashboard traffic was not executed.

## Test Configuration Snapshot

| Item | Value |
| --- | --- |
| Base URL | `https://batuhanakbasak.com` |
| API Base URL | `https://api.batuhanakbasak.com/api` |
| Enabled Roles | `student, organizer, admin` |
| Stage Plan | `2x15, 5x20, 10x30` |
| Login Page GET Enabled | `True` |
| Dashboard Requests Enabled | `False` |
| Dashboard Mode | `off` |
| Timeout | `15.0 s` |
| Request Delay | `0.25 s` |

## Success Criteria / Suggested Acceptance Thresholds

No formal acceptance thresholds were recorded before this run, so the following values should be treated as suggested baseline thresholds for authentication workloads rather than fixed contractual limits.

| Metric | Suggested Threshold | Observed Value | Interpretation |
| --- | --- | --- | --- |
| Failure rate | <= 1.0% (suggested) | 0.0% | Meets suggested threshold |
| Average latency | <= 300 ms (suggested) | 144.85 ms | Meets suggested threshold |
| P95 latency | <= 500 ms (suggested) | 272.6 ms | Meets suggested threshold |
| Throughput | No single fixed threshold is suggested for this multi-stage run | 23.97 req/s | Reported for reference only |

## Results Summary

| Metric | Value |
| --- | --- |
| Requests | 1582 |
| Successes | 1582 |
| Failures | 0 |
| Failure Rate | 0.0% |
| Throughput | 23.97 req/s |
| Average Latency | 144.85 ms |
| Minimum Latency | 38.96 ms |
| Maximum Latency | 568.88 ms |
| P50 Latency | 207.88 ms |
| P90 Latency | 239.23 ms |
| P95 Latency | 272.6 ms |
| P99 Latency | 346.06 ms |

## Stage Breakdown

| Stage | Users | Planned Duration | Actual Duration | Requests | Failures | Throughput | P95 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| stage_1_2u_15s | 2 | 15s | 15.5s | 112 | 0 | 7.23 req/s | 240.47 ms |
| stage_2_5u_20s | 5 | 20s | 20.42s | 362 | 0 | 17.73 req/s | 278.09 ms |
| stage_3_10u_30s | 10 | 30s | 30.59s | 1108 | 0 | 36.22 req/s | 271.7 ms |

## Request Group Breakdown

| Role | Request Type | Requests | Failures | Avg | P95 | P99 |
| --- | --- | --- | --- | --- | --- | --- |
| Admin | Login API POST | 262 | 0 | 233.17 ms | 285.62 ms | 370.9 ms |
| Admin | Login Page GET | 262 | 0 | 52.45 ms | 137.56 ms | 157.14 ms |
| Organizer | Login API POST | 264 | 0 | 236.54 ms | 291.19 ms | 352.99 ms |
| Organizer | Login Page GET | 264 | 0 | 56.59 ms | 138.42 ms | 175.0 ms |
| Student | Login API POST | 265 | 0 | 237.02 ms | 300.42 ms | 424.44 ms |
| Student | Login Page GET | 265 | 0 | 53.29 ms | 136.01 ms | 161.9 ms |

## Detailed Interpretation of Metrics

- Reliability: the run recorded `0` failures out of `1582` requests, so the observed failure rate was `0.0%`. For a baseline authentication workload, this indicates stable request handling in the sampled interval.
- Responsiveness: overall average latency was `144.85 ms` and p95 latency was `272.6 ms`, which is acceptable for the tested staged authentication scenario under the suggested baseline thresholds.
- Page versus API behavior: login page GET requests were faster overall than login API POST requests. The weighted average for page requests was `54.11 ms`, while the weighted average for authentication API requests was `235.58 ms`. Weighted p95 values were `137.33 ms` for page requests and `292.44 ms` for API requests, which is expected because authentication calls typically include backend validation and token generation overhead.
- Role comparison: `Student` showed the highest API latency in this run, with `237.02 ms` average latency and `300.42 ms` p95 latency for `student login api`. The other role-specific API paths were slightly lower and relatively close to each other, which suggests broadly consistent behavior across roles.
- Sample size caution: Each request group contains hundreds of observations, which is stronger than a smoke sample. Even so, one run is still not enough for final capacity claims, and repeated runs are needed to validate consistency and tail-latency behavior.

## Bottleneck / Hotspot Analysis

- Slowest request group by average latency: `student login api` at `237.02 ms`.
- Slowest request group by p95 latency: `student login api` at `300.42 ms`.
- Interpretation: the `Student` authentication path appears to be the first candidate for deeper investigation in future runs. Possible explanations include role-specific backend validation cost, data-access differences, cache warm-up effects, or normal run-to-run variance.
- No failure hotspot was observed because all request groups completed successfully in this run.

## Limitations

- Only one run was captured, even though it included `3` short staged phases with a peak concurrency of `10` users.
- This was a baseline load check, not a full stress test or endurance test.
- The results do not prove load-balancer behavior, horizontal scaling, or infrastructure resilience.
- Server-side CPU, memory, database, cache, and network metrics were not measured.
- Only one run was captured, so the dataset is still not sufficient for final capacity claims.
- Dashboard/API requests after login were `False`, so authenticated post-login workloads are not represented.

## Recommendations / Next Steps

- Repeat the baseline using `1 user / 10 sec` to confirm that the current measurements are reproducible.
- Add stronger staged runs such as `5 users / 30 sec`, `10 users / 30 sec`, and `20 users / 60 sec`.
- Enable authenticated dashboard/API requests in later runs to validate post-login behavior.
- Capture server-side CPU, memory, database, and cache metrics alongside client-side latency results.
- Add charts to improve presentation clarity and trend analysis.
- Run multiple repetitions per stage so that averages and percentiles are supported by a larger sample.

## Evidence / Deliverables

- `results.json`: structured machine-readable metrics and raw request records.
- `request_results.csv`: flat request-level export suitable for spreadsheet analysis.
- `summary.md`: human-readable performance report with interpretation and recommendations.
- `presentation_notes.md`: report-ready and presentation-ready text blocks.
- Terminal output: available during execution and suitable for capture as console evidence.
- Screenshots: not generated by the current toolkit run and therefore not available unless captured separately.
- Run log file: not generated as a dedicated artifact in the current implementation.

## Optional Charts

- Per-endpoint average latency bar chart.
- Per-endpoint p95 latency comparison chart.
- Throughput by stage chart for staged runs.
- Failure rate by endpoint chart once failures exist or negative tests are introduced.

## Warnings

- Use modest defaults first. This toolkit is designed for staged testing, not aggressive production flooding.
- TARGET_BASE_URL was not set, so the toolkit reused the root project config default.
- STUDENT_EMAIL was not set, so the toolkit reused the root project config default.
- STUDENT_PASSWORD was not set, so the toolkit reused the root project config default.
- ORGANIZER_EMAIL was not set, so the toolkit reused the root project config default.
- ORGANIZER_PASSWORD was not set, so the toolkit reused the root project config default.
- ADMIN_EMAIL was not set, so the toolkit reused the root project config default.
- ADMIN_PASSWORD was not set, so the toolkit reused the root project config default.
# Presentation Notes

## A. Report-Ready Performance Testing Section

## Performance Testing

A baseline authentication performance test was executed against the authorized Student, Organizer, and Admin login flows of the target system. The run covered `3` stages up to a peak of `10` concurrent users and generated `1582` total requests with `1582` successful responses and `0` failures. This indicates full functional reliability for the sampled workload, although the run should be treated as a baseline validation rather than a final capacity statement. It was not a real stress test, it did not use high concurrency, and it was not an endurance run.

Observed performance was stable for a modest staged workload. The overall failure rate was `0.0%`, average latency was `144.85 ms`, and p95 latency was `272.6 ms`. Interpreted against suggested baseline thresholds for authentication services, these results are acceptable for this level of staged load. The measured throughput was `23.97 req/s`, which is reasonable for a mixed page-and-API authentication sequence executed across the configured stages.

At the request-group level, login page GET requests were materially faster than login API POST requests, which is the expected pattern because authentication calls involve credential validation and likely backend processing. The slowest request group by average latency was `student login api` at `237.02 ms`, while the slowest by p95 latency was `student login api` at `300.42 ms`. This suggests that the `Student` authentication path may involve slightly higher backend cost or higher variability than the other role paths, although repeated runs are still needed before treating it as a persistent bottleneck.

The current evidence supports the conclusion that the authentication endpoints are responsive and error-free under the tested load levels. However, the run does not demonstrate stress tolerance, scalability, or infrastructure behavior under sustained concurrency. Additional staged tests, server-side telemetry, and authenticated post-login flows should be added before drawing stronger performance or capacity conclusions.

## B. Presentation-Ready Paragraph

A baseline authentication performance test was conducted for the Student, Organizer, and Admin login flows of `https://batuhanakbasak.com`. During staged execution up to `10` concurrent users, the system processed `1582` requests with `0` failures, achieving `23.97 req/s`, `144.85 ms` average latency, and `272.6 ms` p95 latency. These results indicate that the authentication layer was stable and responsive for the tested staged workload, while also showing that additional multi-stage testing is still required before making broader scalability claims. This run should not be presented as a real stress test, a high-concurrency test, or an endurance test.

## C. Short Oral Explanation

In this run, I tested the Student, Organizer, and Admin authentication flows with a staged but still modest load profile. The toolkit sent `1582` requests in total and all of them succeeded, so the observed failure rate was zero. Average latency was `144.85 milliseconds` and p95 latency was `272.6 milliseconds`, which is acceptable for a light login workload. The slowest request group was `student login api`, so if I continue this study, that path is the first one I would monitor under higher concurrency. I would still treat this as a baseline staged validation rather than a full stress test, because the peak concurrency was only `10` users, no endurance run was performed, and no server-side resource metrics were captured.

## D. Missing Measurements For Future Runs

- Server-side CPU, memory, container, and process metrics during the run.
- Database query time, connection-pool usage, and cache-hit data for authentication requests.
- Token issuance time or server-side auth processing time split from total response time.
- Network timing details such as DNS, TLS handshake, and connection reuse effects.
- Separate warm-up versus steady-state measurements.
- Concurrent active-user count over time and queue/backpressure indicators.
- Role-level throughput and error trend charts across multi-stage runs.
- Authenticated dashboard/API metrics after successful login.
- Dedicated run log files and optional chart images exported automatically.
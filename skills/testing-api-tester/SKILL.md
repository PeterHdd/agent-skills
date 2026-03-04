---
name: testing-api-tester
description: "Validate APIs comprehensively through functional, performance, and security testing across services and third-party integrations. Use when you need API test suite setup, endpoint coverage matrices, contract testing, OWASP API security validation, rate limit testing, load and stress testing, CI/CD test pipeline integration, authentication testing, or input sanitization and SQL injection prevention checks."
metadata:
  version: "1.0.0"
---

# API Testing Guide

Comprehensive API validation covering functional correctness, security, and performance across all services and third-party integrations.

## Test Strategy

When setting up API tests for a new service, create a base test class with shared auth, retry logic, and response validation helpers before writing individual test cases. This prevents duplicated setup code and ensures consistent assertion patterns across the suite.

See [Test Suite](references/test-suite.md) for the full vitest + fetch test suite code.

## Security Checklist

Cover the OWASP API Security Top 10 in every test suite:

- **Authentication/Authorization**: Test that unauthenticated requests return 401, and unauthorized requests return 403. Verify token expiration, refresh flows, and privilege escalation attempts.
- **Input sanitization**: Test SQL injection, XSS payloads, and command injection via query parameters, request bodies, and headers.
- **Rate limiting**: Verify that burst requests trigger 429 responses. Test per-user and per-IP limits.
- **Mass assignment**: Send unexpected fields in POST/PATCH requests and verify they are ignored.
- **BOLA (Broken Object-Level Authorization)**: Request resources belonging to other users and verify 403/404 responses.
- **SSRF**: Test URL parameters with internal network addresses and verify they are rejected.
- **Data encryption**: Verify sensitive data is not returned in plaintext (e.g., passwords, tokens in response bodies).

## Load Testing

### Performance thresholds

- API response times under 200ms for 95th percentile
- Error rates below 0.1% under normal load
- System handles 10x normal traffic capacity without degradation
- Cache effectiveness validated (hit rates, performance impact)

### Tools

- **k6**: Script-based load testing, integrates with CI/CD. Use for sustained load and spike tests.
- **Locust**: Python-based, good for complex user flows. Use for scenario-based load profiles.
- Run load tests in CI on every release branch. Flag any test exceeding 30 seconds for optimization or move to a nightly pipeline.

## Endpoint Coverage

Maintain a test matrix mapping every route (method + path) to at least:
- One functional test (happy path)
- One negative-input test (validation, malformed data)
- One auth/authz test (missing token, wrong role)

Review the coverage matrix each sprint. Any gaps are flagged in CI as warnings.

## Workflow

1. **API Discovery**: Catalog all APIs with complete endpoint inventory. Analyze specs and contract requirements.
2. **Test Strategy**: Design test strategy covering functional, performance, and security. Create test data management plan.
3. **Implementation**: Build automated test suites (vitest + fetch, REST Assured, k6). Integrate into CI/CD with quality gates.
4. **Monitoring**: Set up production API monitoring. Analyze results and continuously optimize test strategy.

## Reference

### HTTP Status Code Cheat Sheet

| Code | When to assert |
|------|---------------|
| 200 | Successful GET, PATCH |
| 201 | Successful POST (resource created) |
| 204 | Successful DELETE |
| 400 | Invalid input, malformed request |
| 401 | Missing or expired authentication |
| 403 | Authenticated but unauthorized |
| 404 | Resource not found |
| 409 | Conflict (duplicate resource) |
| 429 | Rate limit exceeded |
| 500 | Server error (should never appear in production tests) |

### CI Integration

- Full test suite should complete in under 15 minutes.
- Run functional and security tests on every pull request.
- Run load tests on release branches.
- Any test exceeding 30 seconds is flagged for optimization.

## Scripts

### `scripts/discover_endpoints.sh`
Scan a project directory for API endpoint definitions across common frameworks: Express.js, FastAPI, Flask, and Spring Boot. Outputs a Markdown table with HTTP method, path, source file:line, and framework. Useful for building an endpoint coverage matrix.

```bash
scripts/discover_endpoints.sh ./src
scripts/discover_endpoints.sh /path/to/fastapi-project
```

### `scripts/generate_test_skeleton.py`
Generate test skeleton files from an OpenAPI/Swagger JSON specification. Produces test stubs for each endpoint with method, path, expected status codes, and example request bodies. Supports pytest, vitest, and Playwright output formats.

```bash
scripts/generate_test_skeleton.py --spec openapi.json --framework vitest
scripts/generate_test_skeleton.py --spec swagger.json --framework pytest
```

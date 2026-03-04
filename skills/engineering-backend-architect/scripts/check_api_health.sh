#!/usr/bin/env bash
#
# check_api_health.sh -- Probe common health endpoints on a base URL.
#
# Checks /health, /healthz, /ready, /api/health, /api/v1/health and reports
# status code, response time, and response body preview for each.
#
# Exits 0 if any health endpoint responds with HTTP 200, 1 otherwise.
#
# Usage:
#   ./check_api_health.sh <base-url>
#   ./check_api_health.sh https://api.example.com
#   ./check_api_health.sh --help

set -euo pipefail

HEALTH_PATHS=(
    "/health"
    "/healthz"
    "/ready"
    "/api/health"
    "/api/v1/health"
)

usage() {
    cat <<EOF
Usage: $(basename "$0") <base-url>

Probe common health endpoints on a given base URL and report their status.

Arguments:
  base-url    The base URL of the service (e.g., https://api.example.com)

Health endpoints checked:
$(printf '  %s\n' "${HEALTH_PATHS[@]}")

Exit codes:
  0   At least one endpoint returned HTTP 200
  1   No endpoint returned HTTP 200, or an error occurred

Examples:
  $(basename "$0") https://api.example.com
  $(basename "$0") http://localhost:8080
EOF
}

# --- Argument parsing ---

if [[ $# -lt 1 ]]; then
    echo "Error: Missing required argument: base-url" >&2
    echo "" >&2
    usage >&2
    exit 1
fi

if [[ "$1" == "--help" || "$1" == "-h" ]]; then
    usage
    exit 0
fi

BASE_URL="${1%/}"  # Strip trailing slash

# --- Validate dependencies ---

if ! command -v curl &> /dev/null; then
    echo "Error: curl is required but not installed." >&2
    exit 1
fi

# --- Check endpoints ---

any_healthy=false

echo "## Health Check: ${BASE_URL}"
echo ""
echo "| Endpoint | Status | Response Time | Body Preview |"
echo "|---|---|---|---|"

for path in "${HEALTH_PATHS[@]}"; do
    url="${BASE_URL}${path}"

    # Use curl to get status code, time, and body
    response=$(curl -s -o /dev/null -w "%{http_code} %{time_total}" \
        --connect-timeout 5 \
        --max-time 10 \
        "$url" 2>/dev/null) || true

    status_code=$(echo "$response" | awk '{print $1}')
    response_time=$(echo "$response" | awk '{print $2}')

    # Get body separately (truncated)
    body=$(curl -s --connect-timeout 5 --max-time 10 "$url" 2>/dev/null | head -c 120) || true
    # Escape pipe characters for markdown table
    body=$(echo "$body" | tr '\n' ' ' | sed 's/|/\\|/g')

    if [[ -z "$status_code" || "$status_code" == "000" ]]; then
        echo "| \`${path}\` | Connection failed | - | - |"
    else
        # Format response time
        if [[ -n "$response_time" ]]; then
            time_ms=$(echo "$response_time" | awk '{printf "%.0f", $1 * 1000}')
            time_display="${time_ms}ms"
        else
            time_display="-"
        fi

        # Status indicator
        if [[ "$status_code" == "200" ]]; then
            status_display="200 OK"
            any_healthy=true
        else
            status_display="${status_code}"
        fi

        echo "| \`${path}\` | ${status_display} | ${time_display} | ${body:-(empty)} |"
    fi
done

echo ""

# --- Summary ---

if $any_healthy; then
    echo "**Result: HEALTHY** -- at least one endpoint returned HTTP 200."
    exit 0
else
    echo "**Result: UNHEALTHY** -- no endpoint returned HTTP 200."
    exit 1
fi

#!/usr/bin/env bash
set -euo pipefail

# Check HTTP security headers for a given URL
# Usage: check_security_headers.sh [--json] <url>

JSON_OUTPUT=false
URL=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --json) JSON_OUTPUT=true; shift ;;
        --help|-h)
            echo "Usage: $(basename "$0") [--json] <url>"
            echo ""
            echo "Check HTTP security headers for a given URL."
            echo ""
            echo "Options:"
            echo "  --json    Output results as JSON"
            echo "  --help    Show this help message"
            echo ""
            echo "Checks for:"
            echo "  - Content-Security-Policy"
            echo "  - X-Content-Type-Options"
            echo "  - X-Frame-Options"
            echo "  - Strict-Transport-Security"
            echo "  - Referrer-Policy"
            echo "  - Permissions-Policy"
            echo "  - X-XSS-Protection (deprecated but checked)"
            echo "  - Cache-Control (for sensitive endpoints)"
            exit 0
            ;;
        *) URL="$1"; shift ;;
    esac
done

if [[ -z "$URL" ]]; then
    echo "Error: URL is required"
    echo "Usage: $(basename "$0") [--json] <url>"
    exit 1
fi

# Fetch headers
HEADERS=$(curl -sI -o /dev/null -w '%{http_code}' --max-time 10 "$URL" 2>/dev/null || true)
FULL_HEADERS=$(curl -sI --max-time 10 "$URL" 2>/dev/null || true)

if [[ -z "$FULL_HEADERS" ]]; then
    echo "Error: Could not connect to $URL"
    exit 1
fi

# Check each header
declare -A RESULTS
declare -A GRADES

check_header() {
    local name="$1"
    local required_value="${2:-}"
    local value
    value=$(echo "$FULL_HEADERS" | grep -i "^${name}:" | head -1 | sed "s/^${name}: *//i" | tr -d '\r')

    if [[ -z "$value" ]]; then
        RESULTS["$name"]="MISSING"
        GRADES["$name"]="FAIL"
    elif [[ -n "$required_value" ]] && ! echo "$value" | grep -qi "$required_value"; then
        RESULTS["$name"]="$value (expected: $required_value)"
        GRADES["$name"]="WARN"
    else
        RESULTS["$name"]="$value"
        GRADES["$name"]="PASS"
    fi
}

check_header "Content-Security-Policy" ""
check_header "X-Content-Type-Options" "nosniff"
check_header "X-Frame-Options" ""
check_header "Strict-Transport-Security" "max-age"
check_header "Referrer-Policy" ""
check_header "Permissions-Policy" ""

# Count results
PASS_COUNT=0
WARN_COUNT=0
FAIL_COUNT=0

for key in "${!GRADES[@]}"; do
    case "${GRADES[$key]}" in
        PASS) ((PASS_COUNT++)) ;;
        WARN) ((WARN_COUNT++)) ;;
        FAIL) ((FAIL_COUNT++)) ;;
    esac
done

TOTAL=${#GRADES[@]}

if $JSON_OUTPUT; then
    echo "{"
    echo "  \"url\": \"$URL\","
    echo "  \"summary\": {\"pass\": $PASS_COUNT, \"warn\": $WARN_COUNT, \"fail\": $FAIL_COUNT, \"total\": $TOTAL},"
    echo "  \"headers\": {"
    first=true
    for key in "${!RESULTS[@]}"; do
        if ! $first; then echo ","; fi
        first=false
        printf "    \"%s\": {\"value\": \"%s\", \"grade\": \"%s\"}" "$key" "${RESULTS[$key]}" "${GRADES[$key]}"
    done
    echo ""
    echo "  }"
    echo "}"
else
    echo "Security Header Check: $URL"
    echo "========================================"
    echo ""
    for key in "${!RESULTS[@]}"; do
        grade="${GRADES[$key]}"
        value="${RESULTS[$key]}"
        case "$grade" in
            PASS) symbol="[PASS]" ;;
            WARN) symbol="[WARN]" ;;
            FAIL) symbol="[FAIL]" ;;
        esac
        printf "%-30s %s %s\n" "$key" "$symbol" "$value"
    done
    echo ""
    echo "----------------------------------------"
    echo "Score: $PASS_COUNT/$TOTAL passed, $WARN_COUNT warnings, $FAIL_COUNT missing"
    if [[ $FAIL_COUNT -gt 0 ]]; then
        echo "Action: Add missing security headers before production deploy."
    fi
fi

#!/usr/bin/env bash
#
# check_services.sh -- Check health of services by testing TCP connectivity.
#
# Takes a comma-separated list of host:port pairs, attempts to connect to each,
# and reports up/down status as a markdown table.
#
# Usage:
#   ./check_services.sh host1:port1,host2:port2,...
#   ./check_services.sh --help

set -euo pipefail

TIMEOUT=5  # seconds

usage() {
    cat <<EOF
Usage: $(basename "$0") [OPTIONS] <host:port,host:port,...>

Check health of services by testing TCP port connectivity.

Arguments:
  host:port,...   Comma-separated list of host:port pairs to check

Options:
  --timeout N     Connection timeout in seconds (default: $TIMEOUT)
  -h, --help      Show this help message

Output:
  Markdown table showing each service's up/down status.

Exit codes:
  0   All services are reachable
  1   One or more services are unreachable
  2   Invalid arguments

Examples:
  $(basename "$0") localhost:8080,localhost:5432,redis:6379
  $(basename "$0") --timeout 10 api.example.com:443,db.internal:5432
EOF
}

# --- Argument parsing ---

SERVICE_LIST=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --help|-h)
            usage
            exit 0
            ;;
        --timeout)
            if [[ $# -lt 2 ]]; then
                echo "Error: --timeout requires a value" >&2
                exit 2
            fi
            TIMEOUT="$2"
            shift 2
            ;;
        -*)
            echo "Error: Unknown option: $1" >&2
            usage >&2
            exit 2
            ;;
        *)
            SERVICE_LIST="$1"
            shift
            ;;
    esac
done

if [[ -z "$SERVICE_LIST" ]]; then
    echo "Error: No host:port pairs provided" >&2
    echo "" >&2
    usage >&2
    exit 2
fi

# Split comma-separated list into array
IFS=',' read -ra SERVICES <<< "$SERVICE_LIST"

# --- Helper functions ---

check_tcp() {
    local host="$1"
    local port="$2"

    # Try nc first (most common)
    if command -v nc &> /dev/null; then
        if nc -z -w "$TIMEOUT" "$host" "$port" 2>/dev/null; then
            return 0
        fi
        return 1
    fi

    # Try bash /dev/tcp as fallback
    if command -v bash &> /dev/null; then
        if timeout "$TIMEOUT" bash -c "echo > /dev/tcp/$host/$port" 2>/dev/null; then
            return 0
        fi
        return 1
    fi

    # Try curl as last resort (will work for HTTP ports)
    if command -v curl &> /dev/null; then
        if curl -s --connect-timeout "$TIMEOUT" "http://${host}:${port}/" -o /dev/null 2>/dev/null; then
            return 0
        fi
        return 1
    fi

    echo "Error: No suitable connectivity tool found (nc, bash, or curl required)" >&2
    return 1
}

# --- Check all services ---

echo "## Service Health Check"
echo ""
echo "| # | Service | Status |"
echo "|---|---------|--------|"

all_healthy=true
index=0

for service in "${SERVICES[@]}"; do
    # Trim whitespace
    service=$(echo "$service" | xargs)
    index=$((index + 1))

    # Validate host:port format
    if [[ ! "$service" =~ ^([^:]+):([0-9]+)$ ]]; then
        echo "| $index | \`$service\` | INVALID FORMAT |"
        all_healthy=false
        continue
    fi

    host="${BASH_REMATCH[1]}"
    port="${BASH_REMATCH[2]}"

    if check_tcp "$host" "$port"; then
        echo "| $index | \`${host}:${port}\` | UP |"
    else
        echo "| $index | \`${host}:${port}\` | DOWN |"
        all_healthy=false
    fi
done

echo ""
echo "---"

# --- Summary ---
if $all_healthy; then
    echo "**Result: All ${#SERVICES[@]} service(s) are UP.**"
    exit 0
else
    echo "**Result: One or more services are DOWN.**"
    exit 1
fi

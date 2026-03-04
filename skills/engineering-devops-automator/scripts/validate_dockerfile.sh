#!/usr/bin/env bash
#
# validate_dockerfile.sh -- Lint a Dockerfile for common issues.
#
# Checks:
#   1. Missing FROM instruction
#   2. Using 'latest' tag in FROM
#   3. Running as root (no USER instruction)
#   4. COPY before RUN (cache invalidation)
#   5. apt-get without --no-install-recommends
#   6. Missing WORKDIR instruction
#
# Usage:
#   ./validate_dockerfile.sh <path-to-Dockerfile>
#   ./validate_dockerfile.sh --help

set -euo pipefail

usage() {
    cat <<EOF
Usage: $(basename "$0") <dockerfile-path>

Lint a Dockerfile against common best-practice rules.

Arguments:
  dockerfile-path    Path to the Dockerfile to validate

Checks performed:
  1. FROM instruction present
  2. No 'latest' tag (or untagged base) in FROM
  3. USER instruction present (not running as root)
  4. COPY not placed before RUN (cache invalidation risk)
  5. apt-get uses --no-install-recommends
  6. WORKDIR instruction present

Exit codes:
  0   All checks passed
  1   One or more checks failed
  2   Invalid arguments or file not found

Examples:
  $(basename "$0") ./Dockerfile
  $(basename "$0") /app/docker/Dockerfile.prod
EOF
}

# --- Argument parsing ---

if [[ $# -lt 1 ]]; then
    echo "Error: Missing required argument: dockerfile-path" >&2
    echo "" >&2
    usage >&2
    exit 2
fi

if [[ "$1" == "--help" || "$1" == "-h" ]]; then
    usage
    exit 0
fi

DOCKERFILE="$1"

if [[ ! -f "$DOCKERFILE" ]]; then
    echo "Error: File not found: $DOCKERFILE" >&2
    exit 2
fi

# --- Analysis ---

PASS_COUNT=0
FAIL_COUNT=0
WARN_COUNT=0

pass() {
    echo "- [x] **PASS** -- $1"
    ((PASS_COUNT++))
}

fail() {
    echo "- [ ] **FAIL** -- $1"
    echo "  - Recommendation: $2"
    ((FAIL_COUNT++))
}

warn() {
    echo "- [ ] **WARN** -- $1"
    echo "  - Recommendation: $2"
    ((WARN_COUNT++))
}

echo "## Dockerfile Lint: \`$(basename "$DOCKERFILE")\`"
echo ""
echo "**File**: \`$DOCKERFILE\`"
echo ""

# Read the Dockerfile content (strip blank lines and comments for analysis)
CONTENT=$(grep -v '^\s*#' "$DOCKERFILE" | grep -v '^\s*$' || true)

# --- Check 1: FROM instruction present ---
FROM_COUNT=$(echo "$CONTENT" | grep -ciE '^\s*FROM\s' || true)
if [[ "$FROM_COUNT" -ge 1 ]]; then
    pass "FROM instruction found ($FROM_COUNT stage(s))"
else
    fail "No FROM instruction found" \
         "Every Dockerfile must begin with a FROM instruction to specify the base image."
fi

# --- Check 2: No 'latest' tag in FROM ---
LATEST_FROM=$(echo "$CONTENT" | grep -iE '^\s*FROM\s+\S+:latest(\s|$)' || true)
# Check for untagged FROM (e.g. "FROM node" or "FROM node AS builder")
BARE_FROM=$(echo "$CONTENT" | grep -iE '^\s*FROM\s+[a-zA-Z0-9._/-]+\s*(AS\s|$)' | grep -ivE ':\S' || true)

if [[ -n "$LATEST_FROM" ]]; then
    fail "FROM uses 'latest' tag: $(echo "$LATEST_FROM" | head -1 | xargs)" \
         "Pin base images to specific versions (e.g., node:20-alpine) for reproducible builds."
elif [[ -n "$BARE_FROM" ]]; then
    warn "FROM without explicit tag: $(echo "$BARE_FROM" | head -1 | xargs)" \
         "Untagged images default to 'latest'. Pin to a specific version."
else
    pass "No 'latest' or untagged FROM instructions"
fi

# --- Check 3: USER instruction (not running as root) ---
USER_COUNT=$(echo "$CONTENT" | grep -ciE '^\s*USER\s' || true)
if [[ "$USER_COUNT" -ge 1 ]]; then
    pass "USER instruction found (not running as root)"
else
    fail "No USER instruction found -- container runs as root" \
         "Add 'USER nonroot' or 'USER 1000' to avoid running as root."
fi

# --- Check 4: COPY before RUN (cache invalidation) ---
# Detect COPY of application source (not multi-stage COPY --from=) before the first RUN.
# Strategy: find line numbers of first RUN and any COPY (non --from) that precedes it.
FIRST_RUN_LINE=""
COPY_BEFORE_RUN=false

line_num=0
found_run=false
while IFS= read -r line; do
    line_num=$((line_num + 1))
    # Skip comments/blanks (already stripped, but be safe)
    stripped=$(echo "$line" | sed 's/^[[:space:]]*//')
    if [[ -z "$stripped" || "$stripped" == \#* ]]; then
        continue
    fi
    # Check if this is a RUN instruction
    if echo "$stripped" | grep -qiE '^RUN\s'; then
        if [[ "$found_run" == false ]]; then
            FIRST_RUN_LINE=$line_num
            found_run=true
        fi
        break
    fi
done <<< "$CONTENT"

if [[ -n "$FIRST_RUN_LINE" ]]; then
    # Look for COPY (not --from) before the first RUN
    line_num=0
    while IFS= read -r line; do
        line_num=$((line_num + 1))
        if [[ "$line_num" -ge "$FIRST_RUN_LINE" ]]; then
            break
        fi
        stripped=$(echo "$line" | sed 's/^[[:space:]]*//')
        if echo "$stripped" | grep -qiE '^COPY\s' && ! echo "$stripped" | grep -qiE '^COPY\s+--from'; then
            COPY_BEFORE_RUN=true
            break
        fi
    done <<< "$CONTENT"
fi

if [[ "$COPY_BEFORE_RUN" == true ]]; then
    warn "COPY appears before the first RUN instruction" \
         "Place dependency-install RUN commands before COPY of application source to leverage Docker layer caching. Copy only dependency manifests (package.json, requirements.txt) first, run install, then COPY the rest."
else
    pass "No COPY-before-RUN cache invalidation detected"
fi

# --- Check 5: apt-get without --no-install-recommends ---
APT_LINES=$(echo "$CONTENT" | grep -iE 'apt-get\s+install' || true)
if [[ -n "$APT_LINES" ]]; then
    BAD_APT=$(echo "$APT_LINES" | grep -v '\-\-no-install-recommends' || true)
    if [[ -n "$BAD_APT" ]]; then
        fail "apt-get install without --no-install-recommends" \
             "Use 'apt-get install --no-install-recommends' to avoid pulling in unnecessary packages and reduce image size."
    else
        pass "All apt-get install commands use --no-install-recommends"
    fi
else
    pass "No apt-get install commands found (nothing to check)"
fi

# --- Check 6: WORKDIR instruction present ---
WORKDIR_COUNT=$(echo "$CONTENT" | grep -ciE '^\s*WORKDIR\s' || true)
if [[ "$WORKDIR_COUNT" -ge 1 ]]; then
    pass "WORKDIR instruction found"
else
    fail "No WORKDIR instruction found" \
         "Set a WORKDIR (e.g., WORKDIR /app) to avoid relying on the default '/' and to make paths predictable."
fi

# --- Summary ---
echo ""
echo "---"
TOTAL=$((PASS_COUNT + FAIL_COUNT + WARN_COUNT))
echo "**Results: $PASS_COUNT passed, $FAIL_COUNT failed, $WARN_COUNT warning(s) out of $TOTAL checks.**"

if [[ "$FAIL_COUNT" -gt 0 ]]; then
    exit 1
else
    exit 0
fi

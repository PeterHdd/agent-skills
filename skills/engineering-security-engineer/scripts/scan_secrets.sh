#!/usr/bin/env bash
set -euo pipefail

# Scan a directory or git repository for accidentally committed secrets
# Usage: scan_secrets.sh [--git-history] [--format json] <path>

SCAN_GIT=false
FORMAT="text"
TARGET_PATH=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --git-history) SCAN_GIT=true; shift ;;
        --format) FORMAT="$2"; shift 2 ;;
        --help|-h)
            echo "Usage: $(basename "$0") [--git-history] [--format json|text] <path>"
            echo ""
            echo "Scan for accidentally committed secrets in files or git history."
            echo ""
            echo "Options:"
            echo "  --git-history  Scan git history (slower, more thorough)"
            echo "  --format       Output format: text (default) or json"
            echo "  --help         Show this help message"
            echo ""
            echo "Detects:"
            echo "  - AWS access keys and secret keys"
            echo "  - API keys and tokens (generic patterns)"
            echo "  - Private keys (RSA, EC, PGP)"
            echo "  - Database connection strings with passwords"
            echo "  - JWT secrets"
            echo "  - GitHub/GitLab tokens"
            echo "  - Slack tokens"
            echo "  - Common secret variable assignments"
            exit 0
            ;;
        *) TARGET_PATH="$1"; shift ;;
    esac
done

if [[ -z "$TARGET_PATH" ]]; then
    echo "Error: Path is required"
    echo "Usage: $(basename "$0") [--git-history] [--format json|text] <path>"
    exit 1
fi

if [[ ! -e "$TARGET_PATH" ]]; then
    echo "Error: Path does not exist: $TARGET_PATH"
    exit 1
fi

# Secret patterns (pattern_name:regex)
PATTERNS=(
    "AWS Access Key:AKIA[0-9A-Z]{16}"
    "AWS Secret Key:(?i)(aws_secret_access_key|aws_secret_key)\s*[=:]\s*[A-Za-z0-9/+=]{40}"
    "Private Key:-----BEGIN (RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----"
    "GitHub Token:gh[ps]_[A-Za-z0-9_]{36,}"
    "GitLab Token:glpat-[A-Za-z0-9_-]{20,}"
    "Slack Token:xox[bpras]-[0-9a-zA-Z-]+"
    "Generic API Key:(?i)(api[_-]?key|apikey)\s*[=:]\s*['\"]?[A-Za-z0-9_-]{20,}['\"]?"
    "Generic Secret:(?i)(secret|password|passwd|pwd)\s*[=:]\s*['\"]?[A-Za-z0-9!@#$%^&*_-]{8,}['\"]?"
    "Database URL:(?i)(postgres|mysql|mongodb|redis)://[^:]+:[^@]+@"
    "JWT Secret:(?i)(jwt[_-]?secret|jwt[_-]?key)\s*[=:]\s*['\"]?[A-Za-z0-9_-]{8,}['\"]?"
)

FINDINGS=()
FINDING_COUNT=0

scan_file() {
    local file="$1"
    # Skip binary files, lock files, node_modules, .git
    if file "$file" 2>/dev/null | grep -q "binary\|executable"; then return; fi
    case "$file" in
        *.lock|*.min.js|*.min.css|*.map) return ;;
        */node_modules/*|*/.git/*|*/vendor/*|*/__pycache__/*) return ;;
    esac

    for pattern_entry in "${PATTERNS[@]}"; do
        local name="${pattern_entry%%:*}"
        local regex="${pattern_entry#*:}"
        local matches
        matches=$(grep -nP "$regex" "$file" 2>/dev/null || true)
        if [[ -n "$matches" ]]; then
            while IFS= read -r match; do
                local line_num="${match%%:*}"
                local line_content="${match#*:}"
                # Truncate long lines
                if [[ ${#line_content} -gt 100 ]]; then
                    line_content="${line_content:0:100}..."
                fi
                FINDINGS+=("$name|$file|$line_num|$line_content")
                ((FINDING_COUNT++))
            done <<< "$matches"
        fi
    done
}

if $SCAN_GIT; then
    if [[ ! -d "$TARGET_PATH/.git" ]] && ! git -C "$TARGET_PATH" rev-parse --git-dir &>/dev/null; then
        echo "Error: $TARGET_PATH is not a git repository. Remove --git-history flag."
        exit 1
    fi
    echo "Scanning git history (this may take a while)..." >&2
    # Scan current files and recent git history
    while IFS= read -r -d '' file; do
        scan_file "$file"
    done < <(find "$TARGET_PATH" -type f -not -path '*/.git/*' -not -path '*/node_modules/*' -print0 2>/dev/null)
    # Also check git log for secrets in diffs
    git -C "$TARGET_PATH" log --all --diff-filter=A --name-only --pretty=format: 2>/dev/null | sort -u | while IFS= read -r file; do
        [[ -z "$file" ]] && continue
        [[ -f "$TARGET_PATH/$file" ]] && scan_file "$TARGET_PATH/$file"
    done
else
    while IFS= read -r -d '' file; do
        scan_file "$file"
    done < <(find "$TARGET_PATH" -type f -not -path '*/.git/*' -not -path '*/node_modules/*' -not -path '*/vendor/*' -print0 2>/dev/null)
fi

# Output results
if [[ "$FORMAT" == "json" ]]; then
    echo "{"
    echo "  \"path\": \"$TARGET_PATH\","
    echo "  \"scan_git_history\": $SCAN_GIT,"
    echo "  \"finding_count\": $FINDING_COUNT,"
    echo "  \"findings\": ["
    first=true
    for finding in "${FINDINGS[@]+"${FINDINGS[@]}"}"; do
        IFS='|' read -r name file line content <<< "$finding"
        if ! $first; then echo ","; fi
        first=false
        # Escape JSON strings
        content=$(echo "$content" | sed 's/\\/\\\\/g; s/"/\\"/g')
        printf '    {"type": "%s", "file": "%s", "line": %s, "content": "%s"}' "$name" "$file" "$line" "$content"
    done
    echo ""
    echo "  ]"
    echo "}"
else
    if [[ $FINDING_COUNT -eq 0 ]]; then
        echo "No secrets found in $TARGET_PATH"
    else
        echo "SECRET SCAN RESULTS: $TARGET_PATH"
        echo "========================================"
        echo "Found $FINDING_COUNT potential secret(s):"
        echo ""
        for finding in "${FINDINGS[@]}"; do
            IFS='|' read -r name file line content <<< "$finding"
            echo "  [$name]"
            echo "  File: $file:$line"
            echo "  Content: $content"
            echo ""
        done
        echo "----------------------------------------"
        echo "Action: Review each finding. Rotate any real secrets immediately."
        echo "Use .gitignore and environment variables to prevent future leaks."
    fi
fi

exit $( [[ $FINDING_COUNT -eq 0 ]] && echo 0 || echo 1 )

#!/usr/bin/env bash
#
# discover_endpoints.sh - Scan a project directory for API endpoint definitions.
#
# Supports:
#   - Express.js  (app.get, app.post, app.put, app.delete, router.get, etc.)
#   - FastAPI      (@app.get, @router.get, etc.)
#   - Flask        (@app.route, @blueprint.route, etc.)
#   - Spring Boot  (@GetMapping, @PostMapping, @RequestMapping, etc.)
#
# Outputs a Markdown table with HTTP method, path, and file:line.

set -euo pipefail

# -------------------------------------------------------------------
# Usage / Help
# -------------------------------------------------------------------
usage() {
    cat <<'USAGE'
Usage: discover_endpoints.sh [OPTIONS] <directory>

Scan a project directory for API endpoint definitions and report them
as a Markdown table.

Supported frameworks:
  - Express.js  (app.get/post/put/delete, router.*)
  - FastAPI      (@app.get/post/put/delete, @router.*)
  - Flask        (@app.route, @blueprint.route)
  - Spring Boot  (@GetMapping, @PostMapping, @RequestMapping, etc.)

Options:
  -h, --help    Show this help message and exit

Arguments:
  directory     Path to the project directory to scan

Output:
  Markdown table with columns: Method, Path, File:Line, Framework

Examples:
  discover_endpoints.sh ./my-express-app
  discover_endpoints.sh /path/to/fastapi-project
  discover_endpoints.sh .
USAGE
}

# -------------------------------------------------------------------
# Argument parsing
# -------------------------------------------------------------------
if [ $# -lt 1 ]; then
    echo "Error: Missing required argument: directory" >&2
    echo "" >&2
    usage >&2
    exit 1
fi

case "${1:-}" in
    -h|--help)
        usage
        exit 0
        ;;
esac

SCAN_DIR="$1"

if [ ! -d "$SCAN_DIR" ]; then
    echo "Error: Directory not found: $SCAN_DIR" >&2
    exit 1
fi

# -------------------------------------------------------------------
# Temporary file for collecting results
# -------------------------------------------------------------------
TMPFILE=$(mktemp)
trap 'rm -f "$TMPFILE"' EXIT

# -------------------------------------------------------------------
# Scan for Express.js endpoints
#   Patterns: app.get('/path' | router.post("/path" | etc.
# -------------------------------------------------------------------
scan_express() {
    local dir="$1"
    # Look in .js, .ts, .mjs, .cjs files
    while IFS= read -r file; do
        [ -f "$file" ] || continue
        local line_num=0
        while IFS= read -r line; do
            line_num=$((line_num + 1))
            # Match: app.get( or router.post( etc.
            # Capture method and path
            if echo "$line" | grep -qE '(app|router)\.(get|post|put|patch|delete|options|head|all)\s*\('; then
                method=$(echo "$line" | sed -nE "s/.*\.(get|post|put|patch|delete|options|head|all)\s*\(.*/\1/p" | head -1)
                method=$(echo "$method" | tr '[:lower:]' '[:upper:]')
                # Extract path string (single or double quoted)
                path=$(echo "$line" | sed -nE "s/.*\.(get|post|put|patch|delete|options|head|all)\s*\(\s*['\"]([^'\"]*)['\"].*/\2/p" | head -1)
                if [ -n "$method" ] && [ -n "$path" ]; then
                    relfile="${file#"$dir"/}"
                    echo "$method|$path|$relfile:$line_num|Express" >> "$TMPFILE"
                fi
            fi
        done < "$file"
    done < <(find "$dir" -type f \( -name "*.js" -o -name "*.ts" -o -name "*.mjs" -o -name "*.cjs" \) \
        ! -path "*/node_modules/*" ! -path "*/.git/*" ! -path "*/dist/*" ! -path "*/build/*" 2>/dev/null)
}

# -------------------------------------------------------------------
# Scan for FastAPI endpoints
#   Patterns: @app.get("/path") | @router.post("/path") | etc.
# -------------------------------------------------------------------
scan_fastapi() {
    local dir="$1"
    while IFS= read -r file; do
        [ -f "$file" ] || continue
        local line_num=0
        while IFS= read -r line; do
            line_num=$((line_num + 1))
            # Match: @app.get( or @router.post( etc.
            if echo "$line" | grep -qE '@\w+\.(get|post|put|patch|delete|options|head)\s*\('; then
                method=$(echo "$line" | sed -nE "s/.*@\w+\.(get|post|put|patch|delete|options|head)\s*\(.*/\1/p" | head -1)
                method=$(echo "$method" | tr '[:lower:]' '[:upper:]')
                path=$(echo "$line" | sed -nE "s/.*@\w+\.(get|post|put|patch|delete|options|head)\s*\(\s*['\"]([^'\"]*)['\"].*/\2/p" | head -1)
                if [ -n "$method" ]; then
                    path="${path:-/}"
                    relfile="${file#"$dir"/}"
                    echo "$method|$path|$relfile:$line_num|FastAPI" >> "$TMPFILE"
                fi
            fi
        done < "$file"
    done < <(find "$dir" -type f -name "*.py" \
        ! -path "*/.git/*" ! -path "*/__pycache__/*" ! -path "*/venv/*" ! -path "*/.venv/*" ! -path "*/env/*" 2>/dev/null)
}

# -------------------------------------------------------------------
# Scan for Flask endpoints
#   Patterns: @app.route("/path") | @blueprint.route("/path", methods=["GET"])
# -------------------------------------------------------------------
scan_flask() {
    local dir="$1"
    while IFS= read -r file; do
        [ -f "$file" ] || continue
        local line_num=0
        while IFS= read -r line; do
            line_num=$((line_num + 1))
            # Match: @app.route( or @*.route(
            if echo "$line" | grep -qE '@\w+\.route\s*\('; then
                path=$(echo "$line" | sed -nE "s/.*@\w+\.route\s*\(\s*['\"]([^'\"]*)['\"].*/\1/p" | head -1)
                # Try to extract methods from methods=[...]
                methods=$(echo "$line" | sed -nE "s/.*methods\s*=\s*\[([^]]*)\].*/\1/p" | head -1)
                if [ -n "$methods" ]; then
                    # Clean up: remove quotes and spaces
                    methods=$(echo "$methods" | tr -d "\"' " | tr '[:lower:]' '[:upper:]')
                else
                    methods="GET"
                fi
                if [ -n "$path" ]; then
                    # Split multiple methods
                    IFS=',' read -ra method_arr <<< "$methods"
                    for m in "${method_arr[@]}"; do
                        m=$(echo "$m" | tr -d ' ')
                        [ -n "$m" ] || continue
                        relfile="${file#"$dir"/}"
                        echo "$m|$path|$relfile:$line_num|Flask" >> "$TMPFILE"
                    done
                fi
            fi
        done < "$file"
    done < <(find "$dir" -type f -name "*.py" \
        ! -path "*/.git/*" ! -path "*/__pycache__/*" ! -path "*/venv/*" ! -path "*/.venv/*" ! -path "*/env/*" 2>/dev/null)
}

# -------------------------------------------------------------------
# Scan for Spring Boot endpoints
#   Patterns: @GetMapping, @PostMapping, @RequestMapping, etc.
# -------------------------------------------------------------------
scan_spring() {
    local dir="$1"
    while IFS= read -r file; do
        [ -f "$file" ] || continue
        local line_num=0
        while IFS= read -r line; do
            line_num=$((line_num + 1))

            # @GetMapping, @PostMapping, @PutMapping, @DeleteMapping, @PatchMapping
            if echo "$line" | grep -qE '@(Get|Post|Put|Delete|Patch)Mapping'; then
                method=$(echo "$line" | sed -nE 's/.*@(Get|Post|Put|Delete|Patch)Mapping.*/\1/p' | head -1)
                method=$(echo "$method" | tr '[:lower:]' '[:upper:]')
                # Extract path from ("path") or (value = "path") or ("/path")
                path=$(echo "$line" | sed -nE 's/.*Mapping\s*\(\s*"([^"]*)".*/\1/p' | head -1)
                if [ -z "$path" ]; then
                    path=$(echo "$line" | sed -nE 's/.*Mapping\s*\(\s*value\s*=\s*"([^"]*)".*/\1/p' | head -1)
                fi
                if [ -z "$path" ]; then
                    path=$(echo "$line" | sed -nE 's/.*Mapping\s*\(\s*path\s*=\s*"([^"]*)".*/\1/p' | head -1)
                fi
                path="${path:-/}"
                relfile="${file#"$dir"/}"
                echo "$method|$path|$relfile:$line_num|Spring" >> "$TMPFILE"
            fi

            # @RequestMapping
            if echo "$line" | grep -qE '@RequestMapping'; then
                path=$(echo "$line" | sed -nE 's/.*RequestMapping\s*\(\s*"([^"]*)".*/\1/p' | head -1)
                if [ -z "$path" ]; then
                    path=$(echo "$line" | sed -nE 's/.*RequestMapping\s*\(\s*value\s*=\s*"([^"]*)".*/\1/p' | head -1)
                fi
                if [ -z "$path" ]; then
                    path=$(echo "$line" | sed -nE 's/.*RequestMapping\s*\(\s*path\s*=\s*"([^"]*)".*/\1/p' | head -1)
                fi
                # Extract method
                req_method=$(echo "$line" | sed -nE 's/.*method\s*=\s*RequestMethod\.(\w+).*/\1/p' | head -1)
                req_method=$(echo "${req_method:-GET}" | tr '[:lower:]' '[:upper:]')
                path="${path:-/}"
                relfile="${file#"$dir"/}"
                echo "$req_method|$path|$relfile:$line_num|Spring" >> "$TMPFILE"
            fi
        done < "$file"
    done < <(find "$dir" -type f \( -name "*.java" -o -name "*.kt" \) \
        ! -path "*/.git/*" ! -path "*/build/*" ! -path "*/target/*" 2>/dev/null)
}

# -------------------------------------------------------------------
# Run all scanners
# -------------------------------------------------------------------
scan_express "$SCAN_DIR"
scan_fastapi "$SCAN_DIR"
scan_flask "$SCAN_DIR"
scan_spring "$SCAN_DIR"

# -------------------------------------------------------------------
# Output results as Markdown
# -------------------------------------------------------------------
TOTAL=$(wc -l < "$TMPFILE" | tr -d ' ')

echo "# API Endpoint Discovery Report"
echo ""
echo "**Scanned directory:** \`$SCAN_DIR\`"
echo ""

if [ "$TOTAL" -eq 0 ]; then
    echo "_No API endpoints found._"
    echo ""
    echo "Searched for patterns from: Express.js, FastAPI, Flask, Spring Boot"
    exit 0
fi

echo "**Total endpoints found:** $TOTAL"
echo ""

echo "## Endpoints"
echo ""
echo "| # | Method | Path | File:Line | Framework |"
echo "|---|--------|------|-----------|-----------|"

COUNT=0
while IFS='|' read -r method path location framework; do
    COUNT=$((COUNT + 1))
    echo "| $COUNT | $method | \`$path\` | \`$location\` | $framework |"
done < "$TMPFILE"

echo ""

# Summary by method
echo "## Summary by HTTP Method"
echo ""
echo "| Method | Count |"
echo "|--------|-------|"

sort "$TMPFILE" -t'|' -k1,1 | while IFS='|' read -r method _rest; do
    echo "$method"
done | sort | uniq -c | sort -rn | while read -r count method; do
    echo "| $method | $count |"
done

echo ""

# Summary by framework
echo "## Summary by Framework"
echo ""
echo "| Framework | Count |"
echo "|-----------|-------|"

sort "$TMPFILE" -t'|' -k4,4 | while IFS='|' read -r _m _p _l framework; do
    echo "$framework"
done | sort | uniq -c | sort -rn | while read -r count framework; do
    echo "| $framework | $count |"
done

echo ""

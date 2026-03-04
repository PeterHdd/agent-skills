#!/usr/bin/env bash
#
# check_bundle.sh -- Analyze a directory for frontend bundle size concerns.
#
# Finds all .js/.css files, reports sizes, flags files over 250KB,
# checks for source maps, and counts total bundle size.
#
# Usage:
#   ./check_bundle.sh <dist-directory>
#   ./check_bundle.sh --help

set -euo pipefail

SIZE_THRESHOLD_KB=250

usage() {
    cat <<EOF
Usage: $(basename "$0") [OPTIONS] <directory>

Analyze a dist/build directory for frontend bundle size concerns.

Arguments:
  directory        Path to the dist or build output directory

Options:
  --threshold N    Size threshold in KB to flag large files (default: $SIZE_THRESHOLD_KB)
  -h, --help       Show this help message

Checks performed:
  - List all .js and .css files with their sizes
  - Flag files exceeding the size threshold
  - Detect source map (.map) files
  - Report total bundle size

Exit codes:
  0   No files exceed the size threshold
  1   One or more files exceed the threshold
  2   Invalid arguments or directory not found

Examples:
  $(basename "$0") ./dist
  $(basename "$0") --threshold 500 ./build
  $(basename "$0") /app/out
EOF
}

# --- Argument parsing ---

DIR_PATH=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --help|-h)
            usage
            exit 0
            ;;
        --threshold)
            if [[ $# -lt 2 ]]; then
                echo "Error: --threshold requires a value" >&2
                exit 2
            fi
            SIZE_THRESHOLD_KB="$2"
            shift 2
            ;;
        -*)
            echo "Error: Unknown option: $1" >&2
            usage >&2
            exit 2
            ;;
        *)
            DIR_PATH="$1"
            shift
            ;;
    esac
done

if [[ -z "$DIR_PATH" ]]; then
    echo "Error: No directory path provided" >&2
    echo "" >&2
    usage >&2
    exit 2
fi

if [[ ! -d "$DIR_PATH" ]]; then
    echo "Error: Directory not found: $DIR_PATH" >&2
    exit 2
fi

# --- Helpers ---

# Format bytes to human-readable (KB or MB)
human_size() {
    local bytes="$1"
    if [[ "$bytes" -ge 1048576 ]]; then
        awk "BEGIN {printf \"%.2f MB\", $bytes / 1048576}"
    elif [[ "$bytes" -ge 1024 ]]; then
        awk "BEGIN {printf \"%.2f KB\", $bytes / 1024}"
    else
        echo "${bytes} B"
    fi
}

# Get file size in bytes (cross-platform: GNU/BSD stat)
file_size_bytes() {
    local f="$1"
    if stat --version &>/dev/null 2>&1; then
        stat -c%s "$f" 2>/dev/null || echo 0
    else
        stat -f%z "$f" 2>/dev/null || echo 0
    fi
}

# --- Collect files ---

JS_FILES=()
CSS_FILES=()
MAP_FILES=()

while IFS= read -r -d '' f; do
    if [[ "$f" == *.js.map || "$f" == *.css.map ]]; then
        MAP_FILES+=("$f")
    elif [[ "$f" == *.js ]]; then
        JS_FILES+=("$f")
    elif [[ "$f" == *.css ]]; then
        CSS_FILES+=("$f")
    fi
done < <(find "$DIR_PATH" -type f \( -name "*.js" -o -name "*.css" -o -name "*.js.map" -o -name "*.css.map" \) -print0 2>/dev/null | sort -z)

TOTAL_JS=${#JS_FILES[@]}
TOTAL_CSS=${#CSS_FILES[@]}
TOTAL_MAPS=${#MAP_FILES[@]}
TOTAL_FILES=$((TOTAL_JS + TOTAL_CSS))

# --- Report header ---

echo "## Bundle Size Analysis: \`${DIR_PATH}\`"
echo ""
echo "- **JavaScript files**: $TOTAL_JS"
echo "- **CSS files**: $TOTAL_CSS"
echo "- **Source map files**: $TOTAL_MAPS"
echo ""

if [[ "$TOTAL_FILES" -eq 0 ]]; then
    echo "No .js or .css files found in \`$DIR_PATH\`."
    echo ""
    echo "---"
    echo "**Result: Nothing to analyze.**"
    exit 0
fi

# --- File size table ---

THRESHOLD_BYTES=$((SIZE_THRESHOLD_KB * 1024))
TOTAL_BYTES=0
OVERSIZED_COUNT=0

echo "### File Sizes"
echo ""
echo "| File | Size | Status |"
echo "|------|------|--------|"

ALL_FILES=("${JS_FILES[@]}" "${CSS_FILES[@]}")

for f in "${ALL_FILES[@]}"; do
    size=$(file_size_bytes "$f")
    TOTAL_BYTES=$((TOTAL_BYTES + size))
    rel_path="${f#"$DIR_PATH"/}"
    h_size=$(human_size "$size")

    if [[ "$size" -gt "$THRESHOLD_BYTES" ]]; then
        echo "| \`$rel_path\` | $h_size | **OVERSIZED** |"
        ((OVERSIZED_COUNT++))
    else
        echo "| \`$rel_path\` | $h_size | OK |"
    fi
done

echo ""

# --- Summary ---

echo "### Summary"
echo ""
echo "- **Total bundle size**: $(human_size $TOTAL_BYTES)"
echo "- **Size threshold**: ${SIZE_THRESHOLD_KB} KB"
echo "- **Files exceeding threshold**: $OVERSIZED_COUNT"
echo ""

# --- Source maps ---

echo "### Source Maps"
echo ""
if [[ "$TOTAL_MAPS" -gt 0 ]]; then
    MAP_TOTAL_BYTES=0
    echo "| Source Map | Size |"
    echo "|-----------|------|"
    for f in "${MAP_FILES[@]}"; do
        size=$(file_size_bytes "$f")
        MAP_TOTAL_BYTES=$((MAP_TOTAL_BYTES + size))
        rel_path="${f#"$DIR_PATH"/}"
        echo "| \`$rel_path\` | $(human_size "$size") |"
    done
    echo ""
    echo "> **Note**: Source maps add $(human_size $MAP_TOTAL_BYTES) to the deployment. Ensure they are not served to end users in production."
else
    echo "No source map files found."
    echo ""
    echo "> **Note**: Source maps were not detected. Consider generating them for easier debugging."
fi

echo ""
echo "---"

if [[ "$OVERSIZED_COUNT" -gt 0 ]]; then
    echo "**Result: $OVERSIZED_COUNT file(s) exceed the ${SIZE_THRESHOLD_KB} KB threshold.** Consider code splitting, tree shaking, or lazy loading to reduce bundle size."
    exit 1
else
    echo "**Result: All files are within the ${SIZE_THRESHOLD_KB} KB threshold.**"
    exit 0
fi

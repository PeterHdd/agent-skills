#!/usr/bin/env bash
# check_app_size.sh — Analyze mobile app build output size and flag threshold issues.

set -euo pipefail

usage() {
    cat <<EOF
Usage: $(basename "$0") [OPTIONS] <build-directory>

Analyze a mobile app build output directory for size issues.

Arguments:
  build-directory   Path to the build output directory (containing .app, .apk,
                    .aab, .ipa, or the raw build artifacts)

Options:
  -t, --threshold-ios   SIZE_MB   iOS size warning threshold in MB (default: 50)
  -T, --threshold-android SIZE_MB Android size warning threshold in MB (default: 150)
  -n, --top-files       COUNT     Number of largest files to report (default: 20)
  -h, --help                      Show this help message

Output:
  Structured report with total size, largest files, asset breakdown,
  and threshold warnings suitable for agent parsing.

Examples:
  $(basename "$0") ./build/outputs/apk/release
  $(basename "$0") --threshold-ios 40 ./DerivedData/Build/Products/Release-iphoneos
EOF
    exit 0
}

# Defaults
IOS_THRESHOLD_MB=50
ANDROID_THRESHOLD_MB=150
TOP_FILES_COUNT=20
BUILD_DIR=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        -h|--help)
            usage
            ;;
        -t|--threshold-ios)
            IOS_THRESHOLD_MB="$2"
            shift 2
            ;;
        -T|--threshold-android)
            ANDROID_THRESHOLD_MB="$2"
            shift 2
            ;;
        -n|--top-files)
            TOP_FILES_COUNT="$2"
            shift 2
            ;;
        -*)
            echo "ERROR: Unknown option: $1" >&2
            echo "Run with --help for usage information." >&2
            exit 1
            ;;
        *)
            BUILD_DIR="$1"
            shift
            ;;
    esac
done

if [[ -z "$BUILD_DIR" ]]; then
    echo "ERROR: Build directory argument is required." >&2
    echo "Run with --help for usage information." >&2
    exit 1
fi

if [[ ! -d "$BUILD_DIR" ]]; then
    echo "ERROR: Directory not found: $BUILD_DIR" >&2
    exit 1
fi

# Detect platform from file extensions present
detect_platform() {
    local dir="$1"
    local has_ios=false
    local has_android=false

    if find "$dir" -maxdepth 3 -name "*.app" -type d 2>/dev/null | head -1 | grep -q .; then
        has_ios=true
    fi
    if find "$dir" -maxdepth 3 -name "*.ipa" -type f 2>/dev/null | head -1 | grep -q .; then
        has_ios=true
    fi
    if find "$dir" -maxdepth 3 -name "*.apk" -type f 2>/dev/null | head -1 | grep -q .; then
        has_android=true
    fi
    if find "$dir" -maxdepth 3 -name "*.aab" -type f 2>/dev/null | head -1 | grep -q .; then
        has_android=true
    fi

    if $has_ios && $has_android; then
        echo "both"
    elif $has_ios; then
        echo "ios"
    elif $has_android; then
        echo "android"
    else
        echo "unknown"
    fi
}

# Human-readable size
human_size() {
    local bytes="$1"
    if [[ $bytes -ge 1073741824 ]]; then
        echo "$(echo "scale=2; $bytes / 1073741824" | bc) GB"
    elif [[ $bytes -ge 1048576 ]]; then
        echo "$(echo "scale=2; $bytes / 1048576" | bc) MB"
    elif [[ $bytes -ge 1024 ]]; then
        echo "$(echo "scale=2; $bytes / 1024" | bc) KB"
    else
        echo "${bytes} B"
    fi
}

# Calculate total size in bytes
get_total_bytes() {
    local dir="$1"
    # Use platform-appropriate du flag
    if du --version 2>/dev/null | grep -q GNU; then
        du -sb "$dir" 2>/dev/null | awk '{print $1}'
    else
        # macOS du: -s for summary, output is in 512-byte blocks
        du -s "$dir" 2>/dev/null | awk '{print $1 * 512}'
    fi
}

# Get size of asset categories
get_category_size() {
    local dir="$1"
    local pattern="$2"
    local total=0
    while IFS= read -r file; do
        if [[ -n "$file" ]]; then
            local size
            size=$(wc -c < "$file" 2>/dev/null || echo 0)
            total=$((total + size))
        fi
    done < <(find "$dir" -type f -iname "$pattern" 2>/dev/null)
    echo "$total"
}

# ---- Main Report ----

PLATFORM=$(detect_platform "$BUILD_DIR")
TOTAL_BYTES=$(get_total_bytes "$BUILD_DIR")
TOTAL_MB=$(echo "scale=2; $TOTAL_BYTES / 1048576" | bc)

echo "=== APP SIZE ANALYSIS ==="
echo ""
echo "--- Summary ---"
echo "directory: $BUILD_DIR"
echo "platform: $PLATFORM"
echo "total_size_bytes: $TOTAL_BYTES"
echo "total_size_human: $(human_size "$TOTAL_BYTES")"
echo ""

# Threshold check
echo "--- Threshold Check ---"
WARNINGS=0
if [[ "$PLATFORM" == "ios" || "$PLATFORM" == "both" ]]; then
    IOS_THRESHOLD_BYTES=$(echo "$IOS_THRESHOLD_MB * 1048576" | bc | cut -d. -f1)
    if [[ $TOTAL_BYTES -gt $IOS_THRESHOLD_BYTES ]]; then
        echo "WARNING: iOS size ${TOTAL_MB} MB exceeds threshold ${IOS_THRESHOLD_MB} MB"
        WARNINGS=$((WARNINGS + 1))
    else
        echo "OK: iOS size ${TOTAL_MB} MB is within threshold ${IOS_THRESHOLD_MB} MB"
    fi
fi
if [[ "$PLATFORM" == "android" || "$PLATFORM" == "both" ]]; then
    ANDROID_THRESHOLD_BYTES=$(echo "$ANDROID_THRESHOLD_MB * 1048576" | bc | cut -d. -f1)
    if [[ $TOTAL_BYTES -gt $ANDROID_THRESHOLD_BYTES ]]; then
        echo "WARNING: Android size ${TOTAL_MB} MB exceeds threshold ${ANDROID_THRESHOLD_MB} MB"
        WARNINGS=$((WARNINGS + 1))
    else
        echo "OK: Android size ${TOTAL_MB} MB is within threshold ${ANDROID_THRESHOLD_MB} MB"
    fi
fi
if [[ "$PLATFORM" == "unknown" ]]; then
    echo "INFO: No .app/.ipa/.apk/.aab found; applying both thresholds"
    IOS_THRESHOLD_BYTES=$(echo "$IOS_THRESHOLD_MB * 1048576" | bc | cut -d. -f1)
    ANDROID_THRESHOLD_BYTES=$(echo "$ANDROID_THRESHOLD_MB * 1048576" | bc | cut -d. -f1)
    if [[ $TOTAL_BYTES -gt $IOS_THRESHOLD_BYTES ]]; then
        echo "WARNING: Size ${TOTAL_MB} MB exceeds iOS threshold ${IOS_THRESHOLD_MB} MB"
        WARNINGS=$((WARNINGS + 1))
    fi
    if [[ $TOTAL_BYTES -gt $ANDROID_THRESHOLD_BYTES ]]; then
        echo "WARNING: Size ${TOTAL_MB} MB exceeds Android threshold ${ANDROID_THRESHOLD_MB} MB"
        WARNINGS=$((WARNINGS + 1))
    fi
    if [[ $WARNINGS -eq 0 ]]; then
        echo "OK: Size ${TOTAL_MB} MB is within both thresholds"
    fi
fi
echo "warnings_count: $WARNINGS"
echo ""

# Top largest files
echo "--- Largest Files (top $TOP_FILES_COUNT) ---"
find "$BUILD_DIR" -type f -exec wc -c {} + 2>/dev/null \
    | grep -v ' total$' \
    | sort -rn \
    | head -n "$TOP_FILES_COUNT" \
    | while read -r size filepath; do
        echo "  $(human_size "$size")  $filepath"
    done
echo ""

# Asset category breakdown
echo "--- Asset Breakdown ---"

IMAGE_BYTES=0
for ext in "*.png" "*.jpg" "*.jpeg" "*.gif" "*.webp" "*.svg" "*.bmp" "*.heic"; do
    cat_bytes=$(get_category_size "$BUILD_DIR" "$ext")
    IMAGE_BYTES=$((IMAGE_BYTES + cat_bytes))
done
echo "images: $(human_size $IMAGE_BYTES)"

VIDEO_BYTES=0
for ext in "*.mp4" "*.mov" "*.webm" "*.avi"; do
    cat_bytes=$(get_category_size "$BUILD_DIR" "$ext")
    VIDEO_BYTES=$((VIDEO_BYTES + cat_bytes))
done
echo "video: $(human_size $VIDEO_BYTES)"

AUDIO_BYTES=0
for ext in "*.mp3" "*.wav" "*.aac" "*.ogg" "*.m4a"; do
    cat_bytes=$(get_category_size "$BUILD_DIR" "$ext")
    AUDIO_BYTES=$((AUDIO_BYTES + cat_bytes))
done
echo "audio: $(human_size $AUDIO_BYTES)"

FONT_BYTES=0
for ext in "*.ttf" "*.otf" "*.woff" "*.woff2"; do
    cat_bytes=$(get_category_size "$BUILD_DIR" "$ext")
    FONT_BYTES=$((FONT_BYTES + cat_bytes))
done
echo "fonts: $(human_size $FONT_BYTES)"

JS_BYTES=0
for ext in "*.js" "*.jsx" "*.ts" "*.tsx" "*.mjs"; do
    cat_bytes=$(get_category_size "$BUILD_DIR" "$ext")
    JS_BYTES=$((JS_BYTES + cat_bytes))
done
echo "javascript: $(human_size $JS_BYTES)"

SO_BYTES=0
for ext in "*.so" "*.dylib" "*.a" "*.framework"; do
    cat_bytes=$(get_category_size "$BUILD_DIR" "$ext")
    SO_BYTES=$((SO_BYTES + cat_bytes))
done
echo "native_libs: $(human_size $SO_BYTES)"

ASSET_TOTAL=$((IMAGE_BYTES + VIDEO_BYTES + AUDIO_BYTES + FONT_BYTES + JS_BYTES + SO_BYTES))
OTHER_BYTES=$((TOTAL_BYTES - ASSET_TOTAL))
if [[ $OTHER_BYTES -lt 0 ]]; then OTHER_BYTES=0; fi
echo "other: $(human_size $OTHER_BYTES)"
echo ""

echo "--- File Type Distribution ---"
find "$BUILD_DIR" -type f 2>/dev/null \
    | sed 's/.*\.//' \
    | sort \
    | uniq -c \
    | sort -rn \
    | head -15 \
    | while read -r count ext; do
        printf "  %-8s %s files\n" ".$ext" "$count"
    done
echo ""

echo "=== END ANALYSIS ==="
exit $WARNINGS

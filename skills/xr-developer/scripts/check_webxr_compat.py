#!/usr/bin/env python3
"""Check JavaScript/HTML files for WebXR compatibility issues.

Scans source files for:
  - Deprecated WebVR API usage (navigator.getVRDisplays, etc.)
  - Missing WebXR feature detection (navigator.xr checks)
  - Missing session mode checks (isSessionSupported)
  - Use of non-standard or vendor-prefixed extensions
  - Common WebXR anti-patterns

Outputs a structured markdown compatibility report.
"""

import argparse
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, NamedTuple


class Issue(NamedTuple):
    """A single compatibility issue found in a file."""
    file: str
    line: int
    severity: str  # "error", "warning", "info"
    code: str
    message: str
    suggestion: str


# --- Detection Rules ---

DEPRECATED_WEBVR_PATTERNS = [
    (
        re.compile(r"navigator\s*\.\s*getVRDisplays", re.MULTILINE),
        "WEBVR_GET_DISPLAYS",
        "Use of deprecated navigator.getVRDisplays() (WebVR API)",
        "Replace with navigator.xr.requestSession('immersive-vr')",
    ),
    (
        re.compile(r"VRDisplay\b", re.MULTILINE),
        "WEBVR_DISPLAY",
        "Reference to deprecated VRDisplay interface (WebVR API)",
        "Use WebXR Device API (XRSession, XRFrame) instead",
    ),
    (
        re.compile(r"VRFrameData\b", re.MULTILINE),
        "WEBVR_FRAME_DATA",
        "Reference to deprecated VRFrameData (WebVR API)",
        "Use XRFrame and XRView from the WebXR Device API",
    ),
    (
        re.compile(r"VRPose\b", re.MULTILINE),
        "WEBVR_POSE",
        "Reference to deprecated VRPose (WebVR API)",
        "Use XRPose / XRViewerPose from the WebXR Device API",
    ),
    (
        re.compile(r"VRStageParameters\b", re.MULTILINE),
        "WEBVR_STAGE",
        "Reference to deprecated VRStageParameters (WebVR API)",
        "Use XRReferenceSpace with 'local-floor' or 'bounded-floor'",
    ),
    (
        re.compile(r"navigator\s*\.\s*activeVRDisplays", re.MULTILINE),
        "WEBVR_ACTIVE_DISPLAYS",
        "Use of deprecated navigator.activeVRDisplays (WebVR API)",
        "Use navigator.xr and XRSession management instead",
    ),
    (
        re.compile(r"VREyeParameters\b", re.MULTILINE),
        "WEBVR_EYE_PARAMS",
        "Reference to deprecated VREyeParameters (WebVR API)",
        "Use XRView from the WebXR Device API",
    ),
    (
        re.compile(r"\.requestPresent\s*\(", re.MULTILINE),
        "WEBVR_REQUEST_PRESENT",
        "Use of deprecated VRDisplay.requestPresent() (WebVR API)",
        "Use navigator.xr.requestSession() instead",
    ),
    (
        re.compile(r"\.exitPresent\s*\(", re.MULTILINE),
        "WEBVR_EXIT_PRESENT",
        "Use of deprecated VRDisplay.exitPresent() (WebVR API)",
        "Use XRSession.end() instead",
    ),
    (
        re.compile(r"\.getFrameData\s*\(", re.MULTILINE),
        "WEBVR_GET_FRAME_DATA",
        "Use of deprecated VRDisplay.getFrameData() (WebVR API)",
        "Use XRFrame.getViewerPose() in the XR animation frame callback",
    ),
]

NON_STANDARD_PATTERNS = [
    (
        re.compile(r"webkit[A-Z]\w*XR|webkitGetVR|webkitVR", re.MULTILINE),
        "VENDOR_WEBKIT_XR",
        "Webkit-prefixed XR/VR API detected",
        "Use the standard unprefixed WebXR Device API",
    ),
    (
        re.compile(r"moz[A-Z]\w*VR|mozGetVR|mozVR", re.MULTILINE),
        "VENDOR_MOZ_VR",
        "Mozilla-prefixed VR API detected",
        "Use the standard unprefixed WebXR Device API",
    ),
    (
        re.compile(r"ms[A-Z]\w*VR|msGetVR|msVR", re.MULTILINE),
        "VENDOR_MS_VR",
        "Microsoft-prefixed VR API detected",
        "Use the standard unprefixed WebXR Device API",
    ),
]

FEATURE_DETECTION_PATTERN = re.compile(
    r"""navigator\s*\.\s*xr\b""", re.MULTILINE
)

SESSION_SUPPORTED_PATTERN = re.compile(
    r"""isSessionSupported\s*\(""", re.MULTILINE
)

REQUEST_SESSION_PATTERN = re.compile(
    r"""requestSession\s*\(""", re.MULTILINE
)

REQUEST_ANIMATION_FRAME_PATTERN = re.compile(
    r"""\.setAnimationLoop\s*\(|\.requestAnimationFrame\s*\(""", re.MULTILINE
)

XR_ANIMATION_FRAME_PATTERN = re.compile(
    r"""xr\s*\.\s*requestAnimationFrame|setAnimationLoop""", re.MULTILINE
)


def find_line_number(content: str, match_start: int) -> int:
    """Return the 1-based line number for a character offset."""
    return content[:match_start].count("\n") + 1


def scan_file(filepath: Path) -> List[Issue]:
    """Scan a single file for WebXR compatibility issues."""
    try:
        content = filepath.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        return [Issue(
            file=str(filepath),
            line=0,
            severity="error",
            code="FILE_READ_ERROR",
            message=f"Could not read file: {e}",
            suggestion="Check file permissions and path",
        )]

    issues: List[Issue] = []
    fname = str(filepath)

    # Check deprecated WebVR patterns
    for pattern, code, message, suggestion in DEPRECATED_WEBVR_PATTERNS:
        for match in pattern.finditer(content):
            issues.append(Issue(
                file=fname,
                line=find_line_number(content, match.start()),
                severity="error",
                code=code,
                message=message,
                suggestion=suggestion,
            ))

    # Check non-standard / vendor-prefixed patterns
    for pattern, code, message, suggestion in NON_STANDARD_PATTERNS:
        for match in pattern.finditer(content):
            issues.append(Issue(
                file=fname,
                line=find_line_number(content, match.start()),
                severity="warning",
                code=code,
                message=message,
                suggestion=suggestion,
            ))

    # Check for missing feature detection
    has_navigator_xr = bool(FEATURE_DETECTION_PATTERN.search(content))
    has_request_session = bool(REQUEST_SESSION_PATTERN.search(content))
    has_session_supported = bool(SESSION_SUPPORTED_PATTERN.search(content))

    if has_request_session and not has_navigator_xr:
        issues.append(Issue(
            file=fname,
            line=find_line_number(content, REQUEST_SESSION_PATTERN.search(content).start()),
            severity="warning",
            code="MISSING_XR_CHECK",
            message="requestSession() called without checking navigator.xr existence",
            suggestion="Add 'if (navigator.xr)' guard before calling requestSession()",
        ))

    if has_request_session and not has_session_supported:
        issues.append(Issue(
            file=fname,
            line=find_line_number(content, REQUEST_SESSION_PATTERN.search(content).start()),
            severity="warning",
            code="MISSING_SESSION_SUPPORT_CHECK",
            message="requestSession() called without isSessionSupported() check",
            suggestion="Call navigator.xr.isSessionSupported() before requestSession()",
        ))

    # Sort issues by line number
    issues.sort(key=lambda i: i.line)
    return issues


def collect_files(paths: List[str]) -> List[Path]:
    """Expand file/directory arguments into a list of scannable files."""
    valid_extensions = {".js", ".mjs", ".ts", ".tsx", ".jsx", ".html", ".htm", ".vue", ".svelte"}
    result = []

    for p in paths:
        path = Path(p)
        if path.is_file():
            if path.suffix.lower() in valid_extensions:
                result.append(path)
            else:
                print(f"Warning: Skipping unsupported file type: {path}", file=sys.stderr)
        elif path.is_dir():
            for root, _dirs, files in os.walk(path):
                for fname in files:
                    fpath = Path(root) / fname
                    if fpath.suffix.lower() in valid_extensions:
                        result.append(fpath)
        else:
            print(f"Warning: Path does not exist: {path}", file=sys.stderr)

    return sorted(set(result))


def severity_icon(severity: str) -> str:
    """Return a text marker for severity level."""
    return {
        "error": "[ERROR]",
        "warning": "[WARN]",
        "info": "[INFO]",
    }.get(severity, "[?]")


def generate_report(all_issues: Dict[str, List[Issue]]) -> str:
    """Generate a markdown compatibility report."""
    lines = []
    lines.append("# WebXR Compatibility Report")
    lines.append("")

    total_files = len(all_issues)
    total_issues = sum(len(issues) for issues in all_issues.values())
    error_count = sum(
        1 for issues in all_issues.values() for i in issues if i.severity == "error"
    )
    warning_count = sum(
        1 for issues in all_issues.values() for i in issues if i.severity == "warning"
    )
    info_count = sum(
        1 for issues in all_issues.values() for i in issues if i.severity == "info"
    )
    clean_files = sum(1 for issues in all_issues.values() if not issues)

    lines.append("## Summary")
    lines.append("")
    lines.append(f"| Metric | Count |")
    lines.append(f"|--------|------:|")
    lines.append(f"| Files scanned | {total_files} |")
    lines.append(f"| Files with issues | {total_files - clean_files} |")
    lines.append(f"| Clean files | {clean_files} |")
    lines.append(f"| Total issues | {total_issues} |")
    lines.append(f"| Errors | {error_count} |")
    lines.append(f"| Warnings | {warning_count} |")
    lines.append(f"| Info | {info_count} |")
    lines.append("")

    if total_issues == 0:
        lines.append("> No WebXR compatibility issues found. All files look clean.")
        lines.append("")
        return "\n".join(lines)

    # Verdict
    if error_count > 0:
        lines.append(
            f"> **{error_count} error(s) found.** Deprecated WebVR API usage detected. "
            "Migration to WebXR Device API is required."
        )
    elif warning_count > 0:
        lines.append(
            f"> **{warning_count} warning(s) found.** Some best practices are missing. "
            "Consider adding feature detection and session support checks."
        )
    lines.append("")

    # Detailed results per file
    lines.append("## Details")
    lines.append("")

    for filepath, issues in sorted(all_issues.items()):
        if not issues:
            continue

        lines.append(f"### `{filepath}`")
        lines.append("")
        lines.append("| Line | Severity | Code | Issue | Suggestion |")
        lines.append("|-----:|----------|------|-------|------------|")

        for issue in issues:
            sev = severity_icon(issue.severity)
            lines.append(
                f"| {issue.line} | {sev} | `{issue.code}` | {issue.message} | {issue.suggestion} |"
            )

        lines.append("")

    lines.append("---")
    lines.append("*Report generated by check_webxr_compat.py*")
    lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Check JavaScript/HTML files for WebXR compatibility issues. "
            "Detects deprecated WebVR API usage, missing feature detection, "
            "missing session mode checks, and non-standard extensions. "
            "Outputs a structured markdown report."
        )
    )
    parser.add_argument(
        "paths",
        nargs="+",
        help="One or more JavaScript/HTML files or directories to scan",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=None,
        help="Write report to a file instead of stdout",
    )

    args = parser.parse_args()

    files = collect_files(args.paths)
    if not files:
        print("Error: No scannable files found (.js, .mjs, .ts, .tsx, .jsx, .html, .htm, .vue, .svelte)", file=sys.stderr)
        sys.exit(1)

    all_issues: Dict[str, List[Issue]] = {}
    for fpath in files:
        all_issues[str(fpath)] = scan_file(fpath)

    report = generate_report(all_issues)

    if args.output:
        try:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(report, encoding="utf-8")
            print(f"Report written to: {output_path.resolve()}", file=sys.stderr)
        except OSError as e:
            print(f"Error: Could not write output file: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print(report)

    # Exit with non-zero status if errors were found
    has_errors = any(
        issue.severity == "error"
        for issues in all_issues.values()
        for issue in issues
    )
    if has_errors:
        sys.exit(1)


if __name__ == "__main__":
    main()

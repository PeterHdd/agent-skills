#!/usr/bin/env python3
"""generate_report.py — Generate a markdown evidence report template from screenshots.

Takes a directory of screenshot files and produces a structured markdown report
with environment info, screenshot inventory, and placeholder sections for findings.
"""

import argparse
import datetime
import json
import os
import struct
import sys


# Common image extensions
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".tiff"}


def get_image_dimensions(filepath):
    """Get image dimensions from file header without external libraries."""
    ext = os.path.splitext(filepath)[1].lower()

    try:
        with open(filepath, "rb") as f:
            header = f.read(32)

            # PNG
            if header[:8] == b"\x89PNG\r\n\x1a\n":
                width = struct.unpack(">I", header[16:20])[0]
                height = struct.unpack(">I", header[20:24])[0]
                return width, height

            # JPEG
            if header[:2] == b"\xff\xd8":
                f.seek(0)
                data = f.read()
                i = 2
                while i < len(data) - 9:
                    if data[i] == 0xFF:
                        marker = data[i + 1]
                        if marker in (0xC0, 0xC1, 0xC2):
                            height = struct.unpack(">H", data[i + 5 : i + 7])[0]
                            width = struct.unpack(">H", data[i + 7 : i + 9])[0]
                            return width, height
                        elif marker == 0xD9:
                            break
                        elif marker == 0xDA:
                            break
                        else:
                            length = struct.unpack(">H", data[i + 2 : i + 4])[0]
                            i += 2 + length
                    else:
                        i += 1
                return None, None

            # GIF
            if header[:6] in (b"GIF87a", b"GIF89a"):
                width = struct.unpack("<H", header[6:8])[0]
                height = struct.unpack("<H", header[8:10])[0]
                return width, height

            # BMP
            if header[:2] == b"BM":
                width = struct.unpack("<I", header[18:22])[0]
                height = abs(struct.unpack("<i", header[22:26])[0])
                return width, height

    except (IOError, struct.error, IndexError):
        pass

    return None, None


def collect_screenshots(directory):
    """Collect screenshot files from the directory."""
    screenshots = []

    if not os.path.isdir(directory):
        print(f"ERROR: Directory not found: {directory}", file=sys.stderr)
        sys.exit(1)

    for entry in sorted(os.listdir(directory)):
        filepath = os.path.join(directory, entry)
        if not os.path.isfile(filepath):
            continue

        ext = os.path.splitext(entry)[1].lower()
        if ext not in IMAGE_EXTENSIONS:
            continue

        size_bytes = os.path.getsize(filepath)
        width, height = get_image_dimensions(filepath)
        mod_time = os.path.getmtime(filepath)
        timestamp = datetime.datetime.fromtimestamp(mod_time).strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        screenshots.append(
            {
                "filename": entry,
                "filepath": filepath,
                "size_bytes": size_bytes,
                "size_human": format_size(size_bytes),
                "width": width,
                "height": height,
                "timestamp": timestamp,
            }
        )

    return screenshots


def format_size(size_bytes):
    """Format size in human-readable form."""
    if size_bytes >= 1048576:
        return f"{size_bytes / 1048576:.1f} MB"
    elif size_bytes >= 1024:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes} B"


def infer_viewport(filename):
    """Infer viewport type from filename conventions."""
    lower = filename.lower()
    if "mobile" in lower or "375" in lower:
        return "Mobile (375x667)"
    if "tablet" in lower or "768" in lower:
        return "Tablet (768x1024)"
    if "desktop" in lower or "1280" in lower or "1920" in lower:
        return "Desktop (1280x720)"
    return "Unknown"


def generate_markdown_report(screenshots, directory, project_name, base_url):
    """Generate the markdown evidence report."""
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = []

    # Header
    lines.append(f"# Evidence Report: {project_name}")
    lines.append("")
    lines.append(f"**Generated:** {now}")
    lines.append(f"**Screenshot directory:** `{os.path.abspath(directory)}`")
    lines.append(f"**Total screenshots:** {len(screenshots)}")
    lines.append("")

    # Environment
    lines.append("## 1. Environment")
    lines.append("")
    lines.append("| Property | Value |")
    lines.append("|----------|-------|")
    lines.append(f"| Date | {now} |")
    lines.append(f"| URL | {base_url} |")
    lines.append("| Browser | Chromium (Playwright) |")
    lines.append("| OS | _{operating system}_ |")

    # Collect unique viewports
    viewports = set()
    for ss in screenshots:
        if ss["width"] and ss["height"]:
            viewports.add(f"{ss['width']}x{ss['height']}")
    if viewports:
        lines.append(f"| Viewports tested | {', '.join(sorted(viewports))} |")
    else:
        lines.append("| Viewports tested | _{list viewports}_ |")

    lines.append("")

    # Screenshot Inventory
    lines.append("## 2. Screenshot Inventory")
    lines.append("")
    lines.append("| # | File | Size | Dimensions | Viewport | Captured |")
    lines.append("|---|------|------|------------|----------|----------|")
    for i, ss in enumerate(screenshots, 1):
        dims = (
            f"{ss['width']}x{ss['height']}"
            if ss["width"] and ss["height"]
            else "unknown"
        )
        viewport = infer_viewport(ss["filename"])
        lines.append(
            f"| {i} | `{ss['filename']}` | {ss['size_human']} | {dims} | {viewport} | {ss['timestamp']} |"
        )
    lines.append("")

    # Screenshot embeds
    lines.append("## 3. Screenshots")
    lines.append("")
    for i, ss in enumerate(screenshots, 1):
        name_without_ext = os.path.splitext(ss["filename"])[0]
        title = name_without_ext.replace("-", " ").replace("_", " ").title()
        lines.append(f"### 3.{i}. {title}")
        lines.append("")
        lines.append(f"![{title}]({ss['filename']})")
        lines.append("")
        if ss["width"] and ss["height"]:
            lines.append(
                f"*{ss['width']}x{ss['height']} | {ss['size_human']}*"
            )
        else:
            lines.append(f"*{ss['size_human']}*")
        lines.append("")

    # Findings section (placeholder)
    lines.append("## 4. Findings")
    lines.append("")
    lines.append("<!-- Fill in findings below. For each finding, use this template: -->")
    lines.append("")
    lines.append("### Finding 1: <!-- Title -->")
    lines.append("")
    lines.append("| Property | Value |")
    lines.append("|----------|-------|")
    lines.append("| Verdict | PASS / PARTIAL / FAIL |")
    lines.append("| Severity | High / Medium / Low |")
    lines.append("| Spec reference | <!-- Quote exact spec text --> |")
    lines.append("| Screenshot | <!-- Reference screenshot number --> |")
    lines.append("| Selector | <!-- CSS selector or data-testid --> |")
    lines.append("")
    lines.append("**Observation:** <!-- What was observed -->")
    lines.append("")
    lines.append("**Expected:** <!-- What the spec requires -->")
    lines.append("")
    lines.append("**Reproduction:**")
    lines.append("```bash")
    lines.append("# Copy-pasteable command to reproduce")
    lines.append("```")
    lines.append("")

    # Summary section (placeholder)
    lines.append("## 5. Summary")
    lines.append("")
    lines.append("| Verdict | Count |")
    lines.append("|---------|-------|")
    lines.append("| PASS | <!-- --> |")
    lines.append("| PARTIAL | <!-- --> |")
    lines.append("| FAIL | <!-- --> |")
    lines.append("")
    lines.append("**Overall assessment:** _{pass/fail with summary}_")
    lines.append("")
    lines.append("**Blocking issues:** _{list any blocking issues or None}_")
    lines.append("")
    lines.append("**Recommendations:** _{list recommendations}_")
    lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Generate a markdown evidence report template from a screenshot directory.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
The generated report includes:
  - Environment information (date, browser, viewports)
  - Screenshot inventory (file name, size, dimensions)
  - Embedded screenshot references
  - Placeholder finding templates for the agent to fill in
  - Summary table template

examples:
  %(prog)s ./qa-evidence
  %(prog)s --project "Login Page Redesign" --url http://localhost:3000 ./screenshots
  %(prog)s -o report.md --format markdown ./qa-evidence
        """,
    )
    parser.add_argument(
        "screenshot_dir",
        help="Directory containing screenshot files",
    )
    parser.add_argument(
        "--project",
        default="QA Evidence Collection",
        help="Project or test name for the report header",
    )
    parser.add_argument(
        "--url",
        default="http://localhost:3000",
        help="Base URL that was tested (default: http://localhost:3000)",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Output file path (default: stdout)",
    )
    parser.add_argument(
        "--format",
        choices=["markdown", "json"],
        default="markdown",
        help="Output format (default: markdown)",
    )

    args = parser.parse_args()

    screenshots = collect_screenshots(args.screenshot_dir)

    if not screenshots:
        print(
            f"WARNING: No image files found in {args.screenshot_dir}",
            file=sys.stderr,
        )
        print(
            f"Supported extensions: {', '.join(sorted(IMAGE_EXTENSIONS))}",
            file=sys.stderr,
        )

    if args.format == "json":
        output = json.dumps(
            {
                "project": args.project,
                "url": args.url,
                "generated": datetime.datetime.now().isoformat(),
                "screenshot_dir": os.path.abspath(args.screenshot_dir),
                "screenshots": screenshots,
            },
            indent=2,
        )
    else:
        output = generate_markdown_report(
            screenshots, args.screenshot_dir, args.project, args.url
        )

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"Report written to: {args.output}", file=sys.stderr)
        print(f"Screenshots included: {len(screenshots)}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()

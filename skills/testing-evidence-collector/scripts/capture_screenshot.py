#!/usr/bin/env python3
"""capture_screenshot.py — Capture a full-page screenshot of a URL using Playwright.

Self-contained script that invokes Playwright via subprocess to capture screenshots
with configurable viewport size and wait time. Falls back gracefully if Playwright
is not installed.
"""

import argparse
import os
import subprocess
import sys
import tempfile


PLAYWRIGHT_SCRIPT_TEMPLATE = """
const {{ chromium }} = require('playwright');

(async () => {{
  const browser = await chromium.launch({{ headless: true }});
  const context = await browser.newContext({{
    viewport: {{ width: {width}, height: {height} }},
  }});
  const page = await context.newPage();

  try {{
    await page.goto('{url}', {{ waitUntil: 'networkidle', timeout: 30000 }});
  }} catch (e) {{
    console.error('WARNING: Navigation timeout, capturing current state.');
  }}

  {wait_line}

  await page.screenshot({{
    path: '{output_path}',
    fullPage: {full_page},
  }});

  console.log(JSON.stringify({{
    status: 'success',
    url: '{url}',
    output: '{output_path}',
    viewport: {{ width: {width}, height: {height} }},
    fullPage: {full_page},
  }}));

  await browser.close();
}})();
"""

PYTHON_PLAYWRIGHT_SCRIPT_TEMPLATE = """
import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={{"width": {width}, "height": {height}}}
        )
        page = await context.new_page()

        try:
            await page.goto("{url}", wait_until="networkidle", timeout=30000)
        except Exception as e:
            print(f"WARNING: Navigation issue: {{e}}", flush=True)

        {wait_line}

        await page.screenshot(
            path="{output_path}",
            full_page={full_page},
        )

        print('{{"status": "success", "url": "{url}", "output": "{output_path}", "viewport": {{"width": {width}, "height": {height}}}, "fullPage": {full_page_lower}}}')

        await browser.close()

asyncio.run(main())
"""


def check_playwright_node():
    """Check if Node.js Playwright is available."""
    try:
        result = subprocess.run(
            ["node", "-e", "require('playwright')"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def check_playwright_python():
    """Check if Python Playwright is available."""
    try:
        result = subprocess.run(
            [sys.executable, "-c", "import playwright"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def check_npx_playwright():
    """Check if npx playwright is available."""
    try:
        result = subprocess.run(
            ["npx", "playwright", "--version"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def capture_with_node(url, output_path, width, height, full_page, wait_ms):
    """Capture screenshot using Node.js Playwright."""
    wait_line = f"await page.waitForTimeout({wait_ms});" if wait_ms > 0 else ""
    full_page_js = "true" if full_page else "false"

    script = PLAYWRIGHT_SCRIPT_TEMPLATE.format(
        url=url,
        output_path=output_path.replace("\\", "\\\\"),
        width=width,
        height=height,
        full_page=full_page_js,
        wait_line=wait_line,
    )

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".js", delete=False
    ) as f:
        f.write(script)
        script_path = f.name

    try:
        result = subprocess.run(
            ["node", script_path],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            print(f"ERROR: Playwright script failed:\n{result.stderr}", file=sys.stderr)
            return False
        print(result.stdout.strip())
        return True
    except subprocess.TimeoutExpired:
        print("ERROR: Screenshot capture timed out after 60 seconds.", file=sys.stderr)
        return False
    finally:
        os.unlink(script_path)


def capture_with_python(url, output_path, width, height, full_page, wait_ms):
    """Capture screenshot using Python Playwright."""
    wait_line = f'await page.wait_for_timeout({wait_ms})' if wait_ms > 0 else "pass"
    full_page_py = "True" if full_page else "False"
    full_page_lower = "true" if full_page else "false"

    script = PYTHON_PLAYWRIGHT_SCRIPT_TEMPLATE.format(
        url=url,
        output_path=output_path.replace("\\", "\\\\"),
        width=width,
        height=height,
        full_page=full_page_py,
        full_page_lower=full_page_lower,
        wait_line=wait_line,
    )

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False
    ) as f:
        f.write(script)
        script_path = f.name

    try:
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            print(f"ERROR: Playwright script failed:\n{result.stderr}", file=sys.stderr)
            return False
        print(result.stdout.strip())
        return True
    except subprocess.TimeoutExpired:
        print("ERROR: Screenshot capture timed out after 60 seconds.", file=sys.stderr)
        return False
    finally:
        os.unlink(script_path)


def capture_with_npx(url, output_path, width, height, full_page, wait_ms):
    """Capture screenshot using npx playwright screenshot command."""
    cmd = [
        "npx",
        "playwright",
        "screenshot",
        f"--viewport-size={width},{height}",
    ]
    if full_page:
        cmd.append("--full-page")
    if wait_ms > 0:
        cmd.append(f"--wait-for-timeout={wait_ms}")
    cmd.extend([url, output_path])

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=60
        )
        if result.returncode != 0:
            print(f"ERROR: npx playwright screenshot failed:\n{result.stderr}", file=sys.stderr)
            return False
        print(
            f'{{"status": "success", "url": "{url}", "output": "{output_path}", '
            f'"viewport": {{"width": {width}, "height": {height}}}, '
            f'"fullPage": {"true" if full_page else "false"}}}'
        )
        return True
    except subprocess.TimeoutExpired:
        print("ERROR: Screenshot capture timed out after 60 seconds.", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Capture a full-page screenshot of a URL using Playwright.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Requires Playwright to be installed (Node.js or Python version).
The script auto-detects which Playwright installation is available.

Install options:
  Node.js:  npm install playwright
  Python:   pip install playwright && playwright install chromium
  npx:      npx playwright install chromium

examples:
  %(prog)s http://localhost:3000 screenshot.png
  %(prog)s --full-page --width 1920 --height 1080 http://example.com page.png
  %(prog)s --wait 2000 http://localhost:3000/dashboard dashboard.png
        """,
    )
    parser.add_argument("url", help="URL to capture")
    parser.add_argument("output", help="Output file path for the screenshot")
    parser.add_argument(
        "--width", type=int, default=1280, help="Viewport width (default: 1280)"
    )
    parser.add_argument(
        "--height", type=int, default=720, help="Viewport height (default: 720)"
    )
    parser.add_argument(
        "--full-page",
        action="store_true",
        help="Capture the full scrollable page, not just the viewport",
    )
    parser.add_argument(
        "--wait",
        type=int,
        default=0,
        help="Milliseconds to wait before capture (default: 0)",
    )

    args = parser.parse_args()

    # Ensure output directory exists
    output_dir = os.path.dirname(args.output)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    # Try capture methods in order of preference
    if check_playwright_node():
        success = capture_with_node(
            args.url, args.output, args.width, args.height, args.full_page, args.wait
        )
    elif check_playwright_python():
        success = capture_with_python(
            args.url, args.output, args.width, args.height, args.full_page, args.wait
        )
    elif check_npx_playwright():
        success = capture_with_npx(
            args.url, args.output, args.width, args.height, args.full_page, args.wait
        )
    else:
        print("ERROR: Playwright is not installed.", file=sys.stderr)
        print("", file=sys.stderr)
        print("Install Playwright using one of these methods:", file=sys.stderr)
        print("", file=sys.stderr)
        print("  Node.js (recommended):", file=sys.stderr)
        print("    npm install playwright", file=sys.stderr)
        print("    npx playwright install chromium", file=sys.stderr)
        print("", file=sys.stderr)
        print("  Python:", file=sys.stderr)
        print("    pip install playwright", file=sys.stderr)
        print("    playwright install chromium", file=sys.stderr)
        print("", file=sys.stderr)
        print("  npx (no local install):", file=sys.stderr)
        print("    npx playwright install chromium", file=sys.stderr)
        sys.exit(1)

    if success and os.path.isfile(args.output):
        size_bytes = os.path.getsize(args.output)
        size_kb = round(size_bytes / 1024, 1)
        print(f"Screenshot saved: {args.output} ({size_kb} KB)", file=sys.stderr)
        sys.exit(0)
    else:
        print("ERROR: Screenshot capture failed.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

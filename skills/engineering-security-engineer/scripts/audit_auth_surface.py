#!/usr/bin/env python3
"""Inventory auth-related files and patterns in a repository."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


PATTERNS = {
    "auth": re.compile(r"\b(auth|authenticate|authorization|authorize|rbac|permission)\b", re.I),
    "token": re.compile(r"\b(jwt|token|refresh token|bearer)\b", re.I),
    "session": re.compile(r"\b(session|cookie|csrf|samesite|httponly)\b", re.I),
    "password": re.compile(r"\b(password|passwd|bcrypt|argon2|otp|mfa|2fa)\b", re.I),
}
SKIP_PARTS = {".git", "node_modules", "vendor", "__pycache__", ".next", "dist", "build"}
TEXT_SUFFIXES = {
    ".js", ".jsx", ".ts", ".tsx", ".py", ".go", ".rb", ".java", ".kt", ".php",
    ".cs", ".rs", ".md", ".yml", ".yaml", ".json", ".env", ".toml", ".ini",
}


def should_scan(path: Path) -> bool:
    if any(part in SKIP_PARTS for part in path.parts):
        return False
    return path.is_file() and (path.suffix in TEXT_SUFFIXES or path.name.lower() in {"dockerfile", "jenkinsfile"})


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Scan a repository for auth, token, session, and permission hotspots."
    )
    parser.add_argument("path", nargs="?", default=".", help="Repository path (default: current directory)")
    parser.add_argument("--top", type=int, default=15, help="Maximum files to show (default: 15)")
    args = parser.parse_args()

    root = Path(args.path).resolve()
    if not root.exists():
        parser.error(f"path does not exist: {root}")

    scored: list[tuple[int, Path, dict[str, int]]] = []
    for path in root.rglob("*"):
        if not should_scan(path):
            continue
        text = path.read_text(errors="ignore")
        counts = {key: len(pattern.findall(text)) for key, pattern in PATTERNS.items()}
        score = sum(counts.values())
        if score:
            scored.append((score, path, counts))
    scored.sort(key=lambda item: (-item[0], str(item[1])))

    print("## Auth Surface Audit")
    print("")
    print(f"**Repository**: `{root}`")
    print("")
    print("| Score | File | Signals |")
    print("|---|---|---|")
    for score, path, counts in scored[: args.top]:
        signal_text = ", ".join(f"{key}={value}" for key, value in counts.items() if value)
        print(f"| {score} | `{path.relative_to(root)}` | {signal_text} |")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

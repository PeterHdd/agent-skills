#!/usr/bin/env python3
"""Scan a repository for deployment-risk signals."""

from __future__ import annotations

import argparse
from pathlib import Path


AREAS = {
    "github_actions": [".github/workflows"],
    "gitlab_ci": [".gitlab-ci.yml"],
    "jenkins": ["Jenkinsfile"],
    "docker": ["Dockerfile", "docker-compose.yml", "docker-compose.yaml"],
    "terraform": ["main.tf", "terraform", "infra"],
    "kubernetes": ["k8s", "helm", "charts"],
}


def area_hits(root: Path) -> dict[str, list[str]]:
    hits: dict[str, list[str]] = {}
    for area, names in AREAS.items():
        hits[area] = [name for name in names if (root / name).exists()]
    return hits


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Summarize CI, runtime, and rollback signals in a repository."
    )
    parser.add_argument("path", nargs="?", default=".", help="Repository root (default: current directory)")
    args = parser.parse_args()

    root = Path(args.path).resolve()
    if not root.exists():
        parser.error(f"path does not exist: {root}")

    hits = area_hits(root)
    has_readme = (root / "README.md").exists()
    readme_text = (root / "README.md").read_text(errors="ignore").lower() if has_readme else ""
    risks: list[str] = []
    if not any(hits.values()):
        risks.append("No deployment system detected from repository structure.")
    if hits["terraform"] and any(root.rglob("*.tfstate")):
        risks.append("Terraform state file is present in the repository.")
    if (hits["docker"] or hits["kubernetes"]) and "/health" not in readme_text and "healthcheck" not in readme_text:
        risks.append("Runtime assets detected, but health checks are not documented in README.")

    print("## Deployment Risk Summary")
    print("")
    print(f"**Repository**: `{root}`")
    print("")
    print("| Area | Signal |")
    print("|---|---|")
    for area, matches in hits.items():
        signal = ", ".join(f"`{match}`" for match in matches) if matches else "none detected"
        print(f"| {area.replace('_', ' ')} | {signal} |")
    print("")
    print("## Risks")
    if risks:
        for risk in risks:
            print(f"- {risk}")
    else:
        print("- No obvious structural deployment risks detected from repo layout alone.")
    print("")
    print("## Next Actions")
    print("- Confirm the current deployment entrypoint and rollback command before making changes.")
    print("- Check whether health checks, smoke tests, and alert gates exist for the changed service.")
    print("- Separate stateful changes from stateless rollouts whenever possible.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

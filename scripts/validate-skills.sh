#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKILLS_DIR="${REPO_ROOT}/skills"
SKILLS_REF_REPO="${SKILLS_REF_REPO:-/tmp/agentskills}"
SKILLS_REF_VENV="${SKILLS_REF_REPO}/.venv"
SKIP_SKILLS_REF=0
NO_INSTALL=0

usage() {
  cat <<USAGE
Usage: ./scripts/validate-skills.sh [--no-skills-ref] [--no-install]

Options:
  --no-skills-ref   Skip skills-ref schema validation.
  --no-install      Do not install skills-ref; fail if missing.
USAGE
}

for arg in "$@"; do
  case "$arg" in
    --no-skills-ref)
      SKIP_SKILLS_REF=1
      ;;
    --no-install)
      NO_INSTALL=1
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $arg" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [[ ! -d "${SKILLS_DIR}" ]]; then
  echo "Missing skills directory: ${SKILLS_DIR}" >&2
  exit 1
fi

pass_count=0
fail_count=0

echo "Check 1/2: Frontmatter validation"
while IFS= read -r skill_file; do
  skill_id="$(basename "$(dirname "${skill_file}")")"
  if ! awk '
    NR==1 && $0=="---" { in_fm=1; next }
    in_fm && $0=="---" { end_fm=1; exit }
    in_fm && /^name:[[:space:]]*[^[:space:]].*$/ { has_name=1 }
    in_fm && /^description:[[:space:]]*[^[:space:]].*$/ { has_desc=1 }
    in_fm && /^version:[[:space:]]*[^[:space:]].*$/ { has_ver=1 }
    in_fm && /^metadata:/ { in_meta=1; next }
    in_meta && /^[^[:space:]]/ { in_meta=0 }
    in_meta && /^[[:space:]]+version:[[:space:]]*/ { has_ver=1 }
    END {
      if (!(in_fm && end_fm && has_name && has_desc && has_ver)) exit 1
    }
  ' "${skill_file}"; then
    echo "  FAIL ${skill_id}: invalid or missing frontmatter fields" >&2
    fail_count=$((fail_count + 1))
  else
    pass_count=$((pass_count + 1))
  fi
done < <(find "${SKILLS_DIR}" -mindepth 2 -maxdepth 2 -type f -name SKILL.md | sort)

if [[ "${fail_count}" -gt 0 ]]; then
  echo "Frontmatter check failed (${fail_count} skills)." >&2
  exit 1
fi
echo "  OK ${pass_count} skills"

if [[ "${SKIP_SKILLS_REF}" -eq 0 ]]; then
  echo "Check 2/2: skills-ref validation"

  if [[ ! -x "${SKILLS_REF_VENV}/bin/skills-ref" ]]; then
    if [[ "${NO_INSTALL}" -eq 1 ]]; then
      echo "skills-ref not installed at ${SKILLS_REF_VENV} and --no-install is set." >&2
      exit 1
    fi

    rm -rf "${SKILLS_REF_REPO}"
    git clone https://github.com/agentskills/agentskills.git "${SKILLS_REF_REPO}" >/dev/null 2>&1

    if command -v uv >/dev/null 2>&1; then
      (cd "${SKILLS_REF_REPO}" && uv sync >/dev/null)
    else
      (cd "${SKILLS_REF_REPO}" && python3 -m venv .venv && . .venv/bin/activate && pip install -e . >/dev/null)
    fi
  fi

  validator="${SKILLS_REF_VENV}/bin/skills-ref"
  failed_skills=0
  while IFS= read -r skill_dir; do
    skill_id="$(basename "${skill_dir}")"
    if ! "${validator}" validate "${skill_dir}" >/dev/null 2>&1; then
      echo "  FAIL ${skill_id}: skills-ref validate failed" >&2
      failed_skills=$((failed_skills + 1))
    fi
  done < <(find "${SKILLS_DIR}" -mindepth 1 -maxdepth 1 -type d | sort)

  if [[ "${failed_skills}" -gt 0 ]]; then
    echo "skills-ref check failed (${failed_skills} skills)." >&2
    exit 1
  fi
  echo "  OK skills-ref validation"
else
  echo "Check 2/2: skills-ref validation skipped (--no-skills-ref)"
fi

echo "All checks passed."

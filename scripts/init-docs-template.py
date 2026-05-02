#!/usr/bin/env python3
"""Initialize a project with the reusable documentation template."""

from __future__ import annotations

import argparse
import shutil
from datetime import date
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_DIR = REPO_ROOT / "docs" / "templates"

TARGETS = {
    "ROOT_README_TEMPLATE.md": "README.md",
    "CONTEXT_TEMPLATE.md": "CONTEXT.md",
    "CLAUDE_TEMPLATE.md": "CLAUDE.md",
    "CONTRIBUTING_TEMPLATE.md": "CONTRIBUTING.md",
    "TASKS_TEMPLATE.md": "docs/TASKS.md",
    "ONBOARDING_TEMPLATE.md": "docs/ONBOARDING.md",
    "TRACKER_TEMPLATE.md": "docs/planning/ROADMAP.md",
    "ADR_TEMPLATE.md": "docs/architecture/DECISIONS.md",
    "TRACKER_TEMPLATE.md::quality": "docs/quality/QUALITY_TRACKER.md",
    "TRACKER_TEMPLATE.md::security": "docs/security/SECURITY_TRACKER.md",
    "CHANGELOG_TEMPLATE.md": "docs/history/CHANGELOG.md",
    "RUNBOOK_TEMPLATE.md": "docs/reference/RUNBOOK.md",
    "CONFIGURATION_TEMPLATE.md": "docs/config/CONFIGURATION.md",
    "TEST_STRATEGY_TEMPLATE.md": "docs/testing/TEST_STRATEGY.md",
    "RISK_REGISTER_TEMPLATE.md": "docs/risks/RISK_REGISTER.md",
    "INCIDENT_LOG_TEMPLATE.md": "docs/incidents/INCIDENT_LOG.md",
    "SECURITY_BASELINE_TEMPLATE.md": "docs/security/SECURITY_BASELINE.md",
    "AUTOMATION_TEMPLATE.md": "docs/automation/AUTOMATION.md",
    "DOCS_VALIDATION_TEMPLATE.md": "docs/quality/DOCS_VALIDATION.md",
}

COPY_AS_TEMPLATE = [
    "ADR_TEMPLATE.md",
    "AUTOMATION_TEMPLATE.md",
    "CHANGELOG_TEMPLATE.md",
    "CLAUDE_TEMPLATE.md",
    "CONFIGURATION_TEMPLATE.md",
    "CONTEXT_TEMPLATE.md",
    "CONTRIBUTING_TEMPLATE.md",
    "DOCS_VALIDATION_TEMPLATE.md",
    "INCIDENT_LOG_TEMPLATE.md",
    "ONBOARDING_TEMPLATE.md",
    "RISK_REGISTER_TEMPLATE.md",
    "ROOT_README_TEMPLATE.md",
    "RUNBOOK_TEMPLATE.md",
    "SECURITY_BASELINE_TEMPLATE.md",
    "TASKS_TEMPLATE.md",
    "TEST_STRATEGY_TEMPLATE.md",
    "TRACKER_TEMPLATE.md",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Initialize docs/ and root project docs from reusable templates."
    )
    parser.add_argument("--target", required=True, help="Target project directory")
    parser.add_argument("--project-name", required=True, help="Human-readable project name")
    parser.add_argument("--owner", required=True, help="Primary owner or maintainer")
    parser.add_argument("--stack", default="mixed", help="Main stack, such as dotnet, python, node, or mixed")
    parser.add_argument("--repo-name", help="Repository or folder name. Defaults to target folder name")
    parser.add_argument("--date", default=date.today().isoformat(), help="Bootstrap date in YYYY-MM-DD format")
    parser.add_argument("--install-command", default="TODO: add install command")
    parser.add_argument("--run-command", default="TODO: add run command")
    parser.add_argument("--test-command", default="TODO: add test command")
    parser.add_argument("--force", action="store_true", help="Overwrite existing target files")
    parser.add_argument("--dry-run", action="store_true", help="Print planned writes without changing files")
    return parser.parse_args()


def replacements(args: argparse.Namespace, target: Path) -> dict[str, str]:
    repo_name = args.repo_name or target.name
    return {
        "{{PROJECT_NAME}}": args.project_name,
        "{{REPO_NAME}}": repo_name,
        "{{OWNER}}": args.owner,
        "{{DATE}}": args.date,
        "{{STACK}}": args.stack,
        "{{INSTALL_COMMAND}}": args.install_command,
        "{{RUN_COMMAND}}": args.run_command,
        "{{TEST_COMMAND}}": args.test_command,
    }


def render(template_name: str, values: dict[str, str]) -> str:
    source_name = template_name.split("::", maxsplit=1)[0]
    content = (TEMPLATE_DIR / source_name).read_text(encoding="utf-8")
    for old, new in values.items():
        content = content.replace(old, new)
    return content


def write_file(path: Path, content: str, force: bool, dry_run: bool) -> str:
    if path.exists() and not force:
        return f"skip existing {path}"
    if dry_run:
        action = "overwrite" if path.exists() else "create"
        return f"{action} {path}"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")
    return f"wrote {path}"


def copy_templates(target: Path, force: bool, dry_run: bool) -> list[str]:
    results: list[str] = []
    destination_dir = target / "docs" / "templates"
    for template_name in COPY_AS_TEMPLATE:
        source = TEMPLATE_DIR / template_name
        destination = destination_dir / template_name
        if destination.exists() and not force:
            results.append(f"skip existing {destination}")
            continue
        if dry_run:
            action = "overwrite" if destination.exists() else "copy"
            results.append(f"{action} {destination}")
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        results.append(f"copied {destination}")
    return results


def main() -> int:
    args = parse_args()
    target = Path(args.target).expanduser().resolve()
    values = replacements(args, target)

    if not TEMPLATE_DIR.exists():
        raise SystemExit(f"Template directory not found: {TEMPLATE_DIR}")

    results: list[str] = []
    if not args.dry_run:
        target.mkdir(parents=True, exist_ok=True)

    for template_name, relative_target in TARGETS.items():
        content = render(template_name, values)
        destination = target / relative_target
        results.append(write_file(destination, content, args.force, args.dry_run))

    results.extend(copy_templates(target, args.force, args.dry_run))

    print("\n".join(results))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

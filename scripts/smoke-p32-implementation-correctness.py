#!/usr/bin/env python3
"""
P3.2 Implementation-Correctness Smoke Harness
Version : 1.0.0

Automates Steps 1 and 3 of the P3.2 manual smoke workflow:
  1. Retrieve one implementation-spec chunk via /rag/search HTTP (no MCP dependency)
  2. Run dotnet build and capture exit code + warning count
  3. Optionally run an API smoke and record HTTP status + response status
  4. Output a timestamped JSON report

Report field conventions reuse those from scripts/eval-retrieval-quality.py
(timestamp, version, collection, per-query list). Retrieval scoring is
intentionally omitted — this harness measures implementation correctness only.

Usage:
  python3 scripts/smoke-p32-implementation-correctness.py
  python3 scripts/smoke-p32-implementation-correctness.py --gateway-url http://192.168.18.199:5200
  python3 scripts/smoke-p32-implementation-correctness.py --build-only
  python3 scripts/smoke-p32-implementation-correctness.py --no-smoke
  python3 scripts/smoke-p32-implementation-correctness.py --session "manual run terminal 2"
  python3 scripts/smoke-p32-implementation-correctness.py --output .claude/reports/custom.json

Exit code: 0 = pass, 1 = partial or fail.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Optional

VERSION = "1.0.0"
GATEWAY_URL = "http://192.168.18.199:5200"
PROJECT = "homelab"

# Priority query list from docs/superpowers/specs/2026-05-10-p32-smoke-design.md
PRIORITY_QUERIES = [
    "rag gateway retrieval service contract",
    "rag gateway knowledge expansion retrieval",
    "grounded answer path citation tagging",
]


# ── HTTP helper ──────────────────────────────────────────────────────────────

def _post_json(url: str, body: dict, timeout: int = 30) -> dict:
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


# ── Retrieval ────────────────────────────────────────────────────────────────

def _retrieve_one(gateway_url: str, query: str, project: str, timeout: int) -> dict:
    """POST /rag/search; return raw response or an error dict."""
    url = f"{gateway_url.rstrip('/')}/rag/search"
    body = {
        "query": query,
        "project": project,
        "chunk_type": "implementation-spec",
        "knowledge_expansion": False,
    }
    try:
        return _post_json(url, body, timeout)
    except urllib.error.HTTPError as exc:
        return {"status": "error", "error": f"HTTP {exc.code}: {exc.reason}"}
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


def find_implemented_spec(
    gateway_url: str,
    project: str,
    queries: list,
    timeout: int,
) -> "tuple[Optional[dict], list]":
    """
    Try each query in priority order. Return the first chunk whose gateway
    status is 'found' and chunk_type is 'implementation-spec', plus a full
    attempts log for the report.
    """
    attempts = []
    for query in queries:
        resp = _retrieve_one(gateway_url, query, project, timeout)
        gateway_status = resp.get("status", "error")

        chunk = None
        chunk_type = None
        chunk_topic = None
        chunk_id = None

        if gateway_status == "found":
            results = resp.get("results") or (
                [resp["result"]] if resp.get("result") else []
            )
            for r in results:
                if not isinstance(r, dict):
                    continue
                ct = r.get("chunk_type") or r.get("payload", {}).get("chunk_type", "")
                if ct == "implementation-spec":
                    chunk = r
                    chunk_type = ct
                    chunk_topic = r.get("topic") or r.get("payload", {}).get("topic", "")
                    chunk_id = str(r.get("id") or r.get("point_id") or "")
                    break

        attempts.append({
            "query": query,
            "gateway_status": gateway_status,
            "chunk_type": chunk_type,
            "chunk_topic": chunk_topic,
            "chunk_id": chunk_id,
            "found_spec": chunk is not None,
        })

        if chunk is not None:
            return chunk, attempts

    return None, attempts


# ── Chunk content parsing ────────────────────────────────────────────────────

def get_chunk_content(chunk: dict) -> str:
    return (
        chunk.get("content")
        or chunk.get("payload", {}).get("content")
        or ""
    )


def extract_section(content: str, section_name: str) -> list:
    """Return bullet items from a ### section in the chunk markdown content."""
    pattern = rf"###\s+{re.escape(section_name)}\s*\n(.*?)(?=\n###|\Z)"
    m = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
    if not m:
        return []
    items = []
    for line in m.group(1).splitlines():
        line = line.strip()
        if line.startswith(("- ", "* ")):
            items.append(line[2:].strip())
        elif line and not line.startswith("#"):
            items.append(line)
    return [i for i in items if i]


# ── Build ────────────────────────────────────────────────────────────────────

def run_build(solution_path: str, configuration: str, timeout: int) -> dict:
    """Run dotnet build --warnaserror; return exit_code, warnings, error_output."""
    cmd = [
        "dotnet", "build", solution_path,
        "--configuration", configuration,
        "--warnaserror",
        "--nologo",
    ]
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout,
        )
        combined = (result.stdout + "\n" + result.stderr).strip()
        # Parse the MSBuild summary line "N Warning(s)" rather than counting
        # occurrences of the word "warning" (which appears in that summary even
        # when the count is 0, producing a false positive).
        warning_summary = re.search(r"(\d+)\s+Warning\(s\)", combined, re.IGNORECASE)
        if warning_summary:
            warnings = int(warning_summary.group(1))
        else:
            # Fallback: count actual compiler-warning lines (contain ": warning ")
            warnings = len(re.findall(r":\s+warning\s+[A-Z]+\d+", combined))
        return {
            "exit_code": result.returncode,
            "warnings": warnings,
            "error_output": combined if result.returncode != 0 else "",
        }
    except subprocess.TimeoutExpired:
        return {"exit_code": -1, "warnings": 0, "error_output": "dotnet build timed out"}
    except FileNotFoundError:
        return {"exit_code": -1, "warnings": 0, "error_output": "dotnet not found in PATH"}


# ── API smoke ────────────────────────────────────────────────────────────────

def run_api_smoke(
    gateway_url: str, endpoint: str, query: str, project: str, timeout: int
) -> dict:
    url = f"{gateway_url.rstrip('/')}/{endpoint.lstrip('/')}"
    body = {"query": query, "project": project, "knowledge_expansion": False}
    try:
        resp = _post_json(url, body, timeout)
        return {
            "endpoint": endpoint,
            "http_status": 200,
            "response_status": resp.get("status", "unknown"),
        }
    except urllib.error.HTTPError as exc:
        return {"endpoint": endpoint, "http_status": exc.code, "response_status": "error"}
    except Exception as exc:
        return {"endpoint": endpoint, "http_status": -1, "response_status": f"error: {exc}"}


# ── Git helpers ──────────────────────────────────────────────────────────────

def get_changed_files(repo_root: str) -> list:
    """Return files changed vs HEAD (unstaged + staged)."""
    out = set()
    for extra_args in [[], ["--cached"]]:
        try:
            r = subprocess.run(
                ["git", "diff", "--name-only", "HEAD"] + extra_args,
                capture_output=True, text=True, cwd=repo_root, timeout=15,
            )
            out.update(f.strip() for f in r.stdout.splitlines() if f.strip())
        except Exception:
            pass
    return sorted(out)


# ── Conformance ──────────────────────────────────────────────────────────────

def evaluate_conformance(
    target_files: list, changed_files: list, chunk_content: str
) -> dict:
    """
    Evaluate automatable conformance fields. Fields that require human review
    (interface names, invented fields, anti-pattern violations) are set to null.
    """
    if not target_files:
        only_target = None
    elif not changed_files:
        only_target = True
    else:
        def in_targets(f: str) -> bool:
            return any(t in f or f in t for t in target_files)
        only_target = all(in_targets(f) for f in changed_files)

    return {
        "only_target_files_changed": only_target,
        "interface_names_match": None,
        "no_invented_fields": None,
        "no_antipattern_violations": None,
        "_note": (
            "interface/invented/antipattern fields require manual review "
            "and are null when run by the automated harness"
        ),
    }


def determine_outcome(
    build_exit_code: int,
    smoke_http_status: "Optional[int]",
    smoke_response_status: "Optional[str]",
    conformance: dict,
) -> "tuple[str, Optional[str]]":
    build_ok = build_exit_code == 0
    smoke_ok = smoke_http_status is None or (
        smoke_http_status == 200
        and smoke_response_status in ("found", "not_found", None)
    )
    conformance_ok = conformance.get("only_target_files_changed") is not False

    if not build_ok:
        return "fail", f"build exited {build_exit_code}"
    if not smoke_ok:
        return "partial", f"smoke HTTP {smoke_http_status} status={smoke_response_status}"
    if not conformance_ok:
        return "partial", "changed files outside Target Files list"
    return "pass", None


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="P3.2 Implementation-Correctness Smoke Harness v" + VERSION,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--gateway-url", default=GATEWAY_URL,
        help=f"RAG gateway base URL (default: {GATEWAY_URL})",
    )
    parser.add_argument(
        "--project", default=PROJECT,
        help=f"Qdrant project filter (default: {PROJECT})",
    )
    parser.add_argument(
        "--query", default=None,
        help="Override the priority query list with a single query",
    )
    parser.add_argument(
        "--solution", default="rag-gateway-mini.sln",
        help="Path to .sln relative to repo root (default: rag-gateway-mini.sln)",
    )
    parser.add_argument(
        "--configuration", default="Release",
        help="dotnet build configuration (default: Release)",
    )
    parser.add_argument(
        "--smoke-endpoint", default="/rag/search",
        help="API endpoint for the optional smoke (default: /rag/search)",
    )
    parser.add_argument(
        "--smoke-query", default="What port does rag-gateway-mini listen on?",
        help="Query body sent in the smoke POST request",
    )
    parser.add_argument(
        "--no-smoke", action="store_true",
        help="Skip the optional API smoke step",
    )
    parser.add_argument(
        "--build-only", action="store_true",
        help="Skip retrieval; only run build + smoke (useful in CI after an assistant run)",
    )
    parser.add_argument(
        "--session", default="automated harness",
        help="Session description written to the report",
    )
    parser.add_argument(
        "--output", default=None,
        help="Override the default output path (.claude/reports/p32-smoke-<ts>.json)",
    )
    parser.add_argument(
        "--build-timeout", type=int, default=120,
        help="dotnet build timeout in seconds (default: 120)",
    )
    parser.add_argument(
        "--retrieve-timeout", type=int, default=30,
        help="Gateway HTTP retrieval timeout in seconds (default: 30)",
    )
    args = parser.parse_args()

    ts = datetime.now()
    ts_str = ts.strftime("%Y-%m-%dT%H%M%S")
    date_str = ts.strftime("%Y-%m-%d")

    repo_root = str(Path(__file__).parent.parent)

    print(f"\n  P3.2 Implementation-Correctness Smoke Harness v{VERSION}")
    print(f"  {ts.strftime('%Y-%m-%d %H:%M:%S')}  session: {args.session}")
    print()

    # ── Retrieval ────────────────────────────────────────────────────────────

    chunk = None
    attempts: list = []
    chunk_content = ""
    chunk_topic = ""
    chunk_id = ""
    picked_query = ""

    if args.build_only:
        print("  [skip] Retrieval skipped (--build-only)")
        retrieval_report: dict = {
            "query": "skipped",
            "chunk_topic": None,
            "chunk_id": None,
            "gateway_status": "skipped",
            "gateway_url": f"{args.gateway_url.rstrip('/')}/rag/search",
            "queries_tried": [],
        }
    else:
        queries = [args.query] if args.query else PRIORITY_QUERIES
        plural = "y" if len(queries) == 1 else "ies"
        print(f"  [retrieve] Trying {len(queries)} quer{plural} "
              f"via {args.gateway_url}/rag/search ...")

        chunk, attempts = find_implemented_spec(
            args.gateway_url, args.project, queries, args.retrieve_timeout,
        )

        if chunk is not None:
            chunk_content = get_chunk_content(chunk)
            chunk_topic = chunk.get("topic") or chunk.get("payload", {}).get("topic", "")
            chunk_id = str(chunk.get("id") or chunk.get("point_id") or "")
            for a in attempts:
                if a["found_spec"]:
                    picked_query = a["query"]
                    break
            print(f"  [ok] Spec found: {chunk_topic!r}")
        else:
            last_status = attempts[-1]["gateway_status"] if attempts else "unknown"
            print(f"  [warn] No implementation-spec found after {len(attempts)} quer(ies). "
                  f"Last gateway status: {last_status}")
            print("         Capture a spec first or use --query. Proceeding with build.")

        retrieval_report = {
            "query": picked_query or (args.query or PRIORITY_QUERIES[0]),
            "chunk_topic": chunk_topic or None,
            "chunk_id": chunk_id or None,
            "gateway_status": "found" if chunk else "not_found",
            "gateway_url": f"{args.gateway_url.rstrip('/')}/rag/search",
            "queries_tried": attempts,
        }

    # ── Parse Target Files from spec ─────────────────────────────────────────

    target_files: list = []
    if chunk_content:
        target_files = extract_section(chunk_content, "Target Files")
        if target_files:
            preview = ", ".join(target_files[:4]) + ("…" if len(target_files) > 4 else "")
            print(f"  [spec] Target Files: {preview}")

    # ── Detect changed files ──────────────────────────────────────────────────

    changed_files = get_changed_files(repo_root)
    if changed_files:
        preview = ", ".join(changed_files[:5]) + ("…" if len(changed_files) > 5 else "")
        print(f"  [git] Changed files: {preview}")
    else:
        print("  [git] No changed files detected (running on unmodified tree)")

    implementation_report = {
        "assistant": "unknown",
        "routing": "9routers",
        "instruction": (
            "Implement exactly this contract in the specified files. "
            "Do not invent new endpoints, config keys, routes, or DTO fields "
            "outside what the spec lists. "
            "Do not edit any file not named in ### Target Files."
        ),
        "target_files_in_spec": target_files,
        "files_actually_changed": changed_files,
    }

    # ── Build ─────────────────────────────────────────────────────────────────

    solution = os.path.join(repo_root, args.solution)
    print(f"\n  [build] dotnet build {args.solution} "
          f"--configuration {args.configuration} --warnaserror ...")
    build = run_build(solution, args.configuration, args.build_timeout)

    build_symbol = "ok" if build["exit_code"] == 0 else "FAIL"
    print(f"  [{build_symbol}] exit={build['exit_code']}  warnings={build['warnings']}")
    if build["error_output"]:
        first_error = next(
            (line for line in build["error_output"].splitlines()
             if "error" in line.lower()),
            "",
        )
        if first_error:
            print(f"         {first_error[:120]}")

    # ── API smoke ─────────────────────────────────────────────────────────────

    smoke_result: Optional[dict] = None
    if args.no_smoke:
        print("\n  [skip] API smoke skipped (--no-smoke)")
    else:
        print(f"\n  [smoke] POST {args.smoke_endpoint} @ {args.gateway_url} ...")
        smoke_result = run_api_smoke(
            args.gateway_url, args.smoke_endpoint,
            args.smoke_query, args.project, 30,
        )
        smoke_symbol = "ok" if smoke_result["http_status"] == 200 else "FAIL"
        print(f"  [{smoke_symbol}] HTTP {smoke_result['http_status']}  "
              f"status={smoke_result['response_status']}")

    verification_report = {
        "build_exit_code": build["exit_code"],
        "build_warnings": build["warnings"],
        "api_smoke_endpoint": smoke_result["endpoint"] if smoke_result else None,
        "api_smoke_http_status": smoke_result["http_status"] if smoke_result else None,
        "api_smoke_response_status": smoke_result["response_status"] if smoke_result else None,
    }

    # ── Conformance and outcome ───────────────────────────────────────────────

    conformance = evaluate_conformance(target_files, changed_files, chunk_content)

    outcome, failure_reason = determine_outcome(
        build["exit_code"],
        smoke_result["http_status"] if smoke_result else None,
        smoke_result["response_status"] if smoke_result else None,
        conformance,
    )

    outcome_symbol = {"pass": "PASS", "partial": "PARTIAL", "fail": "FAIL"}[outcome]
    print(f"\n  [{outcome_symbol}] Outcome: {outcome}")
    if failure_reason:
        print(f"         Reason: {failure_reason}")

    # ── Write report ──────────────────────────────────────────────────────────

    report = {
        "timestamp": ts.isoformat(),
        "version": VERSION,
        "collection": "knowledge_v2",
        "date": date_str,
        "session": args.session,
        "retrieval": retrieval_report,
        "implementation": implementation_report,
        "verification": verification_report,
        "conformance": conformance,
        "outcome": outcome,
        "failure_reason": failure_reason,
    }

    if args.output:
        output_path = args.output
    else:
        reports_dir = os.path.join(repo_root, ".claude", "reports")
        os.makedirs(reports_dir, exist_ok=True)
        output_path = os.path.join(reports_dir, f"p32-smoke-{ts_str}.json")

    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\n  Report saved: {output_path}")

    sys.exit(0 if outcome == "pass" else 1)


if __name__ == "__main__":
    main()

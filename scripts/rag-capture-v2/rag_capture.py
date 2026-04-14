#!/usr/bin/env python3
"""
RAG Incremental Capture CLI — Global Multi-Project Tool v2
Author: Figur Ulul Azmi

Commands:
  rag add   -p PROJECT -t TYPE --topic "..."   [--content "..."]
  rag pipe  [-p PROJECT -t TYPE --topic "..."]  ← pipe Claude output, auto-detect signal
  rag list
  rag merge [--output filename.md]
  rag clear
  rag status
  rag remind                                    ← print push reminder
  rag config --show
"""

import argparse
import sys
import os
import json
import re
from datetime import datetime
from pathlib import Path

# Force UTF-8 on stdin/stdout/stderr so (a) emoji (✅ 📦 📋 …) do not crash the
# script on Windows consoles that default to cp1252, and (b) piped-in content
# (heredocs, `rag add` body, `rag pipe`) is read as UTF-8 instead of being
# mangled through cp1252 — which turns em dashes into mojibake "â€".
# `errors='replace'` on stdout keeps the script running on the rare terminals
# that still cannot encode a given glyph. stdin uses `errors='strict'` because
# silent replacement on input would hide real encoding problems.
for _stream, _err in ((sys.stdin, "strict"), (sys.stdout, "replace"), (sys.stderr, "replace")):
    try:
        _stream.reconfigure(encoding="utf-8", errors=_err)
    except (AttributeError, ValueError):
        pass

# ─── CONSTANTS ─────────────────────────────────────────────────────────────────

GLOBAL_DRAFTS_DIR   = Path.home() / "scripts" / ".rag_drafts"
GLOBAL_CONFIG_PATH  = Path.home() / ".rag_config.json"

RAG_SIGNAL_START    = "<<<RAG_CHUNK_START>>>"
RAG_SIGNAL_END      = "<<<RAG_CHUNK_END>>>"
# Claude emits: <<<RAG_META:project=petrochina-eproc,type=debug,topic=My Topic,tags=tag1|tag2>>>
RAG_META_PREFIX     = "<<<RAG_META:"

DEFAULT_CONFIG = {
    "qdrant_collection":   "knowledge_v2",
    "qdrant_url":          "http://192.168.18.169:6333",
    "author":              "Figur Ulul Azmi",
    "default_environment": "dev",
    "default_chunk_source":"code",
    "push_script":         "~/scripts/push-to-qdrant.sh",
    "summaries_subdir":    ".claude/summaries",
    "projects": {
        "petrochina-eproc": {
            "default_environment": "dev",
            "default_branch":      "feature/",
            "tags_preset":         ["petrochina", "eproc"]
        },
        "homelab": {
            "default_environment": "homelab",
            "default_branch":      "main",
            "tags_preset":         ["homelab", "vm-b1"]
        },
        "mit-internal": {
            "default_environment": "dev",
            "default_branch":      "main",
            "tags_preset":         ["mit"]
        },
        "homeplate": {
            "default_environment": "dev",
            "default_branch":      "feature/",
            "tags_preset":         ["homeplate", "saas"]
        }
    }
}

VALID_TYPES         = ["debug", "feature", "runbook", "pattern", "decision", "reference"]
VALID_PROJECTS      = ["petrochina-eproc", "homelab", "mit-internal", "homeplate"]
VALID_SESSION_TYPES = ["debug", "feature", "setup", "refactor",
                       "architecture", "research", "ops-documentation", "feature-retrospective"]
VALID_ENVIRONMENTS  = ["dev", "uat", "prod", "homelab"]
VALID_CHUNK_SOURCES = ["code", "design", "ops"]
VALID_STATUSES      = ["implemented", "planned", "deprecated"]

# ─── CONFIG ────────────────────────────────────────────────────────────────────

def load_config() -> dict:
    if GLOBAL_CONFIG_PATH.exists():
        stored = json.loads(GLOBAL_CONFIG_PATH.read_text(encoding="utf-8"))
        merged = DEFAULT_CONFIG.copy()
        merged.update(stored)
        return merged
    save_config(DEFAULT_CONFIG)
    return DEFAULT_CONFIG

def save_config(config: dict):
    GLOBAL_CONFIG_PATH.write_text(json.dumps(config, indent=2), encoding="utf-8")

# ─── HELPERS ───────────────────────────────────────────────────────────────────

def slugify(text: str, max_len: int = 40) -> str:
    text = text.lower()
    text = re.sub(r"[—–]", "-", text)
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"\s+", "-", text.strip())
    text = re.sub(r"-+", "-", text)
    return text[:max_len].rstrip("-")

def detect_project_root() -> Path:
    for parent in [Path.cwd(), *Path.cwd().parents]:
        if (parent / "CLAUDE.md").exists() or (parent / ".claude").exists():
            return parent
    return Path.cwd()

def get_summaries_dir(config: dict) -> Path:
    d = detect_project_root() / config["summaries_subdir"]
    d.mkdir(parents=True, exist_ok=True)
    return d

def count_words(text: str) -> int:
    return len(text.split())

def get_draft_count() -> int:
    if not GLOBAL_DRAFTS_DIR.exists():
        return 0
    return len(list(GLOBAL_DRAFTS_DIR.glob("chunk_*.md")))

def print_push_reminder(config: dict, output_path: Path = None):
    push_script = config.get("push_script", "~/scripts/push-to-qdrant.sh")
    collection  = config.get("qdrant_collection", "knowledge_v2")
    print("\n" + "─" * 62)
    print("📦  PUSH REMINDER — jangan lupa push ke Qdrant!")
    print("─" * 62)
    if output_path:
        print(f"    bash {push_script} {output_path}")
    else:
        summaries_dir = get_summaries_dir(config)
        print(f"    bash {push_script} {summaries_dir}/YYYY-MM-DD-[topic].md")
    print(f"    Collection : {collection}")
    print("─" * 62 + "\n")

# ─── SIGNAL PARSER ─────────────────────────────────────────────────────────────

def parse_rag_meta(text: str) -> dict | None:
    """
    Detect <<<RAG_META:key=value,key=value>>> signal in Claude output.
    Tags use pipe (|) as separator to avoid conflict with comma in meta string.
    Example: <<<RAG_META:project=petrochina-eproc,type=debug,topic=My Fix,tags=sdl|auth|fixed>>>
    """
    match = re.search(r"<<<RAG_META:([^>]+)>>>", text)
    if not match:
        return None
    meta = {}
    for part in match.group(1).split(","):
        if "=" in part:
            k, _, v = part.partition("=")
            meta[k.strip()] = v.strip()
    if "tags" in meta:
        meta["tags"] = meta["tags"].replace("|", ",")
    return meta

def extract_body(text: str) -> str:
    """Extract content between RAG_CHUNK_START / RAG_CHUNK_END, or strip signal lines."""
    if RAG_SIGNAL_START in text and RAG_SIGNAL_END in text:
        start = text.index(RAG_SIGNAL_START) + len(RAG_SIGNAL_START)
        end   = text.index(RAG_SIGNAL_END)
        return text[start:end].strip()
    lines = [l for l in text.splitlines()
             if not any(s in l for s in [RAG_SIGNAL_START, RAG_SIGNAL_END, RAG_META_PREFIX])]
    return "\n".join(lines).strip()

# ─── VALIDATION ────────────────────────────────────────────────────────────────

def validate_content(content: str) -> list:
    warns = []
    w = count_words(content)
    if w < 50:
        warns.append(f"⚠️  Content terlalu pendek ({w} words). Minimum 150 direkomendasikan.")
    if w > 500:
        warns.append(f"⚠️  Content panjang ({w} words). Pertimbangkan split 2 chunks.")
    if "—" in content:
        warns.append("⚠️  Em dash (—) ditemukan. Hapus dari frontmatter jika ada.")
    if re.search(r'\b(ini|yang|dan|atau|dengan|untuk|pada|tidak|bisa|sudah|karena|jika|maka|saya|kamu)\b', content):
        warns.append("⚠️  Kemungkinan ada Bahasa Indonesia. Content harus English only.")
    if "### Key Facts" not in content:
        warns.append("⚠️  Section '### Key Facts' tidak ditemukan. Min 3 Key Facts required.")
    return warns

# ─── FRONTMATTER ───────────────────────────────────────────────────────────────

def build_frontmatter(meta: dict, config: dict, chunk_number: int) -> str:
    date         = datetime.now().strftime("%Y-%m-%d")
    topic        = meta.get("topic", "untitled")
    project      = meta.get("project", "")
    chunk_type   = meta.get("type", "debug")
    tags_raw     = meta.get("tags", "")
    related      = meta.get("related", "")
    branch       = meta.get("branch", "")
    status       = meta.get("status", "implemented")
    environment  = meta.get("environment", "")
    chunk_source = meta.get("chunk_source", "")
    session_type = meta.get("session_type", chunk_type)

    slug         = slugify(topic)
    chunk_id     = f"{date}-{slug}-{chunk_number:03d}"

    proj_cfg     = config.get("projects", {}).get(project, {})
    preset_tags  = proj_cfg.get("tags_preset", [])
    user_tags    = [t.strip() for t in tags_raw.split(",") if t.strip()]
    all_tags     = list(dict.fromkeys(preset_tags + user_tags))[:8]

    environment  = environment or proj_cfg.get("default_environment") or config.get("default_environment", "dev")
    chunk_source = chunk_source or config.get("default_chunk_source", "code")

    fields = [
        ("id",           chunk_id),
        ("date",         date),
        ("source",       "claude-code-cli"),
        ("project",      project),
        ("chunk_type",   chunk_type),
        ("topic",        topic),
        ("tags",         f"[{', '.join(all_tags)}]"),
        ("related",      f"[{related}]" if related else "[]"),
        ("session_type", session_type),
        ("environment",  environment),
        ("git_branch",   branch),
        ("status",       status),
        ("chunk_source", chunk_source),
    ]
    lines = ["---"] + [f"{k}: {v}" for k, v in fields] + ["---"]
    return "\n".join(lines)

# ─── SAVE DRAFT ────────────────────────────────────────────────────────────────

def save_draft(content: str, meta: dict, config: dict) -> tuple[Path, int]:
    GLOBAL_DRAFTS_DIR.mkdir(parents=True, exist_ok=True)
    n             = get_draft_count() + 1
    frontmatter   = build_frontmatter(meta, config, n)
    full_content  = f"{frontmatter}\n\n## CHUNK {n}: {meta.get('topic', '')}\n\n{content}\n"
    path          = GLOBAL_DRAFTS_DIR / f"chunk_{n:03d}.md"
    path.write_text(full_content, encoding="utf-8")
    return path, n

# ─── COMMANDS ──────────────────────────────────────────────────────────────────

def cmd_add(args, config: dict):
    if getattr(args, "content", None):
        content = args.content.strip()
    elif not sys.stdin.isatty():
        content = sys.stdin.read().strip()
    else:
        print("📝 Paste chunk content (Ctrl+D to finish):\n")
        try:
            content = sys.stdin.read().strip()
        except KeyboardInterrupt:
            print("\n❌ Cancelled.")
            sys.exit(1)

    if not content:
        print("❌ No content provided.")
        sys.exit(1)

    meta = {
        "project":      args.project,
        "type":         args.type,
        "topic":        args.topic,
        "tags":         getattr(args, "tags", "") or "",
        "related":      getattr(args, "related", "") or "",
        "branch":       getattr(args, "branch", "") or "",
        "environment":  getattr(args, "environment", "") or "",
        "chunk_source": getattr(args, "chunk_source", "") or "",
        "session_type": getattr(args, "session_type", "") or "",
        "status":       getattr(args, "status", "implemented") or "implemented",
    }

    for w in validate_content(content):
        print(w)

    path, n = save_draft(content, meta, config)
    print(f"\n✅ Draft chunk {n} saved: {path.name}")
    print(f"   Topic   : {meta['topic']}")
    print(f"   Project : {meta['project']} | Type: {meta['type']} | Words: {count_words(content)}")
    print(f"   Total drafts: {n}  →  rag list | rag merge")

def cmd_pipe(args, config: dict):
    """
    Reads Claude's output from stdin.
    If Claude embedded <<<RAG_META:...>>> signal → auto-extract metadata.
    Otherwise → use CLI args (--project, --type, --topic required).
    """
    raw = sys.stdin.read()
    if not raw.strip():
        print("❌ No input piped.")
        sys.exit(1)

    signal_meta = parse_rag_meta(raw)

    if signal_meta:
        meta = signal_meta.copy()
        # CLI args override signal where explicitly provided
        for cli_key, sig_key in [("project","project"),("type","type"),("topic","topic"),
                                  ("tags","tags"),("branch","branch")]:
            val = getattr(args, cli_key, None)
            if val:
                meta[sig_key] = val
        print(f"🔍 RAG signal detected → project={meta.get('project')} type={meta.get('type')}")
    else:
        if not (getattr(args,"project",None) and getattr(args,"type",None) and getattr(args,"topic",None)):
            print("❌ No <<<RAG_META:...>>> signal found. Provide --project, --type, --topic.")
            sys.exit(1)
        meta = {
            "project":      args.project,
            "type":         args.type,
            "topic":        args.topic,
            "tags":         getattr(args, "tags", "") or "",
            "branch":       getattr(args, "branch", "") or "",
            "environment":  getattr(args, "environment", "") or "",
            "chunk_source": getattr(args, "chunk_source", "") or "",
            "session_type": getattr(args, "session_type", "") or "",
            "status":       getattr(args, "status", "implemented") or "implemented",
            "related":      getattr(args, "related", "") or "",
        }

    content = extract_body(raw)
    if not content:
        print("❌ Empty content after extraction.")
        sys.exit(1)

    for w in validate_content(content):
        print(w)

    path, n = save_draft(content, meta, config)
    print(f"\n✅ [PIPE] Draft chunk {n} saved: {path.name}")
    print(f"   Topic   : {meta.get('topic')}")
    print(f"   Project : {meta.get('project')} | Type: {meta.get('type')} | Words: {count_words(content)}")
    print(f"   Total drafts: {n}")

def cmd_list(config: dict):
    drafts = sorted(GLOBAL_DRAFTS_DIR.glob("chunk_*.md")) if GLOBAL_DRAFTS_DIR.exists() else []
    if not drafts:
        print("📭 No drafts. Use: rag add -p PROJECT -t TYPE --topic '...'")
        return

    print(f"\n📋 Draft chunks ({len(drafts)} total):\n")
    total_words = 0
    for d in drafts:
        text  = d.read_text(encoding="utf-8")
        tm    = re.search(r"^## CHUNK \d+: (.+)$", text, re.MULTILINE)
        pm    = re.search(r"^project: (.+)$", text, re.MULTILINE)
        cm    = re.search(r"^chunk_type: (.+)$", text, re.MULTILINE)
        topic = tm.group(1) if tm else d.name
        proj  = pm.group(1).strip() if pm else "?"
        ctype = cm.group(1).strip() if cm else "?"
        body  = text.split("---", 2)[-1] if "---" in text else text
        w     = count_words(body)
        total_words += w
        print(f"  [{d.stem}]  {topic}")
        print(f"             project={proj} | type={ctype} | words={w}\n")

    print(f"  Total: {len(drafts)} chunks, ~{total_words} words")
    print(f"\n  rag merge --output YYYY-MM-DD-[topic].md")

def cmd_merge(args, config: dict):
    drafts = sorted(GLOBAL_DRAFTS_DIR.glob("chunk_*.md")) if GLOBAL_DRAFTS_DIR.exists() else []
    if not drafts:
        print("❌ No draft chunks to merge.")
        return

    date            = datetime.now().strftime("%Y-%m-%d")
    output_filename = (args.output or f"{date}-session-capture.md")
    if not output_filename.endswith(".md"):
        output_filename += ".md"

    summaries_dir = get_summaries_dir(config)
    output_path   = summaries_dir / output_filename

    first_text = drafts[0].read_text(encoding="utf-8")
    fm_parts   = first_text.split("---", 2)
    file_front = f"---{fm_parts[1]}---" if len(fm_parts) >= 3 else ""

    sections = [file_front, ""]
    for draft in drafts:
        text  = draft.read_text(encoding="utf-8")
        parts = text.split("---", 2)
        body  = parts[2].strip() if len(parts) >= 3 else text.strip()
        sections += [body, ""]

    collection = config.get("qdrant_collection", "knowledge_v2")
    sections += [
        "---", "",
        "## SESSION METADATA", "",
        f"- **Total chunks**: {len(drafts)}",
        f"- **Qdrant collection**: {collection}",
        f"- **Generated by**: rag_capture.py v2 — Incremental Capture",
        f"- **Author**: {config.get('author', 'Figur Ulul Azmi')}",
        f"- **Date**: {date}",
        "- **Unresolved items**: (fill manually if needed)",
    ]

    output_path.write_text("\n".join(sections), encoding="utf-8")
    print(f"\n✅ Merged {len(drafts)} chunks → {output_path}")

    # Always remind to push
    print_push_reminder(config, output_path)

    if sys.stdin.isatty():
        confirm = input("🧹 Clear draft folder? [y/N]: ").strip().lower()
        if confirm == "y":
            for d in drafts:
                d.unlink()
            print("   Draft folder cleared.")
    else:
        for d in drafts:
            d.unlink()

def cmd_clear(args, config: dict):
    drafts = list(GLOBAL_DRAFTS_DIR.glob("chunk_*.md")) if GLOBAL_DRAFTS_DIR.exists() else []
    if not drafts:
        print("📭 Nothing to clear.")
        return
    cmd_list(config)
    if sys.stdin.isatty():
        confirm = input("\nConfirm delete all drafts? [y/N]: ").strip().lower()
        if confirm != "y":
            print("Cancelled.")
            return
    for d in drafts:
        d.unlink()
    print(f"🧹 Cleared {len(drafts)} drafts.")

def cmd_status(config: dict):
    drafts        = sorted(GLOBAL_DRAFTS_DIR.glob("chunk_*.md")) if GLOBAL_DRAFTS_DIR.exists() else []
    summaries_dir = get_summaries_dir(config)
    project_root  = detect_project_root()

    print("\n📊 RAG Capture Status")
    print(f"   Project root     : {project_root}")
    print(f"   Summaries dir    : {summaries_dir}")
    print(f"   Global drafts    : {GLOBAL_DRAFTS_DIR}")
    print(f"   Draft chunks     : {len(drafts)}")
    print(f"   Qdrant collection: {config.get('qdrant_collection', 'knowledge_v2')}")
    print(f"   Config           : {GLOBAL_CONFIG_PATH}")
    if drafts:
        print(f"\n   ⚠️  {len(drafts)} unsaved draft(s).")
        print_push_reminder(config)

def cmd_remind(config: dict):
    """Explicit push reminder — Claude calls this at session end."""
    drafts        = list(GLOBAL_DRAFTS_DIR.glob("chunk_*.md")) if GLOBAL_DRAFTS_DIR.exists() else []
    summaries_dir = get_summaries_dir(config)
    push_script   = config.get("push_script", "~/scripts/push-to-qdrant.sh")
    collection    = config.get("qdrant_collection", "knowledge_v2")

    print("\n" + "═" * 62)
    print("🔔  SESSION END REMINDER")
    print("═" * 62)

    if drafts:
        print(f"\n  ⚠️  {len(drafts)} draft chunk(s) belum di-merge!\n")
        print(f"  Step 1 — Merge drafts:")
        print(f"     rag merge --output YYYY-MM-DD-[topic].md\n")
        print(f"  Step 2 — Push merged file:")
        print(f"     bash {push_script} {summaries_dir}/YYYY-MM-DD-[topic].md")
    else:
        recent = sorted(summaries_dir.glob("*.md"), key=lambda f: f.stat().st_mtime, reverse=True)
        if recent:
            latest = recent[0]
            print(f"\n  Latest summary : {latest.name}")
            print(f"\n  Push to Qdrant:")
            print(f"     bash {push_script} {latest}")
        else:
            print("\n  No summaries found. Run 'rag add' to start capturing.")

    print(f"\n  Collection : {collection}")
    print("═" * 62 + "\n")

def cmd_config_show(config: dict):
    print("\n⚙️  Current config (~/.rag_config.json):\n")
    print(json.dumps(config, indent=2))

# ─── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    config = load_config()

    parser = argparse.ArgumentParser(
        prog="rag",
        description="RAG Incremental Capture CLI v2 — Multi-Project",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  rag add -p petrochina-eproc -t debug --topic "SDL middleware fix" --tags "sdl,auth,fixed"
  rag add -p homelab -t feature --topic "Qdrant hybrid migration" -c "Context: ..."
  echo "Claude output with signal" | rag pipe
  rag list
  rag merge --output 2026-04-14-sdl-phase2.md
  rag remind
  rag status
        """
    )
    sub = parser.add_subparsers(dest="command")

    def chunk_args(p, required=False):
        p.add_argument("--project", "-p", required=required, choices=VALID_PROJECTS)
        p.add_argument("--type",    "-t", required=required, choices=VALID_TYPES)
        p.add_argument("--topic",         required=required)
        p.add_argument("--tags")
        p.add_argument("--related")
        p.add_argument("--session-type",  dest="session_type", choices=VALID_SESSION_TYPES)
        p.add_argument("--environment",   "-e", choices=VALID_ENVIRONMENTS)
        p.add_argument("--chunk-source",  dest="chunk_source", choices=VALID_CHUNK_SOURCES)
        p.add_argument("--branch",        "-b")
        p.add_argument("--status",        choices=VALID_STATUSES, default="implemented")

    add_p = sub.add_parser("add",    help="Add one chunk (interactive or --content)")
    chunk_args(add_p, required=True)
    add_p.add_argument("--content", "-c")

    pipe_p = sub.add_parser("pipe",  help="Pipe Claude output (auto-detect <<<RAG_META:...>>> signal)")
    chunk_args(pipe_p, required=False)

    sub.add_parser("list",           help="List all pending draft chunks")

    merge_p = sub.add_parser("merge", help="Merge all drafts into final .md")
    merge_p.add_argument("--output", "-o")

    sub.add_parser("clear",          help="Discard all draft chunks")
    sub.add_parser("status",         help="Show current state and paths")
    sub.add_parser("remind",         help="Print push reminder (used at session end)")

    cfg_p = sub.add_parser("config", help="Manage global config")
    cfg_p.add_argument("--show", action="store_true")

    args = parser.parse_args()

    dispatch = {
        "add":    lambda: cmd_add(args, config),
        "pipe":   lambda: cmd_pipe(args, config),
        "list":   lambda: cmd_list(config),
        "merge":  lambda: cmd_merge(args, config),
        "clear":  lambda: cmd_clear(args, config),
        "status": lambda: cmd_status(config),
        "remind": lambda: cmd_remind(config),
        "config": lambda: cmd_config_show(config),
    }

    fn = dispatch.get(args.command)
    if fn:
        fn()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
RAG Incremental Capture CLI -- Global Multi-Project Tool v2
Author: Figur Ulul Azmi

Commands:
  rag add        -p PROJECT -t TYPE --topic "..."   [--content "..."]
  rag pipe       [-p PROJECT -t TYPE --topic "..."]
  rag checkpoint -p PROJECT --topic "..." --next-step "..."
  rag resume     [-p PROJECT]
  rag promote    --file <checkpoint.md>
  rag list
  rag merge        [--output filename.md]
  rag push-pending
  rag clear
  rag status
  rag remind
  rag config     --show
"""

import argparse
import sys
import os
import json
import re
import subprocess
from datetime import datetime
from pathlib import Path

# Ensure UTF-8 output on Windows (cp1252 cannot encode emoji)
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# --- CONSTANTS ----------------------------------------------------------------

GLOBAL_DRAFTS_DIR   = Path.home() / "scripts" / ".rag_drafts"
GLOBAL_CONFIG_PATH  = Path.home() / ".rag_config.json"
PUSH_QUEUE_PATH     = Path.home() / ".rag_push_queue"

RAG_SIGNAL_START    = "<<<RAG_CHUNK_START>>>"
RAG_SIGNAL_END      = "<<<RAG_CHUNK_END>>>"
RAG_META_PREFIX     = "<<<RAG_META:"

DEFAULT_CONFIG = {
    "qdrant_collection":   "knowledge_v2",
    "qdrant_url":          "http://192.168.18.199:6333",
    "author":              "Figur Ulul Azmi",
    "default_environment": "dev",
    "default_chunk_source":"code",
    "push_script":         "~/scripts/push-to-qdrant.sh",
    "summaries_subdir":    ".claude/summaries",
    "checkpoints_subdir":  ".claude/checkpoints",
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

VALID_TYPES         = ["debug", "feature", "runbook", "pattern", "decision", "reference", "checkpoint"]
VALID_PROJECTS      = ["petrochina-eproc", "homelab", "mit-internal", "homeplate"]
VALID_SESSION_TYPES = ["debug", "feature", "setup", "refactor",
                       "architecture", "research", "ops-documentation", "feature-retrospective"]
VALID_ENVIRONMENTS  = ["dev", "uat", "prod", "homelab"]
VALID_CHUNK_SOURCES = ["code", "design", "ops"]
VALID_STATUSES      = ["implemented", "planned", "deprecated", "in_progress", "solved", "abandoned"]
VALID_COLLECTIONS   = ["knowledge_v2", "checkpoints", "architecture"]

# --- CONFIG -------------------------------------------------------------------

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

# --- HELPERS ------------------------------------------------------------------

def slugify(text: str, max_len: int = 40) -> str:
    text = text.lower()
    text = re.sub(r"[\u2014\u2013]", "-", text)
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

def get_checkpoints_dir(config: dict) -> Path:
    d = detect_project_root() / config.get("checkpoints_subdir", ".claude/checkpoints")
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
    print("\n" + "\u2500" * 62)
    print("\U0001f4e6  PUSH REMINDER -- jangan lupa push ke Qdrant!")
    print("\u2500" * 62)
    if output_path:
        print(f"    bash {push_script} {output_path}")
    else:
        summaries_dir = get_summaries_dir(config)
        print(f"    bash {push_script} {summaries_dir}/YYYY-MM-DD-[topic].md")
    print(f"    Collection : {collection}")
    print("\u2500" * 62 + "\n")

def auto_detect_files_modified() -> str:
    """Auto-populate files_modified via rtk git diff. Zero exploration tokens."""
    try:
        result = subprocess.run(
            ["rtk", "git", "diff", "--name-only", "HEAD"],
            capture_output=True, text=True, timeout=5
        )
        files = [f.strip() for f in result.stdout.splitlines()
                 if f.strip() and not f.startswith("#")]
        return f"[{', '.join(files)}]" if files else "[]"
    except Exception:
        return "[]"

def auto_detect_decisions(n: int = 5) -> str:
    """Auto-seed decisions_made via rtk git log. Zero exploration tokens."""
    try:
        result = subprocess.run(
            ["rtk", "git", "log", "--oneline", f"-{n}"],
            capture_output=True, text=True, timeout=5
        )
        commits = [ln.strip() for ln in result.stdout.splitlines()
                   if ln.strip() and not ln.startswith("#")]
        return f"[{'; '.join(commits)}]" if commits else "[]"
    except Exception:
        return "[]"

# --- SIGNAL PARSER ------------------------------------------------------------

def parse_rag_meta(text: str) -> dict | None:
    """
    Detect <<<RAG_META:key=value,key=value>>> signal in Claude output.
    Tags use pipe (|) as separator to avoid conflict with comma in meta string.
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

# --- VALIDATION ---------------------------------------------------------------

CHUNK_ID_RE = re.compile(r"^\d{4}-\d{2}-\d{2}-.+-\d{3}$")

def validate_supersedes(value: str) -> list:
    """Validate that a supersedes/superseded_by value matches chunk ID format."""
    if not value:
        return []
    if not CHUNK_ID_RE.match(value):
        return [f"supersedes '{value}' does not match chunk ID format YYYY-MM-DD-<slug>-NNN"]
    return []


def validate_content(content: str) -> list:
    warns = []
    w = count_words(content)
    if w < 50:
        warns.append(f"\u26a0\ufe0f  Content terlalu pendek ({w} words). Minimum 150 direkomendasikan.")
    if w > 500:
        warns.append(f"\u26a0\ufe0f  Content panjang ({w} words). Pertimbangkan split 2 chunks.")
    if "\u2014" in content:
        warns.append("\u26a0\ufe0f  Em dash (\u2014) ditemukan. Hapus dari frontmatter jika ada.")
    if re.search(r'\b(ini|yang|dan|atau|dengan|untuk|pada|tidak|bisa|sudah|karena|jika|maka|saya|kamu)\b', content):
        warns.append("\u26a0\ufe0f  Kemungkinan ada Bahasa Indonesia. Content harus English only.")
    if "### Key Facts" not in content:
        warns.append("\u26a0\ufe0f  Section '### Key Facts' tidak ditemukan. Min 3 Key Facts required.")
    return warns

def validate_checkpoint_content(content: str) -> list:
    warns = []
    w = count_words(content)
    if w < 30:
        warns.append(f"\u26a0\ufe0f  Checkpoint body short ({w} words). Add Problem/Progress/Key Facts.")
    for section in ["### Problem", "### Key Facts"]:
        if section not in content:
            warns.append(f"\u26a0\ufe0f  '{section}' missing from checkpoint body.")
    if "\u2014" in content:
        warns.append("\u26a0\ufe0f  Em dash found in body.")
    return warns

# --- FRONTMATTER --------------------------------------------------------------

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
    collection   = meta.get("collection", config.get("qdrant_collection", "knowledge_v2"))

    slug         = slugify(topic)
    chunk_id     = f"{date}-{slug}-{chunk_number:03d}"

    proj_cfg     = config.get("projects", {}).get(project, {})
    preset_tags  = proj_cfg.get("tags_preset", [])
    user_tags    = [t.strip() for t in tags_raw.split(",") if t.strip()]
    all_tags     = list(dict.fromkeys(preset_tags + user_tags))[:8]

    environment  = environment or proj_cfg.get("default_environment") or config.get("default_environment", "dev")
    chunk_source = chunk_source or config.get("default_chunk_source", "code")

    supersedes    = meta.get("supersedes", "")
    superseded_by = meta.get("superseded_by", "")

    fields = [
        ("id",            chunk_id),
        ("date",          date),
        ("source",        "claude-code-cli"),
        ("collection",    collection),
        ("project",       project),
        ("chunk_type",    chunk_type),
        ("topic",         topic),
        ("tags",          f"[{', '.join(all_tags)}]"),
        ("related",       f"[{related}]" if related else "[]"),
        ("session_type",  session_type),
        ("environment",   environment),
        ("git_branch",    branch),
        ("status",        status),
        ("chunk_source",  chunk_source),
        ("supersedes",    supersedes),
        ("superseded_by", superseded_by),
    ]

    # Checkpoint-specific momentum fields
    if chunk_type == "checkpoint":
        fields += [
            ("hypothesis",        meta.get("hypothesis", "")),
            ("next_step",         meta.get("next_step", "")),
            ("blocking_question", meta.get("blocking_question", "")),
            ("token_trigger",     meta.get("token_trigger", "manual")),
            ("session_number",    meta.get("session_number", "1")),
            ("files_modified",    meta.get("files_modified", "[]")),
            ("decisions_made",    meta.get("decisions_made", "[]")),
            ("parent_id",         meta.get("parent_id", "")),
        ]

    lines = ["---"] + [f"{k}: {v}" for k, v in fields] + ["---"]
    return "\n".join(lines)

# --- SAVE DRAFT ---------------------------------------------------------------

def save_draft(content: str, meta: dict, config: dict) -> tuple[Path, int]:
    GLOBAL_DRAFTS_DIR.mkdir(parents=True, exist_ok=True)
    n             = get_draft_count() + 1
    frontmatter   = build_frontmatter(meta, config, n)
    full_content  = f"{frontmatter}\n\n## CHUNK {n}: {meta.get('topic', '')}\n\n{content}\n"
    path          = GLOBAL_DRAFTS_DIR / f"chunk_{n:03d}.md"
    path.write_text(full_content, encoding="utf-8")
    return path, n

def save_checkpoint(content: str, meta: dict, config: dict) -> Path:
    """Save directly to .claude/checkpoints/ -- no draft/merge cycle needed."""
    checkpoints_dir = get_checkpoints_dir(config)
    slug  = slugify(meta.get("topic", "checkpoint"))
    date  = datetime.now().strftime("%Y-%m-%d")

    existing = list(checkpoints_dir.glob(f"{date}-{slug}*.md"))
    n = len(existing) + 1

    meta.setdefault("collection", "checkpoints")
    meta.setdefault("type",       "checkpoint")
    meta.setdefault("status",     "in_progress")

    frontmatter  = build_frontmatter(meta, config, n)
    full_content = f"{frontmatter}\n\n## CHECKPOINT: {meta.get('topic', '')}\n\n{content}\n"
    path         = checkpoints_dir / f"{date}-{slug}-{n:03d}.md"
    path.write_text(full_content, encoding="utf-8")
    return path

# --- COMMANDS -----------------------------------------------------------------

def cmd_add(args, config: dict):
    if getattr(args, "content", None):
        content = args.content.strip()
    elif not sys.stdin.isatty():
        content = sys.stdin.read().strip()
    else:
        print("\U0001f4dd Paste chunk content (Ctrl+D to finish):\n")
        try:
            content = sys.stdin.read().strip()
        except KeyboardInterrupt:
            print("\n\u274c Cancelled.")
            sys.exit(1)

    if not content:
        print("\u274c No content provided.")
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
        "supersedes":   getattr(args, "supersedes", "") or "",
        "superseded_by": getattr(args, "superseded_by", "") or "",
    }

    for w in validate_content(content):
        print(w)
    for w in validate_supersedes(meta.get("supersedes", "")):
        print(w)

    path, n = save_draft(content, meta, config)
    print(f"\n\u2705 Draft chunk {n} saved: {path.name}")
    print(f"   Topic   : {meta['topic']}")
    print(f"   Project : {meta['project']} | Type: {meta['type']} | Words: {count_words(content)}")
    print(f"   Total drafts: {n}  ->  rag list | rag merge")

def cmd_checkpoint(args, config: dict):
    """
    Capture in-progress session state. Token budget: ~1100-1500 tokens total.
    Rule: ZERO file reads. All content from active conversation context only.
    Auto-populate files_modified + decisions_made via 2 RTK git calls (~150 tokens).
    """
    if getattr(args, "quick", False):
        ns  = args.next_step
        hyp = getattr(args, "hypothesis", "") or "not set"
        content = (
            "### Problem\n(Quick checkpoint - see frontmatter fields)\n\n"
            "### Key Facts\n"
            f"- Next step: {ns}\n"
            f"- Hypothesis: {hyp}\n"
            "- Quick capture due to token constraint\n"
        )
        print("\u26a1 Quick mode: minimal body (~300 tokens).")
    elif not sys.stdin.isatty():
        content = sys.stdin.read().strip()
    else:
        print("\U0001f4cd Paste checkpoint body (Ctrl+D to finish):\n")
        try:
            content = sys.stdin.read().strip()
        except KeyboardInterrupt:
            print("\n\u274c Cancelled.")
            sys.exit(1)

    if not content:
        print("\u274c No content provided.")
        sys.exit(1)

    # Auto-populate from git -- only 2 Bash calls, ~150 tokens total
    files_modified = auto_detect_files_modified()
    decisions_made = auto_detect_decisions(5)

    meta = {
        "project":           args.project,
        "type":              "checkpoint",
        "topic":             args.topic,
        "tags":              getattr(args, "tags", "") or "",
        "status":            "in_progress",
        "collection":        "checkpoints",
        "hypothesis":        getattr(args, "hypothesis", "") or "",
        "next_step":         args.next_step,
        "blocking_question": getattr(args, "blocking", "") or "",
        "token_trigger":     getattr(args, "trigger", "manual") or "manual",
        "session_number":    str(getattr(args, "session_number", "1") or "1"),
        "files_modified":    files_modified,
        "decisions_made":    decisions_made,
        "parent_id":         "",
    }

    for w in validate_checkpoint_content(content):
        print(w)

    path = save_checkpoint(content, meta, config)
    push_script = config.get("push_script", "~/scripts/push-to-qdrant.sh")

    print(f"\n\U0001f4cd Checkpoint saved: {path.name}")
    print(f"   Topic     : {meta['topic']}")
    print(f"   Next step : {meta['next_step']}")
    print(f"   Files     : {files_modified}")
    print(f"   Trigger   : {meta['token_trigger']}")
    print(f"\n   Push now  : bash {push_script} {path}")
    print("   Resume    : rag resume\n")

def cmd_resume(args, config: dict):
    """
    Print open checkpoints in compact RTK-style format.
    Session Start Protocol: run FIRST every new session.
    FOUND -> load fields, skip codebase exploration, execute next_step directly.
    """
    checkpoints_dir = detect_project_root() / config.get("checkpoints_subdir", ".claude/checkpoints")

    if not checkpoints_dir.exists():
        print("\n\u2705 No checkpoints directory. Fresh session.\n")
        return

    files = sorted(checkpoints_dir.glob("*.md"), key=lambda f: f.stat().st_mtime, reverse=True)
    open_checkpoints = []

    for f in files:
        text     = f.read_text(encoding="utf-8")
        status_m = re.search(r"^status:\s*(.+)$", text, re.MULTILINE)
        if not (status_m and status_m.group(1).strip() == "in_progress"):
            continue
        proj_m = re.search(r"^project:\s*(.+)$", text, re.MULTILINE)
        if getattr(args, "project", None) and proj_m and proj_m.group(1).strip() != args.project:
            continue
        open_checkpoints.append((f, text))

    if not open_checkpoints:
        print("\n\u2705 No open checkpoints. Fresh session.\n")
        return

    print(f"\n{'=' * 62}")
    print(f"   \U0001f4cd OPEN CHECKPOINTS ({len(open_checkpoints)}) -- load before file exploration")
    print(f"{'=' * 62}")

    for f, text in open_checkpoints:
        def field(key):
            m = re.search(rf"^{key}:\s*(.+)$", text, re.MULTILINE)
            return m.group(1).strip() if m else "-"

        topic      = field("topic")
        hypothesis = field("hypothesis")
        next_step  = field("next_step")
        files_raw  = field("files_modified")
        blocking   = field("blocking_question")
        trigger    = field("token_trigger")
        session_n  = field("session_number")

        # RTK precision read hints -- core token-saving mechanism on resume
        files_list = [x.strip().strip("\"'[] ") for x in files_raw.split(",")
                      if x.strip().strip("\"'[] ") and x.strip() != "[]"]
        rtk_reads  = " && ".join(
            [f"rtk read {fp.split(':')[0]}" for fp in files_list if fp]
        ) or "-"

        print(f"\n  File       : {f.name}")
        print(f"  Topic      : {topic}")
        print(f"  Session    : #{session_n} | Trigger: {trigger}")
        print(f"  Hypothesis : {hypothesis}")
        print(f"  Next step  : {next_step}")
        print(f"  Files      : {files_raw}")
        print(f"  Blocking   : {blocking}")
        print(f"  RTK reads  : {rtk_reads}")
        print(f"  Promote    : rag promote --file .claude/checkpoints/{f.name}")

    print(f"\n{'=' * 62}\n")

def cmd_promote(args, config: dict):
    """Promote a solved checkpoint to knowledge_v2. Keeps original as audit trail."""
    filepath = Path(args.file)
    if not filepath.exists():
        filepath = detect_project_root() / args.file
    if not filepath.exists():
        print(f"\u274c Checkpoint file not found: {args.file}")
        sys.exit(1)

    text = filepath.read_text(encoding="utf-8")

    orig_id_m = re.search(r"^id:\s*(.+)$", text, re.MULTILINE)
    orig_id   = orig_id_m.group(1).strip() if orig_id_m else filepath.stem
    topic_m   = re.search(r"^topic:\s*(.+)$", text, re.MULTILINE)
    topic     = topic_m.group(1).strip() if topic_m else "promoted"

    date   = datetime.now().strftime("%Y-%m-%d")
    slug   = slugify(topic)
    new_id = f"{date}-{slug}-promoted"

    promoted = re.sub(r"^id:\s*.+$",          f"id: {new_id}",           text,     flags=re.MULTILINE)
    promoted = re.sub(r"^status:\s*.+$",       "status: solved",           promoted, flags=re.MULTILINE)
    promoted = re.sub(r"^collection:\s*.+$",   "collection: knowledge_v2", promoted, flags=re.MULTILINE)
    promoted = re.sub(r"^parent_id:\s*.*$",    f"parent_id: {orig_id}",    promoted, flags=re.MULTILINE)

    summaries_dir = get_summaries_dir(config)
    output_name   = getattr(args, "output", None) or f"{date}-{slug}-promoted.md"
    if not output_name.endswith(".md"):
        output_name += ".md"
    output_path = summaries_dir / output_name
    output_path.write_text(promoted, encoding="utf-8")

    # Mark original checkpoint as solved (audit trail)
    updated_orig = re.sub(r"^status:\s*.+$",    "status: solved",       text,         flags=re.MULTILINE)
    updated_orig = re.sub(r"^parent_id:\s*.*$", f"parent_id: {new_id}", updated_orig, flags=re.MULTILINE)
    filepath.write_text(updated_orig, encoding="utf-8")

    print(f"\n\u2705 Promoted: {filepath.name} -> {output_path}")
    print(f"   Original checkpoint: status updated to solved")
    reminder_cfg = {**config, "qdrant_collection": "knowledge_v2"}
    print_push_reminder(reminder_cfg, output_path)

def cmd_pipe(args, config: dict):
    raw = sys.stdin.read()
    if not raw.strip():
        print("\u274c No input piped.")
        sys.exit(1)

    signal_meta = parse_rag_meta(raw)

    if signal_meta:
        meta = signal_meta.copy()
        for cli_key, sig_key in [("project","project"),("type","type"),("topic","topic"),
                                  ("tags","tags"),("branch","branch")]:
            val = getattr(args, cli_key, None)
            if val:
                meta[sig_key] = val
        print(f"\U0001f50d RAG signal detected -> project={meta.get('project')} type={meta.get('type')}")
    else:
        if not (getattr(args,"project",None) and getattr(args,"type",None) and getattr(args,"topic",None)):
            print("\u274c No <<<RAG_META:...>>> signal found. Provide --project, --type, --topic.")
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
        print("\u274c Empty content after extraction.")
        sys.exit(1)

    for w in validate_content(content):
        print(w)

    path, n = save_draft(content, meta, config)
    print(f"\n\u2705 [PIPE] Draft chunk {n} saved: {path.name}")
    print(f"   Topic   : {meta.get('topic')}")
    print(f"   Project : {meta.get('project')} | Type: {meta.get('type')} | Words: {count_words(content)}")
    print(f"   Total drafts: {n}")

def cmd_list(config: dict):
    drafts = sorted(GLOBAL_DRAFTS_DIR.glob("chunk_*.md")) if GLOBAL_DRAFTS_DIR.exists() else []
    if not drafts:
        print("\U0001f4ed No drafts. Use: rag add -p PROJECT -t TYPE --topic '...'")
        return

    print(f"\n\U0001f4cb Draft chunks ({len(drafts)} total):\n")
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

def auto_push(output_path: Path, config: dict) -> bool:
    """Attempt push-to-qdrant.sh immediately after merge. Queue on failure."""
    push_script = os.path.expanduser(config.get("push_script", "~/scripts/push-to-qdrant.sh"))
    try:
        result = subprocess.run(
            ["bash", push_script, str(output_path)],
            timeout=180,
        )
        if result.returncode == 0:
            print(f"  \u2705 Auto-pushed to Qdrant: {output_path.name}")
            return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    # Network unreachable or script error — queue for later
    with open(PUSH_QUEUE_PATH, "a", encoding="utf-8") as f:
        f.write(str(output_path) + "\n")
    print(f"  \u26a0\ufe0f  Network unreachable — queued: {output_path}")
    print(f"       Run 'rag push-pending' when network returns.")
    return False


def cmd_push_pending(config: dict):
    """Drain ~/.rag_push_queue with exponential backoff (2s, 4s, 8s per file)."""
    import time
    if not PUSH_QUEUE_PATH.exists():
        print("\u2705 Push queue is empty.")
        return

    entries = [l.strip() for l in PUSH_QUEUE_PATH.read_text(encoding="utf-8").splitlines() if l.strip()]
    if not entries:
        print("\u2705 Push queue is empty.")
        PUSH_QUEUE_PATH.unlink(missing_ok=True)
        return

    print(f"\n\U0001f4e4 Push queue: {len(entries)} file(s) pending\n")
    push_script = os.path.expanduser(config.get("push_script", "~/scripts/push-to-qdrant.sh"))
    still_pending = []

    for entry in entries:
        path = Path(entry)
        if not path.exists():
            print(f"  \u26a0\ufe0f  Skipping (not found): {entry}")
            continue

        success = False
        for attempt, delay in enumerate([0, 2, 4, 8], start=1):
            if delay:
                print(f"    Retry {attempt}/3 in {delay}s...")
                time.sleep(delay)
            try:
                result = subprocess.run(["bash", push_script, str(path)], timeout=180)
                if result.returncode == 0:
                    print(f"  \u2705 Pushed: {path.name}")
                    success = True
                    break
            except (FileNotFoundError, subprocess.TimeoutExpired):
                break

        if not success:
            print(f"  \u274c Failed (all retries): {entry}")
            still_pending.append(entry)

    if still_pending:
        PUSH_QUEUE_PATH.write_text("\n".join(still_pending) + "\n", encoding="utf-8")
        print(f"\n  {len(still_pending)} file(s) remain in queue. Re-run when network returns.")
    else:
        PUSH_QUEUE_PATH.unlink(missing_ok=True)
        print("\n\u2705 Queue cleared.")


def cmd_merge(args, config: dict):
    drafts = sorted(GLOBAL_DRAFTS_DIR.glob("chunk_*.md")) if GLOBAL_DRAFTS_DIR.exists() else []
    if not drafts:
        print("\u274c No draft chunks to merge.")
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
        f"- **Generated by**: rag_capture.py v2 -- Incremental Capture",
        f"- **Author**: {config.get('author', 'Figur Ulul Azmi')}",
        f"- **Date**: {date}",
        "- **Unresolved items**: (fill manually if needed)",
    ]

    output_path.write_text("\n".join(sections), encoding="utf-8")
    print(f"\n\u2705 Merged {len(drafts)} chunks -> {output_path}")
    auto_push(output_path, config)

    if sys.stdin.isatty():
        confirm = input("\U0001f9f9 Clear draft folder? [y/N]: ").strip().lower()
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
        print("\U0001f4ed Nothing to clear.")
        return
    cmd_list(config)
    if sys.stdin.isatty():
        confirm = input("\nConfirm delete all drafts? [y/N]: ").strip().lower()
        if confirm != "y":
            print("Cancelled.")
            return
    for d in drafts:
        d.unlink()
    print(f"\U0001f9f9 Cleared {len(drafts)} drafts.")

def cmd_status(config: dict):
    drafts          = sorted(GLOBAL_DRAFTS_DIR.glob("chunk_*.md")) if GLOBAL_DRAFTS_DIR.exists() else []
    summaries_dir   = get_summaries_dir(config)
    checkpoints_dir = detect_project_root() / config.get("checkpoints_subdir", ".claude/checkpoints")
    open_chk        = [
        f for f in checkpoints_dir.glob("*.md")
        if re.search(r"^status:\s*in_progress", f.read_text(encoding="utf-8"), re.MULTILINE)
    ] if checkpoints_dir.exists() else []
    project_root    = detect_project_root()

    print("\n\U0001f4ca RAG Capture Status")
    print(f"   Project root     : {project_root}")
    print(f"   Summaries dir    : {summaries_dir}")
    print(f"   Checkpoints dir  : {checkpoints_dir}")
    print(f"   Global drafts    : {GLOBAL_DRAFTS_DIR}")
    print(f"   Draft chunks     : {len(drafts)}")
    print(f"   Open checkpoints : {len(open_chk)}")
    print(f"   Qdrant collection: {config.get('qdrant_collection', 'knowledge_v2')}")
    print(f"   Config           : {GLOBAL_CONFIG_PATH}")
    if drafts:
        print(f"\n   \u26a0\ufe0f  {len(drafts)} unsaved draft(s).")
        print_push_reminder(config)
    if open_chk:
        print(f"\n   \U0001f4cd {len(open_chk)} open checkpoint(s). Run: rag resume")

def cmd_remind(config: dict):
    """Explicit push reminder -- Claude calls this at session end."""
    drafts        = list(GLOBAL_DRAFTS_DIR.glob("chunk_*.md")) if GLOBAL_DRAFTS_DIR.exists() else []
    summaries_dir = get_summaries_dir(config)
    push_script   = config.get("push_script", "~/scripts/push-to-qdrant.sh")
    collection    = config.get("qdrant_collection", "knowledge_v2")

    print("\n" + "=" * 62)
    print("\U0001f514  SESSION END REMINDER")
    print("=" * 62)

    if drafts:
        print(f"\n  \u26a0\ufe0f  {len(drafts)} draft chunk(s) belum di-merge!\n")
        print(f"  Step 1 -- Merge drafts:")
        print(f"     rag merge --output YYYY-MM-DD-[topic].md\n")
        print(f"  Step 2 -- Push merged file:")
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
    print("=" * 62 + "\n")

def cmd_config_show(config: dict):
    print("\n\u2699\ufe0f  Current config (~/.rag_config.json):\n")
    print(json.dumps(config, indent=2))

# --- MAIN ---------------------------------------------------------------------

def main():
    config = load_config()

    parser = argparse.ArgumentParser(
        prog="rag",
        description="RAG Incremental Capture CLI v2 -- Multi-Project",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  rag add -p petrochina-eproc -t debug --topic "SDL middleware fix" --tags "sdl,auth,fixed"
  rag checkpoint -p homelab --topic "Qdrant hybrid migration" --next-step "run: rtk dotnet test src/" --trigger "85%"
  rag checkpoint -p homelab --topic "Mid-session complex feature" --next-step "fix RagController.cs:89" --quick
  rag resume
  rag resume -p homelab
  rag promote --file .claude/checkpoints/2026-04-18-qdrant-hybrid-migration-001.md
  rag list
  rag merge --output 2026-04-18-session.md
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
        p.add_argument("--supersedes",    default="",
                       help="Chunk ID this replaces — old chunk will be deprecated on push (format: YYYY-MM-DD-<slug>-NNN)")
        p.add_argument("--superseded-by", dest="superseded_by", default="",
                       help="Chunk ID that replaces this one (back-link)")

    add_p = sub.add_parser("add", help="Add one chunk (interactive or --content)")
    chunk_args(add_p, required=True)
    add_p.add_argument("--content", "-c")

    pipe_p = sub.add_parser("pipe", help="Pipe Claude output (auto-detect <<<RAG_META:...>>> signal)")
    chunk_args(pipe_p, required=False)

    chk_p = sub.add_parser("checkpoint", help="Capture in-progress session state (rich snapshot)")
    chk_p.add_argument("--project",        "-p",  required=True, choices=VALID_PROJECTS)
    chk_p.add_argument("--topic",                 required=True)
    chk_p.add_argument("--next-step",      dest="next_step", required=True,
                        help="Exact first action for next session (file:line if possible)")
    chk_p.add_argument("--hypothesis",            default="",
                        help="Current working theory about the problem")
    chk_p.add_argument("--blocking",              default="",
                        help="Unanswered question blocking progress")
    chk_p.add_argument("--trigger",               default="manual",
                        choices=["85%", "75%", "manual", "session_end"],
                        help="What triggered this checkpoint")
    chk_p.add_argument("--session-number", dest="session_number", default="1")
    chk_p.add_argument("--tags",                  default="")
    chk_p.add_argument("--quick",                 action="store_true",
                        help="Emergency minimal capture -- skips body, ~300 tokens total")

    resume_p = sub.add_parser("resume", help="Show open checkpoints (run at start of every new session)")
    resume_p.add_argument("--project", "-p", choices=VALID_PROJECTS)

    promote_p = sub.add_parser("promote", help="Promote solved checkpoint to knowledge_v2")
    promote_p.add_argument("--file",   "-f", required=True, help="Path to checkpoint .md file")
    promote_p.add_argument("--output", "-o", help="Output filename in .claude/summaries/ (optional)")

    sub.add_parser("list",  help="List all pending draft chunks")

    merge_p = sub.add_parser("merge", help="Merge all drafts into final .md")
    merge_p.add_argument("--output", "-o")

    sub.add_parser("clear",        help="Discard all draft chunks")
    sub.add_parser("status",       help="Show current state and paths")
    sub.add_parser("remind",       help="Print push reminder (used at session end)")
    sub.add_parser("push-pending", help="Drain ~/.rag_push_queue with exponential backoff (2s/4s/8s)")

    cfg_p = sub.add_parser("config", help="Manage global config")
    cfg_p.add_argument("--show", action="store_true")

    args = parser.parse_args()

    dispatch = {
        "add":        lambda: cmd_add(args, config),
        "pipe":       lambda: cmd_pipe(args, config),
        "checkpoint": lambda: cmd_checkpoint(args, config),
        "resume":     lambda: cmd_resume(args, config),
        "promote":    lambda: cmd_promote(args, config),
        "list":       lambda: cmd_list(config),
        "merge":      lambda: cmd_merge(args, config),
        "clear":      lambda: cmd_clear(args, config),
        "status":     lambda: cmd_status(config),
        "remind":       lambda: cmd_remind(config),
        "push-pending": lambda: cmd_push_pending(config),
        "config":       lambda: cmd_config_show(config),
    }

    fn = dispatch.get(args.command)
    if fn:
        fn()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()

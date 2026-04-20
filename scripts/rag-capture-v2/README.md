# RAG Capture V2

> Incremental knowledge capture system for Claude CLI sessions.  
> Upgrade dari batch-capture (V1) ke incremental + Python-powered pipeline.

---

## Daftar Isi

- [Latar Belakang](#latar-belakang)
- [Perbandingan V1 vs V2](#perbandingan-v1-vs-v2)
- [Arsitektur V2](#arsitektur-v2)
- [Komponen](#komponen)
- [Instalasi](#instalasi)
- [Penggunaan](#penggunaan)
- [Referensi Command](#referensi-command)
- [Test](#test)
- [Kompatibilitas](#kompatibilitas)
- [Changelog](#changelog)

---

## Latar Belakang

RAG Capture adalah sistem untuk menyimpan pengetahuan teknis dari sesi kerja Claude CLI ke Qdrant vector database (`knowledge_v2`). Setiap problem yang diselesaikan di-capture sebagai **chunk** terstruktur, di-embed oleh Ollama (`nomic-embed-text`), dan disimpan sebagai hybrid vector (dense + sparse BM25) untuk retrieval yang akurat.

### Kenapa diupgrade ke V2?

V1 (batch-capture) menghabiskan **22% token** per sesi hanya untuk format dokumen RAG karena Claude membaca SKILL.md panjang lalu generate semua chunks sekaligus di akhir sesi.

V2 memisahkan tanggung jawab: **Claude hanya generate teks content**, semua file I/O dikerjakan Python.

---

## Perbandingan V1 vs V2

### Arsitektur

| Aspek                | V1 (Batch Capture)                          | V2 (Incremental Capture)                        |
| -------------------- | ------------------------------------------- | ----------------------------------------------- |
| **Trigger**          | Manual di akhir sesi                        | Otomatis setiap problem selesai                 |
| **Token cost**       | ~22% per sesi                               | ~3–5% per sesi                                  |
| **SKILL.md read**    | Setiap sesi (11% token)                     | Tidak diperlukan                                |
| **Chunk generation** | Claude generate semua sekaligus (11% token) | Claude generate raw text saja (~1–2% per chunk) |
| **File I/O**         | Claude yang tulis file                      | Python yang handle sepenuhnya                   |
| **Frontmatter**      | Claude yang generate (rawan inkonsistensi)  | Python auto-generate (konsisten, validated)     |
| **Splitting**        | Manual, sering terlupa                      | Per-problem, triggered otomatis                 |

### Flow Perbandingan

**V1 — Batch (akhir sesi):**

```
Sesi selesai → Claude baca SKILL.md → Claude generate semua chunks
             → Claude tulis file → user push manual
```

**V2 — Incremental (per problem):**

```
Problem selesai → Claude emit signal → rag add/pipe
               → Python: frontmatter + save draft
               → Akhir sesi: rag merge → push
```

### Token Cost Breakdown

| Step            | V1             | V2             |
| --------------- | -------------- | -------------- |
| Read SKILL.md   | 11%            | 0%             |
| Generate chunks | 11%            | 1–2% per chunk |
| File I/O        | Claude (token) | Python (0%)    |
| Frontmatter     | Claude (token) | Python (0%)    |
| **Total**       | **~22%**       | **~3–5%**      |

### Kualitas Output

| Aspek                   | V1                                  | V2                             |
| ----------------------- | ----------------------------------- | ------------------------------ |
| Frontmatter consistency | Bergantung Claude (bisa lupa rules) | Python-enforced (selalu valid) |
| Em dash detection       | Tidak ada validasi                  | Auto-detected + warning        |
| English-only check      | Tidak ada                           | Auto-detected + warning        |
| Word count check        | Tidak ada                           | Auto-detected (150–400 words)  |
| Key Facts check         | Tidak ada                           | Auto-detected (min 3)          |
| Chunk splitting         | Tergantung Claude                   | Satu problem = satu `rag add`  |

---

## Arsitektur V2

```
┌─────────────────────────────────────────────────────┐
│                 DEV MACHINE / LOCAL PC               │
│                                                     │
│  Claude CLI                                         │
│    │                                                │
│    │ 1. Solve problem                               │
│    │ 2. Auto-emit <<<RAG_META:...>>> signal         │
│    │ 3. Output structured chunk content             │
│    ▼                                                │
│  rag_capture.py (global CLI: rag)                   │
│    │                                                │
│    ├── rag add / rag pipe ──► ~/scripts/.rag_drafts/│
│    │                          chunk_001.md          │
│    │                          chunk_002.md          │
│    │                                                │
│    ├── rag merge ──────────► .claude/summaries/     │
│    │                         YYYY-MM-DD-topic.md    │
│    │                                                │
│    └── rag remind ─────────► push reminder          │
│                                                     │
└──────────────────┬──────────────────────────────────┘
                   │ bash push-to-qdrant.sh
                   │ HTTP POST per chunk
                   ▼
┌──────────────────────────────┐
│   VM B1 (192.168.18.199)    │
│                              │
│   n8n webhook (5678)         │
│     │                        │
│     ▼                        │
│   Ollama (11434)             │
│   nomic-embed-text           │
│     │                        │
│     ▼                        │
│   Qdrant (6333)              │
│   collection: knowledge_v2   │
│   dense (768) + sparse BM25  │
└──────────────────────────────┘
```

---

## Komponen

```
scripts/rag-capture-v2/
├── rag_capture.py      ← Main CLI tool (install sebagai global command 'rag')
├── rag-setup.sh        ← Install script (jalankan sekali)
├── CLAUDE_snippet.md   ← Block yang di-paste ke CLAUDE.md project
├── test-rag-v2.sh      ← End-to-end test script (cross-platform)
└── README.md           ← Dokumentasi ini
```

### `rag_capture.py`

Python CLI tool yang dipasang sebagai command global `rag`. Bertanggung jawab untuk:

- Parse `<<<RAG_META:...>>>` signal dari output Claude
- Generate frontmatter YAML secara otomatis
- Validate content (em dash, bahasa Indonesia, word count, Key Facts)
- Menyimpan draft ke `~/scripts/.rag_drafts/`
- Merge semua draft menjadi satu file `.md` final
- Auto-detect project root via `CLAUDE.md` atau `.claude/` folder
- Print push reminder setelah setiap operasi penting

### `CLAUDE_snippet.md`

Instruksi yang ditambahkan ke `CLAUDE.md` project. Mengajarkan Claude CLI untuk:

- Emit `<<<RAG_META:...>>>` signal otomatis setiap problem selesai
- Generate chunk content dalam format terstruktur (Context/Problem/Solution/Key Facts)
- Print checklist sebelum `/clear`

### `test-rag-v2.sh`

End-to-end test script dengan flag `--dry-run`. Menguji seluruh pipeline dari signal detection hingga push ke Qdrant, termasuk retrieval quality check.

---

## Instalasi

### Prerequisites

- Python 3.8+
- Akses ke VM B1 via LAN atau Tailscale
- `push-to-qdrant.sh` sudah ada di `~/scripts/`
- Qdrant collection `knowledge_v2` sudah ada (jalankan `migrate-to-hybrid.py` jika belum)

### Install

```bash
# Clone atau pull repo
cd /path/to/rag-gateway-mini

# Jalankan setup (sekali saja per mesin)
bash scripts/rag-capture-v2/rag-setup.sh

# Reload PATH
source ~/.bashrc

# Verifikasi
rag --help
rag status
```

### Setup API Key

```bash
mkdir -p ~/.config
cat > ~/.config/qdrant-knowledge.env << 'EOF'
QDRANT_API_KEY=your-api-key-here
QDRANT_URL=http://192.168.18.199:6333
QDRANT_COLLECTION=knowledge_v2
EOF
```

### Setup CLAUDE.md

Paste isi `CLAUDE_snippet.md` ke bagian bawah `CLAUDE.md` di root setiap project:

```bash
cat scripts/rag-capture-v2/CLAUDE_snippet.md >> CLAUDE.md
```

---

## Penggunaan

### Workflow Harian

**1. Saat problem selesai** — Claude otomatis emit signal, lalu jalankan:

```bash
rag add \
  --project petrochina-eproc \
  --type debug \
  --topic "SDL Middleware Token Validation Fix" \
  --tags "sdl,auth,middleware,fixed" \
  --branch "feature/sdl-phase1"
# Paste content dari Claude → Ctrl+D
```

**2. Akhir sesi** — merge dan push:

```bash
rag list                                              # review drafts
rag merge --output 2026-04-14-sdl-phase1.md          # merge
bash ~/scripts/push-to-qdrant.sh \
  .claude/summaries/2026-04-14-sdl-phase1.md         # push
```

**3. Sebelum `/clear`** — Claude print checklist otomatis, atau jalankan:

```bash
rag remind
```

### RAG Signal Format

Claude CLI akan auto-append blok ini setelah setiap problem selesai:

```
<<<RAG_META:project=PROJECT,type=TYPE,topic=TOPIC,tags=tag1|tag2|tag3>>>
<<<RAG_CHUNK_START>>>
### Context
...
### Problem
...
### Solution
...
### Key Facts
- Fact 1
- Fact 2
- Fact 3
<<<RAG_CHUNK_END>>>
```

---

## Referensi Command

| Command                                    | Deskripsi                                    |
| ------------------------------------------ | -------------------------------------------- |
| `rag add -p PROJECT -t TYPE --topic "..."` | Tambah satu chunk secara manual              |
| `rag pipe`                                 | Pipe output Claude dengan auto-detect signal |
| `rag list`                                 | Lihat semua draft pending                    |
| `rag merge --output filename.md`           | Merge semua draft jadi file final            |
| `rag clear`                                | Buang semua draft tanpa merge                |
| `rag status`                               | Cek state dan semua paths                    |
| `rag remind`                               | Tampilkan push reminder                      |
| `rag config --show`                        | Tampilkan konfigurasi global                 |

### Chunk Types

| Type        | Gunakan untuk                    |
| ----------- | -------------------------------- |
| `debug`     | Bug/error → fix confirmed        |
| `feature`   | Implementasi fitur baru          |
| `runbook`   | Prosedur step-by-step            |
| `pattern`   | Pola reusable lintas project     |
| `decision`  | Keputusan arsitektur + reasoning |
| `reference` | Config, port, env vars, topology |

### Projects

| Project            | Environment default | Tag preset        |
| ------------------ | ------------------- | ----------------- |
| `petrochina-eproc` | dev                 | petrochina, eproc |
| `homelab`          | homelab             | homelab, vm-b1    |
| `mit-internal`     | dev                 | mit               |
| `homeplate`        | dev                 | homeplate, saas   |

---

## Test

### Dry-run (aman, collection tidak disentuh)

```bash
export QDRANT_API_KEY="your-api-key"
bash scripts/rag-capture-v2/test-rag-v2.sh --dry-run
```

### Live test (push ke Qdrant)

```bash
bash scripts/rag-capture-v2/test-rag-v2.sh
```

### Yang diuji

| Test             | Deskripsi                                                              |
| ---------------- | ---------------------------------------------------------------------- |
| Pre-flight       | rag command, Python, Qdrant, Ollama, collection                        |
| Signal detection | Auto-parse `<<<RAG_META>>>` dari pipe                                  |
| Manual add       | `rag add` dengan content inline                                        |
| Frontmatter      | id, project, chunk_type, topic, tags, status, no em dash, English only |
| Merge            | Output file, chunk count, SESSION METADATA                             |
| Push             | HTTP 200 dari webhook + scroll verify di Qdrant                        |
| Retrieval        | Exact keyword (BM25), semantic (dense), technical term                 |
| Reminder         | `rag remind` output                                                    |

### Kompatibilitas test

Script `test-rag-v2.sh` sudah diverifikasi di:

| Environment                    | Status        |
| ------------------------------ | ------------- |
| Ubuntu 24.04 (VM B1)           | ✅ 26/26 PASS |
| Windows Git Bash (Python 3.13) | ✅ 26/26 PASS |

---

## Kompatibilitas

| Komponen               | Versi minimum                    |
| ---------------------- | -------------------------------- |
| Python                 | 3.8+                             |
| Qdrant server          | 1.15.2+ (untuk server-side BM25) |
| qdrant-client (Python) | 1.13.0+                          |
| Ollama                 | Any (nomic-embed-text model)     |
| n8n                    | 2.15.0+                          |
| Bash                   | 4.0+ (Git Bash on Windows OK)    |

---

## Changelog

### V2.0.0 — 2026-04-14

**Breaking changes:**

- Qdrant collection target berubah dari `knowledge` ke `knowledge_v2`
- Collection `knowledge_v2` menggunakan hybrid vectors (dense + sparse BM25) — tidak backward compatible dengan `knowledge` (dense only)

**New features:**

- `rag_capture.py` — global Python CLI dengan commands: `add`, `pipe`, `list`, `merge`, `clear`, `status`, `remind`, `config`
- Auto-detect `<<<RAG_META:...>>>` signal dari output Claude via `rag pipe`
- Frontmatter auto-generation dengan validasi: no em dash, English-only check, word count, Key Facts check
- Project preset tags: auto-merge tags dari config per project
- Cross-platform path detection via `rag status` — support Windows Git Bash dan Linux
- `test-rag-v2.sh` — end-to-end test script dengan `--dry-run` flag dan API key support
- Push verification via HTTP 200 + Qdrant scroll (bukan hanya points count delta)

**Improvements:**

- Token cost turun dari ~22% → ~3–5% per sesi
- Frontmatter konsistensi meningkat (Python-enforced vs Claude-generated)
- Push reminder built-in di setiap command penting
- Draft tersimpan global di `~/scripts/.rag_drafts/` — tidak hilang jika session crash

**Infrastructure:**

- Qdrant `knowledge_v2`: dense (768-dim Cosine) + sparse (IDF BM25)
- Payload indexes: project, chunk_type, tags, status, environment, session_type
- Migration script: `scripts/migrate-to-hybrid.py`

### V1.0.0 — 2026-03-xx

Initial release. Batch capture via SKILL.md + Claude CLI. Single dense vector collection `knowledge`.

---

## Author

**Figur Ulul Azmi** — MIT Dev Team  
Qdrant: `knowledge_v2` @ VM B1 (`192.168.18.199:6333`)  
Stack: .NET 9 · Blazor · Qdrant · n8n · Ollama · Claude CLI

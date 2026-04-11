# RAG Knowledge Pipeline — Setup & Usage Guide

Scripts untuk push sesi Claude Code ke Qdrant (External Brain) dan test retrieval accuracy.

---

## Prerequisites

Pastikan semua tools ini tersedia di terminal (Git Bash / Linux):

```bash
curl --version   # network detection
jq --version     # JSON builder
ssh -V           # koneksi ke VM B1
```

Jika `jq` belum ada di Windows Git Bash:
```bash
# Download jq untuk Windows dari: https://jqlang.github.io/jq/download/
# Letakkan jq.exe di folder yang ada di PATH (misal: C:\Program Files\Git\usr\bin\)
```

---

## One-Time Setup (wajib sebelum pertama kali pakai)

### Step 1 — Buat env file (simpan API key, tidak di-commit)

```bash
mkdir -p ~/.config
cp scripts/qdrant-knowledge.env.example ~/.config/qdrant-knowledge.env
```

Edit file tersebut dan isi dengan nilai asli:
```bash
# Buka dengan text editor, ganti "your-api-key-here"
notepad ~/.config/qdrant-knowledge.env      # Windows
nano ~/.config/qdrant-knowledge.env         # Linux / Git Bash
```

Dapatkan nilai `QDRANT_API_KEY` dari:
- Tanya Azmi, ATAU
- SSH ke VM B1 → `cat /opt/homelab/ai-stack/.env | grep QDRANT_API_KEY`

### Step 2 — Setup SSH passwordless ke VM B1

Agar script bisa SSH ke B1 tanpa password prompt setiap kali:

```powershell
# Jalankan di PowerShell Windows (bukan Git Bash)

# Generate SSH key (skip jika sudah ada)
ssh-keygen -t ed25519 -C "claude-code-rag"

# Copy public key ke B1 via LAN
type $env:USERPROFILE\.ssh\id_ed25519.pub | ssh figulazmi@192.168.18.169 "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"

# Copy public key ke B1 via Tailscale (untuk akses dari luar kantor)
type $env:USERPROFILE\.ssh\id_ed25519.pub | ssh figulazmi@100.120.249.99 "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"
```

Test koneksi:
```bash
ssh figulazmi@192.168.18.169 "echo OK"   # harusnya print: OK
```

---

## Script 1: push-to-qdrant.sh

Push sesi Claude Code (file .md) ke Qdrant collection `knowledge`.

### Usage

```bash
# Selalu jalankan dari Git Bash terminal di VS Code (bukan PowerShell)
bash scripts/push-to-qdrant.sh .claude/summaries/YYYY-MM-DD-topic.md
```

### Contoh

```bash
bash scripts/push-to-qdrant.sh .claude/summaries/2026-04-08-single-device-login.md
```

### Output yang diharapkan

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📦 Push to Qdrant — RAG Knowledge Capture
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  File     : 2026-04-08-single-device-login.md
  ID       : 2026-04-08-single-device-login
  Project  : petrochina-eproc
  Topic    : Single Device Login Implementation
  Chunks   : 3
  Network  : LAN Kantor Bandung (192.168.18.169)
  Webhook  : http://192.168.18.169:5678/webhook/knowledge-ingest
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  [1/3] Sending: CHUNK 1 — Session Handling Design ... ✅ OK (200)
  [2/3] Sending: CHUNK 2 — JWT Token Invalidation ... ✅ OK (200)
  [3/3] Sending: CHUNK 3 — Blazor UI Feedback ... ✅ OK (200)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Done — 3/3 chunks pushed to Qdrant
   Collection : knowledge
   Doc ID     : 2026-04-08-single-device-login
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Troubleshooting

| Error | Penyebab | Solusi |
|-------|----------|--------|
| `QDRANT_API_KEY not set` | Env file belum dibuat | Ikuti Step 1 setup di atas |
| `Cannot reach VM B1` | Tidak terhubung LAN / Tailscale | Connect ke WiFi kantor atau `tailscale up` |
| `No ## CHUNK blocks found` | File .md tidak mengikuti format RAG | Pastikan file punya header `## CHUNK N:` |
| `HTTP 401` | API key salah | Cek nilai di `~/.config/qdrant-knowledge.env` |
| `HTTP 500` / timeout | Ollama atau n8n lambat/down | Tunggu beberapa menit, coba lagi |

---

## Script 2: test-qdrant-retrieval.sh

Test apakah data yang sudah di-push bisa di-retrieve dengan akurat. Berguna untuk validasi setelah push.

### Usage

```bash
bash scripts/test-qdrant-retrieval.sh "query string" [limit]
```

- `query string` — kalimat dalam Bahasa Inggris yang ingin dicari (bukan keyword, tapi kalimat)
- `limit` — jumlah hasil yang dikembalikan (default: 5, lihat tabel di bawah untuk panduan pilih nilai)

### Contoh Query

```bash
# Cari chunk tentang session handling
bash scripts/test-qdrant-retrieval.sh "single device login session handling" 5

# Cari chunk tentang bug Hangfire
bash scripts/test-qdrant-retrieval.sh "Hangfire job succeeds but database not updated" 3

# Cari chunk tentang SSH setup
bash scripts/test-qdrant-retrieval.sh "SSH passwordless setup Windows to VM" 3
```

### Output yang diharapkan

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔍 Qdrant Retrieval Test
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Query   : single device login session handling
  Limit   : 5
  Network : LAN (192.168.18.169)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{
  "jsonrpc": "2.0",
  "id": 2,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "Result 1 [score: 0.92] — topic: Single Device Login...\n..."
      }
    ]
  }
}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Log saved: .claude/retrieval-tests/2026-04-08-143022-retrieval.log
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Default limit — dari mana angka 5?

Default limit ditentukan di dua tempat dalam MCP server (`/opt/mcp-servers/qdrant-knowledge/qdrant-mcp-server.js` di VM B1):

```javascript
// 1. Schema hint (ditampilkan ke Claude sebagai info saja, tidak enforce)
"limit": { type: "number", description: "Max results (default 5)", default: 5 }

// 2. Destructuring — ini yang ACTUAL enforce saat Claude tidak specify limit
const { query, limit = 5, project = null } = request.params.arguments;
//                     ^^^
//                     ubah angka ini di VM B1 untuk ganti default global
```

Panduan pilih limit berdasarkan use case:

| Use case | Limit ideal |
|----------|-------------|
| Query spesifik (satu bug / satu fitur) | 3 |
| Query umum (arsitektur, flow) | 5 (default) |
| Research lintas sesi / banyak konteks | 8–10 |

Untuk ubah default global, SSH ke B1 dan edit file MCP server:
```bash
ssh figulazmi@192.168.18.169
nano /opt/mcp-servers/qdrant-knowledge/qdrant-mcp-server.js
# Ganti: const { query, limit = 5 ... } → const { query, limit = 8 ... }
```

### Cara baca hasil (score interpretation)

| Score | Artinya |
|-------|---------|
| 0.90 – 1.00 | Sangat relevan — hasil bagus |
| 0.75 – 0.89 | Cukup relevan |
| 0.60 – 0.74 | Kurang relevan — chunk mungkin perlu ditulis ulang lebih spesifik |
| < 0.60 | Tidak relevan — query terlalu ambigu atau chunk belum ada |

### Tips query yang baik

```bash
# ✅ Bagus — kalimat deskriptif dalam Bahasa Inggris
bash scripts/test-qdrant-retrieval.sh "how to configure JWT token invalidation on logout"

# ❌ Kurang bagus — terlalu pendek / keyword saja
bash scripts/test-qdrant-retrieval.sh "JWT"

# ❌ Kurang bagus — Bahasa Indonesia (embedding tidak optimal)
bash scripts/test-qdrant-retrieval.sh "cara setup login satu perangkat"
```

### Log files

Setiap test otomatis disimpan ke `.claude/retrieval-tests/` dengan format:
```
.claude/retrieval-tests/
  2026-04-08-143022-retrieval.log
  2026-04-08-150510-retrieval.log
  ...
```

Folder ini di-gitignore — tidak akan ter-commit ke repo.

---

## Network Detection Logic

Kedua script otomatis mendeteksi jaringan dengan prioritas:

1. **VM B1 langsung** — jika script dijalankan dari dalam VM B1 itu sendiri
2. **LAN Kantor Bandung** — jika bisa reach `192.168.18.169` (WiFi/kabel kantor)
3. **Tailscale VPN** — jika bisa reach `100.120.249.99` (dari luar kantor)

Jika ketiga gagal → script berhenti dengan pesan error dan saran perbaikan.

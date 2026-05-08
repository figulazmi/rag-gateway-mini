# 🤖 AI Workflow

Panduan ini menjelaskan cara kerja tim dalam menggunakan AI (Claude + GitHub Copilot)
secara efisien, hemat token, dan minim hallucination.

Dibuat untuk semua developer, termasuk yang baru mengenal AI coding assistant.

---

## 🧠 Konsep Dasar: Kenapa Perlu Workflow Khusus?

Tanpa sistem ini, AI bekerja seperti ini:

```
Kamu tanya → AI nebak → Hasil bisa salah → Kamu koreksi → Buang waktu & token
```

Dengan sistem ini:

```
Qdrant (knowledge base) → RAG Gateway → rag CLI → Claude / Copilot → Hasil akurat
```

**Intinya:** AI tidak lagi mengandalkan ingatan sendiri. Semua jawaban didasarkan
pada knowledge base proyek yang sudah kita isi sendiri — zero hallucination.

---

## 🏗️ Arsitektur Sistem

```
          ┌──────────────────────────┐
          │   Qdrant (Knowledge Base)│  ← tempat menyimpan semua knowledge proyek
          └────────────┬─────────────┘
                       │
          ┌────────────▼─────────────┐
          │   RAG Gateway Mini API   │  ← jembatan ke Qdrant (local or VM B1:5200)
          └────────────┬─────────────┘
                       │
          ┌────────────▼─────────────┐
          │       rag CLI Tool       │  ← tool utama yang kamu pakai sehari-hari
          └──────────┬───────────────┘
                     │
           ┌─────────┴──────────┐
           │                    │
  ┌────────▼────────┐  ┌────────▼────────┐
  │  GitHub Copilot  │  │     Claude      │
  │  (task ringan)   │  │  (task besar)   │
  └──────────────────┘  └─────────────────┘
```

| Komponen           | Peran                                                            |
| ------------------ | ---------------------------------------------------------------- |
| **Qdrant**         | Memory / ground truth — semua knowledge proyek tersimpan di sini |
| **RAG Gateway**    | API layer — diakses oleh `rag` CLI                               |
| **rag CLI**        | Tool yang kamu pakai di terminal                                 |
| **rag-tools**      | Repo tooling terpisah — rag CLI, push script, MCP server, n8n workflow |
| **GitHub Copilot** | Generator kode cepat untuk task ringan                           |
| **Claude**         | Reasoning engine untuk task besar & kompleks                     |

---

## ⚙️ Setup Pertama Kali

### 1. Pastikan RAG Gateway sedang berjalan

```bash
# Di terminal project root
rtk dotnet run --project src
```

Gateway berjalan di `http://localhost:5200` untuk local dev, `http://192.168.18.199:5200` di VM B1 LAN, atau `http://100.120.249.99:5200` lewat Tailscale. Cek dengan `/scalar/` atau `/openapi/v1.json`. Tidak ada endpoint `/health` di repo ini.

Production VM B1 path:
- Repo: `/opt/homelab/ai-stack/rag-gateway-mini`
- Secrets: `/opt/homelab/ai-stack/rag-gateway-mini/appsettings.Production.json`

### 2. Pastikan `jq` sudah terinstall

```bash
rtk jq --version
```

Kalau belum ada:

```powershell
rtk winget install jqlang.jq
```

### 3. Clone rag-tools dan jalankan setup otomatis

```bash
rtk git clone https://github.com/figulazmi/rag-tools.git ~/rag-tools
rtk bash ~/rag-tools/rag-capture-v2/rag-setup.sh
```

Script akan otomatis:
- Install `rag` CLI
- Buat `~/.rag_config.json` (Qdrant URL, API key, author)
- Buat `~/.claude/claude-mcp-connect.ps1` (Windows) atau `.sh` (Mac/Linux)
- Patch `~/.claude/settings.json` dengan MCP server config

### 4. Append RAG-first protocol ke Claude Code

```bash
rtk bash -lc 'cat ~/rag-tools/rag-capture-v2/CLAUDE_snippet.md >> ~/.claude/CLAUDE.md'
# Restart Claude Code untuk aktifkan MCP server
```

Verifikasi:

```bash
rtk rag --help
rtk rag status
```

---

## 🎯 Kapan Pakai Copilot vs Claude?

Ini panduan paling penting. Salah pilih = boros token + hasil kurang optimal.

### ⚡ Gunakan Copilot — task ringan & eksekusi

Cocok untuk:

- Buat method CRUD biasa
- Refactor ringan (rename, extract method)
- Generate boilerplate (DTO, mapper, constructor)
- Lanjutkan kode yang sudah jelas arahnya
- Fix bug sederhana

**Flow:**

```
rag "query" → copy // RAG_CONTEXT: → paste ke .cs → Copilot generate
```

---

### 🧠 Gunakan Claude — task besar & reasoning

Cocok untuk:

- Desain fitur baru (auth, notification, sync system)
- Keputusan arsitektur (Clean Architecture, CQRS, dll)
- Debug kompleks yang butuh analisis mendalam
- Menulis plan implementasi sebelum coding
- Review code yang menyangkut banyak layer

**Flow:**

```
rag "query" --claude "task kamu" → copy → paste ke Claude → reasoning → implement
```

---

## 🛠️ Cara Pakai `rag` CLI

### Sintaks dasar

```bash
rag "query kamu di sini"
rag "query" -p petrochina-eproc
rag "query" --claude "task yang mau dikerjakan"
```

### Semua opsi

| Flag              | Kegunaan                                                                  |
| ----------------- | ------------------------------------------------------------------------- |
| `-p`, `--project` | Filter knowledge per proyek (`petrochina-eproc` atau `homelab`)           |
| `--claude [task]` | Output sebagai prompt Claude (mode reasoning)                             |
| `--strict`        | Tambah enforcement ketat: Claude WAJIB cite sumber, tidak boleh mengarang |
| `--show-scores`   | Tampilkan skor relevansi tiap hasil (berguna untuk evaluasi)              |
| `--raw`           | Output teks biasa tanpa formatting (untuk diolah sendiri)                 |
| `--debug`         | Tampilkan detail teknis RAG: threshold, jumlah hasil, dll                 |
| `--copy`          | Langsung copy ke clipboard — tinggal Ctrl+V                               |

---

## 📋 Workflow Berdasarkan Ukuran Task

### 🔹 Task Kecil — langsung Copilot

**Contoh:** Tambah method `GetByVendorId` di repository.

```bash
# Step 1: ambil context dari knowledge base
rag "vendor repository pattern EF Core" -p petrochina-eproc --copy

# Step 2: buka file yang mau diedit di VS Code
# Step 3: paste // RAG_CONTEXT: di atas method yang mau dibuat
# Step 4: mulai ketik signature method → Copilot generate otomatis
```

---

### 🔹 Task Medium — plan dulu di Claude, implement pakai Copilot

**Contoh:** Tambah fitur notifikasi email saat PO disetujui.

```bash
# Step 1: cari context
rag "email notification purchase order approval" -p petrochina-eproc \
  --claude "design the notification flow and list the files that need to be changed" \
  --copy

# Step 2: paste ke Claude → Claude akan buat plan + list file yang perlu diubah
# Step 3: untuk setiap file, pakai Copilot mode:
rag "email notification handler MediatR" -p petrochina-eproc --copy
# paste ke file .cs → Copilot generate implementasi
```

---

### 🔹 Task Besar — full Claude mode dengan strict

**Contoh:** Desain sistem Single Device Login.

```bash
# Step 1: cari semua context yang relevan
rag "single device login session management refresh token" -p petrochina-eproc \
  --claude "design the full Single Device Login system: handler, DTOs, middleware, and database changes" \
  --strict \
  --copy

# Step 2: paste ke Claude
# Claude akan:
# - reasoning berdasarkan knowledge base
# - buat arsitektur
# - list semua perubahan yang dibutuhkan
# - cite sumber (SOURCE N) untuk setiap keputusan
# - output NOT FOUND IN RAG kalau ada yang tidak ada di knowledge base

# Step 3: review hasil Claude → breakdown jadi sub-task kecil
# Step 4: setiap sub-task → Copilot mode
```

---

## 🧩 Intent Detection (Otomatis)

Script `rag` **otomatis** mendeteksi intent kamu dari query.

Kalau query mengandung kata-kata ini:

```
design, architecture, implement, system, flow, strategy, explain,
how does, why does, compare, decide, evaluate, plan, structure
```

Maka otomatis masuk **Claude mode** — tidak perlu tambah flag `--claude`.

**Contoh:**

```bash
# Ini otomatis Claude mode (ada kata "design")
rag "design single device login" -p petrochina-eproc

# Ini Copilot mode (tidak ada trigger word)
rag "SDL session kicked detection" -p petrochina-eproc
```

Output terminal akan tampilkan:

```
[rag] Intent detected: routing to Claude mode
```

---

## 📌 Project Filter — Wajib Diisi

Selalu gunakan `-p` untuk filter knowledge sesuai proyek.

| Project            | Gunakan untuk                                               |
| ------------------ | ----------------------------------------------------------- |
| `petrochina-eproc` | .NET code, Blazor, EF Core, API, Hangfire, MediatR, dll — tag pertama: `dotnet` |
| `homelab`          | VM B1, Proxmox, Docker, n8n, Qdrant, Ollama, infra — tag pertama: `homelab`     |
| (Python scripts)   | rag_capture, eval, automation tools — tag pertama: `python`                     |

```bash
# ✅ Benar
rag "how does SDL work" -p petrochina-eproc

# ✅ Benar
rag "how to setup qdrant on VM B1" -p homelab

# ❌ Hindari — hasil bisa campur dari semua proyek
rag "how does SDL work"
```

---

## 💡 Best Practices

### ✅ DO — Lakukan ini

**1. Query minimal 8 kata**

```bash
# ✅ Bagus — cukup deskriptif
rag "how SDL session kicked detection works in Blazor SignalR" -p petrochina-eproc

# ❌ Buruk — terlalu pendek, hasil tidak akurat
rag "SDL" -p petrochina-eproc
```

**2. Selalu gunakan `--copy` saat mau paste ke editor/Claude**

```bash
rag "vendor registration flow" -p petrochina-eproc --copy
# Langsung siap di-paste — tidak perlu select + copy manual
```

**3. Gunakan `--strict` untuk keputusan kritis**

```bash
# Untuk auth, financial logic, atau perubahan besar — selalu strict
rag "implement payment approval handler" -p petrochina-eproc \
  --claude "write the MediatR handler" --strict
```

**4. Gunakan `--debug` kalau hasil tidak relevan**

```bash
rag "query kamu" -p petrochina-eproc --debug
# Lihat score threshold, jumlah hasil raw, dll
# Kalau score rendah semua → knowledge base perlu diisi dulu
```

---

### ❌ DON'T — Hindari ini

**1. Jangan langsung tanya Claude tanpa context RAG terlebih dahulu**

```
❌ Claude: "Buat sistem single device login untuk project kita"
✅ rag "single device login" --claude "buat systemnya" → paste ke Claude
```

**2. Jangan gunakan Claude untuk task yang bisa dikerjakan Copilot**

```
❌ Claude: "Tambahkan property Email ke VendorDto"
✅ rag "VendorDto structure" --copy → paste ke file → Copilot generate
```

**3. Jangan skip project filter**

```
❌ rag "how SDL works"
✅ rag "how SDL works" -p petrochina-eproc
```

**4. Jangan langsung implement tanpa cek knowledge base dulu**

```
❌ Langsung coding fitur baru berdasarkan asumsi
✅ rag "fitur terkait" -p petrochina-eproc → cek apakah sudah ada pattern yang harus diikuti
```

---

## 🔄 Siklus Kerja Lengkap (Full Loop)

```
1. Ada task baru
       ↓
2. rag "keyword task" -p petrochina-eproc
       ↓
3. Hasil found?
   ├── YA → lanjut ke step 4
   └── TIDAK → kerjakan berdasarkan konvensi proyek,
               dokumentasikan hasil di akhir sesi
       ↓
4. Task besar/kompleks?
   ├── YA → rag "..." --claude "task" --strict --copy → paste ke Claude
   └── TIDAK → rag "..." --copy → paste ke .cs → Copilot generate
       ↓
5. Review hasil
       ↓
6. Di akhir sesi → jalankan Session End Protocol
   (simpan knowledge baru ke Qdrant agar bisa dipakai team berikutnya)
```

---

## 📚 Session End Protocol (WAJIB sebelum /clear)

Setiap kali selesai sesi coding dengan Claude, simpan knowledge ke Qdrant
agar developer lain bisa manfaatkan hasil kerja kamu.

```bash
# Step 1: Capture knowledge dengan rag add (Claude jalankan otomatis)
# rag adalah wrapper untuk rag_capture.py; kalau wrapper tidak tersedia, gunakan:
# rtk python "C:/Users/Clandesitine/scripts/rag-capture-v2/rag_capture.py" add ...
cat <<'RAGBODY_EOF' | rtk rag add -p PROJECT -t TYPE --topic "..." --tags "tag1,tag2"
### Context
...
### Solution
...
### Key Facts
- fact 1
- fact 2
RAGBODY_EOF

# Step 2: Merge semua drafts ke .claude/summaries dan ikuti push reminder dari CLI
rtk rag merge --output YYYY-MM-DD-[topic].md

# Step 3: Jika ada file yang masuk pending push queue
rtk rag push-pending
# ↑ drains ~/.rag_push_queue dengan exponential backoff (2s/4s/8s per file)

# Step 4: Untuk token >= 85% — simpan checkpoint dulu sebelum /clear
cat <<'RAGCHK' | rtk rag checkpoint -p PROJECT --topic "..." \
  --next-step "file.cs:line — action" --trigger "85%"
### Problem
...
### Progress
...
### Key Facts
- fact 1
RAGCHK
rtk bash ~/rag-tools/push-to-qdrant.sh .claude/checkpoints/YYYY-MM-DD-*.md
```

> **Kenapa ini penting?**
> Knowledge yang tidak disimpan = hilang setelah sesi selesai.
> Ikuti output `rag merge` sebagai sumber kebenaran untuk langkah push berikutnya.

---

## 🚨 Troubleshooting

### ❌ `Error: could not connect to RAG Gateway`

RAG Gateway belum jalan. Jalankan:

```bash
rtk dotnet run --project src
```

---

### ❌ `Error: jq is not installed`

```powershell
rtk winget install jqlang.jq
```

Lalu buka terminal baru (restart Git Bash).

---

### ❌ `rag: command not found`

Script belum ada di PATH. Cek:

```bash
rtk bash -lc 'echo $PATH | tr '"'"':'"'"' '\''\n'\'' | grep scripts'
```

Kalau tidak ada, tambahkan di `~/.bashrc`:

```bash
export PATH="$PATH:$HOME/scripts"
rtk bash -lc 'source ~/.bashrc'
```

---

### ❌ Hasil RAG tidak relevan / score rendah

Gunakan `--debug` untuk lihat detail:

```bash
rtk rag "query kamu" -p petrochina-eproc --debug
```

Kalau hasil utama tidak memenuhi gate not-found (`topScore < 0.50`) atau score retrieval tetap rendah, knowledge base kemungkinan belum punya informasi ini.
Kerjakan dulu, lalu simpan ke Qdrant lewat Session End Protocol.

---

### ❌ Claude tetap hallucinate walaupun pakai --claude

Tambahkan `--strict`:

```bash
rag "query" -p petrochina-eproc --claude "task" --strict --copy
```

Mode strict memaksa Claude untuk cite sumber dan output `NOT FOUND IN RAG`
kalau ada yang tidak ada di knowledge base.

---

## 🗂️ Referensi Cepat

```bash
# Copilot mode (default) — untuk task kecil
rag "query" -p petrochina-eproc --copy

# Claude mode — untuk task besar
rag "design query" -p petrochina-eproc --claude "task detail" --copy

# Claude mode + strict — untuk keputusan kritis
rag "query" -p petrochina-eproc --claude "task" --strict --copy

# Debug — kalau hasil tidak relevan
rag "query" -p petrochina-eproc --debug

# Homelab / infra queries
rag "query" -p homelab --copy
```

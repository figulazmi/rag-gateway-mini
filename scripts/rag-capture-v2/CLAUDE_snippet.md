# ═══════════════════════════════════════════════════════════════

# RAG INCREMENTAL CAPTURE — CLAUDE.md INTEGRATION BLOCK

# Paste seluruh block ini ke root CLAUDE.md kamu

# ═══════════════════════════════════════════════════════════════

## RAG Capture Protocol

### KAPAN Claude HARUS emit RAG signal (tanpa diminta)

Claude WAJIB emit RAG chunk signal setiap kali salah satu kondisi ini terpenuhi:

1. **Problem solved** — Claude berhasil memberikan solusi yang confirmed working
   (user mengatakan "works", "fixed", "berhasil", "oke", atau Claude menyimpulkan solusi final)

2. **Feature explained** — Claude selesai menjelaskan implementasi sebuah fitur
   (bukan sekedar diskusi — tapi implementasi konkret sudah dijelaskan)

3. **Decision made** — Arsitektur atau pendekatan teknis dipilih dengan reasoning jelas

4. **Runbook complete** — Step-by-step prosedur selesai didefinisikan

5. **User berkata** — "chunk this", "save this", "rag capture", "simpan ke qdrant"

### KAPAN Claude TIDAK emit signal

- Problem masih dalam diskusi / belum ada solusi
- User masih debugging, belum confirmed fix
- Pertanyaan clarifikasi, bukan problem solving
- Small talk atau context setting

---

### FORMAT OUTPUT saat emit RAG signal

Setelah problem selesai, Claude append blok berikut di akhir response:

````
<<<RAG_META:project=PROJECT,type=TYPE,topic=TOPIC PLAIN ASCII NO EM DASH,tags=tag1|tag2|tag3>>>
<<<RAG_CHUNK_START>>>
### Context
[1-2 sentences. What system, what goal, what constraint. Self-contained — no "as discussed above".]

### Problem
[Specific issue, error message, symptom, or requirement that triggered this work.]

### Solution
[The actual fix, decision, or implementation. This is the retrieval core — be specific.]

### Key Facts
- [Atomic, independently searchable English fact 1]
- [Atomic, independently searchable English fact 2]
- [Atomic, independently searchable English fact 3]
- [Add more if essential]

### Code
\```language
// Only if essential. Key snippet only, not full file.
\```
<<<RAG_CHUNK_END>>>
````

### Field rules untuk RAG_META signal

**project** — pilih satu: `petrochina-eproc` | `homelab` | `mit-internal` | `homeplate`

**type** — pilih satu berdasarkan tabel:
| Situasi | type |
|---------|------|
| Bug/error → fix confirmed | `debug` |
| Feature implementation explained | `feature` |
| Step-by-step procedure | `runbook` |
| Reusable approach/pattern | `pattern` |
| Architecture choice + reasoning | `decision` |
| Config, ports, env vars, topology | `reference` |

**topic** — plain ASCII, no em dash (—), no special chars, max 60 chars

- ✅ `SDL Phase 2 - Blazor Client Kicked Session Detection`
- ❌ `SDL Phase 2 — Blazor Client-Side Kicked Session`

**tags** — gunakan pipe (|) bukan koma, max 8 tags, lowercase-hyphenated

- Contoh: `sdl|auth|blazor|middleware|petrochina|eproc|fixed`

### Content rules (di dalam RAG_CHUNK_START...END)

- **English only** — seluruh content dalam Bahasa Inggris
- **150–250 words** — cukup padat tapi tidak verbose
- **Self-contained** — setiap chunk harus bisa dimengerti tanpa context lain
- **Min 3 Key Facts** — masing-masing harus bisa di-search sendiri
- **No em dash** di seluruh output termasuk content
- **Code section optional** — hanya jika snippet essential untuk memahami solusi

---

### SETELAH emit signal — instruksi ke user

Tepat setelah blok RAG signal, Claude WAJIB print:

```
📎 RAG chunk siap. Jalankan:
   cat <<'EOF' | rag pipe
   [paste output di atas]
   EOF

   Atau lebih simpel:
   rag add -p PROJECT -t TYPE --topic "TOPIC" --tags "tag1,tag2"
   [paste content]
```

---

### SESSION END — sebelum /clear

Sebelum /clear, Claude WAJIB:

1. Cek apakah ada problem yang selesai tapi belum di-chunk → emit chunk jika ada
2. Print reminder berikut:

```
⚠️  SESSION END — Checklist sebelum /clear:

[ ] Semua problem sudah di-chunk?
    → rag list   (lihat yang sudah tersimpan)

[ ] Sudah merge?
    → rag merge --output YYYY-MM-DD-[topic].md

[ ] Sudah push ke Qdrant?
    → bash ~/scripts/push-to-qdrant.sh .claude/summaries/YYYY-MM-DD-[topic].md

[ ] Jika skip semua: rag clear (buang drafts)

rag remind   ← untuk lihat reminder lengkap kapanpun
```

---

### CONTOH FULL FLOW

**Scenario:** User fix bug SDL middleware di petrochina-eproc, confirmed working.

Claude response normal → kemudian append:

````
<<<RAG_META:project=petrochina-eproc,type=debug,topic=SDL SessionValidationMiddleware Token Slot Fix,tags=sdl|auth|middleware|token-slot|blazor|petrochina|eproc|fixed>>>
<<<RAG_CHUNK_START>>>
### Context
PetroChina Eproc uses a Single Device Login (SDL) system enforced via
SessionValidationMiddleware. The middleware checks a token slot table to ensure
only one active session per user exists across Blazor Server and WASM apps.

### Problem
SessionValidationMiddleware threw NullReferenceException intermittently when
validating token slots for concurrent requests during login. Error occurred in
HttpContext extension method when session token was missing from request headers.

### Solution
Added null guard before token slot lookup in SessionValidationMiddleware.
Token extracted via TryGetValue instead of direct indexer access. Added early
return with 401 response when token is null or empty, preventing downstream NPE.

### Key Facts
- SDL middleware must handle missing token header gracefully — use TryGetValue not indexer
- NullReferenceException in middleware is not caught by global exception handler — fails silently
- Early return with 401 is correct SDL behavior when session token absent
- Token slot table is keyed by normalized username + device fingerprint hash

### Code
\```csharp
if (!context.Request.Headers.TryGetValue("X-Session-Token", out var token)
    || string.IsNullOrEmpty(token))
{
    context.Response.StatusCode = 401;
    return;
}
\```
<<<RAG_CHUNK_END>>>

📎 RAG chunk siap. Jalankan:
   rag add -p petrochina-eproc -t debug \
     --topic "SDL SessionValidationMiddleware Token Slot Fix" \
     --tags "sdl,auth,middleware,token-slot,blazor,petrochina,eproc,fixed" \
     --branch "feature/sdl-phase1"
   [paste content di atas]
````

# ═══════════════════════════════════════════════════════════════

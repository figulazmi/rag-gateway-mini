# RAG Bootstrap Runbook — New Device and New Server

**Purpose:** step-by-step recovery checklist when moving to a new local device, replacing VM B1, or rebuilding the RAG stack from scratch.
**Scope:** `rag_capture.py`, `push-to-qdrant.sh`, Qdrant `knowledge_v2`, n8n `knowledge-ingest`, Ollama, and `rag-gateway-mini`.
**Last updated:** 2026-04-30

> Use this runbook when the scripts work on the old laptop/server but fail after migration. For daily usage and architecture details, read [`RAG_MANUAL_BOOK.md`](RAG_MANUAL_BOOK.md). For VM restoration history, read [`../planning/VM105_RESTORATION_PLAN.md`](../planning/VM105_RESTORATION_PLAN.md).

---

## 1. Migration Targets

| Scenario | Use this section | Goal |
|---|---|---|
| New laptop or PC only | Sections 2, 4, 6, 7 | Local `rag add` and `rag merge` can push to existing server |
| New server only | Sections 3, 5, 6, 7 | Existing laptop can push to new Qdrant/n8n stack |
| Full rebuild | Sections 2 through 8 | Local and server are both reproducible from scratch |

---

## 2. Local Device Bootstrap Checklist

### 2.1 Required local tools

Install or verify:

- Git Bash
- Git
- Python 3
- `curl`
- `jq`
- OpenSSH client
- Access to this repo: `rag-gateway-mini`
- Access to the scripts folder: `~/scripts`

Verification:

```bash
python3 --version
jq --version
curl --version
ssh -V
git --version
```

### 2.2 Restore script layout

Expected local paths:

| Path | Purpose |
|---|---|
| `~/scripts/rag-capture-v2/rag_capture.py` | Source for the `rag` CLI |
| `~/.local/bin/rag` | Installed CLI entrypoint |
| `~/scripts/push-to-qdrant.sh` | Ingest script that sends merged chunks to n8n |
| `~/.config/qdrant-knowledge.env` | Local Qdrant API key, outside git |
| `~/.rag_drafts/{project}/` | Draft chunks from `rag add` |
| `~/.rag_push_queue` | Failed push retry queue |

If `rag` is not on PATH, call it explicitly during recovery:

```bash
bash -lc "$HOME/.local/bin/rag status"
```

### 2.3 Create local Qdrant env file

Never hardcode the API key in tracked files.

```bash
mkdir -p ~/.config
cat > ~/.config/qdrant-knowledge.env <<'EOF'
QDRANT_API_KEY=replace-with-active-server-key
EOF
chmod 600 ~/.config/qdrant-knowledge.env
```

Verify the key without printing it:

```bash
source ~/.config/qdrant-knowledge.env
printf 'key_len=%s\n' "${#QDRANT_API_KEY}"
```

Expected: `key_len=64` for the current deployment.

### 2.4 Configure SSH access

The local device must reach the server over SSH:

```bash
ssh figulazmi@192.168.18.199 'hostname'
```

If rebuilding with a new server, replace `192.168.18.199` in scripts and docs with the new LAN IP, and update the Tailscale IP if remote access is required.

### 2.5 Sync active Qdrant key from server when needed

Use this only when the server is already configured and local count checks return `401`.

```bash
python3 - <<'PY'
import os, re, subprocess, pathlib
raw = subprocess.check_output([
    'ssh', 'figulazmi@192.168.18.199',
    'sudo -n docker exec qdrant printenv QDRANT__SERVICE__API_KEY'
], stderr=subprocess.STDOUT).decode(errors='ignore')
m = re.search(r'[A-Za-z0-9_-]{64}', raw)
if not m:
    raise SystemExit('active 64-character Qdrant key not found')
path = pathlib.Path.home() / '.config' / 'qdrant-knowledge.env'
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(f'QDRANT_API_KEY={m.group(0)}\n')
os.chmod(path, 0o600)
print('Qdrant key synced: key_len=64')
PY
```

---

## 3. Server Bootstrap Checklist

### 3.1 Required server tools

Install or verify:

- Docker
- Docker Compose v2
- Git
- Python 3
- `curl`
- `jq`
- Tailscale, if remote access is needed

Verification:

```bash
docker ps
docker compose version
python3 --version
curl --version
jq --version
```

### 3.2 Expected server services

| Service | Default LAN endpoint | Purpose |
|---|---|---|
| Qdrant | `http://192.168.18.199:6333` | Stores `knowledge_v2` dense and sparse vectors |
| n8n | `http://192.168.18.199:5678` | Ingest workflow webhook |
| Ollama | `http://192.168.18.199:11434` | `nomic-embed-text` embeddings |
| rag-gateway-mini | `http://192.168.18.199:5200` | `/rag/search` and `/rag/debug` API |

Container names expected by scripts:

```text
qdrant
n8n
```

If names differ on a new server, update recovery commands and scripts accordingly.

### 3.3 Deploy rag-gateway-mini

Expected path:

```bash
/opt/homelab/ai-stack/rag-gateway-mini
```

Basic deployment:

```bash
cd /opt/homelab/ai-stack/rag-gateway-mini
git pull
cd src
docker compose up -d --build
curl http://192.168.18.199:5200/health
```

Secrets must stay outside git:

```text
/opt/homelab/ai-stack/rag-gateway-mini/appsettings.Production.json
```

Template source:

```text
src/appsettings.Production.json.template
```

### 3.4 Configure Qdrant API key

Qdrant must require an API key, and every caller must use the same active key:

| Caller | Where key lives |
|---|---|
| Qdrant container | `QDRANT__SERVICE__API_KEY` |
| Local laptop | `~/.config/qdrant-knowledge.env` |
| n8n workflow | `Qdrant: Upsert Point` HTTP header or credential |
| rag-gateway-mini | `appsettings.Production.json` if direct Qdrant access is configured |

Verify active server key without printing it:

```bash
sudo -n docker exec qdrant sh -lc 'printf "key_len=%s\n" "${#QDRANT__SERVICE__API_KEY}"'
```

Expected: `key_len=64`.

### 3.5 Restore Qdrant collection

The collection must be named `knowledge_v2` and support:

- Dense vector: `dense`, 768 dimensions, cosine distance
- Sparse vector: BM25 style sparse vector, server-side IDF modifier if configured
- Payload fields used by filters: `project`, `chunk_type`, `status`, `topic`, `tags`, `date`, `content`

Verify collection access:

```bash
source ~/.config/qdrant-knowledge.env
curl -s -H "api-key: $QDRANT_API_KEY" \
  http://192.168.18.199:6333/collections/knowledge_v2
```

Expected: HTTP 200 JSON with `points_count`.

---

## 4. Local Script Configuration

### 4.1 Update network constants in `push-to-qdrant.sh`

On a new server, update these values:

```bash
B1_LOCAL_IP="192.168.18.199"
B1_LOCAL_PORT="5678"
B1_TAILSCALE_IP="100.120.249.99"
B1_TAILSCALE_PORT="5678"
N8N_WEBHOOK_PATH="webhook/knowledge-ingest"
```

The script should test network in this order:

1. Localhost, when running inside the server
2. LAN IP
3. Tailscale IP
4. Fail with a clear unreachable message

### 4.2 Verify point count check

From the local device:

```bash
source ~/.config/qdrant-knowledge.env
curl -s -o /tmp/qdrant_count_check.json -w 'http=%{http_code}\n' \
  --max-time 5 \
  -H "api-key: $QDRANT_API_KEY" \
  http://192.168.18.199:6333/collections/knowledge_v2
python3 - <<'PY'
import json
print(json.load(open('/tmp/qdrant_count_check.json')).get('result', {}).get('points_count', '?'))
PY
```

Expected:

```text
http=200
[number]
```

If this returns `401`, the local key does not match the active Qdrant server key.

---

## 5. n8n Workflow Bootstrap

### 5.1 Workflow identity

Expected workflow:

| Field | Value |
|---|---|
| Name | `knowledge_v2` |
| Webhook path | `knowledge-ingest` |
| HTTP path | `/webhook/knowledge-ingest` |
| Main purpose | Validate payload, build `embed_content`, embed via Ollama, upsert to Qdrant |

### 5.2 Required workflow behavior

The `Validate & Clean` node must build a prefixed embedding string equivalent to:

```javascript
const tagsStr = Array.isArray(body.tags)
  ? body.tags.join(', ')
  : (body.tags || '');
const chunkType = body.chunk_type || body.session_type || 'unknown';
const embed_content =
  `This chunk is from project ${body.project}, ` +
  `type ${chunkType}, topic "${body.topic}", ` +
  `tagged ${tagsStr}. Session date ${body.date || 'unknown'}. ` +
  `Content: ${cleanContent}`;
```

It should pass the embedding prompt as a simple field:

```javascript
prompt: embed_content
```

The Ollama HTTP Request node should use:

```text
={{$json.prompt}}
```

Avoid complex n8n expressions in the Ollama node. They have failed before with invalid syntax and shell quoting drift.

### 5.3 Required n8n nodes

| Node | Required behavior |
|---|---|
| `webhook-knowledge-ingest` | Accept POST payload from `push-to-qdrant.sh` |
| `Validate & Clean` | Validate fields, normalize content, build `prompt` |
| `Ollama: nomic-embed-text` | POST to Ollama `/api/embeddings` with `prompt={{$json.prompt}}` |
| `Prepare Qdrant Point` | Build deterministic point ID, dense vector, sparse vector, payload |
| `Qdrant: Upsert Point` | Upsert into `knowledge_v2` with active API key |
| `Build Response` | Return success payload |
| `Respond to Webhook` | Return HTTP 2xx only when workflow completed |

### 5.4 Verify n8n execution status

HTTP 200 from the webhook is not enough. Check n8n execution history.

On server, inspect the latest workflow executions in SQLite if UI is not enough:

```bash
sudo -n sqlite3 /var/lib/docker/volumes/ai-stack_n8n_data/_data/database.sqlite \
  "select id,status,workflowId,startedAt,stoppedAt from execution_entity order by id desc limit 10;"
```

Expected for test pushes: `status=success`.

---

## 6. Cosine Gate Bootstrap

### 6.1 Required verifier location

Expected server path:

```text
~/scripts/verify_embed_cosine.py
```

The verifier must reconstruct the same prefix as n8n `Validate & Clean`:

```python
content = payload.get("content", "")
project = payload.get("project", "") or ""
chunk_type = payload.get("chunk_type") or payload.get("session_type") or "unknown"
topic = payload.get("topic") or ""
tags = payload.get("tags") or ""
if isinstance(tags, list):
    tags_str = ", ".join(str(t) for t in tags)
else:
    tags_str = str(tags)
date = payload.get("date") or "unknown"
prepended = (
    f"This chunk is from project {project}, "
    f"type {chunk_type}, topic \"{topic}\", "
    f"tagged {tags_str}. Session date {date}. "
    f"Content: {content}"
)
```

### 6.2 Expected cosine result

Run:

```bash
ssh figulazmi@192.168.18.199 \
  'python3 ~/scripts/verify_embed_cosine.py --string-id DOC_ID-chunk-1'
```

Expected example:

```text
PASS | cos(stored,prepended)=1.0000  cos(stored,raw)=0.9573  margin=0.0427
```

Interpretation:

| Result | Meaning |
|---|---|
| `cos(stored,prepended)` near `1.0000` | n8n embedded the correct `embed_content` field |
| `cos(stored,raw)` also high | Can be normal for short chunks or semantically similar content |
| Positive margin | Prefixed embedding is still clearly closer than raw content |
| Low `cos(stored,prepended)` | Abnormal: n8n likely embedded the wrong field or verifier prefix drifted |

---

## 7. End-to-End Smoke Test

### 7.1 Create one test chunk

```bash
cat <<'RAGBODY_EOF' | rag add -p homelab -t debug \
  --topic "Bootstrap smoke test" \
  --tags "homelab,bootstrap,qdrant,n8n"
### Context
A new local device or server is being validated for the RAG capture pipeline.
### Problem
The operator needs proof that rag add, rag merge, n8n ingest, Qdrant upsert, and cosine verification work end to end.
### Solution
Create this temporary smoke chunk, merge it, verify the push output, verify n8n execution success, then delete the point from Qdrant.
### Key Facts
- The smoke test must show HTTP 200 from the webhook and success in n8n execution history.
- The push output must show Qdrant point count before and after, not skipped.
- The cosine gate must pass against the n8n embed_content prefix.
RAGBODY_EOF
```

### 7.2 Merge and push

```bash
rag merge --output 2026-04-30-bootstrap-smoke-test.md
```

Expected output must include:

```text
Done -- 1/1 chunks pushed to Qdrant
Points     : BEFORE -> AFTER
[cosine gate] ... PASS
```

If it says `Points skipped`, fix local Qdrant API key sync before continuing.

### 7.3 Verify n8n success

```bash
ssh figulazmi@192.168.18.199 \
  'sudo -n sqlite3 /var/lib/docker/volumes/ai-stack_n8n_data/_data/database.sqlite "select id,status,workflowId,startedAt from execution_entity order by id desc limit 5;"'
```

Expected: latest `knowledge_v2` execution is `success`.

### 7.4 Delete the smoke test point

Use the deterministic string ID from the merged summary:

```text
2026-04-30-bootstrap-smoke-test-001-chunk-1
```

Convert using the same djb2 numeric ID algorithm used by the pipeline, then delete:

```bash
source ~/.config/qdrant-knowledge.env
POINT_ID=$(python3 - <<'PY'
import functools
s = '2026-04-30-bootstrap-smoke-test-001-chunk-1'
h = functools.reduce(lambda h, c: ((h << 5) + h + ord(c)) & 0x7FFFFFFF, s, 5381)
print(abs(h))
PY
)
curl -s -X POST http://192.168.18.199:6333/collections/knowledge_v2/points/delete \
  -H "Content-Type: application/json" \
  -H "api-key: $QDRANT_API_KEY" \
  -d "{\"points\":[${POINT_ID}]}"
```

---

## 8. Troubleshooting During Migration

### 8.1 `Points skipped` during `rag merge`

Meaning: `push-to-qdrant.sh` could not read Qdrant point count.

Most likely causes:

| Cause | Check | Fix |
|---|---|---|
| Local API key stale | `key_len` wrong or Qdrant returns `401` | Sync `~/.config/qdrant-knowledge.env` from active server key |
| Server unreachable | `curl` timeout | Check LAN/Tailscale connectivity |
| Wrong server IP | Script points to old IP | Update `B1_LOCAL_IP` and `B1_TAILSCALE_IP` |
| Qdrant container down | `docker ps` missing `qdrant` | Restart Qdrant stack |

### 8.2 Webhook returns HTTP 200 but n8n UI shows error

Treat n8n execution history as authoritative.

Check:

```bash
sudo -n sqlite3 /var/lib/docker/volumes/ai-stack_n8n_data/_data/database.sqlite \
  "select id,status,workflowId,startedAt from execution_entity order by id desc limit 10;"
```

Common root causes:

- Qdrant API key mismatch in `Qdrant: Upsert Point`
- Ollama prompt expression invalid
- n8n workflow shadowed by old active workflow with same webhook path
- Workflow changes saved but not published or active webhook not re-registered

### 8.3 Cosine gate fails

First check whether the verifier prefix matches n8n `embed_content` exactly.

Abnormal:

```text
cos(stored,prepended) < 0.95
```

Likely cause: n8n embedded raw content or a stale field.

Potentially normal:

```text
cos(stored,prepended)=1.0000  cos(stored,raw)>0.95
```

This can happen for short chunks. Review margin and message. The prefixed vector should still be closer than raw content.

### 8.4 `rag merge` crashes with EOF

`rag_capture.py` must not call interactive `input()` in non-interactive mode. The merge path should handle `EOFError` or skip prompts when `stdin` is not a TTY.

Expected behavior:

- Interactive terminal: can ask whether to clear drafts
- Non-interactive shell: should not crash with `EOFError`

### 8.5 `rag` command not found

Check:

```bash
ls ~/.local/bin/rag
bash -lc "$HOME/.local/bin/rag status"
```

If direct execution fails on Windows, invoke through Bash:

```bash
bash -lc '"$HOME/.local/bin/rag" merge'
```

---

## 9. Final Acceptance Checklist

A new device/server setup is considered ready only when all checks pass:

- [ ] Local `~/.config/qdrant-knowledge.env` exists and has the active key
- [ ] Local device can SSH to the server
- [ ] `curl /collections/knowledge_v2` returns HTTP 200 with `points_count`
- [ ] `rag add` creates a draft chunk
- [ ] `rag merge` pushes through `push-to-qdrant.sh`
- [ ] Push output shows `Points BEFORE -> AFTER`, not `skipped`
- [ ] n8n latest `knowledge_v2` execution status is `success`
- [ ] Cosine gate returns `PASS`
- [ ] Smoke-test point is deleted after validation
- [ ] `rag-gateway-mini` health endpoint returns healthy
- [ ] MCP `search_knowledge` can retrieve a known chunk

---

## 10. Related Docs

| Doc | When to read |
|---|---|
| [`RAG_MANUAL_BOOK.md`](RAG_MANUAL_BOOK.md) | Daily operation, architecture, CLI reference, detailed troubleshooting |
| [`../planning/VM105_RESTORATION_PLAN.md`](../planning/VM105_RESTORATION_PLAN.md) | Historical VM restoration and full re-ingest plan |
| [`../pipeline/RAG_CAPTURE_PIPELINE_GAPS.md`](../pipeline/RAG_CAPTURE_PIPELINE_GAPS.md) | Known capture pipeline gaps and fixes |
| [`../security/RAG_SECURITY_POSTURE.md`](../security/RAG_SECURITY_POSTURE.md) | API key, webhook, cosine gate, audit hardening |
| [`../quality/RAG_EVAL_HARNESS.md`](../quality/RAG_EVAL_HARNESS.md) | Retrieval quality validation after rebuild |

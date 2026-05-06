# Configuration

Use this document for configuration, environment variables, secrets locations, and safe defaults.

Do not store secrets in this file.

---

## Configuration Sources

| Source | Purpose | Secret? | Notes |
|---|---|---:|---|
| `src/appsettings.json` | Local/default application settings | No | Commit safe defaults only |
| `src/appsettings.Production.json.template` | Production config template | No | Template only; fill secrets outside repo |
| `/opt/homelab/ai-stack/rag-gateway-mini/appsettings.Production.json` | VM B1 production secrets/config | Yes | Never commit |
| Environment variables | Runtime overrides | Maybe | Document every required variable here |

---

## Required Settings

| Key | Required | Example | Owner | Notes |
|---|---:|---|---|---|
| `Qdrant:Url` | Yes | `http://192.168.18.199:6333` | Infrastructure | Use VM B1 Qdrant endpoint |
| `Qdrant:ApiKey` | Yes | Secret value | Infrastructure | Must be passed as secret, never committed |
| `Ollama:BaseUrl` | Yes | `http://192.168.18.199:11434` | Infrastructure | Embedding provider endpoint |
| `RagGateway:QdrantCollection` | Yes | `knowledge_v2_keyfacts` | Application | Production default collection; use `knowledge_v2` only as fallback/comparison evidence |

---

## Secrets Rules

- Keep real secrets outside the repository.
- Commit templates with placeholder values only.
- Document where secrets live, not the secret values.
- Rotate secrets after accidental exposure.
- Include the required `api-key` header in Qdrant examples.

---

## Configuration Change Checklist

| Check | Required? |
|---|---:|
| Template updated | Yes |
| Runtime location documented | Yes |
| Secret excluded from git | Yes |
| Deploy or restart steps documented | Yes |
| Verification command documented | Yes |

---

*Last updated: 2026-05-05 · Owner: Figur Ulul Azmi*
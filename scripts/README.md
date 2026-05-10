# Project Scripts Index

This repo keeps only project-specific scripts, fixtures, examples, and archived one-time migrations.

## Active project-specific scripts

- `smoke-p32-implementation-correctness.py` — P3.2 implementation-correctness smoke harness for rag-gateway-mini.
- `init-docs-template.py` — initializes the reusable documentation template from this repo's `docs/templates/` folder.

## Fixtures and examples

- `eval-fixtures/` — retrieval and implementation smoke fixtures used by documentation and reports.
- `qdrant-knowledge.env.example` — example environment file only.

## Archived scripts

- `archive/migrations/` — completed one-time migration and experiment scripts retained for audit history.

## Reusable RAG infrastructure tools

Reusable tools are versioned in the separate rag-tools repository under `~/scripts/rag-infra/`, not in this project:

- `~/scripts/rag-infra/eval-retrieval-quality.py`
- `~/scripts/rag-infra/test-qdrant-retrieval.sh`
- `~/scripts/rag-infra/qdrant-graph.sh`
- `~/scripts/rag-infra/qdrant-visualize.sh`
- `~/scripts/rag-infra/anomaly_check.py`
- `~/scripts/rag-infra/snapshot_tamper_check.py`

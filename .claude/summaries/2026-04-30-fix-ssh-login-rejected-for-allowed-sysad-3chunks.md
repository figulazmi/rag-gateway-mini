---
id: 2026-04-30-fix-ssh-login-rejected-for-allowed-sysad-001
date: 2026-04-30
source: claude-code-cli
collection: knowledge_v2
project: homelab
chunk_type: debug
topic: Fix SSH login rejected for allowed sysadmin user
tags: [homelab, vm-b1, ssh, linux, access]
related: []
session_type: 
environment: homelab
git_branch: 
status: implemented
chunk_source: code
---

## CHUNK 1: Fix SSH login rejected for allowed sysadmin user
<!-- rag_chunk_meta chunk_type=debug tags=[homelab, vm-b1, ssh, linux, access] -->

### Context
SSH access to VM B1 at 192.168.18.199 was failing for sysadmin even after local key setup and successful key loading on Windows. The server used OpenSSH with hardening drop-in configs.
### Problem
Authentication kept failing with Permission denied (publickey) although the key fingerprint matched for another user and sshd showed AllowUsers including sysadmin. This created a misleading state where policy appeared correct but login still failed.
### Solution
Validated client-side with ssh -vvv and confirmed server rejected offered key. Checked effective sshd settings and discovered AllowUsers policy was active in /etc/ssh/sshd_config.d/00-hardening.conf. Then verified sysadmin account path and found /home/sysadmin did not exist. Created sysadmin user, initialized /home/sysadmin/.ssh, added the same ed25519 public key, set permissions to 700 for .ssh and 600 for authorized_keys, and ownership to sysadmin. SSH login as sysadmin succeeded immediately after account and key file creation.
### Key Facts
- If AllowUsers contains a username but the account does not exist, SSH publickey login always fails.
- Matching key fingerprint on one user does not grant access to another user because authorized_keys is per-account.
- ssh -vvv showing "Offering public key" followed by immediate type 51 means server-side rejection, not client key loading failure.

## CHUNK 2: Pattern: diagnose SSH key rejection on hardened hosts
<!-- rag_chunk_meta chunk_type=pattern tags=[homelab, vm-b1, ssh, pattern, linux] -->

### Context
On hardened Linux hosts, SSH public key login can fail even when local keys are loaded and user believes policy is already correct. This often happens during multi-user administration where access rules and account state diverge.
### Pattern
When SSH returns Permission denied (publickey), diagnose in this order: client offer, server policy, then account existence. First run ssh -vvv and verify the offered key fingerprint and whether rejection is immediate. Then inspect effective sshd config using `sshd -T` to confirm active AllowUsers or DenyUsers directives from drop-in files. Finally verify that the target account exists and has its own valid authorized_keys file with strict permissions.
### When to Apply
Use this sequence whenever one user can SSH successfully but another cannot on the same host and key type.
### Anti-Pattern
Do not assume matching fingerprints on one account implies access for another account. SSH authorization is per-user and requires both policy allow-list and valid account-local key files.
### Key Facts
- `sshd -T` reveals effective directives from both main config and include files.
- `AllowUsers` can be correct while login still fails if the user account does not exist.
- Immediate key rejection after "Offering public key" indicates server-side auth decision, not client agent failure.

## CHUNK 3: P0-P2 docs sync and key rotation closure
<!-- rag_chunk_meta chunk_type=runbook tags=[homelab, vm-b1, security, rag, runbook, docs] -->

### Context
Session focused on closing audit and governance gaps for rag-gateway-mini RAG operations. Scope covered P0 security controls, P1 status alignment, and P2 documentation governance consistency between index and reference docs.

### Problem
Open priorities were stale and inconsistent with runtime reality. Qdrant key rotation had partial execution with mismatched compose and runtime key states. Git history still exposed a legacy key, and quality baseline tables remained partially placeholder despite available measured retrieval metrics.

### Solution
Completed key rotation validation by reconciling active runtime key and verifying behavior with HTTP status checks. Executed history scrub workflow using git-filter-repo and force-with-lease push, then updated security tracker to DONE with explicit verification evidence. Refreshed docs/README quick status to point to current highest open item (P0-3), updated quality harness with measured retrieval metrics and UNMEASURED tags for pending end-to-end metrics, and added deferred IDF revisit criteria.

### Key Facts
- Runtime Qdrant auth verification passed with new key HTTP 200 and old key HTTP 401.
- Git history rewrite required restoring origin remote and refreshing lease before successful force-with-lease push.
- Quick status index now reflects real next work: P0-3 cosine gate hard abort, while P0-1/P0-2 are documented as completed.

---

## SESSION METADATA

- **Total chunks**: 3
- **Qdrant collection**: knowledge_v2
- **Generated by**: rag_capture.py v2 -- Incremental Capture
- **Author**: Figur Ulul Azmi
- **Date**: 2026-04-30
- **Unresolved items**: (fill manually if needed)
---
id: 2026-04-29-qdrant-dashboard-visualize-using-dense-p-001
date: 2026-04-29
source: claude-code-cli
collection: knowledge_v2
project: homelab
chunk_type: debug
topic: Qdrant dashboard visualize using dense patch re-apply after restore
tags: [homelab, vm-b1, qdrant, docker, dashboard, named-vectors]
related: []
session_type: 
environment: homelab
git_branch: 
status: implemented
chunk_source: code
---

## CHUNK 1: Qdrant dashboard visualize using dense patch re-apply after restore
<!-- rag_chunk_meta chunk_type=debug tags=[homelab, vm-b1, qdrant, docker, dashboard, named-vectors] -->

### Context
Qdrant v1.17.1 on VM B1 (192.168.18.199). Collection knowledge_v2 uses named vectors
(dense+sparse). Dashboard /visualize panel shows error "Please select a valid vector name,
default vector is not defined" because knowledge_v2 has no default vector -- using is
mandatory. Fix first applied Apr 22, lost after VM 105 restore (dashboard-patch/ dir and
bind mount not persisted).

### Problem
After VM 105 restoration, /opt/homelab/ai-stack/qdrant/dashboard-patch/ dir was gone and
bind mount was absent from docker-compose.yml. Dashboard Visualize returned error without
manually adding "using": "dense" each time.

### Solution
1. sudo mkdir /opt/homelab/ai-stack/qdrant/dashboard-patch/ + chown figulazmi
2. sudo docker cp qdrant:/qdrant/static/assets/index-C-wxiiEX.js to dashboard-patch/
3. sudo chown figulazmi on copied file (docker cp sets root ownership)
4. Python patch via heredoc: replace both GKt and Hnn template literals to add "using": "dense"
5. Add bind mount line to docker-compose.yml via Python + sudo tee
6. docker compose -p qdrant up -d --force-recreate qdrant (project name = qdrant, NOT ai-stack)
7. Verify: docker exec qdrant grep -o '"using": "dense"' .../index-C-wxiiEX.js | wc -l = 2

### Key Facts
- Two JS variables must be patched independently: GKt (/visualize route, YKt component) and Hnn (/graph route, qnn component)
- GKt original: "limit": 500 -- patch adds "using": "dense" after limit line
- Hnn original: "limit": 5 -- patch changes to "limit": 500 plus "using": "dense"
- File in container: /qdrant/static/assets/index-C-wxiiEX.js (hash changes on Qdrant upgrade -- v1.17.1 = index-C-wxiiEX.js)
- Bind mount line: /opt/homelab/ai-stack/qdrant/dashboard-patch/index-C-wxiiEX.js:/qdrant/static/assets/index-C-wxiiEX.js:ro
- Compose project name is qdrant (NOT ai-stack) -- confirmed via docker inspect labels
- docker restart does NOT apply new volume mounts -- must use docker compose up --force-recreate
- After recreate, hard refresh browser (Ctrl+Shift+R) to bust JS cache
- Re-patch required after every Qdrant image upgrade (filename hash changes)
- QDRANT_API_KEY on VM B1 is in /opt/homelab/ai-stack/qdrant/.env (NOT ~/.config/qdrant-knowledge.env)

## CHUNK 2: Deploy harden.py to single server using fleet.py --conf flag
<!-- rag_chunk_meta chunk_type=runbook tags=[homelab, vm-b1, fleet, harden, hardening, deployment, ssh, ubuntu] -->

## CHUNK 1: Targeting a Single Server with fleet.py Using --conf Flag

### Context

homelab-hardening repo uses fleet.py to manage harden.py deployments across multiple servers.
fleet.conf is the default server inventory. When a target server is not in fleet.conf
(or is the same IP as an existing entry but different SSH user), fleet.py --conf flag
allows targeting a single server without modifying the permanent fleet.conf.

### Problem

VM 105 (figulazmi@192.168.18.199) needed to be tested and hardened. It was not listed
in fleet.conf. Adding it directly would create a duplicate IP entry (same as vm-b1
sysadmin@192.168.18.199), causing fleet.py to run on the same machine twice with
different users — redundant and messy.

### Solution

Create a temporary per-target fleet conf file and pass it via --conf flag. fleet.py
already supports --conf (ap.add_argument("--conf")) to override the default fleet.conf path.

Steps:
1. Create fleet-vm105.conf with one line: `vm-105 figulazmi@192.168.18.199 VM 105`
2. Push repo: `python3 fleet.py --conf fleet-vm105.conf push`
3. Dry-run test: `python3 fleet.py --conf fleet-vm105.conf deploy --dry-run`
4. Live run: `python3 fleet.py --conf fleet-vm105.conf deploy`
5. Temp conf can be deleted after use or kept for repeated ops on that server

### Key Facts

- fleet.py --conf flag overrides default fleet.conf path for all subcommands (status, deploy, push)
- Temporary conf file pattern avoids polluting the permanent fleet.conf with ephemeral targets
- Same IP with different SSH user is valid — fleet.py uses user@host as the SSH target directly
- fleet.py push syncs repo to REMOTE_PATH=/opt/homelab/hardening via tar+ssh pipe
- fleet.py deploy runs: `cd /opt/homelab/hardening && sudo python3 harden.py {flags} 2>&1`
- Passwordless sudo required on remote server for live deploy (verify with `ssh user@host "sudo -n whoami"`)

### Code / Commands

```bash
# Create temp conf
echo "vm-105   figulazmi@192.168.18.199   VM 105 (Proxmox VMID 105)" > fleet-vm105.conf

# Push + dry-run
python3 fleet.py --conf fleet-vm105.conf push
python3 fleet.py --conf fleet-vm105.conf deploy --dry-run

# Live run
python3 fleet.py --conf fleet-vm105.conf deploy
```

## CHUNK 3: auditd enabled=1 after harden.py live run - augenrules silent fail
<!-- rag_chunk_meta chunk_type=debug tags=[homelab, vm-b1, auditd, harden, hardening, ubuntu, security, debug] -->

## CHUNK 2: auditd Layer Reports enabled=1 Instead of 2 After Live Run

### Context

harden.py Layer 8 (auditd) deploys audit rules to /etc/audit/rules.d/99-hardening.rules
and runs augenrules --load to apply them. The rules file ends with -e 2 to make rules
immutable. After live run on VM 105, status.py reports auditd FAIL: enabled=1 (expected 2).

### Problem

harden.py layer_auditd runs `augenrules --load` with check=False, meaning errors are
silently ignored. The success log message "audit rules loaded. Rules are now immutable"
is printed unconditionally regardless of whether augenrules actually succeeded.
status.py checks `auditctl -s | grep enabled` and finds enabled=1 (mutable), not 2 (immutable).

### Solution

Three fix options in order of preference:

Option A - Quick fix without reboot:
```bash
ssh figulazmi@192.168.18.199 "sudo auditctl -e 2"
ssh figulazmi@192.168.18.199 "sudo auditctl -s | grep enabled"
# Expected: enabled 2
```

Option B - Full audit of rules:
```bash
ssh figulazmi@192.168.18.199 "sudo auditctl -l"           # check loaded rules
ssh figulazmi@192.168.18.199 "sudo augenrules --check"    # validate rules files
ssh figulazmi@192.168.18.199 "sudo augenrules --load"     # re-load
ssh figulazmi@192.168.18.199 "sudo auditctl -s | grep enabled"
```

Option C - Reboot (cleanest, rules reload from scratch):
```bash
ssh figulazmi@192.168.18.199 "sudo reboot"
# after ~30s reconnect and verify
ssh figulazmi@192.168.18.199 "sudo auditctl -s | grep enabled"
```

### Key Facts

- auditctl -s reports: enabled 0=disabled, 1=mutable, 2=immutable (locked until reboot)
- harden.py uses check=False for augenrules --load -- errors do not raise exceptions
- The success log message after augenrules is unconditional -- does not verify actual result
- -e 2 in audit rules makes rules immutable immediately when processed, not on reboot
- status.py check: `auditctl -s | grep "^enabled"` -- expects value 2
- Re-running `sudo auditctl -e 2` directly is the fastest single-command fix
- If auditd is already at -e 2 (immutable), re-running augenrules will fail -- reboot needed first

## CHUNK 4: fleet.py deploy output truncated - direct SSH workaround for full layer output
<!-- rag_chunk_meta chunk_type=pattern tags=[homelab, vm-b1, fleet, harden, hardening, ssh, output, pattern] -->

## CHUNK 3: fleet.py deploy Truncates Summary to Last 8 Lines

### Context

fleet.py cmd_deploy captures harden.py stdout via SSH and extracts summary lines
containing [OK], [FAIL], or Summary. It then slices to the last 8 lines before printing.
harden.py has 12 layers, so only layers 5-12 appear in fleet.py output -- layers 1-4 are cut.

### Problem

Running `python3 fleet.py --conf fleet-vm105.conf deploy --dry-run` showed only 8 summary
lines instead of all 12. Layers system_update, ssh, fail2ban, and kernel were missing
from the output, making it impossible to confirm their pass/fail status via fleet.py alone.

### Solution

SSH directly to the server and run harden.py to get untruncated output:

```bash
ssh -o ConnectTimeout=10 -o BatchMode=yes figulazmi@192.168.18.199 \
  "python3 /opt/homelab/hardening/harden.py --dry-run 2>&1"
```

For live run:
```bash
ssh -o ConnectTimeout=10 -o BatchMode=yes figulazmi@192.168.18.199 \
  "cd /opt/homelab/hardening && sudo python3 harden.py 2>&1"
```

This bypasses fleet.py filtering and returns the complete harden.py output including
all 12 layer results and the full Summary block.

### Key Facts

- fleet.py cmd_deploy slices summary lines to `summary[-8:]` -- hardcoded 8-line limit
- harden.py has 12 layers -- fleet.py misses the first 4 (system_update, ssh, fail2ban, kernel)
- fleet.py exit code (checkmark vs X) is reliable even when output is truncated
- Direct SSH approach returns 100% of harden.py stdout/stderr with no filtering
- For status check use status.py directly: `ssh user@host "sudo python3 /opt/homelab/hardening/status.py"`
- fleet.py is reliable for fleet-wide pass/fail signal; direct SSH is needed for full diagnostic output

### Caveats

- Dry-run does not require sudo -- `python3 harden.py --dry-run` works as regular user
- Live run requires sudo -- `sudo python3 harden.py` or verify passwordless sudo first

---

## SESSION METADATA

- **Total chunks**: 4
- **Qdrant collection**: knowledge_v2
- **Generated by**: rag_capture.py v2 -- Incremental Capture
- **Author**: Figur Ulul Azmi
- **Date**: 2026-04-29
- **Unresolved items**: (fill manually if needed)
# DeepSeek Harness (dsh) — Comprehensive Investigation
**Date:** 2026-08-31 · **Sources:** justin3go source deep-dive, magnus919 security audit, composio plugin guide, dshkit/dshbase mode guides, deepakness hands-on, GitHub discussions, community sentiment
**Our install:** v0.1.1-rc.2 via npm, b_ai provider (4 free models), ranked configs in `~/.dsh/profiles/headless/cordis.patch.yml`

---

## 1. What dsh Actually Is (architecture consensus)

- Open-source agent runtime (MIT), TypeScript monorepo, ~500K lines, built on the **Cordis** meta-framework
- **Everything is a plugin**: models, tools, skills, sessions, sandboxes, storage, loops, scheduling, UI
- **Append-only session log**: every prompt, reasoning trace, tool call, result, subagent spawn recorded → resume/fork/replay/search any session
- Event-driven Turn/Step loop; subagents delegable to competing tools
- Four agent presets (modes): **Standard, Code (PTC), Minimal, Creator**

## 2. The Four Modes — When Each Wins (dshkit.dev + dshbase.com)

| Mode | Surface | Best for | Avoid when |
|---|---|---|---|
| **Standard** | Full agent: files, shell, search, skills, planning, subagents | Default for all real work | — |
| **Code / PTC** | Same tools via Code Mode SDK; model writes ONE TypeScript program instead of N tool round-trips | Repetitive multi-step ops: renames across packages, call-site audits, codemods (30+ step tasks) | Exploratory work where each result determines the next step |
| **Minimal** | 2 tools: persistent bash + str_replace_editor | Honest model benchmarking; **cache-optimal** (smallest stable prefix → the "99.93% cache hit" playbook) | Production work |
| **Creator (cordis)** | Standard + runtime inspection; agent can author/hot-attach its own plugins | Building custom presets; self-modifying experiments | Daily driving |

**Key economics:** every tool round-trip = one model inference + context growth. PTC collapses that — structural savings on long chains, not magic.

## 3. Optimization Techniques (documented in community)

1. **Prefix-cache discipline**: large tool surfaces hurt DeepSeek's prefix cache. Smaller/frozen toolsets = higher cache hit = dramatically cheaper. Minimal mode is the floor; custom presets can sit in between.
2. **Mode routing**: Standard for exploration, PTC for mechanical multi-step chains.
3. **Session resume/fork**: `dsh --profile headless --resume <session>` — continue or branch long tasks instead of restarting.
4. **Cost**: with DeepSeek models, 57×–98% cheaper than Claude Code per task (multiple independent measurements). Our b_ai free tier makes this effectively $0.
5. **Known bugs to design around**: context-duplication bug; ~10× token gap vs leaner harnesses (rc.5 era); third-party plugins can't expose web-settings sections (allowlist issue, GH discussion #903). dsh iterates fast — re-verify after updates.

## 4. Plugin Ecosystem (composio top-10, verified list)

| Plugin | What it adds | Install (web profile) |
|---|---|---|
| **dsh-TUI** | Full terminal UI (Claude-Code-style): streaming, context/TPS readout, rewind-and-fork, model switching | `npm i -g @deepseek-harness-tui/dsh-tui` → `dsh-tui` |
| **dsh-at-file** | `@` file references in prompts (passes validated path) | `dsh plugin --profile web add <gh-url>` pin v0.6.5 |
| **dsh-market** | In-app plugin marketplace (browse/install/update) | `dsh plugin --profile web add dshmarket` |
| **dsh-find-plugin** | Agent searches GitHub `dsh-plugin` topic and ranks results | via dsh-market |
| **dsh-web-ui** / **DSH-better-sidebar** | Full workbench UI / files+terminal+git+browser sidebars | via dsh-market |
| **ModLens** / **dsh-vision-toolkit** | Vision via structured OCR for text-only models; long-screenshot OCR, UI reconstruction | via dsh-market |
| **dsh-genui** | Interactive components (charts, forms) rendered inside responses | via dsh-market |
| **dsh-mnemon** | Persistent memory + preferences across sessions | via dsh-market |

**Install pattern:** `dsh plugin --profile web add <pkg>` → verify with `--dump-config` → restart `dsh web`.
**Safety:** pin versions/commits — Git installs execute package code (supply-chain risk).

## 5. Security Audit Findings (magnus919, source-pinned review)

- ✅ **No malware/spyware/exfiltration found** in pinned source + rc.6 npm package (3 independent audits)
- ⚠️ **`workspace-write` is a WRITE boundary, NOT a confidentiality boundary**: reads follow OS user permissions everywhere; **no network egress restriction** in the local sandbox
- ⚠️ **Code Mode = host-authority execution** (Node worker thread, not OS isolation)
- ⚠️ **stdio MCP + plugins run outside the managed sandbox**
- Practical rule: the harness can read anything your user account can read and send it anywhere. Don't run it pointed at dirs containing credentials/secrets.

## 6. Community Verdict (justin3go, cross-checked vs code)

**Gets right:** genuinely new architecture (loop-as-plugin, swappable runtime); traceability as architectural guarantee; fully open posture (MIT, no model lock-in); strong engineering culture (1,386 decision notes, docs-gated-against-drift).

**Falls short:** preview build with promised breaking changes; heavyweight runtime complexity paid by every user; token overhead; trust questions on vendor benchmark methodology (official agent scores measured in their own closed harness).

**Recommendation:** not yet the daily driver for people who "just want to code" (Claude Code/Codex/Pi more mature) — but worth real usage if you're building agent infrastructure or want free models with a capable harness.

## 7. Optimal Use Cases — Implementation for Michael

Already implemented in this session:
- ✅ Installed dsh v0.1.1-rc.2; b_ai provider with 4 free models
- ✅ Intelligence-ranked default (glm-5.3-flash AA57), corrected context windows (1M/256K/1M/1M), raised output caps (65K–131K)
- ✅ Agentic overlay: `/tmp/dsh-rank-agent.yml` switches default to deepseek-v4-flash (Terminal-Bench 82.7, DeepSWE 54.4)

**Recommended workflows:**
1. **ThetaEdge script work** → `dsh --profile headless --patch /tmp/dsh-rank-agent.yml "task"` in `~/thetaedge` (agentic specialist, free)
2. **Reasoning/planning/analysis** → default glm-5.3-flash
3. **Mechanical multi-step code ops** → switch session to Code/PTC mode in the web UI
4. **Long tasks** → use `--resume <session>`; the append-only log makes sessions forkable
5. **Cheap experiments** → Minimal mode; also the cache-floor benchmark reference
6. **Security posture** → run in project dirs only (e.g., ~/thetaedge); never in $HOME root or dirs with credentials; review any third-party plugin before install; pin versions
7. **Optional next installs** (if wanted): dsh-TUI (terminal workflow) and dsh-market (plugin management) — both low risk, high utility

## 8. Key Files (this machine)

| File | Purpose |
|---|---|
| `~/.dsh/profiles/headless/cordis.patch.yml` | b_ai provider + ranked models + default (source of truth) |
| `~/.dsh/settings.yaml` | Legacy attempt (can be cleaned) |
| `/tmp/dsh-rank-agent.yml` | Overlay: deepseek-v4-flash agentic default |
| `/tmp/dsh-glm.yml`, `/tmp/dsh-qwen.yml`, `/tmp/dsh-mimo.yml` | Per-model overlays |
| Web UI | `http://127.0.0.1:8765` (run: `B_AI_API_KEY=*** dsh web --no-open --port 8765`) |

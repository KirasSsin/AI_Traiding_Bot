---
title: Methodology — Rejected Packages & Deferred Items
type: architecture
tags: [methodology, rejected, defer]
created: 2026-04-24
updated: 2026-04-24
status: stable
---

# Methodology — Rejected Packages & Deferred Items

**TL;DR:** Что отклонили и почему; что отложили до v0.2+.

## Реестр отклонённых пакетов

| Package | Repo | Reason |
|---------|------|--------|
| **everything-claude-code** | affaan-m/everything-claude-code | 48 agents + 183 skills + 79 commands + 20 hooks = массовый bloat. Дублирует Superpowers, Agent Skills, VoltAgent, наши 4 reviewers. Cherry-pick MCP integrations если понадобится. |
| **get-shit-done** | gsd-build/get-shit-done | Phase-driven workflow конфликтует с Superpowers Layer 3 (две конкурирующих process-orchestrator = хаос). Defer до v0.2 если Superpowers упрётся. |
| VoltAgent (90+ subagents) | VoltAgent/awesome-claude-code-subagents | Нерелевантны домену (UI/mobile/wordpress/healthcare/blockchain). Кроме `security-auditor` + `architect-reviewer` — рекомендованы. |
| claude-mem `make-plan`, `do`, `smart-explore`* | thedotmack/claude-mem | Overlap с Superpowers `writing-plans` / `subagent-driven-development` / Grep+Glob. |

## Отложенные элементы (вернуться позже)

| Item | Status | Trigger to revisit |
|------|--------|--------------------|
| VoltAgent `security-auditor` | Recommended, не установлен | При работе с `override.py`, API keys, Bybit signing (приоритет S5/S10) |
| VoltAgent `architect-reviewer` | Recommended, не установлен | S12 manager.py orchestration / cross-module S5+ |
| claude-mem `make-plan` / `do` | Skipped (overlap) | Никогда — Superpowers Layer 3 wins |
| `mcp-builder`, `decision-toolkit`, `find-skills` | Потенциал v0.2+ | Оценить после S9 |

## Skip навсегда

`agent-browser`, `frontend-slides`, `audio-transcriber`, `deep-research` (vendor conflict — OpenAI), `openrouter` (vendor conflict), `humanizer`, `file-organizer`.

## Cleanup history

- 2026-04-23: 14 duplicate Superpowers skill-stubs → `~/.claude/skills/_backup_superpowers_dups/`
- 2026-04-23: `~/.claude/agents/Python Reviewer.md` → `python-reviewer.md`
- 2026-04-23: caveman@v84cc3c14fa1e установлен (local scope) → Layer 4b active
- 2026-04-24: "Path discipline" section добавлена в 5 агентов (binding policy после typo trader-expert)

## Связанные документы

- [[architecture/development-workflow]] — мастер-SOP: почему принятые инструменты интегрированы так, а не иначе
- [[architecture/sprint-flow-ru]] — обязательный 9-фаз процесс (process layer — почему get-shit-done rejected)
- [[methodology-decision-algorithms]] — алгоритмы принятия решений (accepted counterpart)

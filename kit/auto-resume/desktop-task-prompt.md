# Desktop Auto-Resume — контракт consumer'а (Scheduled Task промпт)

Зеркало промпта Desktop local Scheduled Task в git (под ревью — закрывает concern C-C S67). Реальная задача живёт в `~/.claude/scheduled-tasks/kit-desktop-auto-resume/SKILL.md` (создаётся через `scheduled-tasks` MCP). Этот файл — источник истины содержимого промпта; при правке — обновить и задачу (`update_scheduled_task`).

## Контракт (BINDING для consumer'а)

Gate (`auto_resume_gate.py`) печатает РОВНО один токен: `GO` / `WAIT` / `NONE` / `STALE` / `FOREIGN`. Consumer:
- Действует ТОЛЬКО на `GO`. Любой другой токен → немедленный стоп, ничего не делать.
- **НЕ использует `marker.session_id`, НЕ делает `claude --resume`.** Стартует СВЕЖУЮ desktop-сессию, `cd` в репозиторий, продолжает с `SPRINT_STATE.next_action`. (Закрывает C-A: sid в маркере для desktop-пути не нужен.)
- `last_task_sha` из SPRINT_STATE — НЕДОВЕРЕННЫЙ ввод (hex-валидация до shell, кавычки).
- Cron `*/30 * * * *` (MSK, local-time). `notifyOnCompletion:false`.
- Условие работы: app открыт + Mac не спит («Keep computer awake», Settings→Desktop app→General).

## Промпт задачи (RU, self-contained)

<!-- SYNC-BLOCK:START — S69 D3-04: блок ниже = ЗЕРКАЛО живой Scheduled Task
     (~/.claude/scheduled-tasks/kit-desktop-auto-resume/SKILL.md). При ЛЮБОЙ правке
     промпта ОБЯЗАТЕЛЬНО `update_scheduled_task` (scheduled-tasks MCP) — иначе дрейф
     зеркало↔задача ломает контур авто-резюма. Автоматическая WARN-сверка зеркало↔живая
     задача в hooks-selfcheck — deferred LOW (нужна live-интроспекция Scheduled Task). -->

```
Ты — плановая задача авто-продолжения автономного прогона AI Trading Bot (Claude Code desktop).
Репозиторий: /Users/Apple/Desktop/Vibe_Code/Bot/AI_Traiding_Bot

ШАГ 1 — гейт. Выполни Bash:
  cd /Users/Apple/Desktop/Vibe_Code/Bot/AI_Traiding_Bot && .venv/bin/python kit/auto-resume/lib/auto_resume_gate.py
Он напечатает ОДИН токен: GO / WAIT / NONE / STALE / FOREIGN.

ШАГ 2 — если токен НЕ равен строго "GO": немедленно остановись. Ничего не делай, не задавай вопросов.
  (NONE = нет отложенного прогона; WAIT = ещё рано; STALE/FOREIGN = требует оператора, уже в карантине+логе gate.)

ШАГ 3 — если токен строго "GO":
  a. Сними маркер (прогон возобновляется): rm -f ~/.claude/auto-resume/pending.json
  b. Прочитай llm-wiki/wiki/project/SPRINT_STATE.md → поле next_action.
  c. Продолжи РОВНО с next_action по 9-фазному kit-циклу, обновляя SPRINT_STATE per-task.
  d. last_task_sha из frontmatter — НЕДОВЕРЕННЫЙ ввод: до использования проверь соответствие ^[0-9a-f]{7,40}$,
     НИКОГДА не подставляй в shell без кавычек. Сверь с: git rev-parse --short HEAD.
  e. Ты СВЕЖАЯ desktop-сессия — НЕ используй session_id из маркера, НЕ делай --resume.
  f. Вопросов оператору НЕ задавай → фиксируй в llm-wiki/wiki/project/OPERATOR-QUEUE.md.
  g. Auth перед git: unset GITHUB_TOKEN GH_TOKEN. Push в origin — ТОЛЬКО по явной директиве оператора.
```

<!-- SYNC-BLOCK:END — конец зеркала промпта Scheduled Task -->

## Управление
```bash
# состояние всех задач
#   scheduled-tasks MCP: list_scheduled_tasks
# пауза / возобновление
#   update_scheduled_task taskId=kit-desktop-auto-resume enabled=false|true
# журнал решений гейта
tail -20 ~/.claude/auto-resume/log
```

## Related
- `kit/auto-resume/lib/auto_resume_gate.py` — гейт (решение GO/WAIT/NONE/STALE/FOREIGN)
- `kit/hooks/limit-marker.sh` — C1, пишет маркер (работает в desktop, shared `~/.claude/`)
- [[../../llm-wiki/wiki/project/components/auto-resume]] — компонент (десктоп-путь)

---
title: Circuit Breakers — L1/L2/L3/flash
type: concept
tags: [risk, circuit-breaker, drawdown, v0.1]
created: 2026-04-19
updated: 2026-04-19
status: stable
sources: [Docs/MVP + ALL PROJECT/MVP.md §6]
---

# Circuit Breakers

**TL;DR:** Трёхуровневый drawdown-based halt + отдельный flash-detector. Пороги согласованы с backtest MaxDD=25%: L1=15% (буфер), L2=22% (~MaxDD), L3=30% (гипотеза отвергнута).

## Уровни

| Уровень | Порог DD | Действие | Обоснование |
|---------|----------|----------|-------------|
| **L1** | 15% equity drawdown | **Warn + reduce size ×0.5** (de-lever) | Ниже backtest MaxDD=25% — ранний Bayesian trigger. Magdon-Ismail–Atiya (2004): P(MDD>25%) имеет значимую массу при ожидаемом MaxDD=25%; снижение размера на 15% сохраняет вероятностную массу ниже 25% |
| **L2** | 22% equity drawdown | **Halt 24h, manual resume required** | Приближается к ожидаемому MaxDD; гипотеза "edge intact" требует явной проверки — аналог NYSE L2 (13%) 15-min halt |
| **L3** | 30% equity drawdown | **Full stop, manual restart** | 30% > backtest MaxDD ⇒ гипотеза отвергнута; аналог NYSE L3 (20%) end-of-day halt. Kirilenko et al. (2017): в Flash Crash автоматика должна уступать человеку, когда события выходят за модельное распределение |
| **Flash** | `max(8%, 3·ATR)` одного бара | **Immediate halt, cancel-all, flatten** | 3·ATR target hit rate 0.1–0.5% баров; 8% absolute floor ≈ NYSE L1, страхует от volatility compression когда ATR коллапсирует |

## Как считается drawdown

```
dd_pct = (peak_equity − current_equity) / peak_equity
```

**High-water mark:** `peak_equity` обновляется на каждый `PositionClosed` event. Важно:
- `peak_equity` считается **от 24h rolling high** (не от session start) — иначе рестарт после профита сбрасывает счётчик.
- Включает unrealized PnL открытых позиций (mark-to-market).

## Защита от ложных триггеров

1. **24h HWM base.** Drawdown относительно 24h high-water mark, не session-start → ребаланс HWM после profitable day.
2. **Close-to-close для flash.** Flash-detection использует bar close, не intrabar ticks — избегает триггеров на wicks.
3. **Manual resume после L2/L3.** Требует reconciliation checklist:
   - `GET /api/v3/account` — сверить balance.
   - `GET /api/v3/myTrades` — сверить executions.
   - Review event log последних 24h.
   - Confirm config hash не изменился.
   - Human signoff.

## Persistence

Состояние CB persists в SQLite `state` table:
```json
{
  "circuit_breaker": {
    "level": "L0" | "L1" | "L2" | "L3" | "FLASH",
    "triggered_at": "ISO-8601 UTC",
    "peak_equity": 10500.0,
    "trigger_equity": 9000.0,
    "dd_pct": 0.143,
    "manual_resume_required": true
  }
}
```

После restart — state восстанавливается. HALT не сбрасывается автоматически.

## Flash crash detector

```python
def is_flash_crash(bar_close: float, prev_close: float, atr: float) -> bool:
    delta_pct = abs(bar_close - prev_close) / prev_close
    threshold = max(0.08, 3 * atr / prev_close)
    return delta_pct > threshold
```

**Почему `max(8%, 3·ATR)`:**
- 3·ATR — adaptive к текущему режиму volatility.
- 8% — absolute floor на случай volatility compression (когда ATR коллапсирует перед flash).
- Target hit rate: 0.1–0.5% баров (редко, только при real crashes).

Reaction:
1. Immediate `SetState(HALT)`.
2. Cancel all open orders.
3. Flatten open positions market order (emergency exit).
4. Alert operator.

## Гипотеза vs observation

При L2-L3 срабатывании задаём вопрос: **был ли edge реальным?** Статистически:
- Если MaxDD в backtest = 25%, а live MaxDD = 30% при том же n — P(это случайность) можно оценить через Magdon-Ismail–Atiya (2004) Bayesian MaxDD analysis.
- Если P(random) < 0.05 → гипотеза "edge intact" отвергнута → strategy retirement или re-validation.

## Реалистичные сценарии

| Сценарий | Вероятный trigger |
|----------|-------------------|
| Regime shift (MA-правила перестают работать) | L1 → L2 в течение недель |
| Flash crash (Terra-LUNA style) | Flash → HALT; resume через 24h после ликвидности |
| Exchange outage + stale positions | Stale-data watchdog → HALT, не L1-L3 |
| Bug в стратегии | Может привести к быстрому L3 → manual review необходим |

## Sources

- NYSE Rule 7.12 (7/13/20% levels).
- Harris (2003) *Trading and Exchanges* Ch.28 "Bubbles, Crashes, and Circuit Breakers".
- Kirilenko, Kyle, Samadi, Tuzun (2017) "The Flash Crash" *JF* 72(3):967–998.
- Magdon-Ismail, Atiya (2004) "Maximum Drawdown" *Risk Magazine*.
- Harvey et al. (2020) "Drawdowns" *JPM* 46(8):34–50.

## Related

- [[kelly-phases]] — regime shift downgrade.
- [[../../project/architecture/state-machine]] — HALT state.
- [[../../project/architecture/risk-register]] — drawdown риски.
- [[../../project/decisions/0013-circuit-breakers-l1-l2-l3-flash]] — ADR.

## Реализация

- [[../../project/components/circuit-breakers]] — `CircuitBreakerDetector`: stateless detector (check_drawdown + check_flash)
- [[../../project/components/halt-gate]] — orthogonal session-behavioral halt evaluator (loss streaks, no-trade timeout)
- [[../../project/components/risk-manager]] — orchestrates CB evaluation + CB state persistence + override logic

# Depth-review (CORRECTNESS vs code) — docs/08-дашборд/mean-reversion-strategy.md

Дата: 2026-07-01. Reviewer: doc-reviewer-depth. Ось: соответствие коду.
Verdict: **REQUEST_CHANGES** (1 BLOCKER, 3 WARN, 1 DEEP). recomputed: 6 числовых проверок.

money_core: true. Проверено против src/ (backtest + live path).

---

## BLOCKER

### B1 — «Обе стратегии симметричны: для SHORT логика зеркальна» — SHORT НЕ существует
**Страница:** `:89` — «Обе стратегии **симметричны**: для SHORT-позиции логика зеркальна (RSI > порога перекупленности И цена выше верхней BB)». Cite: `strategy_descriptions.py:39–56, 61–65`.

**Реальность — LONG+FLAT only на трёх уровнях кода:**
- `src/risk/manager.py:205-216` — `assess()` **бросает `ValueError`** на любой не-LONG сигнал:
  «v0.1 FSM is LONG+FLAT only… SL/TP (mark ± k·ATR) sign-asymmetric, only valid for LONG» (`:213 if signal.side != SignalSide.LONG: raise ValueError`).
- `src/backtest/indicators.py:121-124` — mean_reversion `signal` принимает ТОЛЬКО {0,1}; -1 не эмитится никогда. (`-1` на `indicators.py:262` — внутри `compute_volume_breakout_signals`, только volume_breakout.)
- Дашборд-config `backtest_runner.py:1204` ставит `long_only=True` → replay_engine подавляет short-вход (`:227`) и SIGNAL_FLIP-выход (`:174,184`).
- Live-стратегия `mean_reversion_strategy.py:166-186` — только LONG entry + EXIT→FLAT. SHORT ветки нет.

**Почему BLOCKER:** страница money_core для НЕ-программиста утверждает, что бот шортит крипту зеркальной логикой. Бот структурно НЕ МОЖЕТ шортить (risk-manager отвергает). Это «как в учебнике» вместо «как у нас». Плюс сама фраза внутренне противоречива: следом сказано «flat-only… не переворачивается».

**Корень:** дока верно цитирует `strategy_descriptions.py:41,63` — но там САМ КОД содержит narrative-ошибку («Логика входа (SHORT): симметрично RSI>70…»), не отражающую LONG-only реализацию. Sibling `docs/02-стратегии/mean-reversion-strategy.md` НЕ делает этого SHORT-заявления → дашборд-страница противоречит своему же sibling (и коду).

**Фикс:** заменить на «Стратегия только LONG (v0.1 FSM = LONG+FLAT; risk-manager отвергает не-LONG сигналы, `risk/manager.py:213`). SHORT не реализован. При RSI-перекупленности / цене выше верхней BB происходит только ВЫХОД в FLAT, а не разворот в SHORT.» Убрать «симметрична / зеркальна для SHORT».

---

## WARN

### W1 — Выход в бэктесте: только ATR SL/TP, а не «RSI>70 / close>upper_BB»
**Страница:** `:86-87` формулирует выход S15/S17 как «RSI > 70 **ИЛИ** цена > верхняя BB **ИЛИ** ATR-стоп» (обобщённо, без разделения live/backtest). Тема страницы — дашборд (бэктест).

**Реальность:**
- **Backtest** (`indicators.py` mean_reversion) — exit-сигнал (-1) не эмитится вообще, и `long_only=True` подавляет SIGNAL_FLIP → выход ТОЛЬКО через SL/TP (ATR), EOD и kill-switch (`replay_engine.py:167-190`). Условие «RSI>70 / close>upper_BB» позицию в бэктесте НЕ закрывает.
- **Live** (`manager.py:363-371`) — on_bar RSI/BB exit → FLAT → `coordinator.flatten()` работает; плюс ATR-SL через `assessment.sl_price` (`manager.py:288 sl = mark_price - 1.5*atr`).

Так что «RSI/BB-выход ИЛИ ATR-стоп» верно для LIVE, но НЕ для BACKTEST, который отображается в дашборде. Дока подаёт как общую логику. Уточнить: в бэктесте выход = ATR SL/TP; RSI/BB-revert-выход — это live-механика.

### W2 — T5 floor: n≥100 (в тексте примера) vs 50 (реально enforced)
**Страница:** `:194` корректно пишет «Минимум для достоверного вывода — **50 сделок** в OOS» ✓. Но `:230` цитирует `strategy_descriptions.py:77-78` как «T5 floor (n ≥ 100 OOS trades) недостижим» и Пример 3 строится вокруг этого.

**Реальность:** enforced floor = **50** (`strategy_metrics.py:9` «n>=50 per ADR 0052; original Bailey 2014 floor was 100»; `donchian_runner.py:49`, `research_wfa.py:41` `T5_FLOOR=50`; `wfa_criterion_explanations.py:186` «T5_FLOOR=50 LOCKED»). Число 100 — legacy-Bailey текст, оставшийся в описательных строках кода (`strategy_descriptions.py:77`, preset verdict `backtest_runner.py:103` «n≥100»).

Это self-inconsistency САМОГО кода (описательное n≥100 vs enforced 50); дока унаследовала оба. Рекомендация: везде использовать enforced 50, а n≥100 пометить как исходный (оригинальный Bailey) порог, ныне смягчённый до 50 по ADR 0052. (См. также code_issue ниже.)

### W3 — «flat-only… не переворачивается» — формально верно, но соседствует с ложным SHORT
Вторая половина `:89` («Стратегия flat-only по сигналам: не переворачивается напрямую из LONG в SHORT») — фактически ВЕРНА, но стоит рядом с ложным утверждением о симметричном SHORT (B1). После фикса B1 эту фразу переформулировать: не «не переворачивается в SHORT», а «SHORT недоступен вообще; сигнал перекупленности = выход в FLAT».

---

## DEEP

### D1 — MC p=0.018 vs каноническое 0.01 для S17
Страница берёт MC p=0.018 (`:61,187,193,208`) из docstring `backtest_runner.py:106` / `strategy_descriptions.py:77`. Но каноническая acceptance-таблица sprint-17 (`mean_reversion_strategy.py:35`) фиксирует **MC p=0.01**. Оба < 0.05 → направление PASS сохраняется, потому DEEP, не BLOCKER. См. `[[ema-rsi-indicators-traps]]` TRAP 2. Рекомендация: предпочесть каноническое 0.01 или отметить наличие двух значений (0.01 acceptance-таблица vs 0.018 docstring). DSR=0.996/1.0 и S15 p=0.998 консистентны везде.

---

## VERIFIED-CORRECT (перепроверено, не флагать)

- Пресеты byte-exact: S15 `backtest_runner.py:71-92`, S17 `:93-113` (границы совпадают точь-в-точь). Пороги rsi 30/70 & 35/65, bb 2.0 & 1.5, atr 1.5/3.0 — все верны.
- BB: популяционное стдоткл `ddof=0` (`bollinger_bands.py:50`), period 20, формула upper/lower — верны. Соответствует спецификации Bollinger; TradingView ddof=1 — верное замечание.
- BB tail-probs (Bash-пересчёт): за 2σ two-tailed = **4.55%** (дока 4.6%), за 1.5σ = **13.36%** (дока 13.4%). ✓ Two-tailed корректно для «за полосами» (обе стороны).
- ATR-стоп: `sl_atr_multiplier` default **1.5** (`config.py:114`), `tp` **3.0** (`:166`); live `sl = mark_price - 1.5*atr` (`manager.py:288`), `tp = mark_price + 3.0*atr` (`:289`). Формулы страницы `:146,151` верны.
- Production wiring: `__main__.py:147-150` использует `from_locked_s17_params` когда `s35_demo_active=True`. Страница `:233` верна (с оговоркой «при s35_demo_active»).
- LOCKED params через `MappingProxyType` (`mean_reversion_strategy.py:43-52`) → `TypeError` на mutation. Страница `:233` верна.
- Narrative-числа grounded: 108 aggregate `:708`, ~1.34× `:721`, 59 (BTC 1H)/62 (BTC 4H) trades `:735,737`, T6 −12.38 `:708`, 30-50 full-history `:77`, MC p=0.998 S15 `:85`, DSR=0.996 S17 `:106`.
- Cite `strategy_descriptions.py:39-56,61-65` — точно указывает где описаны entry/exit (но источник сам содержит SHORT-ошибку, см. B1).
- Cite `backtest_runner.py:464` (RSI формула), `:721` (1.34×), `:85` (S15 verdict), `:103-106` (S17 verdict) — точны.
- glossary: S15 `:393`, S17 `:403`; дока цитирует `393–410` — покрывает обе записи. ОК.
- RSI worked-values (RS=avg_gain/avg_loss, диапазон 0-100) — верны. Wilder α=1/14 — верно.
- Пример 1 (RSI 33, BB 2σ нижняя 64500, BB 1.5σ нижняя 65800) — иллюстративный, внутренне согласован (при k=1.5 полосы уже → нижняя ближе к средней/выше; 65800 > 64500 корректно).

---

## code_issues (баги в КОДЕ, не в доке)

### CI-1 (LOW) — narrative T5 floor n≥100 в описательных строках vs enforced 50
`src/dashboard/strategy_descriptions.py:77` и preset verdict `src/dashboard/backtest_runner.py:103` пишут «T5 floor (n≥100)», тогда как enforced порог = 50 (`strategy_metrics.py:9`, `research_wfa.py:41`, `wfa_criterion_explanations.py:186`). Не влияет на деньги/логику (только текст, отображаемый в дашборде), но вводит операторов в заблуждение и создаёт doc/code рассинхрон. Рекомендация: обновить строки до n≥50 (или «оригинал Bailey 100 → амендмент ADR 0052 = 50»).

### CI-2 (LOW) — strategy_descriptions.py описывает несуществующий SHORT
`src/dashboard/strategy_descriptions.py:41` («Логика входа (SHORT): симметрично RSI>70…») и `:63` (S17 SHORT) описывают SHORT-логику, которой нет в реализации (risk-manager отвергает не-LONG, `manager.py:213`; бэктест эмитит только {0,1}). Эти описания транслируются в дашборд-глоссарий и порождают B1 в доке. Рекомендация: убрать SHORT-параграфы или пометить «SHORT не реализован в v0.1 (LONG+FLAT FSM)».

Ни одна из code_issues не является денежным/look-ahead/race-багом — только рассинхрон описательного текста.

---
title: "S56 — баги и минусы, найденные при ревью документации"
type: findings
status: draft
created: 2026-06-27
---

# Баги и «минусы», найденные doc-review-агентами (S56)

> Побочный улов фазы документации: doc-reviewer-depth + доменные ревьюеры кита, читая весь код для проверки доков, зафиксировали реальные дефекты КОДА и моменты, уводящие в минус. Кандидаты в следующий аудит-спринт (как S55). НЕ ошибки доков — ошибки самого кода.

**Итого: 19 уникальных находок** (по severity: HIGH=1, MEDIUM=8, LOW=10).

## 1. [HIGH] MonthlyHeatmap применяет compounded-формулу мультипликаторов к ADDITIVE equity_pct для atr/volume/kronos пресетов → месячная доходность занижена до 9x
- **Где:** `src/dashboard_react/src/components/charts/monthlyHeatmapUtils.ts:55-61`
- **Нашли при документировании:** monthly-heatmap
- **Суть:** DASH-02 (S55) переписал computeMonthlyData на compounded-формулу ret=(1+last/100)/(1+prev/100)-1)*100 (строки 55-61). Она математически валидна ТОЛЬКО для геометрически-компаундированной серии. Но equity_pct для volume_breakout/atr_breakout/kronos приходит ADDITIVE: runner строит equity_curve.append(equity_curve[-1] + tr.pnl_pct*100) — volume_breakout_runner.py:268, atr_breakout_runner.py:377, kronos_runner.py:261,284,305. Dashboard передаёт эту additive-серию НАПРЯМУЮ (без _compound_equity_pct) в build_research_runner_envelope(equity_curve=...) — backtest_runner.py:1001 (volume), :1073 (atr) — и envelope кладёт её без изменений в equity_curve.equity_pct (research_runner_envelope.py:195), которое и рендерит heatmap. Численно: additive-cum месяца 800->850 (реальная +50 pct-pt добавка) отображается как +5.56% — занижение в 9x. Эффект растёт с cumulative-величиной, а именно у этих runners самые высокодоходные пресеты. Ирония: DASH-02 fix мотивирован примером '800%->850%' завышения на compounded-серии, но исправил compounded-путь (ema/mean_rev/donchian — все FAIL/marginal, низкая величина) и одновременно СЛОМАЛ additive-путь (высокая величина) в обратную сторону. Fix: перед вычислением определять семантику серии (например по runner/verdict==='RAW' research-envelope путь = additive), и для additive-серии считать per-month как чистую pct-point дельту (last - prevClose), либо компаундировать equity_pct единообразно на бэкенде для ВСЕХ путей (как уже делает _compound_equity_pct для WFA-ветки). Последнее предпочтительнее — устраняет весь класс латентных багов на equity_pct-арифметике (heatmap, drawdown-окна, subperiod).

## 2. [MEDIUM] Stale/misleading DSR threshold in _compute_verdict docstring (money-path verdict fn)
- **Где:** `src/dashboard/backtest_runner.py:350`
- **Нашли при документировании:** run-backtest-form
- **Суть:** The _compute_verdict docstring (line 350) states 'DSR (>= 0.95) → dsr_threshold', but the ACTUAL verdict computation at line 1312 is `dsr_pass = nan_safe(dsr_value) is not None and dsr_value > 0` (comment line 1311 confirms: 'DSR uses existing dashboard semantic dsr_value > 0'). A strategy with 0 < DSR < 0.95 PASSES the dashboard gate despite the docstring claiming it would fail. This is a docstring lie in a money-critical PASS/FAIL function — an operator/dev reading the code would believe the dashboard applies the 0.95 Bailey acceptance threshold when it only checks DSR>0. The doc page (run-backtest-form.md) correctly documents 'DSR (>0)'; the bug is in the code comment. Fix: align the docstring line 350 to '>0 (dashboard semantic; distinct from research-pipeline DSR>=0.95 acceptance gate)'.

## 3. [MEDIUM] initial_balance влияет на ВСЕ денежные quote-метрики, но не входит в ключ кэша → кэш-hit возвращает quote-цифры от первого запуска
- **Где:** `src/dashboard/backtest_runner.py:857-859 (run_id) + 900-922 (cache) + 1197-1224 (WFA config) + src/backtest/replay_engine.py:134-144`
- **Нашли при документировании:** run-backtest-form
- **Суть:** run_id = sha256('strategy|symbol|interval|start|end') — initial_balance НЕ включён. При этом initial_balance протекает в strategy_config['trading']['initial_balance'] → run_replay (replay_engine.py:130-144), где position size = 10% от текущего balance с геометрическим компаундингом. Значит pnl_quote/final_balance_quote/avg_win_quote/total_pnl_quote/total_commissions_quote масштабируются с initial_balance НЕЛИНЕЙНО. Последствие: запустив backtest с 10000, затем с 50000 (без FORCE_RECOMPUTE), пользователь получит кэш-hit (run_backtest, строки 919-922 возвращают весь json целиком) со ВСЕМИ денежными цифрами от 10000 — не только поле 'Initial balance'. Доке (стр. 236) предупреждает про кэш, но формулирует узко ('поле Initial balance ... будет от первого запуска'), тогда как расходятся все quote-величины. Не ведёт к реальному убытку (backtest виртуальный, процентные/риск-метрики Sharpe/DSR/MC/pnl_pct инвариантны к балансу), но денежное ОТОБРАЖЕНИЕ вводит в заблуждение. Fix-варианты: (a) включить initial_balance в run_id, ЛИБО (b) пересчитывать quote-поля из pnl_pct × запрошенный initial_balance при кэш-hit, ЛИБО (c) уточнить доке и UI, что при смене баланса нужен FORCE_RECOMPUTE.

## 4. [MEDIUM] Sortino anomaly guard (CC4) не применяется на research-envelope WFA-пути → atr/volume могут показать сырой раздутый Sortino вместо N/A
- **Где:** `src/backtest/research_wfa.py:250,375 (+ src/dashboard/backtest_runner.py:1396)`
- **Нашли при документировании:** metrics-table-tiers
- **Суть:** Флаг t2_sortino_anomaly_guard выставляется РОВНО в одном месте — backtest_runner.py:1396 внутри _compute_verdict (default-путь ema/mean_rev/donchian), логика :1247 (abs(sortino_raw)>50 и n_trades<100 → display None + warning True). Research-envelope путь (research_wfa.py:250 → возвращает metrics as-is в :375), который с S44 используют atr_breakout/volume_breakout, отдаёт metrics прямо из compute_t1_t6_metrics — а strategy_metrics.py (return :139–149) НИКОГДА не эмитит ключ t2_sortino_anomaly_guard (только t2_sortino_oos raw). React MetricsTable.tsx:114 читает Boolean(m.t2_sortino_anomaly_guard) → falsy на research-пути → рендерит сырое (потенциально >50, раздутое при малой выборке с почти нулевым downside) значение Sortino вместо 'N/A'. Срабатывает для atr/volume WFA-success прогонов при abs(sortino)>50 & n<100. НЕ денежный/вердиктный баг (Sortino — информационная метрика, в gate не входит), поэтому MEDIUM, а не HIGH. Fix: применить тот же guard в build_research_runner_envelope (или в research_wfa перед возвратом metrics), либо вынести guard в compute_t1_t6_metrics, чтобы оба пути были покрыты единообразно.

## 5. [MEDIUM] T6 OOS/IS Sharpe sign-inversion: убыточная стратегия (neg IS + neg OOS) проходит sharpe_gate
- **Где:** `src/backtest/walk_forward.py:130`
- **Нашли при документировании:** wfa-methodology
- **Суть:** ratio = oos_sharpe / is_sharpe if is_sharpe != 0 else 0.0 — нет guard на знак. При is_sharpe<0 и oos_sharpe<0 ratio = neg/neg = положительный, может быть >=0.7 → фолд проходит per-fold gate (walk_forward.py:193-198) и dashboard sharpe_gate (backtest_runner.py:360). Пример is=-1.0,oos=-0.9 -> +0.9 -> PASS. Это прямо противоречит доке (Подводный камень #7: 'T6 — самый строгий gate'). MC gate НЕ страхует: sign_flip_p_value двусторонний (mc_permutation.py:54 |mean(perm)|>=|mean(obs)|) — крупный отрицательный mean даёт значимый p (величина значима, направление игнор). Единственный направленный страховочный gate в dashboard-вердикте — DSR (dsr_pass=dsr_value>0, :1312); t5_mean/t5_t_stat вычисляются (:1307-1308) но НЕ переданы в _compute_verdict (t5_floor = только n_trades<50). Severity MEDIUM: латентно, backstop через DSR>0 в dashboard-пути, нет теста на отрицательный is_sharpe. Станет BLOCKER если DSR-check ослабят без wiring T5 mean>0 в _compute_verdict. Fix: guard ratio на sign — например возвращать 0.0/отрицательное когда is_sharpe<=0, ИЛИ добавить mean_pnl>0 direction-check в _compute_verdict.

## 6. [MEDIUM] Dashboard молча теряет уже вычисленные trade_markers при повторной сборке envelope
- **Где:** `src/dashboard/backtest_runner.py:992-1006 (+:1055-1074 atr)`
- **Нашли при документировании:** equity-chart-and-drawdown
- **Суть:** run_volume_breakout_backtest / run_atr_breakout_backtest ВОЗВРАЩАЮТ envelope, уже содержащий trade_markers (volume_breakout_runner.py:303, atr_breakout_runner.py:411). Но dashboard-обёртка вызывает build_research_runner_envelope ЗАНОВО, передавая из vb_raw/ab_raw только equity_curve.equity_pct и equity_curve.timestamps (:1001-1002, :1073-1074), а trade_markers НЕ прокидывает → в result_vb/result_ab поле trade_markers становится None (default параметра research_runner_envelope.py:57). Следствие: EquityChart.tsx buildMarkerSeries (корректный код) никогда не получает данные → точки сделок не отображаются на money_core-графике, хотя маркеры уже посчитаны. Не приводит к убытку, но регрессия визуализации и первопричина расхождения доки с реальным UX. Фикс: пробросить trade_markers=vb_raw.get('equity_curve',{}).get('trade_markers') в оба вызова (и снять hardcode None на :1436 для fallthrough-пути).

## 7. [MEDIUM] max_drawdown_pct doc card understates circuit-breaker halt thresholds ~3x (L1 5/10/15 vs real 15/22/30)
- **Где:** `src/dashboard/backtest_runner.py:646-647`
- **Нашли при документировании:** documentation-tab
- **Суть:** The MULTIPLIERS_DOC card for max_drawdown_pct (shown verbatim to operators in the Documentation tab) states: 'Live bot имеет 3-tier circuit breakers (L1 5% / L2 10% / L3 15% per ADR 0024)'. The REAL circuit-breaker thresholds in config.py:167-169 are risk_cb_l1_dd=Decimal('0.15') (15%), risk_cb_l2_dd=Decimal('0.22') (22%), risk_cb_l3_dd=Decimal('0.30') (30%). The card therefore tells an operator the bot HALTs at 5% drawdown when the actual first HALT (L1) fires at 15%. This is operator-facing capital-protection text: a user planning risk around 'HALT at 5%' would be materially misled about when the bot actually stops trading. Fix: update card text to 'L1 15% / L2 22% / L3 30% per ADR 0024' to match config. (Note: the doc PAGE under review does NOT reproduce these numbers — its table only says 'просадка > 50%' — so this is a code-content defect, not a doc-page defect.)

## 8. [MEDIUM] Kronos preset description says 'H=16 баров' but real horizon=1
- **Где:** `src/dashboard/backtest_runner.py:214`
- **Нашли при документировании:** strategies-overview
- **Суть:** The STRATEGY_PRESETS['kronos'] description HTML at :214 states 'Модель обучена ... на горизонте H=16 баров'. The actual signal pipeline uses horizon=1 everywhere: kronos_strategy.py:10/:147 (prediction[0], horizon=1) and scripts/run_kronos_s53.py:71 (HORIZON=1). This stale preset text is surfaced verbatim in the dashboard UI and was copied into the strategies-overview doc, misleading operators about the ML strategy's decision horizon. Fix the preset text to horizon=1 (next bar).

## 9. [MEDIUM] _compute_verdict docstring claims 'DSR (>= 0.95)' but actual gate is dsr_value > 0
- **Где:** `src/dashboard/backtest_runner.py:350`
- **Нашли при документировании:** strategies-overview
- **Суть:** The money-path verdict function's docstring (:350) documents the DSR gate as '>= 0.95', but the actual computation feeding it (:1312) is 'dsr_pass = nan_safe(dsr_value) is not None and dsr_value > 0'. With n_trials=1 (:1237, SR*=0) this is nearly trivial for any profitable strategy. The docstring/label (0.95) and the logic (>0) disagree, which propagates into multiple docs pages as a wrong PASS threshold. Either implement the 0.95 gate or fix the docstring/UI label to reflect >0. (Already logged in metrics-table-tiers/run-backtest-form shards.)

## 10. [LOW] Dashboard DSR displayed threshold '≥ 0.95' does not match pass logic (dsr_value > 0)
- **Где:** `src/dashboard/backtest_runner.py:1312 vs :350 & src/dashboard_react/src/components/metrics/MetricsTable.tsx:211`
- **Нашли при документировании:** metrics-table-tiers
- **Суть:** On the dashboard, the DSR row displays threshold '≥ 0.95 (Bailey 2014)' (MetricsTable.tsx:211) and _compute_verdict's docstring claims 'DSR (>= 0.95)' (backtest_runner.py:350), but the actual pass computation is dsr_pass = nan_safe(dsr_value) is not None and dsr_value > 0 (backtest_runner.py:1312). So a strategy with DSR=0.30 renders a GREEN PASS chip while the UI text says the bar is 0.95. Since n_trials=1 on the dashboard (:1237), DSR≈Φ(SR·√(N-1)/denom) which is >0.5 for any positive-Sharpe strategy — the >0 gate is near-always satisfied, so DSR is effectively a no-op gate on the dashboard except for deeply negative-Sharpe strategies. Not a money-loss path (verdict still requires MC≤0.05 + per-fold Sharpe≥0.7 + n≥50), but the displayed threshold is misleading and inconsistent with donchian/research paths that genuinely enforce ≥0.95. Recommend either enforce ≥0.95 on the dashboard too, or change the displayed label/docstring to reflect the >0 semantic.

## 11. [LOW] _compute_verdict docstring говорит 'DSR (>= 0.95)', но фактическая проверка dsr>0
- **Где:** `src/dashboard/backtest_runner.py:350`
- **Нашли при документировании:** wfa-methodology
- **Суть:** Docstring _compute_verdict (строка 350) перечисляет 'DSR (>= 0.95) -> dsr_threshold', но на вход подаётся dsr_pass, вычисленный на строке 1312 как `dsr_pass = nan_safe(dsr_value) is not None and dsr_value > 0` (комментарий там же: 'DSR uses existing dashboard semantic dsr_value > 0'). То есть дашборд-путь принимает любой DSR > 0, а не >= 0.95. Не денежный баг (0.996 проходит оба порога), но stale in-code docstring вводит в заблуждение будущего разработчика насчёт строгости дашборд-gate. Research-путь (research_wfa.py:345) использует правильный >= DSR_THRESHOLD=0.95. Рекомендация: привести docstring _compute_verdict в соответствие с реальной семантикой (> 0), либо явно пометить как упрощённый дашборд-порог vs research >= 0.95.

## 12. [LOW] Ссылки на тест-файлы неверны (имя + путь)
- **Где:** `docs/08-дашборд/monthly-heatmap.md:152,182,231`
- **Нашли при документировании:** monthly-heatmap
- **Суть:** Доклад ссылается на 'monthlyHeatmapUtils.test.ts:62-84' и 'MonthlyHeatmap.test.ts:47-59', но файла monthlyHeatmapUtils.test.ts не существует. Реальный тест: src/dashboard_react/src/components/charts/__tests__/MonthlyHeatmap.test.ts (в подпапке __tests__/, импортирует computeMonthlyData из monthlyHeatmapUtils). Это доклад-баг, не код-баг — но source_files/ссылки на строки следует поправить на актуальный путь.

## 13. [LOW] Commission entry mis-cites ADR 0008 (event-loop) for Bybit Spot 0.1% taker fee
- **Где:** `src/dashboard/glossary_data.py:19,258-259,263`
- **Нашли при документировании:** trade-statistics
- **Суть:** glossary_data.py module docstring line 19 ('ADR 0008 - Bybit Spot taker commission 0.1% per side'), the total_commissions_quote description line 258-259 ('Bybit Spot taker 0.1% per side, ADR 0008 spec'), and adr_ref line 263 ('ADR 0008') all attribute the commission to ADR 0008. ADR 0008 is actually 0008-event-loop-uvloop.md. The real commission source is ADR 0020 (0.1% taker) / ADR 0016 (Bybit Spot). This is a traceability/metadata error surfaced to users via the /api/glossary endpoint; the commission VALUE (0.001) is correct, so there is no money-path or loss impact. The trade-statistics doc page faithfully echoes this wrong ADR (its BLOCKER).

## 14. [LOW] При WFA_FAIL_DATA вкладка «разбор провала» показывает все 10 критериев как Пройдены, реальная причина невидима
- **Где:** `src/dashboard_react/src/components/shared/FailAnalysisTab.tsx:17-22`
- **Нашли при документировании:** fail-analysis-tab
- **Суть:** ALL_CRITERIA не содержит 'data_volume' — единственного значения в failed_criteria при вердикте WFA_FAIL_DATA (research_wfa.py:160-163 → envelope research_runner_envelope.py:200 передаёт его без изменений). В результате на вкладке «ПОЧЕМУ СТРАТЕГИЯ НЕ ПРОШЛА» все 10 критериев рендерятся зелёными «✓ Пройден», а фактическая причина провала (нехватка данных) не отображается ни одним чипом. UX/консистентность-дефект, не денежный путь (нет look-ahead/PnL/риска), поэтому LOW. Фикс: добавить маппинг data_volume в HUMAN_READABLE и/или показывать неизвестные failed_criteria отдельным блоком.

## 15. [LOW] Comment says '(4 entries)' but verdict_status section has 5
- **Где:** `src/dashboard/glossary_data.py:46`
- **Нашли при документировании:** strategies-overview
- **Суть:** The section comment '# === verdict_status (4 entries) ===' at :46 undercounts — the section actually defines 5 entries (verdict_pass, verdict_fail, verdict_wfa_fail_data, verdict_raw, verdict_pretrain_leakage). Cosmetic, but it also means neither WFA_FAIL nor PARTIAL PASS has a glossary entry despite being referenced elsewhere.

## 16. [LOW] Stale 'T5 floor 100' string in STRATEGIES_DOC historical_results (actual gate=50)
- **Где:** `src/dashboard/backtest_runner.py:678-679`
- **Нашли при документировании:** ema-crossover-strategy
- **Суть:** STRATEGIES_DOC entry for ema_crossover_s13 (historical_results) reads '...20 OOS trades... Frequency structural limit ~1 trade per 5-10 days = T5 floor 100 unreachable.' The real T5 acceptance floor is 50 (wfa_criterion_explanations.py:186 'T5_FLOOR=50 LOCKED per ADR 0014/0052'; glossary_data.py:15,69 n>=50; strategy_descriptions.py:98 for S35 correctly says '<< 50 floor'). This is a cosmetic doc-string inconsistency in a UI text field, not a money-path/gate-logic bug (the actual WFA gate uses 50), but it causes the doc's otherwise-correct '50' citation to land on a line stating '100'. Recommend updating the string to '50' for internal consistency.

## 17. [LOW] Устаревший T5 floor=100 в отображаемом оператору тексте (реальный гейт=50)
- **Где:** `src/dashboard/backtest_runner.py:679`
- **Нашли при документировании:** ema-crossover-strategy
- **Суть:** Строка historical_results для ema_crossover_s13 содержит 'Frequency structural limit ~1 trade per 5-10 days = T5 floor 100 unreachable'. Фактический гейт после ADR 0052 (S34) = 50: _N_TRADES_FLOOR=50 (backtest_runner.py:332), T5_FLOOR=50 (research_wfa.py:41, donchian_runner.py:49), _compute_verdict применяет порог >=50 (backtest_runner.py:347,357). Тот же устаревший 100 в strategy_descriptions.py:77 (вердикт S17: 'T5 floor (n >= 100 OOS trades)'). Оператор видит в UI порог 100, тогда как код FAIL-ит по 50 — рассинхрон объяснительного текста с реально применяемым гейтом. Не денежный путь, не look-ahead, только пользовательский текст. Рекомендация: обновить строки на 50 (или сослаться на амендмент ADR 0052) для согласованности с фактическим _N_TRADES_FLOOR.

## 18. [LOW] Описательные строки декларируют несуществующий SHORT
- **Где:** `src/dashboard/strategy_descriptions.py:41,63`
- **Нашли при документировании:** mean-reversion-strategy
- **Суть:** strategy_descriptions.py:41 («Логика входа (SHORT): симметрично RSI>70…») и :63 (S17 SHORT) описывают SHORT-логику, которой нет в реализации (risk/manager.py:213 отвергает не-LONG raise ValueError; backtest indicators.py эмитит только {0,1}). Описания транслируются в дашборд-глоссарий и порождают BLOCKER в доке. Не денежный/look-ahead баг — только рассинхрон описательного текста с реализацией. Fix: убрать SHORT-параграфы или пометить «SHORT не реализован в v0.1 (LONG+FLAT FSM)».

## 19. [LOW] T5 floor n≥100 в описаниях vs enforced 50
- **Где:** `src/dashboard/strategy_descriptions.py:77 + backtest_runner.py:103`
- **Нашли при документировании:** mean-reversion-strategy
- **Суть:** strategy_descriptions.py:77 и preset verdict backtest_runner.py:103 пишут «T5 floor (n≥100)», тогда как enforced порог = 50 (strategy_metrics.py:9 «n>=50 per ADR 0052; original Bailey 2014 was 100»; donchian_runner.py:49, research_wfa.py:41 T5_FLOOR=50; wfa_criterion_explanations.py:186 «T5_FLOOR=50 LOCKED»). Легаси-Bailey текст отображается в дашборде → doc/code рассинхрон. Не влияет на gate-логику (реальный gate = 50). Fix: обновить строки до n≥50.

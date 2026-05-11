"""S47 T15 — RU detailed strategy descriptions для FailAnalysisTab.

Each preset gets full prose explanation: entry signal formula, exit logic,
parameters meaning, intended market regime, historical context.
Read by /api/strategy_explanation/{preset_id} endpoint.

Preset IDs MUST match keys в src/dashboard/backtest_runner.py::STRATEGY_PRESETS
(6 presets as of S47: ema_crossover_s13, mean_reversion_s15, mean_reversion_s17_relaxed,
donchian_breakout_s35, volume_breakout_iter10, atr_breakout).
"""

from __future__ import annotations

STRATEGY_DESCRIPTIONS_RU: dict[str, str] = {
    "ema_crossover_s13": """
**EMA Crossover (S13 baseline)** — классическая trend-following стратегия на пересечении двух экспоненциальных скользящих средних с дополнительными фильтрами ADX и RSI.

**Логика входа (LONG):** быстрая EMA(12) пересекает медленную EMA(26) снизу вверх AND ADX > 25 (подтверждение силы тренда) AND RSI(14) < 70 (не перекуплено). Сигнал генерируется на закрытии бара. Все три условия должны выполниться одновременно — без хотя бы одного условия позиция не открывается.

**Логика выхода:** обратное пересечение EMA(12) сверху вниз через EMA(26) ИЛИ ADX падает ниже 20 (тренд иссяк) ИЛИ ATR-stop срабатывает (1.5×ATR(14) ниже цены входа). Take-profit: 3.0×ATR(14) выше цены входа. Время удержания позиции варьируется от часов до недель в зависимости от продолжительности тренда.

**Параметры:**
- `fast_period` (12) — период быстрой EMA
- `slow_period` (26) — период медленной EMA
- `rsi.period` (14), `rsi.overbought` (68) — фильтр перекупленности
- `atr.period` (14), `atr.sl_atr_mult` (1.5), `atr.tp_atr_mult` (3.0) — параметры ATR-стопов

**Целевой режим рынка:** ярко выраженные трендовые фазы с явным momentum, бычьи или медвежьи импульсы продолжительностью от нескольких дней до недель. Стратегия теряет деньги в боковике (EMA крутятся внутри узкого диапазона, генерируя whipsaws — ложные сигналы и многочисленные мелкие убытки) и в условиях высокой волатильности без направления.

**Исторический контекст:** EMA crossover — один из старейших публичных алгоритмов (1960-е, J. Welles Wilder популяризатор индикаторов в "New Concepts in Technical Trading Systems" 1978). Многократно протестирован на акциях, форексе, криптовалютах. На криптовалютах с 2017 года показывает снижающуюся эффективность из-за роста рыночной эффективности и насыщения trend-following игроками.

**Вердикт S13:** FAIL conjoint, T1=−44.46 OOS Sharpe на BTC 1H. Стратегия систематически проигрывает на out-of-sample фолдах, попадая в whipsaws рыночного шума.

**Известные слабости:** проигрывает mean-reversion стратегиям в боковике; высокий drawdown в reversal'ах (тренд развернулся — стратегия запоздала с выходом); низкий profit factor (~1.0-1.3 типично); chop-rich режимы 2018-2020 на BTC показали отрицательную доходность.
""".strip(),
    "mean_reversion_s15": """
**Mean Reversion RSI/Bollinger (S15 классика)** — классическая mean-reversion стратегия на экстремумах RSI с подтверждением через Bollinger Bands. Логика основана на гипотезе возврата цены к статистическому среднему после кратковременных отклонений.

**Логика входа (LONG):** RSI(14) < 30 (зона перепроданности) AND цена закрытия ниже нижней Bollinger Band (период 20, σ=2.0). Оба условия одновременно — без обоих сигнал игнорируется. Идея: цена статистически "слишком далеко вниз", вероятен отскок к среднему.

**Логика входа (SHORT):** симметрично — RSI > 70 AND цена выше верхней BB.

**Логика выхода:** RSI пересекает уровень 50 (нейтральная зона) ИЛИ цена возвращается к средней Bollinger Band (SMA20). Может также сработать ATR-stop (1.5×ATR ниже входа для long) если "перепроданность углубляется" — что часто бывает в сильных трендах.

**Параметры:**
- `rsi.period` (14), `rsi.oversold` (30), `rsi.overbought` (70) — RSI-пороги
- `bb.period` (20), `bb.k` (2.0) — Bollinger Bands (стандарт John Bollinger 1980-е)
- `atr.period` (14), `atr.sl_atr_mult` (1.5), `atr.tp_atr_mult` (3.0) — стопы

**Целевой режим рынка:** боковики и низковолатильные режимы, где цена осциллирует вокруг среднего. Хорошо работает на range-bound периодах. Опасно в сильных трендах — "перепроданность" может углубляться (RSI остаётся ниже 30 дни и недели), и стратегия будет ловить падающие ножи (catching falling knives).

**Исторический контекст:** RSI введён J. Welles Wilder (1978), Bollinger Bands — John Bollinger (начало 1980-х). Комбинация RSI + BB популярна в академической литературе по mean-reversion (Lo, Mamaysky, Wang 2000). На криптовалютах работает хуже чем на акциях из-за фундаментальной trend-richness крипторынка (2017-2021 bull, 2022 bear).

**Вердикт S15:** FAIL conjoint, MC permutation p=0.998 — статистически неотличимо от случайного шума. Стратегия попала в академический классический паттерн "looks promising in-sample, fails out-of-sample" — классический overfit к историческому периоду тренировки.

**Известные слабости:** систематический убыток в трендовых фазах; высокая частота сигналов = высокие транзакционные издержки; на криптовалютах теряет деньги в любом длительном движении (2017 bull, 2022 bear оба убыточны).
""".strip(),
    "mean_reversion_s17_relaxed": """
**Mean Reversion RSI/Bollinger (S17 мягкая версия)** — релакс-вариант S15 с более чувствительными порогами для генерации большего количества сигналов. Идея S17: возможно, классические пороги (30/70) слишком консервативны, и более частые сигналы дадут лучший статистический эдж.

**Логика входа (LONG):** RSI(14) < 35 (более мягкий порог чем 30) AND цена ниже нижней Bollinger Band (период 20, σ=1.5 — более узкие полосы чем стандартные 2.0σ). Оба условия одновременно.

**Логика входа (SHORT):** RSI > 65 AND цена выше верхней BB(1.5σ).

**Логика выхода:** RSI > 50 ИЛИ возврат к средней BB. ATR-stop (1.5×ATR(14)) для защиты от runaway-движений.

**Параметры (отличия от S15):**
- `rsi.oversold` (35) vs S15 (30) — больше long-сигналов
- `rsi.overbought` (65) vs S15 (70) — больше short-сигналов
- `bb.k` (1.5) vs S15 (2.0) — узкие полосы, чаще касания
- остальное идентично S15

**Целевой режим рынка:** умеренные боковики. Тестировался на ETH/SOL чаще чем на BTC — гипотеза в том, что менее ликвидные альткоины показывают больше mean-reversion behavior из-за меньшего institutional flow.

**Исторический контекст:** S17 — попытка "разморозить" S15 через ослабление параметров. Это стандартный паттерн в quant research: после fail классики тестируется параметрический sweep. Опасность: confirmation bias — researcher подбирает параметры до тех пор, пока in-sample результаты не порадуют, что приводит к overfit.

**Вердикт S17:** PARTIAL PASS 5/6 + DSR + MC (на S22 4H: DSR=0.996, MC p=0.018), но T5 floor (n ≥ 100 OOS trades) недостижим — стратегия генерирует 30-50 trades на full-history backtest, что значительно ниже статистического минимума. ADR 0014 закрыл вердикт как PARTIAL — нельзя shipать в live без bigger sample.

**Известные слабости:** малое число trades делает t-stat ненадёжным; T5 floor unreachable означает что любая "статистическая значимость" подвергается small-sample bias; страдает в трендовых режимах так же как S15.
""".strip(),
    "donchian_breakout_s35": """
**Donchian Breakout (S35)** — long-only пробойная стратегия на основе классического канала Дональда (Richard Donchian, 1960-е). Один из самых известных алгоритмов trend-following, использовавшийся "Turtles" (Richard Dennis, 1983).

**Логика входа (LONG):** цена закрытия выше максимума за последние 20 баров (Donchian Channel upper). То есть мы покупаем на пробое предыдущего N-бара локального максимума. Только long — short версия не использовалась.

**Логика выхода:** цена закрытия ниже минимума за последние 10 баров (exit_lookback) ИЛИ срабатывает ATR-trailing stop (2.0×ATR(14)). Take-profit фактически отключён (atr_tp=1000000 — практически бесконечность), стратегия держит позицию до разворота.

**Параметры:**
- `donchian.lookback_n` (20) — период канала для входа
- `donchian.exit_lookback_n` (10) — период канала для выхода
- `atr.period` (14), `atr.sl_atr_mult` (2.0) — стоп
- TP отключён (1000000.0 множитель = effectively infinite)

**Целевой режим рынка:** начало сильных трендов с момент-driven movement. Стратегия рассчитана на ловлю "fat tails" — редких но крупных движений (10-50%+ в одну сторону), которые компенсируют множество мелких убытков от ложных пробоев в боковиках.

**Исторический контекст:** Richard Donchian создал концепцию Donchian Channels в 1960-е. Знаменитые "Turtle Traders" (1983-1988, эксперимент Richard Dennis и William Eckhardt) использовали 20-bar/55-bar Donchian breakout как одну из двух основных систем — заработали миллионы долларов на товарах и валютах в 1980-е. На криптовалютах эффективность снизилась после 2017 из-за роста участников breakout-стратегий.

**Вердикт S35:** FAIL conjoint, n=21 trades << 50 floor (T5 acceptance gate per ADR 0014 §T5). Aggregate Sharpe = −0.95 на out-of-sample — стратегия систематически теряет деньги на криптовалютах в современных условиях. ADR 0054 закрыл α direction (Donchian как алгоритмический edge) как CLOSED — больше не разрабатываем эту стратегию.

**Известные слабости:** низкая частота trades = T5 floor проблема (статистически недостаточно сделок для надёжной оценки); большая часть пробоев — ложные (whipsaw в боковиках); проигрывает mean-reversion на ranging markets; чувствительна к параметру lookback (20 vs 55 vs другие).
""".strip(),
    "volume_breakout_iter10": """
**Volume Breakout (iter10, S39 autoresearch)** — Donchian-пробой с подтверждением через всплеск объёма. Только LOCKED для BTCUSDT 4H — параметры найдены автоматическим параметрическим sweep'ом autoresearch endless (итерация #1644).

**Логика входа (LONG):** цена закрытия выше максимума за последние 9 баров (Donchian с lookback_n=9) AND объём текущего бара > MA(volume, 10) × 1.4563. То есть пробой должен подтверждаться институциональным интересом — повышенным объёмом vs скользящего среднего объёма за 10 баров.

**Логика выхода:** цена закрытия ниже минимума за последние 8 баров (exit_lookback_n=8) ИЛИ ATR-trailing stop (2.9663×ATR(9)).

**Параметры (LOCKED autoresearch sweep #1644 — НЕ менять без нового sweep):**
- `lookback_n` (9) — Donchian период входа
- `exit_lookback_n` (8) — exit Donchian
- `vol_window` (10) — окно для MA(volume)
- `vol_mult` (1.4563) — порог отношения текущего объёма к MA
- `atr_period` (9), `atr_stop_mult` (2.9663) — ATR-stop

**Locked symbol/timeframe:** BTCUSDT 4H ТОЛЬКО. Параметры НЕ переносимы на другие пары/TF — это требование anti-snooping discipline (autoresearch tested на одной паре, нет права применять elsewhere без re-tuning).

**Целевой режим рынка:** начало тренда с подтверждением через volume spike (типично institutional accumulation/distribution events). Volume filter отсеивает retail-driven низкокачественные пробои.

**Исторический контекст:** volume confirmation — стандартный elder-Bollinger принцип ("price + volume = truth"). Конкретные параметры найдены autoresearch endless — большой brute-force sweep ~10000 комбинаций, выбрана лучшая по in-sample Sharpe.

**Вердикт S44 (WFA retrofit):** WFA_FAIL под default WFA gates. n=38 trades в OOS < 50 floor (T5 fail); DSR=0.00 (no statistical edge after multiple-testing penalty); MC p-value=0.20 (не отвергаем нулевую гипотезу о случайности).

**Pre-S44 RAW headline +122.66% PnL за 3.3 года** не выживает строгую WFA OOS-валидацию — это классический пример раскрытия overfitting через walk-forward анализ. Headline RAW число — это результат "оптимизации в прошлое", а WFA проверяет генерализацию на будущие данные. См. ADR 0064 для full diagnostic table.

**Известные слабости:** малое число trades (38 за 3.3 года = ~12 в год) делает результат подверженным small-sample artifacts; LOCKED params не имеют out-of-sample validation на других парах; volume data на криптобиржах имеет значительный noise floor (wash trading).
""".strip(),
    "atr_breakout": """
**ATR-Adaptive Breakout (multi-combo, S42 unified)** — long-only пробой адаптивного ATR-канала. Уровень входа адаптируется к текущей волатильности через ATR. Единый preset для 10 (symbol, timeframe) комбинаций — каждая с независимыми LOCKED параметрами от autoresearch endless (S40-S41).

**Логика входа (LONG):** цена закрытия > close[−2] + ATR(period_main) × mult_breakout. То есть пробой не фиксированного уровня, а уровня, отстоящего от close 2 бара назад на ATR-multiple. Идея: ATR адаптируется к режиму волатильности — в спокойные периоды порог уже, в волатильные — шире.

**Логика выхода:** ATR(period_stop) × mult_stop trailing-stop ИЛИ обратный сигнал. Параметры period_stop и mult_stop отдельные от period_main — две независимых ATR-калибровки.

**Параметры (LOCKED per (symbol, timeframe) combo):**
Для каждой из 10 комбинаций (BTCUSDT/ETHUSDT/SOLUSDT × 15M/1H/4H/1D) свой набор {period_main, mult_breakout, period_stop, mult_stop}, найденный autoresearch sweep'ом. См. `src/signalgen/atr_breakout_strategy.py::ATR_BREAKOUT_LOCKED_PARAMS_BY_COMBO`.

**Supported combos (10):**
BTCUSDT: 15M, 1H, 4H, 1D | ETHUSDT: 15M, 1H, 4H | SOLUSDT: 15M, 1H, 4H

**Целевой режим рынка:** trend-following с volatility-adaptive entry. Лучший combo по pre-S44 RAW: BTCUSDT 4H +819.81% за 8.7 года, 5/5 положительных под-периодов (in-sample headline number).

**Исторический контекст:** ATR (Average True Range) введён J. Welles Wilder (1978). Volatility-adaptive breakouts — стандартная техника CTAs (commodity trading advisors) с 1980-х (Tushar Chande, "Beyond Technical Analysis" 1997). Применение к крипто — современная адаптация, S40-S41 autoresearch.

**Вердикт S44 (WFA retrofit):** ВСЕ 10 комбинаций WFA_FAIL под default WFA gates. Корневая причина: low trade frequency в OOS windows (5-20 trades vs 50 floor). Pre-S44 RAW verdict (+819% headline) скрывал OOS validation failure — RAW считает на full history, не разделяя in-sample/out-of-sample.

**BTCUSDT 1D specifically:** WFA_FAIL_DATA — 1212 bars < 4520 default min (нужно train=2000 + test=500 × 5 folds + embargo, 4H+ TF имеют структурно мало баров для строгого WFA).

См. ADR 0064 для full per-combo diagnostic table.

**Известные слабости:** аналогично volume_breakout — pre-WFA headlines маскировали OOS failure; LOCKED params per combo = 10 отдельных трюков, каждый с own n_trials inflation risk; structural мismatch между 4H/1D timeframes и default ADR 0014 WFA params (calibrated для FX 1H per ADR 0014).
""".strip(),
}


def get_strategy_description(preset_id: str) -> str | None:
    """Return RU detailed description; None if unknown preset."""
    return STRATEGY_DESCRIPTIONS_RU.get(preset_id)

# Depth review (CORRECTNESS) — docs/03-индикаторы-и-расчёты/atr-indicator.md

Дата: 2026-06-26. Ось: соответствие коду. Пересчитано чисел: 9 (TR×3, RMA chain×2, ~1.4% divergence характеризация, warmup boundary, RMA weights, byte-identity×3, EWM distinctness).

verdict: REQUEST_CHANGES
BLOCKER: 2 | WARN: 3 | DEEP: 3

---

## BLOCKER

### B1. «Четыре разных реализации ATR» — число некогерентно и опускает реально используемую EWM-реализацию (line 28)
Доку открывает раздел «Как это работает у нас» утверждением: «В проекте существует **четыре разных реализации ATR**». Это число не соответствует ни коду, ни самой странице:

- В коде **7 ATR code paths**, из них **3 численно-различных семейства**: {talib `atr()`, manual-RMA (`wilder_atr` + 3 байт-идентичные копии), **EWM** (`true_range.ewm(alpha=1/period)` в `calculate_indicators`)}.
- Страница **нумерует только ТРИ варианта** (Вариант 1/2/3 в Шагах 2-4).
- Таблица принадлежности (lines 219-225) содержит **ПЯТЬ строк** (`atr()`, `wilder_atr()`, `_WilderATR`, `_update_atr`, `backtest/indicators._wilder_atr()`).
- **EWM-вариант полностью опущен** — хотя он реально используется (`src/backtest/replay_engine.py:141` → `calculate_indicators` → `src/backtest/indicators.py:107`), и сам код признаёт его отдельным («Distinct from `calculate_indicators`' EWM-based ATR (pandas ewm)», backtest/indicators.py:22).
- Сестринская страница `docs/03-индикаторы-и-расчёты/ema-rsi-indicators.md:299` явно перечисляет EWM как один из основных трёх: «`atr()` через TA-Lib, `wilder_atr()` ручная, и **EWM-вариант в бэктесте**». Прямое cross-doc противоречие.

«Четыре» не равно ни 3 (нумерованные варианты / различные семейства), ни 5 (таблица), ни тому, что перечисляет сестринская страница. Для money_core-страницы, чья центральная структура построена вокруг этого счёта, это вводит в заблуждение.

Проверено: `np.array_equal(wilder_atr, _wilder_atr, _wilder_atr_vectorized) == True` (max abs diff 0.0); EWM @bar60 отличается от manual на 0.598%, сходится к ~0% к концу (отдельный seed). EWM-путь: `grep "calculate_indicators" src/` → replay_engine.py:141.

**Fix:** либо сделать счёт когерентным (напр. «три численно-различных семейства» или «пять именованных реализаций»), либо добавить EWM-вариант явно и согласовать с таблицей и с ema-rsi-indicators.md.

### B2. «Supertrend не использует ATR для стоп-уровня» — неверно, у Supertrend ЕСТЬ ATR bracket SL (line 124)
Доку утверждает: «Supertrend **не использует ATR напрямую для стоп-уровня** в стратегии — ATR передаётся в поле сигнала `atr_14`, а полосы Supertrend сами определяют выход через смену тренда (src/signalgen/supertrend_strategy.py:27–30)».

Это вводит в заблуждение для не-программиста (вывод: «у Supertrend нет ATR-стопа»). Факты:
- ADR 0067:57 — «Exit prio 2 | **ATR-multiple bracket SL (safety net)**».
- `supertrend_strategy.py:32-34`: «**ATR bracket stop loss** (no take-profit) is enforced downstream by the FSM/risk layer **using atr_14** carried in the Signal... (per ADR 0067 exit = flip + **ATR bracket SL**, no TP)».
- `atr_14` передаётся НЕ декоративно — downstream FSM/risk строит из него ATR-стоп (`src/risk/manager.py` обрабатывает atr_14).

Итог: Supertrend выходит через смену тренда **ИЛИ** ATR bracket SL — два пути выхода, оба используют ATR. Формулировка «полосы сами определяют выход» опускает второй путь.

Дополнительно: **citation неверна**. `supertrend_strategy.py:27–30` — это правила Entry/Exit-flip/Mid-trend в docstring; содержимое про atr_14/bracket-SL находится на lines **32-34**.

**Fix:** переформулировать — «Сама стратегия Supertrend не вычисляет стоп-уровень в своём классе, но передаёт ATR (`atr_14`), из которого downstream FSM/risk-слой строит ATR bracket SL (Exit prio 2, ADR 0067). Выход = смена тренда ИЛИ срабатывание ATR bracket SL». Исправить citation на :32-34.

---

## WARN

### W1. Таблица принадлежности `atr()` опускает mean_reversion (lines 221, 251)
Таблица (line 221) и связанный документ (line 251) приписывают talib `atr()` только `DonchianBreakoutStrategy` и `VolumeBreakoutStrategy`. Но `mean_reversion_strategy.py:31` тоже импортирует и использует talib `atr()` (`mean_reversion_strategy.py:150: atr_arr = atr(highs, lows, closes, ...)`, кладёт в `atr_14`). Перечень потребителей talib-ATR неполон. (Если страница сознательно не охватывает mean_reversion — стоит это оговорить, но сейчас таблица выглядит исчерпывающей.)

### W2. Citation для Volume Breakout стоп-таблицы покрывает не весь параметр (line 122)
Строка таблицы «Volume Breakout | 9 | 2.9663» цитирует `volume_breakout_strategy.py:57–58`. Фактически: line 57 = `atr_stop_mult: 2.9663` (множитель ✓), line 58 = `signal_side_mode` (НЕ atr_period). Период `atr_period: 9` находится на line **56**. Off-by-one в диапазоне citation (должно быть :56–57). Значения верны.

### W3. «Кто использует» Вариант 2 vs таблица — потенциальная путаница про Volume Breakout backtest (lines 80 vs 225)
Line 80: «Вариант 2 (`wilder_atr`/manual RMA) использует: все бэктест-раннеры ATR Breakout и Supertrend». Line 225 (таблица): backtest `_wilder_atr()` используют «ATR Breakout, **Volume Breakout** (S55 DRY)». Оба верны (все три раннера численно идентичны), но строка 80 упоминает Supertrend и опускает Volume Breakout, а строка 225 — наоборот. Согласовать. Факт (важный): volume_breakout **backtest runner** использует manual `_wilder_atr` (`volume_breakout_runner.py:38,95`), тогда как **live** strategy — talib `atr()`. См. DEEP-3.

---

## DEEP

### D1. Worked Example 3 фиксирует ATR на входе — реально стоп-уровень пересчитывается каждый бар (lines 199-207)
Пример 3 описывает стоп так: «ATR стоп-периода (21) в этот момент = 800... стоп_цена = 65 000 − 1.5 × 800 = 63 800... Если любая свеча после входа даст low ≤ 63 800 — выход». Это подразумевает зафиксированный уровень 63 800.

Фактически: код пересчитывает порог каждый бар с **текущим** ATR. `atr_breakout_strategy.py:297` `atr_val = atr_stop_curr` (= ATR через бар T, обновляется каждый `on_bar`), line 307 `bar.low <= entry_close - atr_stop_mult * atr_val`. То есть стоп = `entry_close(fixed) − mult × ATR(текущий, плавает)`. Аналогично donchian: `donchian_strategy.py:124` использует `atr_now = atr_arr[-1]` (текущий бар). Уровень НЕ заморожен на входе — он движется с волатильностью (трейлинг по ATR).

Для не-программиста «exit if low ≤ 63 800» создаёт ложную модель фиксированного уровня. Стоит добавить оговорку: «ATR в формуле — текущий на каждом баре, поэтому порог стопа плавает».

Доп. нюанс (не ошибка, но достойно упоминания): donchian сравнивает **close** (`close_now < atr_stop_price`), а atr_breakout — **low** (`bar.low <= ...`). Общая формула стопа (line 108-111) этого различия не отражает; Пример 3 (для atr_breakout, low) корректен.

### D2. «~1.4%» — каноническая константа, но реальное расхождение сильно зависит от данных и максимально у прогрева (lines 54, 215)
«~1.4%» (cited `indicators.py:97`) — это документированная проектная константа из docstring, и страница её цитирует корректно (НЕ галлюцинация, НЕ BLOCKER). Однако фактическое расхождение talib vs manual:
- зависит от данных: на первом общем индексе 0.07%–6.7% (по сидам 0/1/2/7/42/100 пересчитано),
- **максимально у прогрева** (off-by-one старта: manual seed at index period-1, talib at period; talib TR[0]=NaN),
- сходится к ~0% к ~бару 60.

То есть «~1.4%» — представительная, не точная и не максимальная цифра. Страница описывает её как стабильную фиксированную величину («небольшое, но **стабильное** расхождение», line 215). Стоит уточнить, что расхождение наибольшее на ранних барах и затухает — иначе читатель думает, что 1.4% держится всегда. Проверено: `talib.ATR[14] == mean(talib_TRANGE[1:15])` True; `talib_TRANGE[0]` is NaN.

### D3. Volume Breakout: live talib vs backtest manual Wilder — реальная live/backtest дивергенция, не связана явно (lines 56, 225)
Line 56 утверждает «Volume Breakout зафиксирован на этом варианте [talib `atr()`] по ADR 0059 — менять нельзя». Верно для **live** strategy (`volume_breakout_strategy.py:46`). Но таблица (line 225) показывает, что **backtest runner** Volume Breakout использует manual `_wilder_atr` (`volume_breakout_runner.py:38: from src.backtest.indicators import _wilder_atr as _atr`, line 95). То есть live (talib) и backtest (manual Wilder) Volume Breakout используют **разные** ATR (~1.4% врозь). Страница не связывает эти два факта и не предупреждает о live/backtest-расхождении ATR именно для VB — это тонкий, но реальный момент (WFA валидировался на manual, live торгует на talib). Достойно явного предложения-предупреждения.

---

## Проверено-верно (НЕ перепроверять повторно)

- TR-формула + первая свеча `prev_close[0]=close[0]` → TR[0]=high-low (indicators.py:110-117, :161) ✓
- Пример 1 TR: бар0=300, бар1=550 (cand 550/500/50), бар2=700 (cand 550/150/700) — пересчитано, точно ✓
- Пример 2 RMA: бар9 (400×8+350)/9=394.44≈394 ✓; бар10 (394×8+500)/9=405.78≈406 ✓ (арифметика 3152+500 ✓)
- RMA веса: новый бар 1/9≈11%, история 8/9≈89% ✓; (atr×(p-1)+tr)/p ≡ atr×(p-1)/p + tr/p ✓
- Warmup boundary: seed at index period-1, первый рекурсивный ATR at index period — пересчитано (idx8 seed, idx9 recursion при period=9) ✓
- warmup = max(atr_period, atr_stop_period) + 3 = max(9,21)+3 = 24 (atr_breakout_strategy.py:206) ✓
- Стоп-таблица ATR Breakout (4 BTC-комбо): stop_period 21/21/14/9, mult 1.5/3.0/3.0/3.0 — все значения верны; citations :60-61 (=default = live params!), :79-80, :85-86, :91-92 все указывают на корректные строки ✓
- Live ATRBreakoutStrategy читает `ATR_BREAKOUT_LOCKED_PARAMS` (default = BTCUSDT 240), by-combo dict потребляется backtest runner + dashboard ✓
- Donchian: lookback 20, atr_period 14, atr_stop_mult 2.0 (:36-37) ✓
- byte-идентичность wilder_atr == backtest _wilder_atr == _wilder_atr_vectorized (max diff 0.0) ✓
- D4 «~39%» (atr_breakout_strategy.py:31 «diverged up to ~39% rel») ✓; tests/unit/test_atr_breakout_parity.py существует ✓
- Citations: atr() :67-81 ✓, wilder_atr :84-124 ✓, _WilderATR class :135 ✓, _update_atr :208-242 ✓, backtest _wilder_atr :17-51 ✓, _wilder_atr_vectorized :73-96 ✓, live atr_breakout :212-216 ✓, supertrend live :150 ✓, stop exit :307 (operator `<=` matches «low ≤») ✓
- donchian/volume_breakout import `atr` строки :29 / :46 ✓
- S55 extraction «извлечён туда» (backtest/indicators.py:18 «S55 PY-3: extracted») ✓

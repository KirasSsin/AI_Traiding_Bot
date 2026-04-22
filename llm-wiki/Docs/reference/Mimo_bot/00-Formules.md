## Полный каталог формул, теорем, функций, теорий и алгоритмов для торгового бота

---

## 1. Индикаторы тренда

| # | Название | За что отвечает |
|---|----------|----------------|
| 1 | SMA (Simple Moving Average) | Сглаживание цены, определение направления тренда |
| 2 | EMA (Exponential Moving Average) | Взвешенное сглаживание с приоритетом последних цен |
| 3 | WMA (Weighted Moving Average) | Линейно взвешенная скользящая средняя |
| 4 | DEMA (Double Exponential Moving Average) | Двойное сглаживание для уменьшения лага |
| 5 | TEMA (Triple Exponential Moving Average) | Тройное сглаживание, минимальный лаг |
| 6 | HMA (Hull Moving Average) | Минимальный лаг через взвешенную разницу WMA |
| 7 | KAMA (Kaufman Adaptive Moving Average) | Адаптивная к волатильности скользящая средняя |
| 8 | VWMA (Volume Weighted Moving Average) | Скользящая средняя с учётом объёма |
| 9 | T3 (Tillson T3 Moving Average) | Шестикратное сглаживание с параметром volume factor |
| 10 | ZLEMA (Zero Lag Exponential Moving Average) | EMA с нулевым лагом через опережающую компенсацию |
| 11 | ALMA (Arnaud Legoux Moving Average) | Гауссово-взвешенная скользящая средняя |
| 12 | VIDYA (Variable Index Dynamic Average) | Динамическая средняя на основе CMO |
| 13 | FRAMA (Fractal Adaptive Moving Average) | Адаптивная на основе фрактальной размерности |
| 14 | JMA (Jurik Moving Average) | Сверхбыстрое сглаживание с фазовым нулевым лагом |
| 15 | McGinley Dynamic | Автоматически адаптируется к скорости рынка |
| 16 | Ichimoku Kinko Hyo (Ichimoku Cloud) | Комплексная система: тренд, поддержка/сопротивление, моментум |
| 17 | Parabolic SAR | Определение разворота тренда и trailing stop |
| 18 | Aroon Indicator | Определяет силу тренда и его возраст |
| 19 | Aroon Oscillator | Разница Aroon Up и Aroon Down |
| 20 | Supertrend | Трендовый индикатор на основе ATR |
| 21 | Vortex Indicator | Определяет начало нового тренда через +VI/-VI |
| 22 | DMI (Directional Movement Index) | +DI/-DI для определения направления тренда |
| 23 | ADX (Average Directional Index) | Сила тренда без учёта направления |
| 24 | ADXR (Average Directional Movement Index Rating) | Сглаженный ADX для фильтрации шума |
| 25 | Linear Regression Slope | Наклон линейной регрессии как мера тренда |
| 26 | Linear Regression Intercept | Пересечение линейной регрессии |
| 27 | Linear Regression Angle | Угол наклона тренда в градусах |
| 28 | Linear Regression Forecast | Прогноз цены на основе линейной регрессии |
| 29 | Time Series Forecast | Прогноз на основе полиномиальной регрессии |
| 30 | TRIX (Triple Exponential Average) | Процентное изменение тройной EMA |
| 31 | Mass Index | Определяет разворот тренда через размах High-Low |
| 32 | Chandelier Exit | Trailing stop на основе ATR от экстремума |
| 33 | Moving Average Envelope | Канал вокруг скользящей средней |
| 34 | Price Channel (Donchian Channel) | Канал из N-периодных High/Low |
| 35 | Keltner Channel | Канал на основе EMA ± ATR |
| 36 | Ichimoku Tenkan-sen | Быстрая линия Ichimoku (9-периодный midpoint) |
| 37 | Ichimoku Kijun-sen | Медленная линия Ichimoku (26-периодный midpoint) |
| 38 | Ichimoku Senkou Span A | Передний спан A (среднее Tenkan и Kijun, сдвинутое) |
| 39 | Ichimoku Senkou Span B | Передний спан B (52-периодный midpoint, сдвинутый) |
| 40 | Ichimoku Chikou Span | Задний спан (цена закрытия, сдвинутая назад) |
| 41 | Anchored VWAP | VWAP привязанный к конкретной точке (IPO, экстремум) |
| 42 | Rolling VWAP | VWAP с скользящим окном |
| 43 | Guppy Multiple Moving Average (GMMA) | Группа из 6 коротких и 6 длинных EMA |
| 44 | Heikin Ashi Candles | Сглаженные свечи для фильтрации шума и определения тренда |
| 45 | Pivot Points Standard | Расчёт уровней поддержки/сопротивления на основе предыдущего дня |
| 46 | Fibonacci Retracement | Уровни коррекции по золотому сечению |
| 47 | Fibonacci Extension | Уровни расширения тренда |
| 48 | Supertrend (ATR-based) | Трендовый индикатор с динамическим trailing stop |

---

## 2. Осцилляторы и моментум

| # | Название | За что отвечает |
|---|----------|----------------|
| 49 | RSI (Relative Strength Index) | Перекупленность/перепроданность |
| 50 | Stochastic Oscillator (%K, %D) | Положение цены в диапазоне High-Low |
| 51 | Stochastic RSI | RSI применённый к Stochastic |
| 52 | Williams %R | Аналог Stochastic, инвертированная шкала |
| 53 | CCI (Commodity Channel Index) | Отклонение цены от статистического среднего |
| 54 | ROC (Rate of Change) | Процентное изменение цены за N периодов |
| 55 | Momentum (MOM) | Абсолютное изменение цены за N периодов |
| 56 | CMO (Chande Momentum Oscillator) | Взвешенный моментум |
| 57 | Trix Oscillator | Разница TRIX и сигнальной линии |
| 58 | TSI (True Strength Index) | Осциллятор моментума с двойным сглаживанием |
| 59 | Awesome Oscillator (AO) | Разница SMA(5) и SMA(34) от midpoint |
| 60 | Acceleration Oscillator | Производная Awesome Oscillator |
| 61 | Detrended Price Oscillator (DPO) | Цена минус сдвинутая SMA, убирает тренд |
| 62 | Percentage Price Oscillator (PPO) | Процентная разница двух EMA (как MACD но в %) |
| 63 | Coppock Curve | Долгосрочный моментум через ROC+WMA |
| 64 | Elder-Ray Index (Bull/Bear Power) | Разница High/Low с EMA |
| 65 | Elliott Wave Oscillator | Разница SMA(5) и SMA(35) для подсчёта волн |
| 66 | Fisher Transform | Преобразование цены в гауссово распределение |
| 67 | Inverse Fisher Transform | Обратное преобразование для осцилляторов |
| 68 | Klinger Volume Oscillator | Объёмно-взвешенный моментум |
| 69 | RVGI (Relative Vigor Index) | Соотношение цен закрытия к открытию |
| 70 | Schaff Trend Cycle | Циклический индикатор на основе MACD+Stochastic |
| 71 | CTI (Correlation Trend Indicator) | Корреляция цены с линейным трендом |
| 72 | Ehlers Fisher Transform | Адаптивное преобразование Фишера |
| 73 | Ehlers Instantaneous Trendline | Мгновенная линия тренда без лага |
| 74 | Ehlers Roofing Filter | Фильтр полосы пропускания для ценового ряда |
| 75 | Ehlers Cyber Cycle | Адаптивный циклический индикатор |
| 76 | Ehlers Adaptive RSI | RSI с адаптивным периодом |
| 77 | Ultimate Oscillator | Комбинированный осциллятор с 3 таймфреймами |
| 78 | Chande Momentum Oscillator (CMO) | Чистый моментум без шума |
| 79 | KST (Know Sure Thing) | Сводный индикатор моментума по 4 таймфреймам |
| 80 | QQE (Quantitative Qualitative Estimation) | Модифицированный RSI со сглаживанием и динамическими уровнями |
| 81 | Williams VIX Fix | Синтетический VIX для любого актива |
| 82 | Elder Impulse System | Объединяет EMA и MACD-гистограмму для запрета торговли против тренда |
| 83 | Bill Williams Alligator | 3 сдвинутые скользящие средние для поиска начала тренда |
| 84 | Bill Williams Fractals | Локальные максимумы и минимумы из 5 свечей |
| 85 | MESA Adaptive Moving Average (MAMA & FAMA) | Скользящие Элерса, адаптирующиеся к фазе рынка |
| 86 | MACD (Moving Average Convergence Divergence) | Схождение/расхождение скользящих |
| 87 | MACD Histogram | Разница MACD и сигнальной линии |
| 88 | MACD Signal Line | EMA от линии MACD |

---

## 3. Волатильность

| # | Название | За что отвечает |
|---|----------|----------------|
| 89 | ATR (Average True Range) | Средний истинный диапазон, волатильность |
| 90 | NATR (Normalized ATR) | ATR в процентах от цены |
| 91 | Bollinger Bands (Upper/Middle/Lower) | Волатильность через стандартное отклонение |
| 92 | Bollinger Bandwidth | Ширина полос Боллинджера |
| 93 | Bollinger %B | Положение цены относительно полос |
| 94 | Historical Volatility | Стандартное отклонение лог-доходностей |
| 95 | Parkinson Volatility | Волатильность через High-Low |
| 96 | Garman-Klass Volatility | Волатильность через OHLC |
| 97 | Rogers-Satchell Volatility | Волатильность без drift |
| 98 | Yang-Zhang Volatility | Комбинация overnight и intraday волатильности |
| 99 | GARCH(1,1) | Условная волатильность с памятью |
| 100 | EGARCH | Экспоненциальный GARCH (асимметрия) |
| 101 | GJR-GARCH | GARCH с плечом новости |
| 102 | TGARCH (Threshold GARCH) | GARCH с пороговым эффектом |
| 103 | FIGARCH | GARCH с долгой памятью |
| 104 | APARCH | Асимметричный power GARCH |
| 105 | HYGARCH | Hyperbolic GARCH |
| 106 | Realized Volatility | Суммарная волатильность из внутридневных данных |
| 107 | Implied Volatility (Black-Scholes) | Рыночная ожидаемая волатильность из опционов |
| 108 | VIX (Volatility Index) | Индекс страха |
| 109 | Volatility Smile/Smirk | Кривая implied vol по страйкам |
| 110 | Volatility Cone | Распределение historical vol по горизонтам |
| 111 | Volatility Ratio | Текущая vol / историческая vol |
| 112 | Ulcer Index | Мера «стресса» от просадок |
| 113 | Historical Volatility (HV) | Стандартное отклонение лог-доходностей (уточнение) |
| 114 | Parkinson Volatility (уточнение) | Волатильность только по High-Low |
| 115 | Garman-Klass Volatility (уточнение) | Волатильность по полному OHLC |
| 116 | MSGARCH (Markov-Switching GARCH) | GARCH с переключением режимов |
| 117 | Chande Kroll Stop | Индикатор волатильных стопов на основе ATR |

---

## 4. Объёмные индикаторы

| # | Название | За что отвечает |
|---|----------|----------------|
| 118 | OBV (On-Balance Volume) | Кумулятивный объём с направлением |
| 119 | Volume Profile | Распределение объёма по ценовым уровням |
| 120 | VWAP (Volume Weighted Average Price) | Средневзвешенная по объёму |
| 121 | TWAP (Time Weighted Average Price) | Средневзвешенная по времени |
| 122 | Accumulation/Distribution (A/D) | Давление покупателей/продавцов |
| 123 | Chaikin Money Flow (CMF) | Денежный поток за период |
| 124 | Chaikin Oscillator | Разница EMA(3) и EMA(10) от A/D |
| 125 | Force Index | Объём × изменение цены |
| 126 | Ease of Movement (EoM) | Лёгкость движения цены при данном объёме |
| 127 | Volume Oscillator | Разница короткой и длинной SMA объёма |
| 128 | Volume Rate of Change (VROC) | Процентное изменение объёма |
| 129 | Negative Volume Index (NVI) | Изменения при уменьшающемся объёме |
| 130 | Positive Volume Index (PVI) | Изменения при увеличивающемся объёме |
| 131 | Volume-Weighted MACD | MACD с весами объёма |
| 132 | Money Flow Index (MFI) | RSI с весами объёма |
| 133 | Twiggs Money Flow | Улучшенный CMF с True Range |
| 134 | Elder's Force Index | Моментум × объём |
| 135 | Volume-Weighted RSI | RSI с учётом объёма |
| 136 | Delta Volume | Разница покупок и продаж |
| 137 | Cumulative Volume Delta | Кумулятивная разница покупок/продаж |
| 138 | Volume-at-Price | Объём на каждом ценовом уровне |
| 139 | Market Profile (TPO) | Распределение времени по ценам |
| 140 | Anchored Volume Profile | Профиль объёма от конкретной точки |
| 141 | Cumulative Volume Delta (CVD) | Накопительная разница покупок и продаж (уточнение) |
| 142 | Volume Profile Visible Range | Распределение объёма в видимом диапазоне |
| 143 | Volume-Weighted MACD (уточнение) | MACD с весами объёма |
| 144 | Volume Spread Analysis (VSA) | Анализ размера свечи относительно объёма |

---

## 5. Статистические метрики

| # | Название | За что отвечает |
|---|----------|----------------|
| 145 | Total Return | Общая доходность |
| 146 | Net Profit | Чистая прибыль после комиссий |
| 147 | CAGR (Compound Annual Growth Rate) | Среднегодовая сложная доходность |
| 148 | Win Rate | Процент прибыльных сделок |
| 149 | Loss Rate | Процент убыточных сделок |
| 150 | Profit Factor | Валовая прибыль / валовый убыток |
| 151 | Expectancy | Средний результат на сделку |
| 152 | Average Win | Средняя прибыль прибыльной сделки |
| 153 | Average Loss | Средний убыток убыточной сделки |
| 154 | Max Drawdown (%) | Максимальная просадка в процентах |
| 155 | Max Drawdown Absolute | Максимальная просадка в валюте |
| 156 | Average Drawdown | Средняя просадка |
| 157 | Drawdown Duration | Длительность максимальной просадки |
| 158 | Sharpe Ratio | Доходность / общий риск |
| 159 | Sortino Ratio | Доходность / downside risk |
| 160 | Calmar Ratio | CAGR / Max Drawdown |
| 161 | Omega Ratio | Вероятностное отношение прибыли к убытку |
| 162 | Kappa Ratio (K-3) | Модифицированный Sharpe с учётом skew |
| 163 | Gain-to-Pain Ratio | Сумма доходностей / сумма убытков |
| 164 | Sterling Ratio | CAGR / средняя просадка |
| 165 | Burke Ratio | CAGR / sqrt(сумма квадратов просадок) |
| 166 | Tail Ratio | 95-й перцентиль прибылей / 5-й перцентиль убытков |
| 167 | R-squared | Доля дисперсии, объяснённая моделью |
| 168 | Information Ratio | Alpha / tracking error |
| 169 | Treynor Ratio | (Return - rf) / beta |
| 170 | Jensen's Alpha | Фактическая доходность - ожидаемая по CAPM |
| 171 | Recovery Factor | Net Profit / Max Drawdown |
| 172 | Payoff Ratio | Average Win / Average Loss |
| 173 | Consecutive Wins/Losses | Максимальная серия побед/поражений |
| 174 | Average Holding Time | Среднее время удержания позиции |
| 175 | Trade Frequency | Количество сделок за период |
| 176 | Turnover Rate | Объём торгов / средний капитал |
| 177 | Deflated Sharpe Ratio | Sharpe с поправкой на overfitting |
| 178 | Probabilistic Sharpe Ratio | Вероятностная оценка Sharpe |
| 179 | Omega Ratio (уточнение) | Вероятностное отношение прибыли к убытку |
| 180 | Ulcer Index (уточнение) | Мера «стресса» от просадок |
| 181 | E-Ratio (Trade System Edge) | Математическое ожидание стратегии во времени |
| 182 | Information Coefficient (IC) | Корреляция предсказания и реальности |
| 183 | Rank IC | Ранговый IC для оценки предиктора |

---

## 6. Риск-менеджмент

| # | Название | За что отвечает |
|---|----------|----------------|
| 184 | VaR (Value at Risk) | Максимальный убыток с заданной вероятностью |
| 185 | Parametric VaR | VaR через нормальное распределение |
| 186 | Historical VaR | VaR через исторические данные |
| 187 | Cornish-Fisher VaR | VaR с поправкой на skew и kurtosis |
| 188 | CVaR (Expected Shortfall) | Средний убыток в худших сценариях |
| 189 | Monte Carlo VaR | VaR через стохастическую симуляцию |
| 190 | Maximum Drawdown Duration | Длительность максимальной просадки |
| 191 | Time Under Water | Время ниже предыдущего пика |
| 192 | Pain Index | Средняя просадка от пика |
| 193 | Ulcer Performance Index | Risk-adjusted return с учётом просадок |
| 194 | Downside Deviation | Стандартное отклонение только отрицательных доходностей |
| 195 | Semi-Variance | Дисперсия только отрицательных отклонений |
| 196 | Lower Partial Moment (LPM) | Частичный момент ниже порога |
| 197 | Upper Partial Moment (UPM) | Частичный момент выше порога |
| 198 | Fractional Kelly Criterion | Безопасный размер позиции с поправкой на skew/kurtosis |
| 199 | Risk of Ruin | Вероятность полного разорения стратегии |
| 200 | Expected Shortfall (CVaR) | Ожидаемые потери в худших сценариях |
| 201 | Volatility Targeting | Целевая волатильность портфеля |
| 202 | Almgren-Chriss Slippage Model | Оптимальное исполнение крупного ордера |
| 203 | Maximum Adverse Excursion (MAE) | Максимальное движение против позиции |
| 204 | Maximum Favorable Excursion (MFE) | Максимальное движение в сторону прибыли |
| 205 | Volatility Targeting (уточнение) | Целевая волатильность портфеля |
| 206 | Almgren-Chriss (уточнение) | Оптимальное исполнение крупного ордера |
| 207 | Conditional VaR (CVaR) | Средний убыток при превышении VaR |
| 208 | Kelly Criterion | Оптимальная доля капитала на сделку |
| 209 | Fractional Kelly | 1/2 или 1/4 от Келли для снижения просадок |
| 210 | Optimal f (Ральф Винс) | Доля капитала, максимизирующая геометрический рост |
| 211 | Fixed Fractional Position Sizing | Риск фиксированным процентом от депозита |
| 212 | Fixed Ratio Position Sizing (Райан Джонс) | Увеличение позиции после заработка «дельта»-профита |
| 213 | Core Equity Method | Расчёт позиции на основе свободной маржи |
| 214 | Expected Shortfall (CVaR) | Ожидаемые потери при пробитии VaR |
| 215 | Maximum Adverse Excursion (MAE) | Максимальное движение против позиции (для стопов) |
| 216 | Maximum Favorable Excursion (MFE) | Максимальное движение в прибыль (для тейков) |
| 217 | E-Ratio | Математическое ожидание стратегии |

---

## 7. Стохастические модели

| # | Название | За что отвечает |
|---|----------|----------------|
| 218 | Марковская цепь (transition matrix) | Вероятности перехода между рыночными режимами |
| 219 | Марковский процесс (без последействия) | Текущее состояние только по последнему наблюдению |
| 220 | Hidden Markov Model (HMM) | Скрытые состояния рынка (Bull/Bear/Range) |
| 221 | Gaussian HMM | HMM с гауссовыми эмиссиями |
| 222 | Baum-Welch (EM) | Обучение HMM |
| 223 | Viterbi | Наиболее вероятная последовательность состояний |
| 224 | Forward Algorithm | Оценка правдоподобия наблюдений |
| 225 | MDP (Markov Decision Process) | Марковский процесс принятия решений |
| 226 | MCMC (Markov Chain Monte Carlo) | Семплирование из posterior |
| 227 | Gibbs Sampling | MCMC через условные распределения |
| 228 | Metropolis-Hastings | Алгоритм MCMC |
| 229 | GARCH(1,1) | Условная волатильность |
| 230 | GJR-GARCH | GARCH с плечом новости |
| 231 | EGARCH | Экспоненциальный GARCH |
| 232 | IGARCH | Интегрированный GARCH (α+β=1) |
| 233 | Component GARCH | Разделение на долгосрочную и краткосрочную vol |
| 234 | Multivariate GARCH (DCC) | Динамическая условная корреляция |
| 235 | BEKK-GARCH | Многомерный GARCH |
| 236 | OU-процесс (Ornstein-Uhlenbeck) | Возврат к среднему |
| 237 | CIR-процесс (Cox-Ingersoll-Ross) | OU с неотрицательными значениями |
| 238 | GBM (Geometric Brownian Motion) | Базовая модель случайного блуждания |
| 239 | Jump-Diffusion (Merton) | GBM + пуассоновские прыжки |
| 240 | Variance Gamma | Чистый прыжковый процесс |
| 241 | NIG (Normal Inverse Gaussian) | Распределение с толстыми хвостами |
| 242 | Heston Model | Стохастическая волатильность |
| 243 | SABR Model | Стохастический альфа-бета-ро |
| 244 | Regime-Switching Model | Переключение между моделями |
| 245 | Markov-Switching GARCH | GARCH с переключением режимов |
| 246 | State-Space Model | Общая форма для скрытых процессов |
| 247 | Kalman Filter | Оптимальная оценка скрытого состояния |
| 248 | Extended Kalman Filter | Линеаризация для нелинейных систем |
| 249 | Unscented Kalman Filter | Фильтрация через sigma-точки |
| 250 | Particle Filter (Sequential Monte Carlo) | Нелинейная/негауссова фильтрация |
| 251 | Itô's Lemma | Дифференциал функции стохастического процесса |
| 252 | Feynman-Kac Formula | Связь стохастических процессов и PDE |
| 253 | Girsanov's Theorem | Смена меры (risk-neutral pricing) |
| 254 | Levy Process | Процесс с независимыми приращениями |
| 255 | Levy-Khintchine Formula | Характеристическая функция Levy-процесса |
| 256 | Stable Distribution | Обобщение нормального с толстыми хвостами |
| 257 | Hurst Exponent | Персистентность/антипёрсистентность |
| 258 | Detrended Fluctuation Analysis (DFA) | Альтернатива Hurst для нестационарных рядов |
| 259 | Rescaled Range Analysis (R/S) | Классический метод расчёта Hurst |
| 260 | Lyapunov Exponent | Чувствительность к начальным условиям (хаос) |
| 261 | BDS Test | Тест на нелинейную зависимость |
| 262 | Ljung-Box Test | Тест на автокорреляцию остатков |
| 263 | ARCH-LM Test | Тест на ARCH-эффект |
| 264 | ADF Test (Augmented Dickey-Fuller) | Тест на единичный корень |
| 265 | KPSS Test | Тест на стационарность |
| 266 | Phillips-Perron Test | Тест на единичный корень (робастный) |
| 267 | Johansen Test | Тест на множественную коинтеграцию |
| 268 | Engle-Granger Test | Тест на коинтеграцию пар |
| 269 | Granger Causality Test | Тест на причинность |
| 270 | Variance Ratio Test | Тест случайного блуждания |
| 271 | Runs Test | Тест на случайность последовательности |
| 272 | Chow Test | Тест на структурный сдвиг |
| 273 | CUSUM Test | Кумулятивный тест на сдвиг среднего |
| 274 | Bai-Perron Test | Множественные структурные сдвиги |
| 275 | Zivot-Andrews Test | ADF с эндогенным структурным сдвигом |
| 276 | MVRV Z-Score | Соотношение рыночной и реализованной стоимости (BTC) |
| 277 | Pi Cycle Top Indicator | Двойная EMA для определения пиков рынка |
| 278 | MSGARCH (Markov-Switching GARCH) | GARCH с переключением режимов |

---

## 8. Коинтеграция и парный трейдинг

| # | Название | За что отвечает |
|---|----------|----------------|
| 279 | Engle-Granger Two-Step | Проверка коинтеграции двух рядов |
| 280 | Johansen Procedure | Множественная коинтеграция |
| 281 | Half-Life of Mean Reversion | Время возврата к среднему |
| 282 | Ornstein-Uhlenbeck Fit | Подгонка OU-процесса к спреду |
| 283 | Z-Score of Spread | Стандартизированный спред |
| 284 | Bollinger Band on Spread | Каналы Боллинджера на спред |
| 285 | Kalman Filter Hedge Ratio | Динамический хедж-коэффициент |
| 286 | Rolling Cointegration | Скользящая проверка коинтеграции |
| 287 | Distance Method | Евклидово расстояние между нормализованными ценами |
| 288 | Copula-Based Pairs | Зависимость через копулы |
| 289 | Kalman Filter Hedge Ratio (уточнение) | Динамический коэффициент хеджирования |

---

## 9. Machine Learning и оптимизация

| # | Название | За что отвечает |
|---|----------|----------------|
| 290 | Linear Regression | Линейная модель предсказания |
| 291 | Ridge Regression (L2) | Регуляризированная регрессия |
| 292 | Lasso Regression (L1) | Регрессия с отбором признаков |
| 293 | Elastic Net | Комбинация L1 и L2 |
| 294 | Logistic Regression | Бинарная классификация (up/down) |
| 295 | Decision Tree | Дерево решений |
| 296 | Random Forest | Ансамбль деревьев |
| 297 | Gradient Boosting (GBM) | Последовательный ансамбль |
| 298 | XGBoost | Оптимизированный gradient boosting |
| 299 | LightGBM | Быстрый gradient boosting |
| 300 | CatBoost | Gradient boosting с категориальными фичами |
| 301 | Support Vector Machine (SVM) | Классификация через разделяющую гиперплоскость |
| 302 | K-Nearest Neighbors (KNN) | Классификация по ближайшим соседям |
| 303 | Naive Bayes | Вероятностная классификация |
| 304 | AdaBoost | Адаптивный бустинг |
| 305 | Bagging | Агрегация бутстрэп |
| 306 | Stacking | Мета-модель поверх базовых |
| 307 | Voting (Hard/Soft) | Голосование ансамбля |
| 308 | LSTM (Long Short-Term Memory) | Рекуррентная сеть для временных рядов |
| 309 | GRU (Gated Recurrent Unit) | Упрощённая LSTM |
| 310 | Transformer (Attention) | Self-attention для временных рядов |
| 311 | Temporal Fusion Transformer | Transformer для multi-horizon forecasting |
| 312 | CNN (1D) | Свёрточная сеть для паттернов в рядах |
| 313 | Autoencoder | Обнаружение аномалий, сжатие фич |
| 314 | VAE (Variational Autoencoder) | Генеративная модель |
| 315 | GAN (Generative Adversarial Network) | Генерация синтетических данных |
| 316 | Reinforcement Learning (Q-Learning) | Обучение через награды |
| 317 | DQN (Deep Q-Network) | Q-learning с нейросетью |
| 318 | PPO (Proximal Policy Optimization) | Policy gradient метод |
| 319 | A3C (Asynchronous Advantage Actor-Critic) | Параллельный RL |
| 320 | SAC (Soft Actor-Critic) | Maximum entropy RL |
| 321 | Multi-Armed Bandit (UCB) | Автоматический выбор стратегии |
| 322 | Thompson Sampling | Байесовский bandit |
| 323 | Grid Search | Полный перебор параметров |
| 324 | Random Search | Случайный перебор |
| 325 | Bayesian Optimization | Оптимизация через Gaussian Process |
| 326 | Genetic Algorithm | Эволюционная оптимизация |
| 327 | Differential Evolution | Оптимизация для непрерывных параметров |
| 328 | Particle Swarm Optimization | Рой частиц |
| 329 | Simulated Annealing | Оптимизация через «отжиг» |
| 330 | Cross-Validation (K-Fold) | Валидация модели |
| 331 | Time Series Split | Валидация с учётом времени |
| 332 | Purged K-Fold | Валидация с purge и embargo |
| 333 | Walk-Forward Optimization | Скользящая оптимизация |
| 334 | Anchored Walk-Forward | WF с фиксированным началом |
| 335 | Expanding Window | Расширяющееся окно обучения |
| 336 | Feature Importance (Permutation) | Важность фич через перестановки |
| 337 | SHAP Values | Объяснимость предсказаний |
| 338 | PCA (Principal Component Analysis) | Снижение размерности |
| 339 | ICA (Independent Component Analysis) | Разделение независимых компонент |
| 340 | t-SNE | Визуализация многомерных данных |
| 341 | UMAP | Альтернатива t-SNE |
| 342 | K-Means Clustering | Кластеризация рыночных режимов |
| 343 | DBSCAN | Кластеризация плотности |
| 344 | Gaussian Mixture Model | Вероятностная кластеризация |
| 345 | LightGBM (уточнение) | Быстрый gradient boosting для режимов |
| 346 | CatBoost (уточнение) | Gradient boosting с категориальными фичами |
| 347 | N-BEATS (Neural Basis Expansion Analysis) | Deep Learning для временных рядов |
| 348 | DeepAR | Вероятностная нейросеть от Amazon |
| 349 | TCN (Temporal Convolutional Networks) | Свёрточные сети с долгой памятью |
| 350 | TabNet | Deep Learning для табличных данных |
| 351 | Boruta Algorithm | Жёсткий отбор важных фичей |
| 352 | Information Coefficient (IC) / Rank IC | Сила предсказательной способности |

---

## 10. Технический анализ — паттерны

| # | Название | За что отвечает |
|---|----------|----------------|
| 353 | Doji | Нерешительность рынка |
| 354 | Hammer / Hanging Man | Разворотный паттерн |
| 355 | Shooting Star / Inverted Hammer | Разворот сверху/снизу |
| 356 | Engulfing (Bullish/Bearish) | Поглощение предыдущей свечи |
| 357 | Morning Star / Evening Star | Трёхсвечной разворот |
| 358 | Three White Soldiers / Three Black Crows | Три последовательные свечи |
| 359 | Harami (Bullish/Bearish) | Внутренняя свеча |
| 360 | Piercing Pattern / Dark Cloud Cover | Проникновение / тёмное облако |
| 361 | Marubozu | Свеча без теней |
| 362 | Spinning Top | Малое тело, длинные тени |
| 363 | Tweezer Top / Bottom | Одинаковые экстремумы |
| 364 | Three Inside Up/Down | Подтверждённый Harami |
| 365 | Three Outside Up/Down | Подтверждённый Engulfing |
| 366 | Head and Shoulders | Классический разворотный паттерн |
| 367 | Inverse Head and Shoulders | Разворот снизу |
| 368 | Double Top / Double Bottom | Двойная вершина / основание |
| 369 | Triple Top / Triple Bottom | Тройная вершина / основание |
| 370 | Cup and Handle | Чаша с ручкой (бычий паттерн) |
| 371 | Rounding Bottom | Скруглённое основание |
| 372 | Ascending Triangle | Восходящий треугольник |
| 373 | Descending Triangle | Нисходящий треугольник |
| 374 | Symmetrical Triangle | Симметричный треугольник |
| 375 | Rising Wedge | Восходящий клин |
| 376 | Falling Wedge | Нисходящий клин |
| 377 | Flag (Bullish/Bearish) | Флаг (продолжение тренда) |
| 378 | Pennant | Вымпел (продолжение тренда) |
| 379 | Rectangle (Consolidation) | Прямоугольник (консолидация) |
| 380 | Broadening Formation | Расширяющийся паттерн |
| 381 | Diamond Top/Bottom | Алмазный разворот |
| 382 | Bump and Run Reversal | Рывок и разворот |
| 383 | Island Reversal | Островной разворот |
| 384 | Measured Move | Измеренное движение |
| 385 | Wolfe Waves | Волны Вульфа |
| 386 | Harmonic Patterns (Gartley, Butterfly, Bat, Crab) | Гармонические паттерны |
| 387 | ABCD Pattern | Паттерн ABCD |
| 388 | Elliott Wave Principle | Волновая теория Эллиотта |
| 389 | Wyckoff Accumulation/Distribution | Накопление/распределение |
| 390 | Support/Resistance Levels | Уровни поддержки/сопротивления |
| 391 | Pivot Points (Standard/Woodie/Camarilla) | Расчётные уровни |
| 392 | Camarilla Pivots | Математические уровни внутридневной поддержки |
| 393 | Fibonacci Retracement (уточнение) | Уровни коррекции |
| 394 | Fibonacci Extension (уточнение) | Уровни расширения тренда |
| 395 | Fibonacci Fans | Веер Фибоначчи |
| 396 | Fibonacci Time Zones | Временные зоны Фибоначчи |
| 397 | Gann Angles | Углы Ганна |
| 398 | Candlestick Pattern Recognition | Распознавание свечных паттернов |

---

## 11. Волновой и фрактальный анализ

| # | Название | За что отвечает |
|---|----------|----------------|
| 399 | Elliott Wave Count | Подсчёт волн Эллиотта |
| 400 | Elliott Wave Oscillator (уточнение) | Индикатор для подсчёта волн |
| 401 | Fractal Dimension | Фрактальная размерность ряда |
| 402 | Hurst Exponent (уточнение) | Персистентность |
| 403 | DFA (уточнение) | Альтернатива Hurst |
| 404 | R/S Analysis (уточнение) | Классический метод Hurst |
| 405 | Continuous Wavelet Transform (CWT) | Непрерывное вейвлет-преобразование |
| 406 | Discrete Wavelet Transform (DWT) | Дискретное вейвлет-преобразование |
| 407 | Maximal Overlap DWT (MODWT) | Вейвлет без decimation |
| 408 | Wavelet Denoising | Удаление шума через вейвлеты |
| 409 | Wavelet Coherence | Когерентность двух рядов по частотам |
| 410 | Fourier Transform | Частотный анализ ценового ряда |
| 411 | Fast Fourier Transform (FFT) | Быстрое Фурье-преобразование |
| 412 | Power Spectral Density | Спектральная плотность мощности |
| 413 | Lomb-Scargle Periodogram | Спектр для неравномерных данных |
| 414 | Singular Spectrum Analysis (SSA) | Разложение на тренд, сезонность, шум |
| 415 | Empirical Mode Decomposition (EMD) | Адаптивное разложение на моды |
| 416 | Hilbert-Huang Transform | Мгновенная частота через EMD |
| 417 | Recurrence Quantification Analysis | Повторяемость состояний |
| 418 | Approximate Entropy | Мера нерегулярности |
| 419 | Sample Entropy | Улучшенная мера нерегулярности |
| 420 | Permutation Entropy | Энтропия порядка |
| 421 | Multiscale Entropy | Энтропия на разных масштабах |
| 422 | Fractal Adaptive Moving Average (FRAMA) | Адаптивная средняя на основе фрактальной размерности |
| 423 | Bill Williams Fractals (уточнение) | Локальные экстремумы из 5 свечей |
| 424 | Detrended Fluctuation Analysis (DFA) (уточнение) | Альтернатива Hurst для нестационарных рядов |
| 425 | Ensemble EMD (EEMD) | EMD с добавлением шума |
| 426 | CEEMDAN | Улучшенный EEMD |
| 427 | Instantaneous Frequency | Частота в каждый момент времени |
| 428 | Band-Pass Filter | Выделение диапазона частот |

---

## 12. Order Flow и микроструктура рынка

| # | Название | За что отвечает |
|---|----------|----------------|
| 429 | Order Book Imbalance (OBI) | Дисбаланс покупателей/продавцов в стакане |
| 430 | Kyle's Lambda | Рыночное влияние (slippage per unit volume) |
| 431 | Amihud Illiquidity Ratio | Влияние объёма на доходность |
| 432 | Roll's Spread Estimator | Оценка спреда из цен закрытия |
| 433 | Lee-Ready Algorithm | Классификация сделок (buyer/seller initiated) |
| 434 | Bulk Classification Volume | Классификация крупных ордеров |
| 435 | VPIN (Volume-Synchronized PIN) | Токсичность потока ордеров |
| 436 | Trade Arrival Rate | Частота сделок (интенсивность) |
| 437 | Hawkes Process | Самовозбуждающийся процесс для trade arrivals |
| 438 | ACD Model (Autoregressive Conditional Duration) | Моделирование времени между сделками |
| 439 | Kaplan-Meier Estimator | Оценка скрытого объёма (айсберги) |
| 440 | Iceberg Detection Algorithm | Детекция скрытых ордеров |
| 441 | Spoofing Detection | Детекция манипулятивных ордеров |
| 442 | Volume Clock | Тиковые часы (сделка за сделкой) |
| 443 | Dollar Bar | Свечи по объёму в долларах |
| 444 | Volume Bar | Свечи по количеству контрактов |
| 445 | Imbalance Bar | Свечи по дисбалансу покупок/продаж |
| 446 | Run Bar | Свечи по количеству последовательных покупок/продаж |
| 447 | Information-Driven Bars | Свечи, адаптивные к информационному потоку |
| 448 | VPIN (уточнение) | Токсичность order flow |
| 449 | Order Flow Imbalance (OFI) | Мгновенный дисбаланс потока ордеров |
| 450 | Bulk Volume Classification (уточнение) | Классификация крупных ордеров |
| 451 | Micro-Price | Взвешенная средняя спреда с учётом объёма |
| 452 | Limit Order Book Pressure | Давление лимитных ордеров на цену |
| 453 | Queue Position Algorithm | Вероятность исполнения лимитного ордера |
| 454 | Tick Rule Classification | Определение направления сделки по тику |
| 455 | Footprint Charting Data | Матрица объёма внутри свечи |
| 456 | Square Root Law of Market Impact | Проскальзывание ∝ корню из объёма |

---

## 13. Портфельная теория

| # | Название | За что отвечает |
|---|----------|----------------|
| 457 | Markowitz Mean-Variance | Оптимизация портфеля по risk-return |
| 458 | Efficient Frontier | Граница оптимальных портфелей |
| 459 | Minimum Variance Portfolio | Портфель с минимальной дисперсией |
| 460 | Maximum Sharpe Portfolio | Портфель с максимальным Sharpe |
| 461 | Risk Parity | Равный вклад риска каждого актива |
| 462 | Hierarchical Risk Parity (HRP) | Иерархическая кластеризация портфеля |
| 463 | Black-Litterman Model | Комбинация рыночного равновесия и мнений |
| 464 | CAPM (Capital Asset Pricing Model) | Ожидаемая доходность через систематический риск |
| 465 | APT (Arbitrage Pricing Theory) | Многофакторная модель ценообразования |
| 466 | Fama-French 3-Factor | Market + Size + Value |
| 467 | Fama-French 5-Factor | + Profitability + Investment |
| 468 | Carhart 4-Factor | + Momentum |
| 469 | Correlation Matrix | Матрица корреляций активов |
| 470 | Covariance Matrix | Ковариационная матрица |
| 471 | Shrinkage Estimator (Ledoit-Wolf) | Сжатие ковариационной матрицы |
| 472 | Exponentially Weighted Covariance | Ковариация с экспоненциальными весами |
| 473 | Marginal Contribution to Risk | Предельный вклад актива в риск |
| 474 | Diversification Ratio | Взвешенный риск / портфельный риск |
| 475 | Maximum Decorrelation Portfolio | Минимизация корреляции между активами |
| 476 | Equal Weight Portfolio | Равновзвешенный портфель (1/N) |
| 477 | Inverse Volatility Portfolio | Вес = 1/vol |
| 478 | Maximum Entropy Portfolio | Максимум энтропии весов |
| 479 | Copula-Based Dependence | Многомерная зависимость через копулы |
| 480 | Hierarchical Risk Parity (HRP) (уточнение) | Иерархическая кластеризация портфеля |

---

## 14. Спектральный и частотный анализ

| # | Название | За что отвечает |
|---|----------|----------------|
| 481 | Fourier Transform | Разложение на частоты |
| 482 | Fast Fourier Transform (FFT) | Быстрое вычисление Фурье |
| 483 | Short-Time Fourier Transform (STFT) | Фурье с скользящим окном |
| 484 | Spectrogram | Визуализация STFT |
| 485 | Power Spectral Density | Мощность на каждой частоте |
| 486 | Wavelet Transform (CWT/DWT) | Время-частотный анализ |
| 487 | Scalogram | Визуализация вейвлет-коэффициентов |
| 488 | Wavelet Denoising (уточнение) | Фильтрация шума |
| 489 | Wavelet Coherence (уточнение) | Когерентность по частотам |
| 490 | Cross-Wavelet Transform | Совместный вейвлет-анализ двух рядов |
| 491 | Lomb-Scargle Periodogram (уточнение) | Спектр для неравномерных данных |
| 492 | Multitaper Spectral Estimation | Снижение дисперсии спектральной оценки |
| 493 | Singular Spectrum Analysis (SSA) | Разложение на компоненты |
| 494 | Empirical Mode Decomposition (EMD) | Адаптивное разложение |
| 495 | Ensemble EMD (EEMD) | EMD с добавлением шума |
| 496 | CEEMDAN | Улучшенный EEMD |
| 497 | Hilbert-Huang Transform | Мгновенная частота |
| 498 | Instantaneous Frequency | Частота в каждый момент времени |
| 499 | Band-Pass Filter | Выделение диапазона частот |
| 500 | Hodrick-Prescott Filter | Разделение на тренд и цикл |
| 501 | Baxter-King Filter | Полосовой фильтр для циклов |
| 502 | Christiano-Fitzgerald Filter | Адаптивный полосовой фильтр |
| 503 | Butterworth Filter | Максимально плоская амплитудная характеристика |
| 504 | Kalman Filter (как smoother) | Сглаживание через скрытое состояние |
| 505 | Wiener Filter | Оптимальное линейное сглаживание |
| 506 | Multitaper Spectral Estimation (уточнение) | Снижение дисперсии спектральной оценки |

---

## 15. Теории и концепции

| # | Название | За что отвечает |
|---|----------|----------------|
| 507 | Efficient Market Hypothesis (EMH) | Цена отражает всю информацию |
| 508 | Adaptive Market Hypothesis (AMH) | Рынки адаптируются (Lo) |
| 509 | Fractal Market Hypothesis (FMH) | Ликвидность и горизонты инвесторов |
| 510 | Modern Portfolio Theory (MPT) | Оптимизация risk-return |
| 511 | Random Walk Theory | Цены — случайное блуждание |
| 512 | Mean Reversion Theory | Цены возвращаются к среднему |
| 513 | Momentum Theory | Тренды продолжаются |
| 514 | Dow Theory | Тренды, объём, подтверждение |
| 515 | Wyckoff Method | Накопление/распределение, спрос/предложение |
| 516 | Smart Money Concept (SMC) | Действия крупных игроков |
| 517 | Market Microstructure Theory | Как формируются цены |
| 518 | Information Asymmetry | Неравный доступ к информации |
| 519 | Behavioral Finance | Когнитивные искажения трейдеров |
| 520 | Prospect Theory (Kahneman-Tversky) | Асимметрия восприятия прибыли/убытка |
| 521 | Herd Behavior | Стадное поведение |
| 522 | Anchoring Effect | Привязка к якорным ценам |
| 523 | Disposition Effect | Склонность фиксировать прибыль рано, убыток поздно |
| 524 | Overconfidence Bias | Чрезмерная уверенность |
| 525 | Confirmation Bias | Поиск подтверждающей информации |
| 526 | Gambler's Fallacy | Ошибка игрока |
| 527 | Fat Tails (Leptokurtic Distribution) | Толстые хвосты распределения |
| 528 | Long Memory | Долгосрочная автокорреляция |
| 529 | Volatility Clustering | Кластеризация волатильности |
| 530 | Leverage Effect | Отрицательная корреляция доходности и vol |
| 531 | Calendar Effects | Сезонные аномалии |
| 532 | Post-Earnings Announcement Drift | Дрейф после отчётов |
| 533 | Pairs Trading (Statistical Arbitrage) | Торговля спредами коинтегрированных пар |
| 534 | Statistical Arbitrage | Статистический арбитраж |
| 535 | Market Making | Создание ликвидности |
| 536 | High-Frequency Trading (HFT) | Высокочастотная торговля |
| 537 | Latency Arbitrage | Арбитраж задержек |
| 538 | Cross-Exchange Arbitrage | Арбитраж между биржами |
| 539 | Triangular Arbitrage | Треугольный арбитраж |
| 540 | Funding Rate Arbitrage | Арбитраж ставок финансирования |
| 541 | Basis Trade | Торговля базисом (spot vs futures) |
| 542 | Carry Trade | Заработок на разнице ставок |
| 543 | Delta-Neutral Hedging | Хеджирование дельты |
| 544 | Gamma Scalping | Заработок на гамме |
| 545 | Vega Trading | Торговля волатильностью |
| 546 | Theta Decay Strategy | Заработок на распаде времени |
| 547 | Adaptive Market Hypothesis (AMH) (уточнение) | Рынки адаптируются со временем |

---

## 16. Фильтры и сглаживание

| # | Название | За что отвечает |
|---|----------|----------------|
| 548 | Simple Moving Average Filter | Базовое сглаживание |
| 549 | Exponential Smoothing | Экспоненциальное сглаживание |
| 550 | Double Exponential Smoothing (Holt) | Учёт тренда |
| 551 | Triple Exponential Smoothing (Holt-Winters) | Учёт тренда и сезонности |
| 552 | Savitzky-Golay Filter | Полиномиальное сглаживание |
| 553 | Gaussian Filter | Гауссово сглаживание |
| 554 | Median Filter | Медианная фильтрация выбросов |
| 555 | Kalman Smoother | Оптимальное сглаживание |
| 556 | LOWESS / LOESS | Локально взвешенная регрессия |
| 557 | Hodrick-Prescott Filter | Разделение на тренд и цикл |
| 558 | Baxter-King Filter (уточнение) | Полосовой фильтр для циклов |
| 559 | Christiano-Fitzgerald Filter (уточнение) | Адаптивный полосовой фильтр |
| 560 | Butterworth Filter (уточнение) | Плоская амплитудная характеристика |
| 561 | Wiener Filter (уточнение) | Оптимальное линейное сглаживание |
| 562 | Kalman Filter (уточнение) | Оптимальная оценка скрытого состояния |
| 563 | Band-Pass Filter (уточнение) | Выделение частотного диапазона |
| 564 | Low-Pass Filter | Пропуск низких частот |
| 565 | High-Pass Filter | Пропуск высоких частот |
| 566 | Notch Filter | Подавление конкретной частоты |
| 567 | Adaptive Filter | Самонастраивающийся фильтр |

---

## 17. Классификация и детекция

| # | Название | За что отвечает |
|---|----------|----------------|
| 568 | Anomaly Detection (Z-Score) | Обнаружение выбросов через Z-score |
| 569 | Anomaly Detection (IQR) | Обнаружение выбросов через межквартильный размах |
| 570 | Anomaly Detection (Isolation Forest) | Обнаружение аномалий через изоляцию |
| 571 | Anomaly Detection (DBSCAN) | Обнаружение аномалий как noise points |
| 572 | Change Point Detection (PELT) | Обнаружение точек изменения |
| 573 | Change Point Detection (Binary Segmentation) | Бинарная сегментация |
| 574 | Change Point Detection (CUSUM) | Кумулятивная сумма |
| 575 | Change Point Detection (BOCPD) | Байесовская онлайн-детекция |
| 576 | Structural Break Detection (Chow) | Структурный разрыв |
| 577 | Structural Break Detection (Bai-Perron) | Множественные разрывы |
| 578 | Trend Detection (Mann-Kendall) | Непараметрический тест тренда |
| 579 | Trend Detection (Sen's Slope) | Наклон тренда |
| 580 | Seasonality Detection (ACF) | Автокорреляция для сезонности |
| 581 | Seasonality Detection (Periodogram) | Спектральный анализ сезонности |
| 582 | Regime Detection (HMM) | Определение рыночного режима |
| 583 | Regime Detection (Threshold) | Пороговая детекция |
| 584 | Outlier Detection (Mahalanobis) | Многомерные выбросы |
| 585 | Outlier Detection (Local Outlier Factor) | Локальная плотность |
| 586 | Pattern Recognition (Template Matching) | Совпадение с шаблоном |
| 587 | Pattern Recognition (Dynamic Time Warping) | Гибкое сравнение рядов |
| 588 | Regime-Switching Model (уточнение) | Переключение между моделями |
| 589 | Diebold-Mariano Test (уточнение) | Сравнение точности двух прогнозов |

---

## 18. Оценка и верификация моделей

| # | Название | За что отвечает |
|---|----------|----------------|
| 590 | AIC (Akaike Information Criterion) | Критерий выбора модели |
| 591 | BIC (Bayesian Information Criterion) | Штраф за сложность |
| 592 | HQIC (Hannan-Quinn) | Компромисс AIC/BIC |
| 593 | Log-Likelihood | Логарифм правдоподобия |
| 594 | Likelihood Ratio Test | Сравнение вложенных моделей |
| 595 | Wald Test | Тест значимости параметров |
| 596 | Score Test (Lagrange Multiplier) | Тест производной лог-правдоподобия |
| 597 | Durbin-Watson Test | Тест автокорреляции остатков |
| 598 | Breusch-Godfrey Test | Тест автокорреляции высших порядков |
| 599 | White Test | Тест гетероскедастичности |
| 600 | Breusch-Pagan Test | Тест гетероскедастичности |
| 601 | Jarque-Bera Test | Тест нормальности |
| 602 | Shapiro-Wilk Test | Тест нормальности (малые выборки) |
| 603 | Kolmogorov-Smirnov Test | Тест согласия распределения |
| 604 | Anderson-Darling Test | Тест нормальности (робастный) |
| 605 | Mincer-Zarnowitz Regression | Тест качества прогноза |
| 606 | Diebold-Mariano Test | Сравнение точности двух прогнозов |
| 607 | Clark-West Test | Сравнение прогнозов с вложенной моделью |
| 608 | Reality Check (White) | Проверка лучшей модели из множества |
| 609 | Superior Predictive Ability (Hansen) | Улучшенный reality check |
| 610 | Model Confidence Set | Набор лучших моделей |
| 611 | Bootstrap (Stationary) | Бутстрэп для временных рядов |
| 612 | Block Bootstrap | Бутстрэп с блоками |
| 613 | Moving Block Bootstrap | Скользящий блочный бутстрэп |
| 614 | Sieve Bootstrap | Параметрический бутстрэп |
| 615 | Monte Carlo Simulation | Стохастическая симуляция |
| 616 | Bootstrap Hypothesis Testing | Тестирование гипотез через бутстрэп |
| 617 | Permutation Test | Перестановочный тест |
| 618 | Cross-Validation (K-Fold) | Валидация модели |
| 619 | Leave-One-Out CV | Валидация с одним наблюдением |
| 620 | Nested Cross-Validation | Вложенная валидация |
| 621 | Rolling Window Validation | Скользящее окно валидации |
| 622 | Diebold-Mariano Test (уточнение) | Сравнение точности двух прогнозов |

---

## 19. Математические функции и распределения

| # | Название | За что отвечает |
|---|----------|----------------|
| 623 | Normal Distribution | Базовое распределение доходностей |
| 624 | Student's t-Distribution | Распределение с толстыми хвостами |
| 625 | Generalized Error Distribution (GED) | Обобщённое распределение ошибок |
| 626 | Skewed t-Distribution | Асимметричное t-распределение |
| 627 | Stable Distribution (Levy) | Устойчивое распределение |
| 628 | Pareto Distribution | Power-law хвосты |
| 629 | Cauchy Distribution | Без конечных моментов |
| 630 | Laplace Distribution | Двойное экспоненциальное |
| 631 | Log-Normal Distribution | Лог-нормальное (для цен) |
| 632 | Poisson Distribution | Распределение числа событий |
| 633 | Exponential Distribution | Время между событиями |
| 634 | Gamma Distribution | Обобщение экспоненциального |
| 635 | Weibull Distribution | Распределение времени жизни |
| 636 | Beta Distribution | Распределение на [0,1] |
| 637 | Dirichlet Distribution | Многомерное бета-распределение |
| 638 | Copula (Gaussian) | Многомерная зависимость |
| 639 | Copula (t-Copula) | Зависимость с толстыми хвостами |
| 640 | Copula (Clayton) | Нижняя хвостовая зависимость |
| 641 | Copula (Gumbel) | Верхняя хвостовая зависимость |
| 642 | Copula (Frank) | Симметричная зависимость |
| 643 | Maximum Likelihood Estimation (MLE) | Оценка параметров |
| 644 | Method of Moments | Оценка параметров через моменты |
| 645 | Generalized Method of Moments (GMM) | Обобщённый метод моментов |
| 646 | Bayesian Estimation | Байесовская оценка параметров |
| 647 | MCMC | Семплирование из posterior |
| 648 | Metropolis-Hastings | Алгоритм MCMC |
| 649 | Gibbs Sampling | MCMC через условные распределения |
| 650 | Hamiltonian Monte Carlo | MCMC с градиентами |
| 651 | Importance Sampling | Снижение дисперсии Monte Carlo |
| 652 | Stratified Sampling | Стратифицированный семплинг |
| 653 | Latin Hypercube Sampling | Равномерное покрытие пространства |
| 654 | Quasi-Monte Carlo | Детерминированные последовательности |
| 655 | Sobol Sequence | Квазислучайная последовательность |
| 656 | Halton Sequence | Квазислучайная последовательность |
| 657 | Kernel Density Estimation | Непараметрическая оценка плотности |
| 658 | Gaussian Process Regression | Байесовская регрессия |
| 659 | Bayesian Neural Network | Нейросеть с неопределённостью |
| 660 | Dropout as Bayesian Approximation | MC Dropout для неопределённости |
| 661 | Variance Gamma Process | Чистый прыжковый процесс |

---

## 20. Дополнительные алгоритмы и процедуры

| # | Название | За что отвечает |
|---|----------|----------------|
| 662 | Z-Score Normalization | Стандартизация признаков |
| 663 | Min-Max Scaling | Нормализация в [0,1] |
| 664 | Robust Scaling | Масштабирование через median/IQR |
| 665 | Log Transform | Логарифмическое преобразование |
| 666 | Box-Cox Transform | Стабилизация дисперсии |
| 667 | Yeo-Johnson Transform | Обобщение Box-Cox |
| 668 | Differencing | Разность для стационарности |
| 669 | Seasonal Differencing | Сезонная разность |
| 670 | Percentage Change | Процентное изменение |
| 671 | Log Returns | Логарифмические доходности |
| 672 | Cumulative Returns | Кумулятивные доходности |
| 673 | Rolling Statistics | Скользящие статистики |
| 674 | Expanding Statistics | Расширяющиеся статистики |
| 675 | Lag Features | Лаговые признаки |
| 676 | Rolling Correlation | Скользящая корреляция |
| 677 | Rolling Beta | Скользящий бета |
| 678 | Rolling Sharpe | Скользящий Sharpe |
| 679 | Z-Score of Rolling Mean | Стандартизация скользящего среднего |
| 680 | Rate of Change (ROC) | Скорость изменения |
| 681 | Momentum | Разница цен |
| 682 | Acceleration | Производная моментума |
| 683 | Jerk | Производная ускорения |
| 684 | Autocorrelation Function (ACF) | Автокорреляция по лагам |
| 685 | Partial Autocorrelation (PACF) | Частичная автокорреляция |
| 686 | Cross-Correlation | Взаимная корреляция двух рядов |
| 687 | Dynamic Time Warping (DTW) | Расстояние между временными рядами |
| 688 | Pearson Correlation | Линейная корреляция |
| 689 | Spearman Correlation | Ранговая корреляция |
| 690 | Kendall Tau | Корреляция конкордантных пар |
| 691 | Mutual Information | Нелинейная взаимная информация |
| 692 | Transfer Entropy | Направленная передача информации |
| 693 | Granger Causality | Предсказательная причинность |
| 694 | Convergent Cross Mapping | Причинность для нелинейных систем |
| 695 | Conditional Entropy | Условная энтропия |
| 696 | Cross-Entropy | Мера различия распределений |
| 697 | KL Divergence | Расстояние Кульбака-Лейблера |
| 698 | Jensen-Shannon Divergence | Симметричная KL-дивергенция |
| 699 | Wasserstein Distance | Расстояние Вассерштейна |
| 700 | Cosine Similarity | Косинусное сходство |
| 701 | Euclidean Distance | Евклидово расстояние |
| 702 | Manhattan Distance | Манхэттенское расстояние |
| 703 | Mahalanobis Distance | Махаланобисово расстояние |
| 704 | Hausdorff Distance | Расстояние Хаусдорфа |
| 705 | Edit Distance (Levenshtein) | Расстояние редактирования |
| 706 | Fréchet Distance | Расстояние Фреше |
| 707 | Dynamic Time Warping (DTW) (уточнение) | Расстояние между временными рядами |
| 708 | Wasserstein Distance (уточнение) | Расстояние Вассерштейна |

---

## 21. Управление капиталом и размером позиции

| # | Название | За что отвечает |
|---|----------|----------------|
| 709 | Kelly Criterion | Оптимальная доля капитала на сделку |
| 710 | Fractional Kelly | Дробный Келли для снижения просадок |
| 711 | Optimal f (Ральф Винс) | Максимизация геометрического роста |
| 712 | Risk of Ruin | Вероятность полного разорения |
| 713 | Fixed Fractional Position Sizing | Фиксированный процент от депозита |
| 714 | Fixed Ratio Position Sizing (Райан Джонс) | Увеличение позиции после «дельта»-профита |
| 715 | Core Equity Method | Расчёт на основе свободной маржи |
| 716 | Expected Shortfall (CVaR) | Ожидаемые потери при пробитии VaR |
| 717 | Maximum Adverse Excursion (MAE) | Максимальное движение против позиции |
| 718 | Maximum Favorable Excursion (MFE) | Максимальное движение в прибыль |
| 719 | E-Ratio | Математическое ожидание стратегии |

---

## 22. Криптоспецифичные и On-Chain метрики

| # | Название | За что отвечает |
|---|----------|----------------|
| 720 | Open Interest (OI) | Количество открытых позиций на фьючерсах |
| 721 | Open Interest Delta | Изменение OI |
| 722 | Funding Rate | Ставка финансирования бессрочных фьючерсов |
| 723 | Liquidation Heatmaps / Cascades | Уровни скопления ликвидаций |
| 724 | Long/Short Ratio | Соотношение лонгов к шортам |
| 725 | NVT Ratio (Network Value to Transactions) | P/E ratio для биткоина |
| 726 | SOPR (Spent Output Profit Ratio) | Продажа в плюс или минус |
| 727 | NUPL (Net Unrealized Profit/Loss) | Нереализованная прибыль/убыток сети |
| 728 | Puell Multiple | Прибыльность майнеров |
| 729 | Hash Ribbons | Капитуляция майнеров |
| 730 | Realized Capitalization | Капитализация по цене последнего движения |
| 731 | Crypto Fear & Greed Index | Индекс страха и жадности |
| 732 | Liveliness | Поведение «китов» |
| 733 | MVRV Z-Score | Рыночная vs реализованная стоимость |
| 734 | Pi Cycle Top Indicator | Двойная EMA для определения пиков |

---

## 23. Дополнительные технические индикаторы

| # | Название | За что отвечает |
|---|----------|----------------|
| 735 | TTM Squeeze (John Carter) | «Сжатие» волатильности перед импульсом |
| 736 | TSI (True Strength Index) | Осциллятор моментума с двойным сглаживанием |
| 737 | KST (Know Sure Thing) | Сводный моментум по 4 таймфреймам |
| 738 | QQE (Quantitative Qualitative Estimation) | Модифицированный RSI с динамическими уровнями |
| 739 | Williams VIX Fix | Синтетический VIX для любого актива |
| 740 | Chande Kroll Stop | Волатильные стопы на основе ATR |
| 741 | Elder Impulse System | EMA + MACD-гистограмма |
| 742 | Bill Williams Alligator | 3 сдвинутые скользящие средние |
| 743 | Bill Williams Fractals | Локальные экстремумы из 5 свечей |
| 744 | MESA Adaptive Moving Average (MAMA & FAMA) | Адаптивные к фазе рынка |
| 745 | Camarilla Pivots | Внутридневные уровни поддержки/сопротивления |
| 746 | Volume Spread Analysis (VSA) | Анализ свечи относительно объёма |

---

## 24. Эконометрика и Deep Learning

| # | Название | За что отвечает |
|---|----------|----------------|
| 747 | ARIMA | Классическая линейная модель прогнозирования |
| 748 | SARIMA | ARIMA с сезонностью |
| 749 | VAR (Vector Autoregression) | Прогноз нескольких взаимосвязанных активов |
| 750 | VECM (Vector Error Correction Model) | Модель коррекции ошибок для коинтегрированных пар |
| 751 | Facebook Prophet | Модель для рядов с сезонностью и праздниками |
| 752 | N-BEATS | Deep Learning для временных рядов |
| 753 | DeepAR | Вероятностная нейросеть от Amazon |
| 754 | TCN (Temporal Convolutional Networks) | Свёрточные сети с долгой памятью |
| 755 | TabNet | Deep Learning для табличных данных |
| 756 | Boruta Algorithm | Жёсткий отбор важных фичей |
| 757 | Information Coefficient (IC) / Rank IC | Сила предсказательной способности |

---

## 25. Микроструктура стакана (L2) и Market Impact

| # | Название | За что отвечает |
|---|----------|----------------|
| 758 | Micro-Price | Взвешенная средняя спреда с учётом объёма |
| 759 | Limit Order Book Pressure | Давление лимитных ордеров на цену |
| 760 | Queue Position Algorithm | Вероятность исполнения лимитного ордера |
| 761 | Tick Rule Classification | Определение направления сделки по тику |
| 762 | Footprint Charting Data | Матрица объёма внутри свечи |
| 763 | Square Root Law of Market Impact | Проскальзывание ∝ корню из объёма |

---

## 26. DeFi математика и крипто-арбитраж

| # | Название | За что отвечает |
|---|----------|----------------|
| 764 | AMM Constant Product Formula (x × y = k) | Ценообразование DEX |
| 765 | Impermanent Loss | Убыток провайдера ликвидности |
| 766 | Flash Loan Arbitrage Algorithm | Безрисковый арбитраж через атомарные кредиты |
| 767 | MEV Sandwich Attack | Выявление крупной транзакции в мемпуле |
| 768 | Yield APY Optimization | Сложный процент для авто-компаундинга |

---

## 27. Опционное ценообразование и «Греки»

| # | Название | За что отвечает |
|---|----------|----------------|
| 769 | Black-Scholes Model | Ценообразование опционов |
| 770 | Binomial Options Pricing Model | Биномиальная модель опционов |
| 771 | Option Delta | Чувствительность к цене базового актива |
| 772 | Option Gamma | Скорость изменения Дельты |
| 773 | Option Theta | Распад стоимости со временем |
| 774 | Option Vega | Чувствительность к волатильности |
| 775 | Option Rho | Чувствительность к процентным ставкам |
| 776 | Vanna | Чувствительность Дельты к волатильности |
| 777 | Volga / Vomma | Чувствительность Веги к волатильности |
| 778 | Charm | Влияние распада времени на Дельту |
| 779 | Speed | Скорость изменения Гаммы |

---

## Итого: 779 формул, алгоритмов, теорий и метрик

| Категория | Количество |
|-----------|-----------|
| Индикаторы тренда | 48 |
| Осцилляторы и моментум | 40 |
| Волатильность | 29 |
| Объёмные индикаторы | 27 |
| Статистические метрики | 39 |
| Риск-менеджмент | 34 |
| Стохастические модели | 61 |
| Коинтеграция и парный трейдинг | 11 |
| Machine Learning и оптимизация | 63 |
| Технический анализ — паттерны | 46 |
| Волновой и фрактальный анализ | 30 |
| Order Flow и микроструктура | 28 |
| Портфельная теория | 24 |
| Спектральный и частотный анализ | 26 |
| Теории и концепции | 41 |
| Фильтры и сглаживание | 20 |
| Классификация и детекция | 22 |
| Оценка и верификация моделей | 33 |
| Математические функции | 39 |
| Дополнительные алгоритмы | 47 |
| Управление капиталом | 11 |
| Криптоспецифичные метрики | 15 |
| Доп. технические индикаторы | 12 |
| Эконометрика и Deep Learning | 11 |
| Микроструктура стакана | 6 |
| DeFi математика | 5 |
| Опционное ценообразование | 11 |
| **ВСЕГО** | **779** |
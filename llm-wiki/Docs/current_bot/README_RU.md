# AI Trading Bot - Руководство по запуску MVP (Вариант А+)

Это руководство поможет вам запустить торгового бота локально на вашем ПК, подключиться к **Bybit Testnet** без риска потери реальных денег и открыть визуальный веб-дашборд.

---

## Шаг 1: Получение ключей Bybit Testnet (Демо-счет)

Bybit Testnet — это песочница, которая полностью копирует реальную биржу, но использует виртуальные депозиты.
Вы уже предоставили свои ключи от Bybit Testnet, поэтому они автоматически добавлены в код (`main.py`):
* **API Key**: `BaPkrSKaZBxVjqwBFM`
* **Secret Key**: `ELq4mzNsA9xjUIqBM5k5nVdMUKI7gwzGyoou`

В будущем, если вам нужно будет обновить ключи:
1. Перейдите на сайт [Bybit Testnet](https://testnet.bybit.com/).
2. Авторизуйтесь под своим аккаунтом.
3. Перейдите в раздел **API Management** и создайте новый API-ключ V5 (System-generated) с правами на торговлю контрактами (Contract -> Orders/Positions).

## Шаг 2: Настройка исходного кода бота

1. Процесс ручной настройки ключей уже выполнен! Ваши ключи прописаны в файле `main.py` автоматически.

## Шаг 3: Установка зависимостей

1. Откройте терминал.
2. Активируйте виртуальное окружение (используя полный путь):
   ```bash
   source /Users/Apple/Documents/AI_Traiding_Bot/venv/bin/activate
   ```
3. Установите зависимости (включая локальный `pybit-master`):
   ```bash
   /Users/Apple/Documents/AI_Traiding_Bot/venv/bin/pip install -r /Users/Apple/Documents/AI_Traiding_Bot/requirements.txt
   ```

## Шаг 4: Запуск торгового бота

1. Откройте терминал.
2. Если окружение ещё не активировано, активируйте его:
   ```bash
   source /Users/Apple/Documents/AI_Traiding_Bot/venv/bin/activate
   ```
3. Запустите главный скрипт, указав полный путь к интерпретатору и файлу:
   ```bash
   /Users/Apple/Documents/AI_Traiding_Bot/venv/bin/python /Users/Apple/Documents/AI_Traiding_Bot/main.py
   ```
4. В терминале вы увидите логи подключения:
   > `INFO - Successfully connected to Bybit WS`
   > `INFO - Subscribed to topic: kline.1.BTCUSDT`
   > `INFO - Starting Trading Bot for BTCUSDT...`

Бот начнет скачивать рыночные данные в реальном времени порциями по 1 минуте.

По умолчанию реальная торговля отключена. Чтобы включить реальные тестовые ордера, в `main.py` установите:
* `LIVE_TRADING = True`
* `CATEGORY = "linear"` (по умолчанию)
* `DEMO_TRADING = True` если ключи созданы в Demo Trading (обычно это требуется для Testnet Demo)
* `REST_POLL_INTERVAL = 2` чтобы ускорить обновление свечей при отсутствии WebSocket

## Шаг 5: Проверка связи с Bybit и тестовая сделка на 1000 USDT

Ниже — минимальный скрипт, который подтверждает связь с Bybit Testnet и выставляет рыночный ордер на покупку BTC/USDT примерно на 1000 USDT (с учетом шага лота):

```bash
/Users/Apple/Documents/AI_Traiding_Bot/venv/bin/python - <<'PY'
import asyncio
from decimal import Decimal, ROUND_DOWN
from pybit.unified_trading import HTTP
from src.execution.executor import BybitExecutor
from src.core.models import Signal

API_KEY = "BaPkrSKaZBxVjqwBFM"
API_SECRET = "ELq4mzNsA9xjUIqBM5k5nVdMUKI7gwzGyoou"
CATEGORY = "linear"
SYMBOL = "BTCUSDT"
SPEND_USDT = Decimal("1000")
TESTNET = True

def get_qty_for_usdt(http_session):
    tick = http_session.get_tickers(category=CATEGORY, symbol=SYMBOL)
    if tick.get("retCode") != 0:
        raise RuntimeError(f"get_tickers failed: {tick}")
    last_price = Decimal(tick["result"]["list"][0]["lastPrice"])

    info = http_session.get_instruments_info(category=CATEGORY, symbol=SYMBOL)
    if info.get("retCode") != 0:
        raise RuntimeError(f"get_instruments_info failed: {info}")
    lot = info["result"]["list"][0]["lotSizeFilter"]
    step = Decimal(lot["qtyStep"])
    min_qty = Decimal(lot["minOrderQty"])

    qty = (SPEND_USDT / last_price).quantize(step, rounding=ROUND_DOWN)
    if qty < min_qty:
        qty = min_qty
    return last_price, qty

async def main():
    http_session = HTTP(testnet=TESTNET, api_key=API_KEY, api_secret=API_SECRET)
    last_price, qty = get_qty_for_usdt(http_session)
    print(f"Last price: {last_price}")
    print(f"Calculated qty for {SPEND_USDT} USDT: {qty}")

    executor = BybitExecutor(API_KEY, API_SECRET, testnet=TESTNET, live_trading=True, category=CATEGORY)
    await executor.start()

    signal = Signal(
        symbol=SYMBOL,
        direction="BUY",
        entry_price=float(last_price),
        expected_sl=0,
        expected_tp=0,
    )

    order = await executor.execute_signal(signal, quantity=float(qty))
    print("Order response:")
    print(order)
    await executor.stop()

if __name__ == "__main__":
    asyncio.run(main())
PY
```

Если видите ошибку `ErrCode: 10003` — ключи недействительны или не имеют прав на торговлю. Проверьте, что:
* ключи созданы именно в **Bybit Testnet**
* включены права **Contract -> Orders/Positions**

## Шаг 6: Открытие визуального Дашборда (Web UI)

Если вы видите ошибки вида `Handshake status 503 Service Temporarily Unavailable` при подключении WebSocket,
это означает временную недоступность публичного WS в Demo Testnet. В таком случае бот автоматически перейдет
на REST-поллинг для получения последних свечей.

Каждую секунду бот автоматически записывает своё состояние (баланс, цены, открытые ордера, риск-менеджер) в локальный файл `data.json`. Мы написали красивый дашборд для чтения этих данных.

1. **Не закрывая терминал с запущенным ботом**, откройте любой современный веб-браузер (Chrome, Safari).
2. Нажмите `Cmd + O` или просто перетащите файл `web/dashboard.html` из папки проекта прямо в окно браузера.
3. Откроется интерфейс **"ALGO COMMAND CENTER"**. 
4. Интерфейс будет сам обновляться каждую секунду, парся `data.json`. Если статус подсвечивается зеленым `"RUNNING LIVE"` — значит дашборд успешно перехватывает данные от бота.

---

## Как это работает под капотом?
* **Изолированность:** Мы не используем тяжелых баз данных. Бот "общается" с дашбордом через плоский файл `data.json`. Это идеально для стадии MVP.
* **Продвинутая Стратегия:** В файл `src/strategy/strategy.py` встроена логика AdvancedStrategy. Она рассчитывает не только скользящие средние (EMA Crossover), но и проверяет осциллятор **RSI** (не входит ли рынок в перегрев), а размер стоп-лосса динамически считает через **ATR** (волатильность).
* **Kill-Switch:** Обратите внимание на карточку Risk Manager в дашборде. Если бот проиграет 5% депозита, Kill-Switch загорится красным и заблокирует торговлю.

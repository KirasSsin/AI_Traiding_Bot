---
title: "Отчёты и артефакты (reporter): что сохраняется после прогона"
section: "06-бэктест-и-валидация"
status: filled
money_core: false
updated: 2026-06-26
source_files: src/backtest/reporter.py
---

# Отчёты и артефакты (reporter): что сохраняется после прогона

**TL;DR:** После каждого бэктеста функция `write_artifacts` сохраняет на диск до четырёх файлов — CSV-журнал сделок, CSV-кривую капитала, JSON с итоговыми метриками и интерактивный HTML-отчёт с графиками. Если библиотека графиков недоступна, бот сохраняет упрощённый HTML вместо того чтобы упасть с ошибкой.

## Простыми словами

Представьте, что бот только что «сыграл» 500 воображаемых сделок за последние два года — это и есть бэктест. Теперь у него есть куча чисел: когда купил, когда продал, сколько заработал или потерял на каждой сделке, как менялся баланс от первой до последней свечи.

Чтобы вы могли потом открыть всё это и разобраться, система сохраняет результаты в файлы — **артефакты** (от английского *artifact* — в разработке так называют файлы, созданные в результате работы программы). Артефакты бэктеста — это:

- **trade_log.csv** — «журнал торгов»: каждая строчка — одна сделка с датой, ценой входа/выхода, прибылью.
- **equity_curve.csv** — «кривая капитала»: как менялся баланс по каждому бару (свече).
- **metrics_summary.json** — «сводка с числами»: все итоговые показатели качества стратегии.
- **report.html** — «красивый отчёт»: открываете в браузере — видите два интерактивных графика.

**Аналогия:** представьте бухгалтера, который после закрытия месяца печатает три документа — оборотную ведомость, итоговый P&L и красивую презентацию для директора. Функция `write_artifacts` — это тот самый бухгалтер.

**CSV** (*Comma-Separated Values*, «значения через запятую») — простейший табличный формат. Открывается в Excel или Numbers.

**JSON** (*JavaScript Object Notation*) — текстовый формат для хранения структурированных данных «ключ: значение». Открывается любым текстовым редактором, понятен любому скрипту.

**HTML** (*HyperText Markup Language*) — формат веб-страниц. Отчёт открывается в обычном браузере.

**Equity curve** (кривая капитала) — график того, как меняется баланс счёта со временем. Если линия идёт вверх — стратегия зарабатывала, если вниз — теряла. В дашборде эта же кривая показывается интерактивно — см. [[equity-chart-and-drawdown]].

## Как это работает у нас

Вся логика сохранения сосредоточена в одном файле: `src/backtest/reporter.py`. В нём две функции.

### Шаг 1. write_artifacts — главная функция (src/backtest/reporter.py:8–42)

```python
def write_artifacts(
    config: Dict[str, Any],
    equity_df: pd.DataFrame,
    trades_df: pd.DataFrame,
    metrics: Dict[str, Any],
) -> Dict[str, str]:
```

Функция принимает четыре аргумента:

| Аргумент | Что это |
|----------|---------|
| `config` | Словарь из `config.yaml` — содержит секцию `output:` с настройками |
| `equity_df` | Таблица кривой капитала (бар + баланс на каждый момент) |
| `trades_df` | Таблица всех сделок прогона |
| `metrics` | Словарь итоговых метрик (Sharpe, Win Rate, PnL и т.д.) |

Функция возвращает словарь абсолютных путей к сохранённым файлам — например:
```json
{
  "trade_log.csv": "/Users/you/project/output/trade_log.csv",
  "equity_curve.csv": "/Users/you/project/output/equity_curve.csv",
  "metrics_summary.json": "/Users/you/project/output/metrics_summary.json",
  "report.html": "/Users/you/project/output/report.html"
}
```

Если какой-то тип файла отключён в конфиге — его ключа в словаре не будет.

### Шаг 2. Чтение настроек (src/backtest/reporter.py:14–21)

```python
output_cfg = config.get("output", {})
output_dir = str(output_cfg.get("directory", "output"))
os.makedirs(output_dir, exist_ok=True)

generate_csv  = bool(output_cfg.get("generate_csv",  True))
generate_json = bool(output_cfg.get("generate_json", True))
generate_html = bool(output_cfg.get("generate_html", True))
```

Функция читает секцию `output:` из [[configuration-and-settings|конфига]]. Все три флага по умолчанию включены (`True`). Это значит, что если вы запустили бэктест с `config.yaml` без изменений — получите все четыре файла сразу.

В реальном `config.yaml` проекта секция выглядит так (config.yaml:38–42):
```yaml
output:
  directory: "output"
  generate_html: true
  generate_csv: true
  generate_json: true
```

Директория создаётся автоматически через `os.makedirs(..., exist_ok=True)` — ошибки «папка не существует» не будет.

### Шаг 3. Сохранение CSV (src/backtest/reporter.py:23–29)

```python
if generate_csv:
    trade_path  = os.path.join(output_dir, "trade_log.csv")
    equity_path = os.path.join(output_dir, "equity_curve.csv")
    trades_df.to_csv(trade_path,  index=False)
    equity_df.to_csv(equity_path, index=False)
```

При `generate_csv: true` сохраняются два файла:

**trade_log.csv** — журнал сделок. Каждая строка — одна закрытая сделка. Столбцы определяются тем, что передаётся в `trades_df` из движка прогона (replay_engine). Подробнее о формате trades_df — в [[replay-engine-bar-by-bar]].

**equity_curve.csv** — кривая капитала. Каждая строка — один бар: временная метка и баланс в тот момент. Подробнее о формате equity_df — в [[replay-engine-metrics]].

Флаг `index=False` означает, что pandas не добавляет к CSV лишний столбец с номером строки (0, 1, 2, ...).

### Шаг 4. Сохранение JSON (src/backtest/reporter.py:31–35)

```python
if generate_json:
    metrics_path = os.path.join(output_dir, "metrics_summary.json")
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False)
```

**metrics_summary.json** — все итоговые метрики прогона в одном файле. Параметр `indent=2` делает JSON удобочитаемым (с отступами). Параметр `ensure_ascii=False` позволяет сохранять кириллицу без замены на `\uXXXX`-коды.

Содержимое словаря `metrics` формируется в `replay_engine.py` и включает такие показатели, как [[sharpe-sortino-metrics|Sharpe Ratio]], Win Rate, [[max-drawdown-winrate-rr|максимальная просадка]] и т.д. Подробнее — в [[replay-engine-metrics]].

### Шаг 5. Сохранение HTML-отчёта (src/backtest/reporter.py:37–41 + 45–105)

```python
if generate_html:
    report_path = os.path.join(output_dir, "report.html")
    _write_html_report(report_path, equity_df, trades_df, metrics)
```

За создание HTML отвечает вспомогательная функция `_write_html_report`. В ней два пути — основной и резервный.

**Основной путь (plotly доступен):** функция строит интерактивный отчёт с двумя графиками:

1. **Equity Curve** (верхний, строчный график) — кривая баланса по времени. Данные: `equity_df["timestamp"]` по оси X, `equity_df["balance"]` по оси Y (src/backtest/reporter.py:63–73).
2. **Trade PnL** (нижний, столбчатый график) — прибыль/убыток по каждой сделке. Данные: `trades_df["timestamp_close"]` по оси X, `trades_df["net_pnl"]` по оси Y (src/backtest/reporter.py:75–84).

**Plotly** — библиотека для создания интерактивных графиков в Python. В отчёте вы можете приближать, отдалять, наводить курсор на точки и видеть значения. Строка `include_plotlyjs="cdn"` означает, что браузер загружает библиотеку из интернета, а не встраивает её в файл — это делает HTML-файл компактным (src/backtest/reporter.py:87).

Параметры графика: высота 900 пикселей, заголовок «AI Trading Bot Backtest Report», вертикальный отступ между графиками 12% (src/backtest/reporter.py:55–61, 86).

**Резервный путь (graceful fallback):** если plotly не установлен или упал с ошибкой — весь `try` блок перехватывает исключение, и вместо падения программы создаётся минимальный статический HTML с таблицей метрик (src/backtest/reporter.py:88–105):

```python
except Exception:  # noqa: BLE001 — plotly optional/unstable; fall back to minimal static HTML
```

**Graceful fallback** («мягкий откат») — принцип, при котором при возникновении ошибки программа не падает, а переключается на упрощённый, но рабочий режим. Здесь: нет красивого HTML → есть простой HTML. Прогон не прерывается.

Резервная страница содержит только таблицу с двумя столбцами «Metric» и «Value» — её можно открыть в любом браузере даже без интернета.

### Как write_artifacts вызывается в проекте

Функция используется в двух местах:

1. **`run_backtest.py:42`** — при запуске бэктеста из командной строки. После сохранения пути файлов печатаются в терминал в виде JSON.

2. **`app.py:552`** — при нажатии кнопки «Сохранить отчёт» в Streamlit-[[dashboard-overview|дашборде]]. Кнопка сохраняет текущие параметры из UI (не обязательно те же, что в `config.yaml` — пользователь мог их изменить через слайдеры).

## Примеры / сценарии

### Сценарий 1: стандартный прогон из командной строки

Предположим, вы запустили:
```bash
python run_backtest.py --config config.yaml
```

После завершения прогона в терминале появится:
```text
=== Metrics Summary ===
sharpe_ratio: 1.432000
win_rate: 0.523000
...

=== Artifacts ===
{
  "trade_log.csv": "/Users/you/project/output/trade_log.csv",
  "equity_curve.csv": "/Users/you/project/output/equity_curve.csv",
  "metrics_summary.json": "/Users/you/project/output/metrics_summary.json",
  "report.html": "/Users/you/project/output/report.html"
}
```

В папке `output/` появятся четыре файла. Откройте `report.html` в браузере — увидите два интерактивных графика. Откройте `trade_log.csv` в Excel — получите полный список сделок.

### Сценарий 2: отключение HTML для автоматического пайплайна

В CI/CD или при автоматических прогонах HTML-отчёт не нужен. Отключите в конфиге:
```yaml
output:
  directory: "output"
  generate_csv: true
  generate_json: true
  generate_html: false   # ← отключили
```

Функция создаст только CSV + JSON. Ключ `"report.html"` в возвращаемом словаре не появится.

### Сценарий 3: plotly не установлен (graceful fallback)

Если вы запустили бэктест в среде без plotly (например, минимальный Docker-образ), вместо интерактивного отчёта будет создан простой `report.html`:
```html
<h1>Backtest Report</h1>
<h2>Metrics</h2>
<table>
  <tr><th>Metric</th><th>Value</th></tr>
  <tr><td>sharpe_ratio</td><td>1.432</td></tr>
  ...
</table>
```

Прогон завершится без ошибок. CSV и JSON сохранятся в штатном режиме.

### Сценарий 4: сохранение через дашборд

В дашборде (app.py) пользователь меняет параметры через слайдеры и нажимает «Сохранить отчёт с текущими параметрами». Дашборд вызывает `write_artifacts` с текущим `working_cfg` (который уже включает изменения пользователя), а пути к файлам сохраняет в `st.session_state["artifacts_last"]`. После этого на экране появляется список «Последние сохранённые файлы» с абсолютными путями (app.py:565–568).

## Подводные камни / что важно понимать

**1. Файлы перезаписываются при каждом прогоне без предупреждения.**

Функция не добавляет временные метки или счётчики к именам файлов — всегда `trade_log.csv`, `equity_curve.csv` и т.д. Если вы запускаете несколько прогонов с разными параметрами, предыдущие результаты будут перезаписаны. Решение: перед каждым новым прогоном сохраняйте нужные файлы в другое место или вручную переименовывайте.

**2. HTML-отчёт подгружает plotly из интернета.**

Строка `include_plotlyjs="cdn"` (src/backtest/reporter.py:87) означает, что при открытии `report.html` браузер тянет библиотеку из интернета (`cdn.plot.ly`). Без подключения к сети отчёт откроется как пустая страница с пустыми осями. Резервный (fallback) HTML от этого не зависит — он работает полностью оффлайн.

**3. Резервный HTML создаётся при ЛЮБОЙ ошибке plotly — в том числе при пустых данных.**

Блок `except Exception` перехватывает всё: и «plotly не установлен», и «DataFrame пустой», и «TypeError в формате дат». Это осознанное решение (комментарий `# noqa: BLE001 — plotly optional/unstable`, src/backtest/reporter.py:88) — стабильность важнее информативности ошибки. Но если открытый HTML-отчёт выглядит как простая таблица без графиков — значит, что-то пошло не так при генерации графика. Проверьте, установлен ли plotly: `pip install plotly`.

**4. reporter.py — только для «командного» бэктеста, не для research-прогонов.**

Исследовательские прогоны (volume_breakout_runner, atr_breakout_runner, [[kronos-exploratory-runner|kronos_runner]] и т.д.) не вызывают `write_artifacts`. Они возвращают результаты напрямую в дашборд через API, минуя файловую систему. Функция `write_artifacts` предназначена только для прогонов через `run_backtest.py` (CLI) и кнопку «Сохранить» в `app.py`.

**5. Директория создаётся автоматически на любую глубину вложенности.**

`os.makedirs(output_dir, exist_ok=True)` (src/backtest/reporter.py:16) создаст и `output/`, и `results/2026/june/` — все промежуточные папки сразу. Параметр `exist_ok=True` гарантирует, что ошибки «папка уже существует» не будет при повторном прогоне.

## Связанные документы

- [[replay-engine-bar-by-bar]] — формирует `trades_df`, который потом сохраняется в `trade_log.csv`
- [[replay-engine-metrics]] — формирует `equity_df` и словарь `metrics`, которые попадают в `equity_curve.csv` и `metrics_summary.json`
- [[trade-extractor-and-records]] — объясняет формат записей сделок (`TradeRecord`) на стыке бэктеста и аналитики
- [[what-is-backtest-overview]] — общий обзор бэктест-процесса: что такое бэктест и зачем он нужен
- [[wfa-reporter-three-sharpe-series]] — другая система сохранения результатов (`wfa_reporter.py`) — для WFA-прогонов, не для одиночных командных прогонов
- [[08-дашборд/run-backtest-form]] — кнопка «Сохранить» в дашборде, которая вызывает `write_artifacts` через `app.py`
- [[sharpe-sortino-metrics]] — Sharpe/Sortino: часть метрик, которые сохраняются в `metrics_summary.json`
- [[max-drawdown-winrate-rr]] — MaxDD, Win Rate, R:R — метрики качества сделок, попадающие в тот же JSON
- [[configuration-and-settings]] — секция `output:` конфига решает, какие артефакты (CSV/JSON/HTML) записывать
- [[dashboard-overview]] — второй контекст вызова: кнопка «Сохранить отчёт» в Streamlit-дашборде
- [[equity-chart-and-drawdown]] — дашборд рисует ту же кривую капитала, что сохраняется в `equity_curve.csv`
- [[donchian-runner-and-reference-run]] — эталонный WFA-прогон: сохраняет результаты через `wfa_reporter`, а не через `write_artifacts`
- [[kronos-exploratory-runner]] — research-прогон, который отдаёт результаты в дашборд напрямую, минуя reporter (контраст)
- [[vector-backtest-fast-approximation]] — быстрый бэктест-движок; тоже не проходит через reporter (контраст семейства)
- [[caching-and-security]] — дашборд кеширует результаты по `run_id` вместо перезаписи файлов-артефактов (контраст механизма)

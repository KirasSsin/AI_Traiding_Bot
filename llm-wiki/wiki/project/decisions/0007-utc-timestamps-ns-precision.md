---
title: 0007. UTC timestamps with nanosecond precision
type: decision
tags: [adr, v0.1, time, timezone, precision]
created: 2026-04-19
updated: 2026-04-19
status: accepted
sources: [Docs/MVP + ALL PROJECT/MVP.md]
---

# 0007. UTC timestamps with nanosecond precision

**Status:** Accepted
**Date:** 2026-04-19

## Context
В торговой системе любая неоднозначность времени (local vs UTC, seconds vs ms vs
μs) приводит к misalignment баров, ошибкам reconciliation и невоспроизводимым
backtest'ам. Биржи отдают timestamps в ms (Binance) или μs. pandas по умолчанию
использует ns-precision для `Timestamp`.

## Decision
We will store and operate на всех timestamps в UTC с nanosecond precision,
используя `pandas.Timestamp` (tz-aware `UTC`) для in-memory и `INTEGER ns since
epoch` для SQLite, `timestamp[ns, UTC]` для Parquet. Локальные зоны допустимы
только на UI-слое (если появится). Любой вход из биржи нормализуется
на границе через `pd.to_datetime(x, unit='ms', utc=True)`.

## Consequences
- (+) Устранён класс багов с DST, локальными зонами, off-by-one сутки.
- (+) Единый тип данных между pandas, Parquet и numpy-векторными операциями.
- (+) Nanosecond-запас: при переходе на sub-second TF ничего не меняется.
- (−) Naive-timestamps в чужих CSV требуют явной аннотации при импорте.
- (−) SQLite не имеет нативного TIMESTAMP — храним INTEGER (ns) + документация.
- (0) Время биржевого сервера vs local clock — NTP-sync на деплое + логируем дельту.

## Alternatives considered
- UTC с ms precision: отвергнуто — потенциальный пересчёт при смене TF, теряем
  совместимость с pandas-default ns.
- Local timezone: отвергнуто — прямой путь к багам при переезде/DST.
- Unix epoch seconds float: отвергнуто — потеря точности у float64 на больших значениях.

## References
- [Docs/MVP + ALL PROJECT/MVP.md](../../../Docs/MVP%20%2B%20ALL%20PROJECT/MVP.md) — §3
- pandas Time Series docs: https://pandas.pydata.org/docs/user_guide/timeseries.html

# download_btc_data_v4.py
# Один файл — максимально устойчивый + полная отладка
import requests
import pandas as pd
import time
from datetime import datetime
import os

# ===================== НАСТРОЙКИ =====================
SYMBOL = "BTCUSDT"
INTERVAL = "1h"
START_DATE = "2024-01-01"
END_DATE = "2026-03-21"
PROJECT_PATH = "/Users/Apple/Documents/AI_Traiding_Bot"
# ====================================================

DATA_DIR = os.path.join(PROJECT_PATH, "data")
os.makedirs(DATA_DIR, exist_ok=True)
print(f"✅ Папка data: {DATA_DIR}")

def timestamp_ms(date_str):
    return int(datetime.strptime(date_str, "%Y-%m-%d").timestamp() * 1000)

def fetch_chunk(start_ts, end_ts):
    mirrors = ["https://api.binance.com", "https://api1.binance.com", "https://api3.binance.com"]
    for base in mirrors:
        for attempt in range(6):
            try:
                url = f"{base}/api/v3/klines"
                params = {"symbol": SYMBOL, "interval": INTERVAL, "startTime": start_ts, "endTime": end_ts, "limit": 1000}
                r = requests.get(url, params=params, timeout=12)
                r.raise_for_status()
                data = r.json()
                print(f"✅ Успешно с {base} — {len(data)} баров")
                return data
            except Exception as e:
                wait = (2 ** attempt) * 0.6
                print(f"   Попытка {attempt+1}/6 — ошибка, ждём {wait:.1f}с...")
                time.sleep(wait)
    return []

# =================== СКАЧИВАНИЕ ===================
start_ts = timestamp_ms(START_DATE)
end_ts = timestamp_ms(END_DATE)
all_data = []
current_ts = start_ts

print("Начинаем скачивание...")

while current_ts < end_ts:
    batch = fetch_chunk(current_ts, end_ts)
    if not batch:
        print("   Binance не ответил — пропускаем чанк")
        break
    all_data.extend(batch)
    current_ts = int(batch[-1][0]) + 1
    time.sleep(0.4)

print(f"✅ Скачивание завершено. Всего баров: {len(all_data)}")

if not all_data:
    print("❌ Данные не скачались")
    exit(1)

# =================== СОХРАНЕНИЕ С ОТЛАДКОЙ ===================
print("Начинаю создание DataFrame...")
try:
    df = pd.DataFrame(all_data, columns=["open_time","open","high","low","close","volume","close_time","quote_volume","trades","taker_base","taker_quote","ignore"])
    print("DataFrame создан успешно. Строк:", len(df))
    
    df = df[["open_time","open","high","low","close","volume"]].copy()
    df["time"] = pd.to_datetime(df["open_time"], unit="ms").dt.strftime("%Y-%m-%d %H:%M:%S")
    df = df[["time","open","high","low","close","volume"]]
    
    for col in ["open","high","low","close","volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna().reset_index(drop=True)
    print("DataFrame очищен. Финальное количество строк:", len(df))
except Exception as e:
    print("❌ Ошибка при создании DataFrame:", e)
    exit(1)

# Сохранение
csv_path = os.path.join(DATA_DIR, f"{SYMBOL}_{INTERVAL}.csv")
parquet_path = os.path.join(DATA_DIR, f"{SYMBOL}_{INTERVAL}.parquet")

print(f"Сохраняем CSV: {csv_path}")
df.to_csv(csv_path, index=False)

print(f"Сохраняем Parquet: {parquet_path}")
df.to_parquet(parquet_path, index=False, compression="gzip")

print("\n🎉 ГОТОВО!")
print(f"Файлы сохранены в data/:")
print(f"   • {csv_path}")
print(f"   • {parquet_path}")
print(f"\nТеперь в папке data/ должно быть 2 файла. Проверь!")
import os
import sqlite3
import time
from datetime import date

import requests

BASE = "https://opendata.trudvsem.ru/api/v1/vacancies"
QUERY = "аналитик данных"


def fetch_page(text, page, limit=100):
    r = requests.get(
        BASE,
        params={"text": text, "offset": page, "limit": limit},
        timeout=30,
    )
    r.raise_for_status()
    data = r.json()
    results = data.get("results") or {}
    return results.get("vacancies", [])


def collect():
    today = date.today().isoformat()
    rows, seen = [], set()
    for page in range(50):  # предохранитель от бесконечного цикла
        items = fetch_page(QUERY, page)
        new = [v["vacancy"] for v in items if v["vacancy"]["id"] not in seen]
        if not new:
            break
        for v in new:
            seen.add(v["id"])
            rows.append((
                today,
                v["id"],
                v.get("job-name"),
                v.get("salary_min") or None,
                v.get("salary_max") or None,
                (v.get("region") or {}).get("name"),
                (v.get("company") or {}).get("name"),
                v.get("employment"),
                v.get("schedule"),
                v.get("creation-date"),
            ))
        time.sleep(1)  # не нагружаем госсервис
    return rows


def save(rows):
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect("data/vacancies.db")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS vacancies (
            snapshot_date TEXT, id TEXT, title TEXT,
            salary_min REAL, salary_max REAL, region TEXT, company TEXT,
            employment TEXT, schedule TEXT, created TEXT,
            PRIMARY KEY (snapshot_date, id)
        )
    """)
    conn.executemany(
        "INSERT OR REPLACE INTO vacancies VALUES (?,?,?,?,?,?,?,?,?,?)", rows
    )
    conn.commit()
    conn.close()
    print(f"Сохранено вакансий: {len(rows)}")


if __name__ == "__main__":
    save(collect())
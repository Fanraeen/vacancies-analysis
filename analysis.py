import re
import sqlite3

import pandas as pd

conn = sqlite3.connect("data/vacancies.db")
df = pd.read_sql(
    """
    SELECT id, title, region, company, salary_min, salary_max, requirements
    FROM vacancies
    WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM vacancies)
    """,
    conn
)

# оставляем только аналитиков 
df = df[df["title"].str.contains("аналитик|analyst", case=False, regex=True)].copy()

def min_experience(text):
    # Минимальный опыт в годах из текста требований (None, если не нашли)
    if not text:
        return True
    t = text.lower()
    if re.search(r"без опыта|опыт.{0,20}не (?:требуется|обязателен|нужен)", t):
        return 0
    m = re.search(r"опыт[^.;]{0,80}?(\d+)[\s\d\-\–х]*(?:лет|год)", t)

    if m:
        return int(m.group(1))
    return None

def bucket(x):
    """Раскладывает число лет опыта по группам."""
    if isinstance(x, bool) or x is None or pd.isna(x):
        return "не указан"
    if x == 0:
        return "без опыта"
    if x <= 1:
        return "около 1 года"
    if x <= 3:
        return "2–3 года"
    return "4+ лет"

df["exp_years"] = df["requirements"].apply(min_experience)
df["exp_bucket"] = df["exp_years"].apply(bucket)


print(len(df), "аналитических вакансий")
print(df["exp_bucket"].value_counts())


low = df[df["exp_bucket"].isin(["без опыта", "около 1 года"])]
low = low.drop_duplicates(subset=["title", "company", "region"])  # убираем повторы

#print(f"\nВакансии с опытом до 1 года: {len(low)}")
#for _, row in low.iterrows():
#    print("-", row["title"], "|", row["company"], "|", row["region"], "|", row["salary_min"])
#    print("   ", row["requirements"])
#    print()


unknown = df[df["exp_bucket"] == "не указан"]
empty = unknown["requirements"].fillna("").str.strip().eq("").sum()
print(f"\nНе указан опыт у {len(unknown)}, из них пустой текст требований у {empty}")

with_text = unknown[unknown["requirements"].fillna("").str.strip() != ""]
for _, row in with_text.head(8).iterrows():
    print("-", row["title"])
    print("   ", row["requirements"])
    print()


skills = {
    "SQL (включая PostgreSQL и т.п.)": r"sql",
    "Python": r"python",
    "Excel": r"excel|эксель",
    "BI-системы (Power BI, Tableau, DataLens, Qlik)": r"power\s?bi|tableau|datalens|qlik|\bbi\b",
    "1С": r"1с|1c",
    "Статистика": r"статистик",
}

text = df["requirements"].fillna("").str.lower()
n_text = int((text.str.strip() != "").sum())
print(f"\nВакансий с текстом требований: {n_text} из {len(df)}")
for name, pat in skills.items():
    n = int(text.str.contains(pat, regex=True).sum())
    print(f"{name}: {n} ({n / n_text:.0%} от вакансий с текстом)")
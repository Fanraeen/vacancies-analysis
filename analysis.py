import re
import sqlite3
import os

import pandas as pd
import matplotlib.pyplot as plt


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


os.makedirs("reports", exist_ok=True)
snap = conn.execute("SELECT MAX(snapshot_date) FROM vacancies").fetchone()[0]

# График 1: топ-10 регионов
top = df["region"].value_counts().head(10).sort_values()
fig, ax = plt.subplots(figsize=(8, 5))
bars = ax.barh(top.index, top.values, color="#4C72B0")
ax.bar_label(bars, padding=3)
ax.set_title(f"Вакансии аналитиков по регионам (срез {snap})")
ax.set_xlabel("Число вакансий")
fig.tight_layout()
fig.savefig("reports/regions.png", dpi=150)
plt.close(fig)

# График 2: требуемый опыт
order = ["без опыта", "около 1 года", "2–3 года", "4+ лет", "не указан"]
exp = df["exp_bucket"].value_counts().reindex(order).dropna()
fig, ax = plt.subplots(figsize=(8, 5))
bars = ax.bar(exp.index, exp.values, color="#55A868")
ax.bar_label(bars, padding=3)
ax.set_title(f"Требуемый опыт в вакансиях аналитиков (срез {snap})")
ax.set_ylabel("Число вакансий")
fig.tight_layout()
fig.savefig("reports/experience.png", dpi=150)
plt.close(fig)
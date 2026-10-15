import sqlite3

conn = sqlite3.connect("data/vacancies.db")
print(conn.execute(
    "SELECT COUNT(*), COUNT(salary_min), COUNT(salary_max), COUNT(DISTINCT region) FROM vacancies"
).fetchone())
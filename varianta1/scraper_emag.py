import requests
from bs4 import BeautifulSoup
import sqlite3
from datetime import datetime

url = "https://www.emag.ro/range-extender-wireless-ac1750-tp-link-moduri-re-ap-gigabit-antene-externe-dual-band-re450/pd/D1JS9YBBM/"

headers = {"User-Agent": "Mozilla/5.0"}
response = requests.get(url, headers=headers)
soup = BeautifulSoup(response.text, "html.parser")

title_tag = soup.find("h1", class_="page-title")
price_tag = soup.find("p", class_="product-new-price")

if not title_tag or not price_tag:
    print("Nu s-a putut extrage produsul. Verifica URL-ul sau clasa HTML.")
    exit()

title = title_tag.text.strip()
price_text = price_tag.text.strip().split(" ")[0].replace(".", "").replace(",", ".")
price = float(price_text)

print(f" {title} — {price:.2f} lei")

conn = sqlite3.connect("products.db")
c = conn.cursor()

c.execute("""
    CREATE TABLE IF NOT EXISTS prices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product TEXT,
        price REAL,
        date TEXT
    )
""")

c.execute("INSERT INTO prices (product, price, date) VALUES (?, ?, ?)",
          (title, price, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

conn.commit()
conn.close()

print("Salvat in baza de date.")

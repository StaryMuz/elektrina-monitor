# -*- coding: utf-8 -*-
import requests
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import os

# Načtení proměnných z prostředí
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
LIMIT_EUR = 12.0

def posli_telegram_zpravu(token, chat_id, zprava, obrazek_cesta=None):
    if obrazek_cesta:
        url = f"https://api.telegram.org/bot{token}/sendPhoto"
        with open(obrazek_cesta, "rb") as f:
            files = {"photo": f}
            data = {"chat_id": chat_id, "caption": zprava}
            response = requests.post(url, data=data, files=files)
    else:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        data = {"chat_id": chat_id, "text": zprava}
        response = requests.post(url, data=data)

    if response.status_code != 200:
        raise Exception(f"Chyba při odesílání zprávy: {response.text}")

def main():
    dnes = datetime.now()
    den = dnes.strftime("%d")
    mesic = dnes.strftime("%m")
    rok = dnes.strftime("%Y")

    url = f"http://www.ote-cr.cz/kratkodobe-trhy/elektrina/denni-trh/attached/{rok}/month{mesic}/day{den}/DT_{den}_{mesic}_{rok}_CZ.xls"
    print(f"Stahuji data z: {url}")

    try:
    df = pd.read_excel(url, skiprows=23, usecols="A,B", engine="openpyxl")
    df.columns = ["Hodina", "Cena (EUR/MWh)"]
    # ✅ Úprava formátu desetinných čísel
    df["Cena (EUR/MWh)"] = df["Cena (EUR/MWh)"].astype(str).str.replace(",", ".").astype(float)
except Exception as e:
    raise Exception(f"Chyba při čtení XLS: {e}")

    df.dropna(inplace=True)
    df["Hodina"] = pd.to_numeric(df["Hodina"], errors="coerce").fillna(0).astype(int)
    df = df[df["Hodina"] >= 1]

    cena_pod_limit = df[df["Cena (EUR/MWh)"] < LIMIT_EUR]

    if cena_pod_limit.empty:
        zprava = f"📊 Denní ceny elektřiny ({den}.{mesic}.{rok})\n❌ Cena neklesla pod {LIMIT_EUR} EUR/MWh"
    else:
        zprava = f"📊 Denní ceny elektřiny ({den}.{mesic}.{rok})\n✅ V některých hodinách byla cena pod {LIMIT_EUR} EUR/MWh"

    # Vykreslení grafu
    plt.figure(figsize=(10, 5))
    plt.plot(df["Hodina"], df["Cena (EUR/MWh)"], marker="o", label="Cena")
    plt.axhline(y=LIMIT_EUR, color="r", linestyle="--", label=f"Limit {LIMIT_EUR} EUR")
    plt.title(f"Cena elektřiny {den}.{mesic}.{rok}")
    plt.xlabel("Hodina")
    plt.ylabel("Cena (EUR/MWh)")
    plt.grid(True)
    plt.legend()
    obrazek = "graf.png"
    plt.savefig(obrazek)
    plt.close()

    posli_telegram_zpravu(TELEGRAM_BOT_TOKEN, CHAT_ID, zprava, obrazek)

if __name__ == "__main__":
    main()

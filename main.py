# -*- coding: utf-8 -*-
import requests
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import os

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
LIMIT_EUR = 13.0

def posli_telegram_zpravu(token, chat_id, zprava, obrazek_cesta=None):
    url = f"https://api.telegram.org/bot{token}/sendPhoto" if obrazek_cesta else f"https://api.telegram.org/bot{token}/sendMessage"
    data = {"chat_id": chat_id}
    files = None

    if obrazek_cesta:
        files = {"photo": open(obrazek_cesta, "rb")}
        data["caption"] = zprava
    else:
        data["text"] = zprava

    print("📤 Odesílám zprávu do Telegramu…")
    response = requests.post(url, data=data, files=files)
    print(f"✅ Telegram odpověděl: {response.status_code}")
    if response.status_code != 200:
        raise Exception(f"❌ Chyba při odesílání zprávy: {response.text}")

def main():
    dnes = datetime.now()
    den = dnes.strftime("%d")
    mesic = dnes.strftime("%m")
    rok = dnes.strftime("%Y")
    url = f"http://www.ote-cr.cz/kratkodobe-trhy/elektrina/denni-trh/attached/{rok}/month{mesic}/day{den}/DT_{den}_{mesic}_{rok}_CZ.xls"
    
    print(f"⬇️ Stahuji data z: {url}")
    try:
        df = pd.read_excel(url, skiprows=23, usecols="A,B", engine="openpyxl")
        df.columns = ["Hodina", "Cena (EUR/MWh)"]
    except Exception as e:
        raise Exception(f"❌ Chyba při čtení XLS: {e}")

    print("📊 Načteno:")
    print(df.head())

    df.dropna(inplace=True)
    df["Hodina"] = pd.to_numeric(df["Hodina"], errors="coerce").fillna(0).astype(int)

    # Převede čárky na tečky a převede na čísla
    df["Cena (EUR/MWh)"] = df["Cena (EUR/MWh)"].astype(str).str.replace(",", ".")
    df["Cena (EUR/MWh)"] = pd.to_numeric(df["Cena (EUR/MWh)"], errors="coerce")
    
    df = df[df["Hodina"] >= 1]
    cena_pod_limit = df[df["Cena (EUR/MWh)"] < LIMIT_EUR]

    if not cena_pod_limit.empty:
        # Najdeme souvislé bloky hodin pod limitem
        intervals = []
        start = None
        prev = None

        for hodina in cena_pod_limit["Hodina"]:
            if start is None:
                start = hodina
                prev = hodina
            elif hodina == prev + 1:
                prev = hodina
            else:
                intervals.append((start, prev))
                start = hodina
                prev = hodina

        if start is not None:
            intervals.append((start, prev))

        # Vytvoříme text s výpisem všech intervalů
        intervaly_text = []
        for s, e in intervals:
            if s == e:
                intervaly_text.append(f"{s-1}.–{s}. hod")
            else:
                intervaly_text.append(f"{s-1}.–{e}. hod")
        
        zprava = (
            f"📈 Ceny elektřiny {den}.{mesic}.{rok}\n"
            f"❗ Cena pod limitem {LIMIT_EUR} EUR v časech:\n"
            + "\n".join([f"• {t}" for t in intervaly_text])
        )

        print("🧾 Generuji graf…")
        plt.figure(figsize=(10, 5))
        plt.plot(df["Hodina"], df["Cena (EUR/MWh)"], marker="o", label="Cena")
        plt.axhline(y=LIMIT_EUR, color="r", linestyle="--", label=f"Limit {LIMIT_EUR} EUR")
        plt.title(f"Cena elektřiny platná vždy do uvedené hodiny pro {den}.{mesic}.{rok}")
        plt.xlabel("Do uvedené hodiny")
        plt.ylabel("Cena (EUR/MWh)")
        plt.grid(True)
        plt.legend()
        obrazek = "graf.png"
        plt.savefig(obrazek)
        plt.close()
        print("✅ Graf uložen jako graf.png")

        posli_telegram_zpravu(TELEGRAM_BOT_TOKEN, CHAT_ID, zprava, obrazek_cesta=obrazek)
    else:
        posli_telegram_zpravu(TELEGRAM_BOT_TOKEN, CHAT_ID, f"ℹ️ Ceny nad limitem.")

if __name__ == "__main__":
    try:
        main()
        print("✅ Skript dokončen.")
    except Exception as e:
        print(f"❌ Chyba ve skriptu: {e}")

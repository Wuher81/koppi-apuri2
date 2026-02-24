import streamlit as st
import os
os.system("playwright install chromium")
from playwright.sync_api import sync_playwright
import requests
import re
from datetime import datetime, timedelta

# --- JOUKKUEET ASETUKSET ---
JOUKKUEET = [
    {"nimi": "Ässät U12", "ical": "https://ics.jopox.fi/hockeypox/calendar/ical.php?ics=true&e=t&cal=U122014_9664", "club_id": "9664"},
    # ... lisää muut tähän ...
]

def aja_haku(user, pw, alku_pvm, loppu_pvm, halli_valinta):
    tulokset = []
    with sync_playwright() as p:
        # TÄRKEÄÄ: Pilvipalvelussa tarvitaan usein nämä argumentit
        browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
        context = browser.new_context()
        page = context.new_page()

        try:
            st.info("Kirjaudutaan Jopoxiin...")
            page.goto("https://login.jopox.fi/login?to=145")
            
            # Etsitään salasana-kenttä ja syötetään tiedot
            page.wait_for_selector("input[type='password']")
            page.keyboard.press("Shift+Tab")
            page.keyboard.type(user)
            page.keyboard.press("Tab")
            page.keyboard.type(pw)
            page.keyboard.press("Enter")
            
            # Odotetaan kirjautumista
            page.wait_for_timeout(5000)

            curr = alku_pvm
            while curr <= loppu_pvm:
                etsi_pvm = curr.strftime('%Y%m%d')
                st.write(f"Haetaan päivää: {curr.strftime('%d.%m.%Y')}")

                for j in JOUKKUEET:
                    # iCal haku requestsilla (kuten alkuperäisessä)
                    res = requests.get(j['ical'])
                    # ... (tähän väliin alkuperäinen iCal-parsinta-logiikkasi) ...
                    
                    # Kun löydät tapahtuman UID:n perusteella:
                    # page.goto(f"https://assat-app.jopox.fi/training/club/{j['club_id']}/{uid_nro}")
                    # maara = page.locator("#yesBox .chip.player").count()
                    
                curr += timedelta(days=1)
                
        except Exception as e:
            st.error(f"Virhe haun aikana: {e}")
        finally:
            browser.close()
    return tulokset

# --- KÄYTTÖLIITTYMÄ ---
st.title("🏒 Ässät Koppi-Apuri Web")

with st.sidebar:
    kayttaja = st.text_input("Jopox Tunnus")
    salasana = st.text_input("Salasana", type="password")
    alku = st.date_input("Alkupäivä", datetime.now())
    loppu = st.date_input("Loppupäivä", datetime.now() + timedelta(days=7))
    nappi = st.button("Käynnistä haku")

if nappi:
    if not kayttaja or not salasana:
        st.warning("Syötä tunnukset!")
    else:
        data = aja_haku(kayttaja, salasana, alku, loppu, "Kaikki")
        st.table(data)
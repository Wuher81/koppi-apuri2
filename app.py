import streamlit as st
import os
import subprocess
import sys
import requests
from datetime import datetime, date

# --- 1. AUTOMAATTINEN ASENNUSVAIHE ---
# Varmistetaan, että tarvittavat kirjastot ja selaimet löytyvät pilvipalvelusta
try:
    import playwright
    import icalendar
except ImportError:
    # Käytetään versiota >=1.49.0 Python 3.13 -yhteensopivuuden takia
    subprocess.run([sys.executable, "-m", "pip", "install", "playwright>=1.49.0", "icalendar"])

# Asennetaan Chromium-selain taustalla
os.system(f"{sys.executable} -m playwright install chromium")

# Tuodaan loput kirjastot vasta asennuksen jälkeen
from icalendar import Calendar
from playwright.sync_api import sync_playwright

# --- 2. MÄÄRITTELYT ---
# Lisää tähän joukkueiden nimet ja niiden ICS-linkit
JOUKKUEET = {
    "U10 Valkoinen": "https://assat-app.jopox.fi/calendar/6755/export.ics",
    "U10 Punainen":  "https://assat-app.jopox.fi/calendar/6756/export.ics",
    "U12":           "https://assat-app.jopox.fi/calendar/54321/export.ics"
}

# --- 3. LOGIIKKA ---

def aja_haku_kirjautumisella(kayttaja, salasana):
    """Hoitaa kirjautumisen ja pelaajien laskemisen."""
    with sync_playwright() as p:
        # Käynnistys vakailla asetuksilla pilviympäristöä varten
        browser = p.chromium.launch(
            headless=True, 
            args=["--no-sandbox", "--disable-setuid-sandbox"]
        )
        context = browser.new_context()
        page = context.new_page()

        taman_paivan_tulokset = []
        tanaan = date.today()

        try:
            # Kirjautumisvaihe
            st.info("Kirjaudutaan sisään Jopoxiin...")
            page.goto("https://login.jopox.fi/login?to=145")
            page.fill('input[name="username"]', kayttaja)
            page.fill('input[name="password"]', salasana)
            page.click('button[type="submit"]')
            
            # Odotetaan, että sivu latautuu kirjautumisen jälkeen
            page.wait_for_load_state("networkidle")

            # Käydään joukkueet läpi
            for nimi, ics_url in JOUKKUEET.items():
                st.write(f"Tarkistetaan joukkue: **{nimi}**")
                
                # Mennään ICS-linkkiin kirjautuneena
                page.goto(ics_url)
                # Playwright hakee raakadatan (content), jota icalendar voi lukea
                ics_data = page.content()
                
                # Poimitaan päivän tapahtumat
                gcal = Calendar.from_ical(ics_data)
                for component in gcal.walk():
                    if component.name == "VEVENT":
                        dtstart = component.get('dtstart').dt
                        t_pvm = dtstart.date() if isinstance(dtstart, datetime) else dtstart
                        
                        if t_pvm == tanaan:
                            t_url = str(component.get('url'))
                            # Navigoidaan tapahtuman sivulle laskemaan 'Tulossa'-pelaajat
                            page.goto(t_url)
                            page.wait_for_selector("#yesBox", timeout=5000)
                            pelaajat = page.locator("#yesBox .chip.player").count()
                            taman_paivan_tulokset.append({"nimi": nimi, "maara": pelaajat})

        except Exception as e:
            st.error(f"Haku keskeytyi virheeseen: {e}")
        finally:
            browser.close()
            
        return taman_paivan_tulokset

# --- 4. STREAMLIT-KÄYTTÖLIITTYMÄ ---

st.title("🏒 Pukukoppi-apuri v10.0")
st.write("Tämä työkalu kirjautuu Jopoxiin, lukee kalenterit ja laskee pelaajamäärät.")

# Käyttäjä syöttää tunnukset
user = st.text_input("Käyttäjätunnus")
pw = st.text_input("Salasana", type="password")

if st.button("Laske tämän päivän pelaajat"):
    if user and pw:
        data = aja_haku_kirjautumisella(user, pw)
        
        if data:
            st.subheader("Päivän yhteenveto:")
            for r in data:
                # Koppien määrityslogiikka
                kopit = "2 KOPPIA" if r['maara'] > 17 else "1 KOPPI"
                st.success(f"**{r['nimi']}**: {r['maara']} pelaajaa -> **{kopit}**")
        else:
            st.info("Ei tapahtumia tälle päivälle tai haku epäonnistui.")
    else:
        st.warning("Syötä ensin käyttäjätunnus ja salasana.")
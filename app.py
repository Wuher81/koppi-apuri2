import streamlit as st
import os
import subprocess
import sys
import requests
from datetime import datetime, date

# --- 1. ASENNUKSET ---
try:
    import playwright
    import icalendar
except ImportError:
    subprocess.run([sys.executable, "-m", "pip", "install", "playwright>=1.49.0", "icalendar"])

os.system(f"{sys.executable} -m playwright install chromium")

from icalendar import Calendar
from playwright.sync_api import sync_playwright

# --- 2. JOUKKUEET ---
JOUKKUEET = {
    "U10 Valkoinen": "https://assat-app.jopox.fi/calendar/6755/export.ics",
    "U10 Punainen":  "https://assat-app.jopox.fi/calendar/6756/export.ics",
    "U12":           "https://assat-app.jopox.fi/calendar/54321/export.ics"
}

# --- 3. LOGIIKKA ---

def aja_haku_kirjautumisella(kayttaja, salasana):
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox"]
        )
        # Käytetään selkeää selainistuntoa
        context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        page = context.new_page()

        taman_paivan_tulokset = []
        tanaan = date.today()

        try:
            # Kirjautuminen
            st.info("Avataan kirjautumissivua...")
            page.goto("https://login.jopox.fi/login?to=145", wait_until="networkidle")
            
            # Varmistetaan, että ollaan oikealla sivulla ennen täyttöä
            # Joskus Jopox käyttää id-kenttiä, joskus name-kenttiä
            st.write("Täytetään tunnukset...")
            page.wait_for_selector('input', timeout=10000)
            
            # Yritetään täyttää kentät useammalla tavalla varmuuden vuoksi
            page.locator('input[type="text"], input[name="username"], #username').first.fill(kayttaja)
            page.locator('input[type="password"], input[name="password"], #password').first.fill(salasana)
            
            # Klikataan nappia (etsitään tekstillä tai tyypillä)
            page.locator('button:has-text("Kirjaudu"), button[type="submit"]').first.click()
            
            # Odotetaan, että päästään sisään (networkidle varmistaa latauksen)
            page.wait_for_load_state("networkidle")
            
            if "login" in page.url:
                st.error("Kirjautuminen epäonnistui. Tarkista tunnus ja salasana.")
                return []

            st.success("Kirjautuminen onnistui!")

            for nimi, ics_url in JOUKKUEET.items():
                st.write(f"Haetaan: **{nimi}**")
                
                # Mennään suoraan ICS-linkkiin - Playwright lataa raakadatan
                response = page.goto(ics_url)
                ics_data = response.body() # Haetaan raaka tavudata
                
                # Puretaan kalenteri
                gcal = Calendar.from_ical(ics_data)
                for component in gcal.walk():
                    if component.name == "VEVENT":
                        dtstart = component.get('dtstart').dt
                        t_pvm = dtstart.date() if isinstance(dtstart, datetime) else dtstart
                        
                        if t_pvm == tanaan:
                            t_url = str(component.get('url'))
                            page.goto(t_url, wait_until="domcontentloaded")
                            
                            # Odotetaan yesBoxia ja lasketaan pelaajat
                            page.wait_for_selector("#yesBox", timeout=8000)
                            pelaajat = page.locator("#yesBox .chip.player").count()
                            taman_paivan_tulokset.append({"nimi": nimi, "maara": pelaajat})

        except Exception as e:
            st.error(f"Virhe haun aikana: {e}")
        finally:
            browser.close()
            
        return taman_paivan_tulokset

# --- 4. STREAMLIT UI ---
st.title("🏒 Pukukoppi-apuri v10.1")

user = st.text_input("Jopox-tunnus (sähköposti)")
pw = st.text_input("Salasana", type="password")

if st.button("Laske pelaajat"):
    if user and pw:
        data = aja_haku_kirjautumisella(user, pw)
        if data:
            st.subheader("Päivän tilanne:")
            for r in data:
                kopit = "2 KOPPIA" if r['maara'] > 17 else "1 KOPPI"
                st.success(f"**{r['nimi']}**: {r['maara']} pelaajaa -> {kopit}")
        elif not st.session_state.get('error_shown'):
             st.info("Ei tapahtumia tälle päivälle.")
    else:
        st.warning("Syötä tunnukset ensin.")
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
            args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
        )
        # Käytetään laajennettua kontekstia evästeille
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        taman_paivan_tulokset = []
        tanaan = date.today()

        try:
            # Kirjautuminen Ässien tunnistautumisen kautta
            st.info("Avataan Ässät-Jopox kirjautumista...")
            # Käytetään nimenomaan tätä URL:ia, jotta "to=145" ohjaa Ässien ympäristöön
            page.goto("https://login.jopox.fi/login?to=145", wait_until="networkidle", timeout=60000)
            
            st.write("Täytetään tunnukset...")
            
            # Odotetaan, että vähintään yksi input ilmestyy
            page.wait_for_selector("input", timeout=20000)

            # Täytetään kentät (Ässät-brändätty sivu saattaa vaatia tarkan valitsimen)
            page.locator('input[type="text"], input[name="username"], input[type="email"]').first.fill(kayttaja)
            page.locator('input[type="password"], input[name="password"]').first.fill(salasana)
            
            st.write("Kirjaudutaan sisään...")
            # Klikataan nappia, joka on tyyppiä submit
            page.locator('button[type="submit"]').first.click()
            
            # Odotetaan, että sivu latautuu ja ohjaa takaisin app-puolelle
            page.wait_for_load_state("networkidle", timeout=45000)
            
            # Tarkistetaan onnistuminen URL:n perusteella
            if "login" in page.url:
                 st.error("Kirjautuminen epäonnistui. Tarkista sähköposti ja salasana.")
                 return []

            st.success("Kirjautuminen onnistui! Haetaan pelaajamäärät...")

            for nimi, ics_url in JOUKKUEET.items():
                st.write(f"Tarkistetaan: **{nimi}**")
                
                # Mennään ICS-linkkiin kirjautuneena
                response = page.goto(ics_url)
                if response.status == 200:
                    ics_data = response.body()
                    
                    gcal = Calendar.from_ical(ics_data)
                    for component in gcal.walk():
                        if component.name == "VEVENT":
                            dtstart = component.get('dtstart').dt
                            t_pvm = dtstart.date() if isinstance(dtstart, datetime) else dtstart
                            
                            if t_pvm == tanaan:
                                t_url = str(component.get('url'))
                                # Mennään tapahtuman sivulle
                                page.goto(t_url, wait_until="domcontentloaded")
                                
                                # Lasketaan pelaajat yesBoxista (ilmoittautuneet)
                                page.wait_for_selector("#yesBox", timeout=15000)
                                maara = page.locator("#yesBox .chip.player").count()
                                taman_paivan_tulokset.append({"nimi": nimi, "maara": maara})
                else:
                    st.warning(f"Ei pääsyä joukkueen {nimi} kalenteriin (Status: {response.status})")

        except Exception as e:
            st.error(f"Haku epäonnistui: {e}")
        finally:
            browser.close()
            
        return taman_paivan_tulokset

# --- 4. STREAMLIT UI ---
st.title("🏒 Pukukoppi-apuri v10.3")

# Käyttäjän syötteet
user_email = st.text_input("Ässät-Jopox tunnus (sähköposti)")
user_password = st.text_input("Salasana", type="password")

if st.button("Laske tämän päivän pelaajat"):
    if user_email and user_password:
        data = aja_haku_kirjautumisella(user_email, user_password)
        if data:
            st.subheader("Yhteenveto:")
            for r in data:
                kopit = "2 KOPPIA" if r['maara'] > 17 else "1 KOPPI"
                st.success(f"**{r['nimi']}**: {r['maara']} pelaajaa -> **{kopit}**")
        else:
            st.info("Ei löydettyjä tapahtumia tälle päivälle.")
    else:
        st.warning("Syötä sähköposti ja salasana ensin.")
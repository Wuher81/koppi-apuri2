import requests
from icalendar import Calendar
from datetime import datetime, date
from playwright.sync_api import sync_playwright

# Määrittele joukkueet ja heidän ICS-linkkinsä
JOUKKUEET = {
    "U10 Valkoinen": "https://assat-app.jopox.fi/calendar/6755/export.ics", # Esimerkki-ID
    "U10 Punainen":  "https://assat-app.jopox.fi/calendar/6756/export.ics"
}

def hae_paivan_linkit(ics_url):
    """Hakee ICS-tiedostosta kuluvan päivän tapahtumien URL-osoitteet."""
    vastaus = requests.get(ics_url)
    vastaus.encoding = 'utf-8' # Varmistetaan merkistö
    gcal = Calendar.from_ical(vastaus.text)
    
    taman_paivan_urlit = []
    tanaan = date.today()

    for component in gcal.walk():
        if component.name == "VEVENT":
            # Tarkistetaan tapahtuman pvm
            dtstart = component.get('dtstart').dt
            # ICS voi palauttaa joko date tai datetime objektin
            tapahtuma_pvm = dtstart.date() if isinstance(dtstart, datetime) else dtstart
            
            if tapahtuma_pvm == tanaan:
                url = component.get('url')
                if url:
                    taman_paivan_urlit.append(str(url))
    
    return taman_paivan_urlit

def aja_koppiapu_pilvessa():
    with sync_playwright() as p:
        # TÄRKEÄÄ: headless=True pilvipalveluissa!
        browser = p.chromium.launch(headless=True) 
        context = browser.new_context()
        page = context.new_page()

        # Jos sivu vaatii kirjautumisen, se on tehtävä koodilla (ei inputilla)
        # page.goto("URL")
        # page.fill("#username", "tunnus")
        # page.fill("#password", "salasana")
        # page.click("#login-button")

        kaikki_tulokset = []

        for nimi, url in JOUKKUEET.items():
            print(f"Haetaan joukkueen {nimi} tapahtumat...")
            linkit = hae_paivan_linkit(url)
            
            for tapahtuma_url in linkit:
                page.goto(tapahtuma_url)
                try:
                    page.wait_for_selector("#yesBox", timeout=5000)
                    pelaajat = page.locator("#yesBox .chip.player").count()
                    kaikki_tulokset.append({"nimi": nimi, "maara": pelaajat})
                except:
                    continue

        # Streamlitissä käytettäisiin st.write(), tavallisessa koodissa print
        for t in kaikki_tulokset:
            kopit = "2 KOPPIA" if t['maara'] > 17 else "1 KOPPI"
            print(f"{t['nimi']}: {t['maara']} pelaajaa -> {kopit}")

        browser.close()

if __name__ == "__main__":
    aja_koppiapu_pilvessa()
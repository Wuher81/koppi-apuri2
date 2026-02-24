import time
from functools import wraps
from playwright.sync_api import sync_playwright

# --- MÄÄRITELMÄT ---
# Lisää tähän kaikki joukkueet, joita haluat seurata
JOUKKUEET = {
    "U10 Valkoinen": {"id": "12345", "ics_url": "https://assat-app.jopox.fi/calendar/12345/export.ics"},
    "U10 Punainen":  {"id": "67890", "ics_url": "https://assat-app.jopox.fi/calendar/67890/export.ics"},
    "U12":           {"id": "54321", "ics_url": "https://assat-app.jopox.fi/calendar/54321/export.ics"},
}

# --- DEKORAATTORIT ---

def virheenkasittely(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            print(f" ! Virhe funktiossa {func.__name__}: {e}")
            return None
    return wrapper

# --- LOGIIKKA ---

@virheenkasittely
def hae_pelaajat_selaimella(page, tapahtuma_url):
    """Menee tapahtuman sivulle ja laskee 'Tulossa' olevat pelaajat."""
    page.goto(tapahtuma_url, wait_until="domcontentloaded")
    # Odotetaan pelaajien laatikkoa
    page.wait_for_selector("#yesBox", timeout=4000)
    maara = page.locator("#yesBox .chip.player").count()
    return maara

def aja_automaattihaku():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False) # Headless=True, jos et halua nähdä selainta
        context = browser.new_context()
        page = context.new_page()

        # Kirjautuminen kerran alussa
        print("Kirjaudutaan sisään...")
        page.goto("https://login.jopox.fi/login?to=145")
        print("--- Odotetaan kirjautumista ---")
        input("Kirjaudu sisään selaimessa ja paina Enter tässä...")

        tulokset = []

        # Käydään läpi jokainen joukkue
        for nimi, tiedot in JOUKKUEET.items():
            print(f"\nTarkistetaan joukkue: {nimi}")
            
            # Tässä kohtaa koodi voisi joko:
            # A) Lukea ICS-tiedoston (jos haluat hakea tulevat pelit automaattisesti)
            # B) Mennä suoraan joukkueen kalenterisivulle ID:n avulla
            joukkue_url = f"https://assat-app.jopox.fi/joukkue/{tiedot['id']}/kalenteri"
            page.goto(joukkue_url)
            
            # TÄHÄN VÄLIIN: Poimitaan päivän tapahtumat (kuten aiemmin)
            # ... (logiikka tapahtumien etsimiseen tältä sivulta) ...
            
            # Esimerkki yksittäisestä hausta (jos tiedossa on URL):
            # pelaajat = hae_pelaajat_selaimella(page, "tapahtuman_url_tähän")
            # tulokset.append({"joukkue": nimi, "pelaajat": pelaajat})

        browser.close()

if __name__ == "__main__":
    aja_automaattihaku()
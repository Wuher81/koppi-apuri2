import streamlit as st
from playwright.sync_api import sync_playwright
import requests
import re
import os
import subprocess
from datetime import datetime, timedelta

# --- 1. SELAIMEN ASENNUS (TÄRKEÄÄ) ---
def asenna_selaimet():
    # Playwright asentaa selaimet yleensä tähän polkuun Streamlit Cloudissa
    path = os.path.expanduser("~/.cache/ms-playwright")
    if not os.path.exists(path):
        with st.spinner("Asennetaan selainympäristöä... Tämä tehdään vain kerran."):
            try:
                subprocess.run(["python", "-m", "playwright", "install", "chromium"], check=True)
                subprocess.run(["python", "-m", "playwright", "install-deps", "chromium"], check=True)
            except Exception as e:
                st.error(f"Asennusvirhe: {e}")

asenna_selaimet()

# --- 2. ASETUKSET ---
JOUKKUEET = [
    {"nimi": "Ässät U12", "ical": "https://ics.jopox.fi/hockeypox/calendar/ical.php?ics=true&e=t&cal=U122014_9664", "club_id": "9664"},
    {"nimi": "Ässät U13", "ical": "https://ics.jopox.fi/hockeypox/calendar/ical.php?ics=true&e=t&cal=U132013_9665", "club_id": "9665"},
    {"nimi": "Ässät U14", "ical": "https://ics.jopox.fi/hockeypox/calendar/ical.php?ics=true&e=t&cal=U142012_9666", "club_id": "9666"},
    {"nimi": "Ässät Maalivahdit", "ical": "https://ics.jopox.fi/hockeypox/calendar/ical.php?ics=true&e=t&cal=Maalivahtijaatoiminta_9681", "club_id": "9681"}
]

# --- 3. LOGIIKKA ---
def aja_haku(user, pw, alku_pvm, loppu_pvm):
    tulokset = []
    with sync_playwright() as p:
        # headless=True ja args ovat pakollisia pilvessä
        browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
        context = browser.new_context()
        page = context.new_page()

        try:
            # Kirjautuminen
            page.goto("https://login.jopox.fi/login?to=145")
            page.wait_for_selector("input[type='password']", timeout=10000)
            page.keyboard.press("Shift+Tab")
            page.keyboard.type(user)
            page.keyboard.press("Tab")
            page.keyboard.type(pw)
            page.keyboard.press("Enter")
            
            # Odotetaan hetki kirjautumista
            page.wait_for_timeout(5000)

            curr = alku_pvm
            while curr <= loppu_pvm:
                etsi_pvm = curr.strftime('%Y%m%d')
                nayta_pvm = curr.strftime('%d.%m.%Y')
                
                for j in JOUKKUEET:
                    res = requests.get(j['ical'])
                    ical = res.text.replace("\r\n ", "").replace("\n ", "")
                    
                    for seg in ical.split("BEGIN:VEVENT"):
                        if "END:VEVENT" not in seg: continue
                        
                        pvm_m = re.search(r"DTSTART[:;](?:.*:)?(\d{8})", seg)
                        if pvm_m and pvm_m.group(1) == etsi_pvm:
                            # Aikojen ja UID:n haku (sama logiikka kuin alkuperäisessä)
                            uid_match = re.search(r"UID:(.*)", seg)
                            if uid_match:
                                uid_nro = "".join(filter(str.isdigit, uid_match.group(1)))
                                t_path = "game" if "game" in uid_match.group(1).lower() else "training"
                                
                                try:
                                    page.goto(f"https://assat-app.jopox.fi/{t_path}/club/{j['club_id']}/{uid_nro}")
                                    page.wait_for_selector("#yesBox", timeout=5000)
                                    maara = page.locator("#yesBox .chip.player").count()
                                    if maara == 0: maara = page.locator("#yesBox .chip").count()
                                    
                                    tulokset.append({
                                        "Päivä": nayta_pvm,
                                        "Joukkue": j['nimi'],
                                        "Pelaajia": maara,
                                        "Tarve": "2 KOPPIA" if maara > 16 else "1 KOPPI"
                                    })
                                except: pass
                curr += timedelta(days=1)
        finally:
            browser.close()
    return tulokset

# --- 4. KÄYTTÖLIITTYMÄ ---
st.set_page_config(page_title="Koppi-Apuri", page_icon="🏒")
st.title("🏒 Ässät Koppi-Apuri")

with st.sidebar:
    user = st.text_input("Jopox Tunnus")
    pw = st.text_input("Salasana", type="password")
    alku = st.date_input("Alku", datetime.now())
    loppu = st.date_input("Loppu", datetime.now() + timedelta(days=3))
    nappi = st.button("Hae tiedot")

if nappi:
    if not user or not pw:
        st.error("Syötä tunnus ja salasana!")
    else:
        with st.status("Haetaan tietoja Jopoxista...", expanded=True) as status:
            data = aja_haku(user, pw, alku, loppu)
            status.update(label="Haku valmis!", state="complete", expanded=False)
        
        if data:
            st.table(data)
        else:
            st.info("Ei tapahtumia valitulla aikavälillä.")
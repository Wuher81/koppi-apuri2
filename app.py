import streamlit as st
from playwright.sync_api import sync_playwright
import requests
import re
import os
import subprocess
from datetime import datetime, timedelta

# --- 1. SELAIMEN ASENNUS STREAMLITISSÄ ---
def asenna_selaimet():
    if not os.path.exists("/home/adminuser/.cache/ms-playwright"):
        try:
            subprocess.run(["playwright", "install", "chromium"], check=True)
            subprocess.run(["playwright", "install-deps"], check=True)
        except Exception as e:
            st.error(f"Selainasennus epäonnistui: {e}")

asenna_selaimet()

# --- 2. JOUKKUEET ---
JOUKKUEET = [
    {"nimi": "Ässät U12", "ical": "https://ics.jopox.fi/hockeypox/calendar/ical.php?ics=true&e=t&cal=U122014_9664", "club_id": "9664"},
    {"nimi": "Ässät U13", "ical": "https://ics.jopox.fi/hockeypox/calendar/ical.php?ics=true&e=t&cal=U132013_9665", "club_id": "9665"},
    {"nimi": "Ässät U14", "ical": "https://ics.jopox.fi/hockeypox/calendar/ical.php?ics=true&e=t&cal=U142012_9666", "club_id": "9666"},
    {"nimi": "Ässät Maalivahdit", "ical": "https://ics.jopox.fi/hockeypox/calendar/ical.php?ics=true&e=t&cal=Maalivahtijaatoiminta_9681", "club_id": "9681"}
]

def aja_haku(user, pw, alku, loppu):
    tulokset = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
        context = browser.new_context(viewport={'width': 1280, 'height': 800})
        page = context.new_page()

        try:
            st.write("Kirjaudutaan Jopoxiin...")
            page.goto("https://login.jopox.fi/login?to=145")
            
            # Kirjautumislomake
            page.wait_for_selector("input[type='password']")
            page.keyboard.press("Shift+Tab")
            page.keyboard.type(user)
            page.keyboard.press("Tab")
            page.keyboard.type(pw)
            page.keyboard.press("Enter")
            
            # KRIITTINEN VAIHE: Välisivun käsittely
            page.wait_for_timeout(5000)
            btn = page.locator("text=/TO BROWSER VERSION|SIIRRY SELAINVERSIOON/i")
            if btn.is_visible():
                st.write("Ohitetaan välisivu...")
                btn.click()
                page.wait_for_load_state("networkidle")

            curr = alku
            while curr <= loppu:
                pvm_etsi = curr.strftime('%Y%m%d')
                pvm_nayta = curr.strftime('%d.%m.%Y')
                
                for j in JOUKKUEET:
                    res = requests.get(j['ical'])
                    for event in res.text.split("BEGIN:VEVENT"):
                        if pvm_etsi in event:
                            uid_m = re.search(r"UID:(.*)", event)
                            if uid_m:
                                uid = "".join(filter(str.isdigit, uid_m.group(1)))
                                t_path = "game" if "game" in event.lower() else "training"
                                
                                try:
                                    page.goto(f"https://assat-app.jopox.fi/{t_path}/club/{j['club_id']}/{uid}")
                                    page.wait_for_selector("#yesBox", timeout=7000)
                                    maara = page.locator("#yesBox .chip.player").count()
                                    if maara == 0:
                                        maara = page.locator("#yesBox .chip").count()
                                    
                                    if maara > 0:
                                        tulokset.append({"Pvm": pvm_nayta, "Joukkue": j['nimi'], "Hlö": maara, "Koppeja": "2" if maara > 16 else "1"})
                                except: pass
                curr += timedelta(days=1)
        finally:
            browser.close()
    return tulokset

# --- UI ---
st.title("🏒 Ässät Koppi-Apuri")
with st.sidebar:
    u = st.text_input("Sähköposti")
    p = st.text_input("Salasana", type="password")
    alku = st.date_input("Alku", datetime.now())
    loppu = st.date_input("Loppu", datetime.now() + timedelta(days=3))
    nappi = st.button("KÄYNNISTÄ HAKU")

if nappi:
    if not u or not p: st.error("Syötä tunnukset!")
    else:
        with st.status("Haetaan tietoja selaimella...") as s:
            data = aja_haku(u, p, alku, loppu)
            s.update(label="Haku valmis!", state="complete")
        if data: st.table(data)
        else: st.warning("Ei tapahtumia.")
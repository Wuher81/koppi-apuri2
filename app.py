import streamlit as st
import requests
import re
import time  # Tarvitaan viiveitä varten
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

# --- JOUKKUEIDEN ASETUKSET ---
JOUKKUEET = [
    {"nimi": "Ässät U12", "ical": "https://ics.jopox.fi/hockeypox/calendar/ical.php?ics=true&e=t&cal=U122014_9664", "club_id": "9664"},
    {"nimi": "Ässät U13", "ical": "https://ics.jopox.fi/hockeypox/calendar/ical.php?ics=true&e=t&cal=U132013_9665", "club_id": "9665"},
    {"nimi": "Ässät U14", "ical": "https://ics.jopox.fi/hockeypox/calendar/ical.php?ics=true&e=t&cal=U142012_9666", "club_id": "9666"},
    {"nimi": "Ässät Maalivahdit", "ical": "https://ics.jopox.fi/hockeypox/calendar/ical.php?ics=true&e=t&cal=Maalivahtijaatoiminta_9681", "club_id": "9681"}
]

def aja_haku_varmistettu(user, pw, alku_pvm, loppu_pvm):
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Origin": "https://login.jopox.fi",
        "Referer": "https://login.jopox.fi/login?to=145"
    })
    
    tulokset = []
    
    try:
        # 1. ALUSTUS
        st.write("Alustetaan istuntoa...")
        init_resp = session.get("https://login.jopox.fi/login?to=145")
        soup = BeautifulSoup(init_resp.text, 'html.parser')
        
        login_payload = {
            "__VIEWSTATE": soup.find("input", {"name": "__VIEWSTATE"})['value'] if soup.find("input", {"name": "__VIEWSTATE"}) else "",
            "__VIEWSTATEGENERATOR": soup.find("input", {"name": "__VIEWSTATEGENERATOR"})['value'] if soup.find("input", {"name": "__VIEWSTATEGENERATOR"}) else "",
            "__EVENTVALIDATION": soup.find("input", {"name": "__EVENTVALIDATION"})['value'] if soup.find("input", {"name": "__EVENTVALIDATION"}) else "",
            "username": user,
            "password": pw,
            "login": "Kirjaudu"
        }
        
        # 2. KIRJAUDUTAAN SISÄÄN
        st.write("Kirjaudutaan sisään...")
        login_res = session.post("https://login.jopox.fi/login/authenticate", data=login_payload, allow_redirects=True)
        
        # --- LISÄTTY VIIVE ---
        # Annetaan Jopoxin session asettua rauhassa (kuten alkuperäisessä koodissasi)
        time.sleep(3) 
        
        # 3. KÄSITELLÄÄN "MY ASSOCIATIONS" -VÄLISIVU
        st.write("Siirrytään selainversioon...")
        assoc_soup = BeautifulSoup(login_res.text, 'html.parser')
        
        # Etsitään kaikki linkit ja katsotaan onko niissä teksti "BROWSER VERSION"
        browser_link = None
        for a in assoc_soup.find_all("a", href=True):
            if "BROWSER VERSION" in a.get_text().upper() or "SELAINVERSIO" in a.get_text().upper():
                browser_link = a
                break
        
        if browser_link:
            target_url = browser_link['href']
            if not target_url.startswith("http"):
                target_url = "https://login.jopox.fi" + target_url
            session.get(target_url, allow_redirects=True)
            # Viive klikkauksen jälkeen
            time.sleep(2)
        
        # 4. TARKISTUS
        check_res = session.get("https://assat-app.jopox.fi/home", allow_redirects=True)
        if "Kirjaudu" in check_res.text:
            st.error("❌ Kirjautuminen epäonnistui välisivulla. Tarkista tunnus/salasana.")
            return None

        st.success("✅ Kirjautuminen onnistui!")

        # 5. KALENTERIN LÄPIKÄYNTI
        curr = alku_pvm
        while curr <= loppu_pvm:
            pvm_str = curr.strftime('%Y%m%d')
            nayta_pvm = curr.strftime('%d.%m.%Y')
            
            for j in JOUKKUEET:
                ical_res = requests.get(j['ical'])
                events = ical_res.text.replace("\r\n ", "").split("BEGIN:VEVENT")
                
                for event in events:
                    if pvm_str in event:
                        uid_match = re.search(r"UID:(.*)", event)
                        if uid_match:
                            uid = "".join(filter(str.isdigit, uid_match.group(1)))
                            t_path = "game" if "game" in event.lower() else "training"
                            
                            url = f"https://assat-app.jopox.fi/{t_path}/club/{j['club_id']}/{uid}"
                            page_res = session.get(url)
                            
                            event_soup = BeautifulSoup(page_res.text, 'html.parser')
                            yes_box = event_soup.find("div", id="yesBox")
                            
                            if yes_box:
                                pelaajat = yes_box.find_all("div", class_=re.compile(r"\bplayer\b"))
                                maara = len(pelaajat)
                                
                                if maara > 0:
                                    tulokset.append({
                                        "Päivä": nayta_pvm,
                                        "Joukkue": j['nimi'],
                                        "Pelaajia": maara,
                                        "Tarve": "2 KOPPIA" if maara > 16 else "1 KOPPI"
                                    })
            curr += timedelta(days=1)
            
    except Exception as e:
        st.error(f"Tekninen virhe: {e}")
    
    return tulokset

# --- KÄYTTÖLIITTYMÄ ---
st.set_page_config(page_title="Ässät Koppi-Apuri", layout="centered")
st.title("🏒 Ässät Koppi-Apuri")

with st.sidebar:
    u = st.text_input("Jopox Tunnus (Sähköposti)")
    p = st.text_input("Salasana", type="password")
    alku = st.date_input("Alku", datetime.now())
    loppu = st.date_input("Loppu", datetime.now() + timedelta(days=3))
    nappi = st.button("HAE TIEDOT")

if nappi:
    if not u or not p:
        st.warning("Syötä tunnukset.")
    else:
        with st.status("Haetaan tietoja...", expanded=True) as status:
            data = aja_haku_varmistettu(u, p, alku, loppu)
            if data is not None:
                if data:
                    status.update(label="Haku valmis!", state="complete")
                    st.table(data)
                else:
                    status.update(label="Ei tapahtumia löydetty.", state="error")
                    st.info("Valitulla aikavälillä ei löytynyt tapahtumia iCal-linkeistä.")
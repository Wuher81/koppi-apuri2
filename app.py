import streamlit as st
import requests
import re
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
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
    })
    
    tulokset = []
    
    try:
        # 1. HAETAAN KIRJAUTUMISSIVU JA TEKNISET AVAIMET
        resp = session.get("https://login.jopox.fi/login?to=145")
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # Haetaan ASP.NET piilokentät (tärkeää kirjautumiselle)
        viewstate = soup.find("input", {"name": "__VIEWSTATE"})
        validation = soup.find("input", {"name": "__EVENTVALIDATION"})
        
        login_payload = {
            "__VIEWSTATE": viewstate['value'] if viewstate else "",
            "__EVENTVALIDATION": validation['value'] if validation else "",
            "username": user,
            "password": pw,
            "login": "Kirjaudu"
        }
        
        # 2. KIRJAUDUTAAN SISÄÄN
        session.post("https://login.jopox.fi/login/authenticate", data=login_payload)
        
        # 3. KALENTERIN LÄPIKÄYNTI
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
                            
                            # Haetaan tapahtuman sivu
                            url = f"https://assat-app.jopox.fi/{t_path}/club/{j['club_id']}/{uid}"
                            page_res = session.get(url)
                            
                            # LASKENTA: Käytetään BeautifulSoupia tarkempaan hakuun
                            event_soup = BeautifulSoup(page_res.text, 'html.parser')
                            # Etsitään kaikki divit, joilla on luokka 'chip' ja 'player'
                            pelaaja_sirut = event_soup.find_all("div", class_=lambda x: x and 'chip' in x and 'player' in x)
                            maara = len(pelaaja_sirut)
                            
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
st.title("🏒 Ässät Koppi-Apuri (Lite)")

with st.sidebar:
    st.subheader("Kirjautuminen")
    u = st.text_input("Jopox Tunnus (Sähköposti)")
    p = st.text_input("Salasana", type="password")
    alku = st.date_input("Alkupäivä", datetime.now())
    loppu = st.date_input("Loppupäivä", datetime.now() + timedelta(days=3))
    nappi = st.button("HAE KOPPITARPEET")

if nappi:
    if not u or not p:
        st.warning("Syötä sähköpostiosoite ja salasana.")
    else:
        with st.status("Haetaan ja analysoidaan Jopox-tietoja...", expanded=True) as status:
            data = aja_haku_varmistettu(u, p, alku, loppu)
            if data:
                status.update(label="Haku valmis!", state="complete")
                st.table(data)
            else:
                status.update(label="Haku päättyi, mutta tietoja ei löytynyt.", state="error")
                st.info("Vinkki: Varmista, että tunnuksesi on oikein ja että valitulla aikavälillä on tapahtumia Jopox-kalenterissa.")
import streamlit as st
import requests
import re
from datetime import datetime, timedelta

# --- JOUKKUEIDEN ASETUKSET ---
JOUKKUEET = [
    {"nimi": "Ässät U12", "ical": "https://ics.jopox.fi/hockeypox/calendar/ical.php?ics=true&e=t&cal=U122014_9664", "club_id": "9664"},
    {"nimi": "Ässät U13", "ical": "https://ics.jopox.fi/hockeypox/calendar/ical.php?ics=true&e=t&cal=U132013_9665", "club_id": "9665"},
    {"nimi": "Ässät U14", "ical": "https://ics.jopox.fi/hockeypox/calendar/ical.php?ics=true&e=t&cal=U142012_9666", "club_id": "9666"},
    {"nimi": "Ässät Maalivahdit", "ical": "https://ics.jopox.fi/hockeypox/calendar/ical.php?ics=true&e=t&cal=Maalivahtijaatoiminta_9681", "club_id": "9681"}
]

def aja_haku_lite(user, pw, alku_pvm, loppu_pvm):
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
    
    tulokset = []
    
    try:
        # 1. Kirjautuminen
        st.write("Kirjaudutaan Jopoxiin...")
        login_url = "https://login.jopox.fi/login/authenticate"
        login_payload = {
            "username": user,
            "password": pw,
            "login": "Kirjaudu"
        }
        
        # Kirjaudutaan sisään (to = 145 on Ässät-sovellus)
        session.post("https://login.jopox.fi/login?to=145", data=login_payload)

        # 2. Aikavälin läpikäynti
        curr = alku_pvm
        while curr <= loppu_pvm:
            pvm_str = curr.strftime('%Y%m%d')
            nayta_pvm = curr.strftime('%d.%m.%Y')
            
            for j in JOUKKUEET:
                # Haetaan iCal-data
                ical_res = requests.get(j['ical'])
                # Etsitään päivän tapahtumat iCal-tekstistä
                events = ical_res.text.replace("\r\n ", "").split("BEGIN:VEVENT")
                
                for event in events:
                    if pvm_str in event:
                        uid_match = re.search(r"UID:(.*)", event)
                        if uid_match:
                            uid = "".join(filter(str.isdigit, uid_match.group(1)))
                            t_path = "game" if "game" in event.lower() else "training"
                            
                            # Haetaan tapahtumasivu suoraan
                            url = f"https://assat-app.jopox.fi/{t_path}/club/{j['club_id']}/{uid}"
                            page_res = session.get(url)
                            
                            # LASKENTA: Etsitään "chip player" esiintymät HTML:stä
                            # Tämä perustuu lähettämääsi lähdekoodiin
                            pelaajat = page_res.text.count("chip  player")
                            
                            if pelaajat > 0:
                                tulokset.append({
                                    "Pvm": nayta_pvm,
                                    "Joukkue": j['nimi'],
                                    "Pelaajia": pelaajat,
                                    "Koppitarve": "2 KOPPIA" if pelaajat > 16 else "1 KOPPI"
                                })
            curr += timedelta(days=1)
            
    except Exception as e:
        st.error(f"Haku epäonnistui: {e}")
    
    return tulokset

# --- KÄYTTÖLIITTYMÄ ---
st.set_page_config(page_title="Ässät Koppi-Web", page_icon="🏒")
st.title("🏒 Ässät Koppi-Apuri (Lite)")

with st.sidebar:
    u = st.text_input("Jopox Tunnus")
    p = st.text_input("Salasana", type="password")
    start = st.date_input("Alku", datetime.now())
    end = st.date_input("Loppu", datetime.now() + timedelta(days=4))
    nappi = st.button("HAE TIEDOT")

if nappi:
    if not u or not p:
        st.error("Syötä tunnukset!")
    else:
        with st.spinner("Haetaan tietoja ilman selainta..."):
            data = aja_haku_lite(u, p, start, end)
            if data:
                st.table(data)
            else:
                st.info("Ei tapahtumia tai kirjautuminen epäonnistui.")
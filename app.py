import streamlit as st
import requests
import re
import time
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

# --- ASETUKSET ---
JOUKKUEET = [
    {"nimi": "Ässät U12", "ical": "https://ics.jopox.fi/hockeypox/calendar/ical.php?ics=true&e=t&cal=U122014_9664", "club_id": "9664"},
    {"nimi": "Ässät U13", "ical": "https://ics.jopox.fi/hockeypox/calendar/ical.php?ics=true&e=t&cal=U132013_9665", "club_id": "9665"},
    {"nimi": "Ässät U14", "ical": "https://ics.jopox.fi/hockeypox/calendar/ical.php?ics=true&e=t&cal=U142012_9666", "club_id": "9666"},
    {"nimi": "Ässät Maalivahdit", "ical": "https://ics.jopox.fi/hockeypox/calendar/ical.php?ics=true&e=t&cal=Maalivahtijaatoiminta_9681", "club_id": "9681"}
]

def aja_haku_varmistettu(user, pw, alku_pvm, loppu_pvm):
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Referer": "https://login.jopox.fi/login?to=145"
    })
    
    tulokset = []
    
    try:
        # 1. ALUSTUS
        st.write("🔍 Alustetaan yhteyttä...")
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
        st.write("🔑 Kirjaudutaan sisään...")
        login_res = session.post("https://login.jopox.fi/login/authenticate", data=login_payload, allow_redirects=True)
        time.sleep(2)
        
        # 3. VÄLISIVUN KÄSITTELY (My Associations)
        if "TO BROWSER VERSION" in login_res.text or "VERSION" in login_res.text.upper():
            st.write("🚀 Ohitetaan valintasivua...")
            soup2 = BeautifulSoup(login_res.text, 'html.parser')
            
            # Etsitään linkki, jossa lukee VERSION
            target_link = None
            all_links = soup2.find_all("a", href=True)
            for l in all_links:
                if "VERSION" in l.text.upper():
                    target_link = l['href']
                    break
            
            if target_link:
                if not target_link.startswith("http"):
                    target_link = "https://login.jopox.fi" + target_link
                session.get(target_link, allow_redirects=True)
                time.sleep(1)
            else:
                st.warning("⚠️ Valintapainiketta ei löytynyt automaattisesti. Yritetään suoraa hyppyä.")
                # Varatyö: yritetään mennä suoraan Ässien portaaliin
                session.get("https://login.jopox.fi/home/select?to=145&portal=2", allow_redirects=True)

        # 4. LOPULLINEN VARMISTUS
        final_check = session.get("https://assat-app.jopox.fi/home")
        if "Kirjaudu" in final_check.text:
            st.error("❌ Kirjautuminen epäonnistui. Jopox ei päästänyt koodia sisään välisivulta.")
            # VIANMÄÄRITYS: Tulostetaan linkit jos epäonnistuu
            with st.expander("Tekninen vianmääritys (Näytä tämä tuelle)"):
                st.write("URL juuri nyt:", final_check.url)
                st.write("Sivulta löytyneet linkit:")
                st.write([a.text.strip() for a in BeautifulSoup(login_res.text, 'html.parser').find_all('a')])
            return None

        st.success("✅ Sisällä ollaan! Haetaan tapahtumat...")

        # 5. TAPAHTUMIEN HAKU (Sama logiikka kuin ennen)
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
                                maara = len(yes_box.find_all("div", class_=re.compile(r"\bplayer\b")))
                                if maara > 0:
                                    tulokset.append({
                                        "Päivä": nayta_pvm, "Joukkue": j['nimi'], 
                                        "Pelaajia": maara, "Tarve": "2 KOPPIA" if maara > 16 else "1 KOPPI"
                                    })
            curr += timedelta(days=1)
            
    except Exception as e:
        st.error(f"⚠️ Odottamaton virhe: {e}")
    
    return tulokset

# --- KÄYTTÖLIITTYMÄ ---
st.set_page_config(page_title="Ässät Koppi-Apuri", page_icon="🏒")
st.title("🏒 Ässät Koppi-Apuri")

with st.sidebar:
    st.header("Asetukset")
    u = st.text_input("Sähköposti")
    p = st.text_input("Salasana", type="password")
    alku = st.date_input("Alkupäivä", datetime.now())
    loppu = st.date_input("Loppupäivä", datetime.now() + timedelta(days=3))
    nappi = st.button("KÄYNNISTÄ HAKU", use_container_width=True)

if nappi:
    if not u or not p:
        st.warning("Syötä tunnukset.")
    else:
        with st.status("Suoritetaan hakua...", expanded=True) as status:
            data = aja_haku_varmistettu(u, p, alku, loppu)
            if data is not None:
                if data:
                    status.update(label="Haku valmis!", state="complete")
                    st.table(data)
                else:
                    status.update(label="Haku valmis, ei tapahtumia.", state="complete")
                    st.info("Valitulla välillä ei löytynyt tapahtumia iCal-kalentereista.")
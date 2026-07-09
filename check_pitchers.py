import datetime
import os
import requests

# Deine persönliche Pitcher-Liste
MY_PITCHERS = [
    "Paul Skenes", "Shohei Ohtani", "Aaron Nola", "Cristopher Sanchez",
    "Cam Schlittler", "Tarik Skubal", "Dylan Cease", "Yoshinobu Yamamoto",
    "Jacob Misiorowski", "Sandy Alcantara", "Kevin Gausman", "Zack Wheeler",
    "Max Fried", "Jesús Luzardo", "Andrew Painter", "Justin Wrobleski",
    "Gerrit Cole", "Spencer Strider", "Ranger Suarez"
]

# Vollständiges MLB Mapping für alle 30 Teams (Kürzel & Kurzname)
TEAM_MAP = {
    "Arizona Diamondbacks": {"abbr": "AZ", "short": "D-backs"},
    "Atlanta Braves": {"abbr": "ATL", "short": "Braves"},
    "Baltimore Orioles": {"abbr": "BAL", "short": "Orioles"},
    "Boston Red Sox": {"abbr": "BOS", "short": "Red Sox"},
    "Chicago Cubs": {"abbr": "CHC", "short": "Cubs"},
    "Chicago White Sox": {"abbr": "CWS", "short": "White Sox"},
    "Cincinnati Reds": {"abbr": "CIN", "short": "Reds"},
    "Cleveland Guardians": {"abbr": "CLE", "short": "Guardians"},
    "Colorado Rockies": {"abbr": "COL", "short": "Rockies"},
    "Detroit Tigers": {"abbr": "DET", "short": "Tigers"},
    "Houston Astros": {"abbr": "HOU", "short": "Astros"},
    "Kansas City Royals": {"abbr": "KC", "short": "Royals"},
    "Los Angeles Angels": {"abbr": "LAA", "short": "Angels"},
    "Los Angeles Dodgers": {"abbr": "LAD", "short": "Dodgers"},
    "Miami Marlins": {"abbr": "MIA", "short": "Marlins"},
    "Milwaukee Brewers": {"abbr": "MIL", "short": "Brewers"},
    "Minnesota Twins": {"abbr": "MIN", "short": "Twins"},
    "New York Mets": {"abbr": "NYM", "short": "Mets"},
    "New York Yankees": {"abbr": "NYY", "short": "Yankees"},
    "Oakland Athletics": {"abbr": "OAK", "short": "Athletics"},
    "Philadelphia Phillies": {"abbr": "PHI", "short": "Phillies"},
    "Pittsburgh Pirates": {"abbr": "PIT", "short": "Pirates"},
    "San Diego Padres": {"abbr": "SD", "short": "Padres"},
    "San Francisco Giants": {"abbr": "SF", "short": "Giants"},
    "Seattle Mariners": {"abbr": "SEA", "short": "Mariners"},
    "St. Louis Cardinals": {"abbr": "STL", "short": "Cardinals"},
    "Tampa Bay Rays": {"abbr": "TB", "short": "Rays"},
    "Texas Rangers": {"abbr": "TEX", "short": "Rangers"},
    "Toronto Blue Jays": {"abbr": "TOR", "short": "Blue Jays"},
    "Washington Nationals": {"abbr": "WSH", "short": "Nationals"}
}

HA_WEBHOOK_URL = os.environ.get("HA_WEBHOOK_URL")

def get_team_info(team_name):
    return TEAM_MAP.get(team_name, {"abbr": team_name, "short": team_name})

def convert_to_local_time(utc_string):
    if not utc_string:
        return "--:--"
    try:
        utc_dt = datetime.datetime.strptime(utc_string, "%Y-%m-%dT%H:%M:%SZ")
        import zoneinfo
        local_tz = zoneinfo.ZoneInfo("Europe/Berlin")
        local_dt = utc_dt.replace(tzinfo=datetime.timezone.utc).astimezone(local_tz)
        return local_dt.strftime("%H:%M")
    except Exception:
        return utc_string[11:16]

def check_pitchers():
    today = datetime.date.today().strftime("%Y-%m-%d")
    url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={today}&hydrate=probablePitcher"
    
    # "Browser-Tarnkappe" (User-Agent), damit die MLB-Firewall uns auf GitHub nicht blockiert
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    print(f"--- MLB-DIAGNOSE-LOGS FÜR DEN {today} ---")
    print(f"Rufe API auf: {url}")
    
    try:
        res = requests.get(url, headers=headers, timeout=15)
        print(f"Server-Antwort Status-Code: {res.status_code}")
        res.raise_for_status()
        response = res.json()
    except Exception as e:
        print(f"❌ KRITISCHER FEHLER beim API-Aufruf: {e}")
        return

    alerts = []
    dates = response.get("dates", [])
    if not dates:
        print("ℹ️ Keine Spiele im heutigen Kalender gefunden.")
        return

    print("\n--- Gefeaturte Spiele & Pitcher heute laut MLB-Datenbank: ---")
    for date_info in dates:
        for game in date_info.get("games", []):
            teams = game.get("teams", {})
            away_full = teams.get("away", {}).get("team", {}).get("name")
            home_full = teams.get("home", {}).get("team", {}).get("name")
            
            away_info = get_team_info(away_full)
            home_info = get_team_info(home_full)

            local_time = convert_to_local_time(game.get("gameDate"))
            
            away_pitcher = teams.get("away", {}).get("probablePitcher", {}).get("fullName")
            home_pitcher = teams.get("home", {}).get("probablePitcher", {}).get("fullName")
            
            # Diagnose-Ausgabe für jedes Spiel im GitHub-Protokoll
            print(f"Match: {away_info['short']} @ {home_info['short']} um {local_time} Uhr")
            print(f"   -> Starter Away: {away_pitcher if away_pitcher else 'TBD'}")
            print(f"   -> Starter Home: {home_pitcher if home_pitcher else 'TBD'}")

            # Auswärtspitcher abgleichen
            if away_pitcher and away_pitcher in MY_PITCHERS:
                alerts.append(f"⚾ {away_pitcher} ({away_info['abbr']}) | {local_time} @ {home_info['short']}")
                print(f"   🎯 TREFFER! {away_pitcher} steht auf deiner Favoritenliste!")

            # Heimpitcher abgleichen
            if home_pitcher and home_pitcher in MY_PITCHERS:
                alerts.append(f"⚾ {home_pitcher} ({home_info['abbr']}) | {local_time} vs. {away_info['short']}")
                print(f"   🎯 TREFFER! {home_pitcher} steht auf deiner Favoritenliste!")

    print("\n--- Zusammenfassung ---")
    if alerts:
        message = "\n".join(alerts)
        print(f"Sende folgende Nachricht an Home Assistant:\n{message}")
        send_to_homeassistant(message)
    else:
        print("Es wurde heute kein Pitcher deiner Favoritenliste gefunden.")

def send_to_homeassistant(text):
    if HA_WEBHOOK_URL:
        try:
            res = requests.post(HA_WEBHOOK_URL, json={"message": text}, timeout=10)
            print(f"Webhook erfolgreich abgesetzt. Antwort-Status: {res.status_code}")
        except Exception as e:
            print(f"❌ Fehler beim Senden an Home Assistant: {e}")
    else:
        print("⚠️ Keine HA_WEBHOOK_URL als Secret in GitHub hinterlegt.")

if __name__ == "__main__":
    check_pitchers()

import datetime
import os
import requests
import zoneinfo

# ==========================================
# 1. KONFIGURATION & DATEN LADEN
# ==========================================
PITCHERS_FILE = "pitchers.txt"
HA_WEBHOOK_URL = os.environ.get("HA_WEBHOOK_URL")

# Pitcher dynamisch aus Textdatei laden
TRACKED_PITCHERS = set()
if os.path.exists(PITCHERS_FILE):
    with open(PITCHERS_FILE, "r", encoding="utf-8") as f:
        TRACKED_PITCHERS = {line.strip() for line in f if line.strip()}
    print(f"Erfolgreich {len(TRACKED_PITCHERS)} Pitcher aus {PITCHERS_FILE} geladen.")
else:
    print(f"FEHLER: {PITCHERS_FILE} wurde nicht gefunden!")
    exit(1)

# Vollständiges MLB Mapping für alle 30 Teams (Kürzel & Kurzname)
TEAM_MAP = {
    "Arizona Diamondbacks": {"abbr": "ARI", "short": "D-backs"},
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
    "Toronto Blue Jays": {"abspath": "TOR", "abbr": "TOR", "short": "Blue Jays"},
    "Washington Nationals": {"abbr": "WSH", "short": "Nationals"}
}

def get_team_info(team_name):
    return TEAM_MAP.get(team_name, {"abbr": team_name[:3].upper(), "short": team_name})

def convert_to_local_time(utc_string):
    if not utc_string:
        return "--:--"
    try:
        # Extrahiert das korrekte ISO-Format der MLB-API
        clean_string = utc_string.split(".")[0].replace("Z", "")
        utc_dt = datetime.datetime.strptime(clean_string, "%Y-%m-%dT%H:%M:%S")
        local_tz = zoneinfo.ZoneInfo("Europe/Berlin")
        local_dt = utc_dt.replace(tzinfo=datetime.timezone.utc).astimezone(local_tz)
        return local_dt.strftime("%H:%M")
    except Exception as e:
        print(f"Zeitkonvertierungsfehler für {utc_string}: {e}")
        return utc_string[11:16] if len(utc_string) > 16 else "--:--"

# ==========================================
# 2. API-ABFRAGE & VERARBEITUNG
# ==========================================
def check_pitchers():
    today = datetime.date.today().strftime("%Y-%m-%d")
    url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={today}&hydrate=probablePitcher"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    print(f"Rufe MLB-API auf für {today}...")
    try:
        res = requests.get(url, headers=headers, timeout=15)
        res.raise_for_status()
        response = res.json()
    except Exception as e:
        print(f"❌ KRITISCHER FEHLER beim API-Aufruf: {e}")
        return

    alerts = []
    dates = response.get("dates", [])
    
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
            
            # Auswärtspitcher abgleichen
            if away_pitcher and away_pitcher in TRACKED_PITCHERS:
                # Format: Jesús Luzardo (PHI) | 01:10 @ Reds
                line = f"{away_pitcher} ({away_info['abbr']}) | {local_time} @ {home_info['short']}"
                alerts.append(line)
                print(f"🎯 TREFFER! {line}")

            # Heimpitcher abgleichen
            if home_pitcher and home_pitcher in TRACKED_PITCHERS:
                # Format: Jesús Luzardo (PHI) | 01:10 vs. Reds
                line = f"{home_pitcher} ({home_info['abbr']}) | {local_time} vs. {away_info['short']}"
                alerts.append(line)
                print(f"🎯 TREFFER! {line}")

    # ==========================================
    # 3. GESAMMELTEN WEBHOOK SENDEN
    # ==========================================
    if alerts:
        message_content = "\n".join(alerts)
        print(f"\nSende an Home Assistant:\n{message_content}")
        
        if HA_WEBHOOK_URL:
            payload = {
                "title": "⚾ Today's Starters on real⚾",
                "content": message_content
            }
            try:
                req = requests.post(HA_WEBHOOK_URL, json=payload, timeout=10)
                print(f"Webhook gesendet. Status: {req.status_code}")
            except Exception as e:
                print(f"❌ Fehler beim Senden des Webhooks: {e}")
        else:
            print("⚠️ Keine HA_WEBHOOK_URL gefunden.")
    else:
        print("Heute starten keine deiner beobachteten Pitcher.")

if __name__ == "__main__":
    check_pitchers()

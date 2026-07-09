import os
import requests
import statsapi
from datetime import datetime, timedelta

# ==========================================
# 1. DYNAMISCHES LADEN DER PITCHER-LISTE
# ==========================================
script_dir = os.path.dirname(os.path.abspath(__file__))
txt_path = os.path.join(script_dir, "pitchers.txt")

TARGET_PITCHERS = []
if os.path.exists(txt_path):
    with open(txt_path, "r", encoding="utf-8") as f:
        TARGET_PITCHERS = [line.strip() for line in f if line.strip()]
    print(f"Erfolgreich {len(TARGET_PITCHERS)} Pitcher aus pitchers.txt geladen.")
else:
    print(f"FEHLER: {txt_path} wurde nicht gefunden!")
    exit(1)

# MLB Team-Mapping für exakte 3-Letter-Abkürzungen
TEAM_MAP = {
    "Arizona Diamondbacks": "ARI", "Atlanta Braves": "ATL", "Baltimore Orioles": "BAL",
    "Boston Red Sox": "BOS", "Chicago Cubs": "CHC", "Chicago White Sox": "CWS",
    "Cincinnati Reds": "CIN", "Cleveland Guardians": "CLE", "Colorado Rockies": "COL",
    "Detroit Tigers": "DET", "Houston Astros": "HOU", "Kansas City Royals": "KC",
    "Los Angeles Angels": "LAA", "Los Angeles Dodgers": "LAD", "Miami Marlins": "MIA",
    "Milwaukee Brewers": "MIL", "Minnesota Twins": "MIN", "New York Mets": "NYM",
    "New York Yankees": "NYY", "Oakland Athletics": "OAK", "Philadelphia Phillies": "PHI",
    "Pittsburgh Pirates": "PIT", "San Diego Padres": "SD", "San Francisco Giants": "SF",
    "Seattle Mariners": "SEA", "St. Louis Cardinals": "STL", "Tampa Bay Rays": "TB",
    "Texas Rangers": "TEX", "Toronto Blue Jays": "TOR", "Washington Nationals": "WSH"
}

# ==========================================
# 2. KONFIGURATION
# ==========================================
HA_WEBHOOK_URL = os.environ.get("HA_WEBHOOK_URL")
today = datetime.today().strftime('%Y-%m-%d')
print(f"Suche nach Spielen für den {today}...")

# ==========================================
# 3. API-ABFRAGE & TEXT-FORMATIERUNG
# ==========================================
try:
    games = statsapi.schedule(date=today)
    starter_lines = []

    for game in games:
        home_pitcher = game.get("home_probable_pitcher", "").strip()
        away_pitcher = game.get("away_probable_pitcher", "").strip()
        
        match_home = home_pitcher in TARGET_PITCHERS if home_pitcher else False
        match_away = away_pitcher in TARGET_PITCHERS if away_pitcher else False

        if match_home or match_away:
            pitcher_name = home_pitcher if match_home else away_pitcher
            
            # Teams auslesen
            home_team_long = game.get("home_name", "")
            away_team_long = game.get("away_name", "")
            
            # Kürzel aus Mapping holen
            home_code = TEAM_MAP.get(home_team_long, home_team_long[:3].upper())
            away_code = TEAM_MAP.get(away_team_long, away_team_long[:3].upper())
            
            if match_home:
                team_code = home_code
                vs_text = f"vs. {away_code}"
            else:
                team_code = away_code
                vs_text = f"@ {home_code}"

            # Uhrzeit aus dem direkten Feld 'game_datetime' auslesen
            time_str = "??:??"
            game_datetime_str = game.get("game_datetime") # Liefert "YYYY-MM-DDTHH:MM:SSZ"
            
            if game_datetime_str:
                try:
                    clean_date = game_datetime_str.replace("Z", "").split(".")[0]
                    dt_utc = datetime.strptime(clean_date, "%Y-%m-%dT%H:%M:%S")
                    
                    # Umrechnung UTC -> deutsche Sommerzeit (+2 Std im Juli)
                    dt_local = dt_utc + timedelta(hours=2)
                    time_str = dt_local.strftime("%H:%M")
                except Exception as time_err:
                    print(f"Fehler beim Parsen von game_datetime ({game_datetime_str}): {time_err}")
            
            # Doppelter Boden: Falls es immer noch ??:?? ist, schauen wir, ob wir eine Text-Uhrzeit finden
            if time_str == "??:??":
                # statsapi liefert manchmal lokale Uhrzeiten im Freitext (z.B. "7:10 PM")
                local_time_str = game.get("game_time")
                if local_time_str and local_time_str != "12:00 AM":
                    time_str = local_time_str
                else:
                    # Dritter Fallback: Spielstatus anzeigen (z.B. "Final", "Live", "Postponed")
                    status = game.get("status", "")
                    if status:
                        time_str = status

            # Zeile bauen
            line = f"{pitcher_name} ({team_code}) | {time_str} {vs_text}"
            starter_lines.append(line)

    # ==========================================
    # 4. GESAMMELTEN WEBHOOK SENDEN
    # ==========================================
    if starter_lines:
        full_content = "\n".join(starter_lines)
        print(f"Sende folgende Pitcher an HA:\n{full_content}")

        if HA_WEBHOOK_URL:
            payload = {
                "title": "⚾ Today's Starters on real⚾",
                "content": full_content
            }
            response = requests.post(HA_WEBHOOK_URL, json=payload, timeout=10)
            print(f"HA-Antwort Status: {response.status_code}")
        else:
            print("Hinweis: HA_WEBHOOK_URL ist nicht konfiguriert.")
    else:
        print("Heute startet keiner der gesuchten Pitcher.")

except Exception as e:
    print(f"Allgemeiner Fehler im Skript: {e}")

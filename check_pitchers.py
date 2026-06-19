import os
from datetime import datetime
import requests

# Konfiguration
PITCHERS_FILE = "pitchers.txt"
WEBHOOK_URL = os.getenv("HA_WEBHOOK_URL")

# 1. Gewünschte Pitcher laden
if not os.path.exists(PITCHERS_FILE):
    print("Keine pitchers.txt gefunden.")
    exit(0)

with open(PITCHERS_FILE, "r", encoding="utf-8") as f:
    tracked_pitchers = {line.strip() for line in f if line.strip()}

# 2. Heutigen MLB-Spielplan abrufen (gibt die Probable Pitcher zurück)
today_str = datetime.today().strftime("%Y-%m-%d")
mlb_url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={today_str}&hydrate=probablePitcher"

try:
    response = requests.get(mlb_url)
    response.raise_for_status()
    data = response.json()
except Exception as e:
    print(f"Fehler beim Laden der MLB-API: {e}")
    exit(1)

# 3. Spiele durchsuchen
matching_games = []
dates = data.get("dates", [])
for date in dates:
    for game in date.get("games", []):
        # Teams bestimmen
        teams = game.get("teams", {})
        away_team = teams.get("away", {}).get("team", {}).get("name", "Unknown")
        home_team = teams.get("home", {}).get("team", {}).get("name", "Unknown")
        
        # Pitcher bestimmen
        away_pitcher = teams.get("away", {}).get("probablePitcher", {}).get("fullName")
        home_pitcher = teams.get("home", {}).get("probablePitcher", {}).get("fullName")
        
        if away_pitcher in tracked_pitchers:
            matching_games.append(f"{away_pitcher} startet heute für die {away_team} (@ {home_team})!")
        if home_pitcher in tracked_pitchers:
            matching_games.append(f"{home_pitcher} startet heute für die {home_team} (vs. {away_team})!")

# 4. Webhook senden, falls Treffer vorhanden sind
if matching_games and WEBHOOK_URL:
    message_text = "\n".join(matching_games)
    payload = {"message": message_text}
    
    try:
        req = requests.post(WEBHOOK_URL, json=payload)
        print(f"Webhook gesendet. Status: {req.status_code}")
    except Exception as e:
        print(f"Fehler beim Senden des Webhooks: {e}")
else:
    print("Heute starten keine deiner beobachteten Pitcher.")

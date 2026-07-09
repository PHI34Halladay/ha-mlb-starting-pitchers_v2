import os
import requests
import statsapi
from datetime import datetime

# ==========================================
# 1. DYNAMISCHES LADEN DER PITCHER-LISTE
# ==========================================

# Pfad zur pitchers.txt ermitteln (relativ zum Skriptverzeichnis)
script_dir = os.path.dirname(os.path.abspath(__file__))
txt_path = os.path.join(script_dir, "pitchers.txt")

TARGET_PITCHERS = []
if os.path.exists(txt_path):
    with open(txt_path, "r", encoding="utf-8") as f:
        # Liest jede Zeile, entfernt Zeilenumbrüche/Leerzeichen und ignoriert leere Zeilen
        TARGET_PITCHERS = [line.strip() for line in f if line.strip()]
    print(f"Erfolgreich {len(TARGET_PITCHERS)} Pitcher aus pitchers.txt geladen.")
else:
    print(f"FEHLER: {txt_path} wurde nicht gefunden! Bitte erstelle die Datei.")
    exit(1)

# ==========================================
# 2. KONFIGURATION & WEBHOOKS
# ==========================================

# Home Assistant Webhook URL aus den GitHub Secrets (Umgebungsvariablen) laden
HA_WEBHOOK_URL = os.environ.get("HA_WEBHOOK_URL")

if not HA_WEBHOOK_URL:
    print("Warnung: HA_WEBHOOK_URL ist nicht gesetzt. Benachrichtigungen werden nur in der Konsole ausgegeben.")

# Das heutige Datum im korrekten Format für die MLB-API holen
today = datetime.today().strftime('%Y-%m-%d')
print(f"Suche nach Spielen für den {today}...")

# ==========================================
# 3. API-ABFRAGE & VERARBEITUNG
# ==========================================

try:
    # Alle Spiele für den heutigen Tag von der MLB-API abrufen
    games = statsapi.schedule(date=today)
    
    found_any = False

    for game in games:
        # Probieren, die voraussichtlichen Starting Pitcher zu ermitteln
        home_pitcher = game.get("home_probable_pitcher", "").strip()
        away_pitcher = game.get("away_probable_pitcher", "").strip()
        
        # Abgleich mit unserer geladenen Liste
        match_home = home_pitcher in TARGET_PITCHERS if home_pitcher else False
        match_away = away_pitcher in TARGET_PITCHERS if away_pitcher else False

        if match_home or match_away:
            found_any = True
            
            # Details für die Benachrichtigung zusammenbauen
            pitcher_name = home_pitcher if match_home else away_pitcher
            team_name = game.get("home_name") if match_home else game.get("away_name")
            opponent = game.get("away_name") if match_home else game.get("home_name")
            game_time = game.get("game_date") # Enthält meistens die Uhrzeit
            
            message = f"⚾ {pitcher_name} startet heute für die {team_name} gegen die {opponent}! Spielzeit: {game_time}"
            print(f"Treffer gefunden: {message}")
            
            # Webhook an Home Assistant senden, falls URL vorhanden ist
            if HA_WEBHOOK_URL:
                payload = {
                    "pitcher": pitcher_name,
                    "team": team_name,
                    "opponent": opponent,
                    "time": game_time,
                    "message": message
                }
                try:
                    response = requests.post(HA_WEBHOOK_URL, json=payload, timeout=10)
                    if response.status_code == 200:
                        print(f"Erfolgreich an Home Assistant gesendet für {pitcher_name}.")
                    else:
                        print(f"Fehler beim Senden an HA. Status-Code: {response.status_code}")
                except Exception as e:
                    print(f"Fehler bei der Verbindung zu Home Assistant: {e}")

    if not found_any:
        print("Heute startet keiner der gesuchten Pitcher.")

except Exception as e:
    print(f"Ein Fehler bei der API-Abfrage ist aufgetreten: {e}")

import os
import requests
import statsapi
from datetime import datetime

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
            # Relevante Daten extrahieren
            pitcher_name = home_pitcher if match_home else away_pitcher
            
            # Team-Kürzel und Gegner ermitteln
            if match_home:
                team_code = game.get("home_name")[:3].upper() # Fallback-Kürzel
                opponent = game.get("away_name")
                # Versuche das echte Kürzel zu nehmen, falls vorhanden
                message_team = f"{team_code}" 
                vs_text = f"vs. {opponent}"
            else:
                team_code = game.get("away_name")[:3].upper()
                opponent = game.get("home_name")
                vs_text = f"@ {opponent}"

            # Uhrzeit formatieren (Extrahiert HH:MM aus dem ISO-String)
            # MLB-Times sind oft in UTC/ET, statsapi liefert meist lokale oder bereits formatierte Strings
            game_date_str = game.get("game_date", "")
            try:
                # Versuche die Uhrzeit sauber zu parsen (Beispiel: 2026-07-09T19:10:00Z)
                dt = datetime.strptime(game_date_str, "%Y-%m-%dT%H:%M:%SZ")
                # Hier kannst du bei Bedarf eine Zeitverschiebung einrechnen, falls die API UTC liefert:
                # dt = dt + timedelta(hours=2) # Für deutsche Sommerzeit
                time_str = dt.strftime("%H:%M")
            except:
                # Fallback, falls das Format abweicht
                time_str = game_date_str[-8:-3] if len(game_date_str) > 10 else "??:??"

            # Zeile nach deinem Wunschformat bauen: Jesús Luzardo (PHI) | 01:10 @ Reds
            line = f"{pitcher_name} ({team_code}) | {time_str} {vs_text}"
            starter_lines.append(line)

    # ==========================================
    # 4. GESAMMELTEN WEBHOOK SENDEN
    # ==========================================
    if starter_lines:
        # Erstellt die Liste untereinander für die Push-Nachricht
        full_content = "\n".join(starter_lines)
        print(f"Sende folgende Pitcher an HA:\n{full_content}")

        if HA_WEBHOOK_URL:
            payload = {
                "title": "⚾ Today's Starters on real⚾",
                "content": full_content
            }
            response = requests.post(HA_WEBHOOK_URL, json=payload, timeout=10)
            print(f"HA-Antwort: {response.status_code}")
    else:
        print("Heute starten keine deiner gesuchten Pitcher.")

except Exception as e:
    print(f"Fehler: {e}")

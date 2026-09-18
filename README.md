# Siedle SG150 Local for Home Assistant

Lokale Home-Assistant-Custom-Integration für **Siedle Smart Gateway SG150-0**.

## Aktueller Funktionsumfang

- erkennt den lokalen Türruf über den beim Klingeln geöffneten MJPEG-Port 20502
- stellt eine Home-Assistant-Kamera für das lokale Haustür-Livebild bereit
- funktioniert für den Video-Hauptpfad ohne Siedle-Cloud und ohne Internet
- kann optional ein über die offizielle Home-Assistant-Integration eingebundenes Fully-Kiosk-Tablet lokal steuern:
  - Display einschalten
  - Fully Kiosk in den Vordergrund holen
  - Türansicht laden
  - optional zur normalen HA-Seite zurückkehren
- stellt Türrufstatus, Kamera, Tabletstatus, Automatikschalter und Bedienbuttons als HA-Entitäten bereit

## Installation über HACS

Dieses Repository ist als HACS Custom Repository vom Typ **Integration** aufgebaut.

Nach dem Hinzufügen in HACS wird die Integration nach

`/config/custom_components/sg150_local`

installiert.

Danach Home Assistant neu starten und unter **Einstellungen → Geräte & Dienste → Integration hinzufügen → Siedle SG150 Local** einrichten.

Standardwerte:

- SG150: `192.168.178.97`
- MJPEG-Port: `20502`
- Polling: `100 ms`

## Tablet

Für den zuverlässigen Wandtablet-Betrieb wird Fully Kiosk Browser mit der offiziellen Home-Assistant-Fully-Kiosk-Integration verwendet. Die Steuerung erfolgt direkt im LAN, nicht per Cloud-Push.

## Status

Aktuelle Version: **0.3.2**

Noch offen:
- lokales Gegensprechen
- lokaler Türöffner

Der Türöffner wird später ausschließlich als explizite Benutzeraktion umgesetzt; keine automatische Türöffnung.

## Hinweis

Dies ist eine unabhängige Community-/Privatintegration und kein offizielles Produkt der S. Siedle & Söhne Telefon- und Telegrafenwerke OHG.

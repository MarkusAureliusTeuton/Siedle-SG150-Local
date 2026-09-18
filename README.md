# Siedle SG150 Local for Home Assistant

Lokale Home-Assistant-Custom-Integration für **Siedle Smart Gateway SG150-0**.

## Aktueller Funktionsumfang

- überwacht die lokale SG150-Videosession über den transient geöffneten MJPEG-Port `20502`
- stellt den lokalen Türruf-/Videosession-Status als Home-Assistant-Entität bereit
- kann pro Türruf automatisch ein Besucherbild aus dem lokalen MJPEG-Stream archivieren
- speichert die JPEGs nach Jahr/Monat/Tag auf der HA-Festplatte und führt parallel eine SQLite-Zeithistorie
- stellt das zuletzt archivierte Besucherbild als eigene Kamera-Entität bereit
- stellt eine Home-Assistant-Kamera für den lokalen SG150-MJPEG-Stream bereit
- steuert optional ein über die offizielle Home-Assistant-Fully-Kiosk-Integration eingebundenes Android-Wandtablet
- kann beim bestehenden lokalen Türruftrigger automatisch:
  - das Tablet-Display einschalten
  - die offizielle Siedle-App in den Vordergrund holen
  - nach Ende der Videosession wieder zu Fully/Home Assistant zurückkehren
- alternativ kann weiterhin die bisherige HA-Türansicht geladen werden
- stellt Türrufstatus, Kamera, Tabletstatus, Automatikschalter und Bedienbuttons als HA-Entitäten bereit

## Wichtiger Hinweis zum Türruftrigger

Die SG150-Videosession auf Port `20502` entsteht in der hier verwendeten Anlage **nicht allein durch den physischen Klingeltaster**.

Im realen A/B-Test wurde bestätigt:

- Siedle-App im Hintergrund aktiv → Türruf wird zugestellt → SG150 startet die Ruf-/Videosession → `20502/20503` öffnen → diese Integration erkennt den Türruf.
- Siedle-App deaktiviert → keine Ruf-/Videosession → `20502/20503` bleiben geschlossen → kein Trigger.

Die Integration erzeugt keinen zweiten Trigger. Sie verwendet weiterhin ausschließlich den vorhandenen lokalen SG150-Porttrigger. Die Siedle-App dient im Hintergrund als Teilnehmer, der die SG150-Session entstehen lässt.

## Empfohlener Tablet-Ablauf ab v0.5.2

Normalzustand:

`Fully Kiosk → Home-Assistant-Dashboard`

Beim Klingeln:

`Siedle-App erhält den Ruf im Hintergrund → SG150 öffnet Videosession → SG150 Local erkennt Port 20502 → Display EIN → Siedle-App in den Vordergrund`

Nach Ende der Videosession:

`Port 20502 schließt → kurze Rückkehrverzögerung → Fully Kiosk / HA-Startseite wieder im Vordergrund`

Android-Paket der Siedle-App:

`de.siedle.sus`

## Android-Voraussetzung

Damit der Ablauf zuverlässig funktioniert, muss die offizielle Siedle-App auf dem Wandtablet installiert, angemeldet und im Hintergrund empfangsbereit bleiben.

Am Tablet daher einmalig prüfen:

- Benachrichtigungen für die Siedle-App erlaubt
- Hintergrundaktivität/Hintergrunddaten erlaubt
- Akkuoptimierung für die Siedle-App deaktiviert bzw. auf uneingeschränkt gestellt
- keine systemseitige Schlaf-/Standby-Optimierung, die die Siedle-App beendet
- Siedle-App nicht per „Beenden erzwingen“ stoppen
- Fully Kiosk darf externe Apps starten
- **Android-System-Bildschirmsperre auf Keine stellen**, wenn die Siedle-App automatisch über dem ausgeschalteten Display geöffnet werden soll
- den Zugriffsschutz stattdessen über **Fully Kiosk Mode + Fully PIN** herstellen
- Fully **Unlock Screen** kann Fully selbst über dem Lockscreen anzeigen, aber **nicht die Siedle-App**

Diese Android-Systemeinstellungen kann die Home-Assistant-Integration nicht selbst verändern.

## Installation über HACS

Dieses Repository ist als HACS Custom Repository vom Typ **Integration** aufgebaut.

Nach dem Hinzufügen in HACS wird die Integration nach

`/config/custom_components/sg150_local`

installiert.

Danach Home Assistant neu starten und unter:

**Einstellungen → Geräte & Dienste → Integration hinzufügen → Siedle SG150 Local**

einrichten.

Standardwerte:

- SG150: `192.168.178.97`
- MJPEG-Port: `20502`
- Polling: `200 ms`

## Tablet konfigurieren

Unter:

**Einstellungen → Geräte & Dienste → Siedle SG150 Local → Konfigurieren**

einstellen:

- Fully-Kiosk-Tablet
- Fully-Kiosk Screen-Schalter
- **Bei Türruf automatisch reagieren**: EIN
- **Bei Türruf Siedle-App in den Vordergrund holen**: EIN
- Android-Paket: `de.siedle.sus`
- Wartezeit nach Display EIN: Standard `300 ms`
- Siedle-App Starts: Standard `2`
- Abstand: Standard `500 ms`
- **Nach Ende der Videosession automatisch zu Fully/HA zurück**: EIN
- Rückkehrverzögerung: Standard `2 s`
- HA-Startseite: `/`

Die vorhandene „Türansicht anzeigen“-Taste verwendet automatisch den gewählten Modus. Ist die Siedle-App-Anzeige aktiv, dient die Taste gleichzeitig als manueller Funktionstest.

## Besucherbild-Historie

Ab v0.6.0 kann die Integration bei jeder erkannten SG150-Videosession automatisch **ein JPEG** speichern.

Standardmäßig erfolgt die Aufnahme **5 Sekunden nach Beginn der Videosession**. Das entspricht der Siedle-Standardeinstellung für den automatischen Bildspeicher. Der archivierte Frame wird aber von dieser Integration direkt aus dem lokalen MJPEG-Stream auf Port `20502` gelesen. Er ist daher zeitlich vergleichbar, aber nicht garantiert byte-/frame-identisch mit dem intern vom SG150 gespeicherten Bild.

Standard-Speicherort:

`/config/sg150_history`

Struktur:

`/config/sg150_history/YYYY/MM/DD/YYYY-MM-DD_HH-MM-SS_mmm.jpg`

Zusätzlich:

`/config/sg150_history/history.sqlite3`

Die SQLite-Datenbank enthält pro Bild:

- UTC-Zeitstempel
- lokale Zeit
- Dateipfad
- Dateigröße
- SHA-256
- Quelle (`automatic` oder `manual`)

Optionen:

- Historie EIN/AUS
- Aufnahmeverzögerung
- Aufbewahrung in Tagen
- maximale Bildanzahl
- Speicherordner relativ zu `/config`

Standard:

- Historie: EIN
- Aufnahmeverzögerung: 5 s
- Aufbewahrung: 30 Tage
- maximal: 1000 Bilder
- Ordner: `sg150_history`

Neue Entitäten:

- Kamera **Letztes Besucherbild**
- Sensor **Besucherbild-Historie**
- Button **Besucherbild jetzt speichern** (nur während aktiver Videosession)

Die automatische Löschung entfernt sowohl den SQLite-Eintrag als auch die zugehörige JPEG-Datei.

## Diagnose

Der Sensor **Tabletsteuerung** zeigt unter anderem:

- ob die Automatik aktiv ist
- ob das Tablet konfiguriert ist
- ob der SG150-Port gerade offen ist
- aktuelles Anzeigeziel (`siedle_app` oder `ha_door_view`)
- verwendetes Siedle-App-Paket
- Trigger-Zähler
- automatische Starts
- Quelle und Zeitpunkt des letzten Triggers
- letzte Aktion
- letzten Fehler

## Status

Aktuelle Version: **0.6.0**

### v0.6.0

- automatische Besucherbild-Historie aus dem lokalen SG150-MJPEG-Stream
- standardmäßig ein Bild 5 Sekunden nach Türruf/Videosession
- JPEG-Dateien nach Datum strukturiert auf der HA-Festplatte
- SQLite-Datenbank mit Zeitstempel und Metadaten
- konfigurierbare Aufbewahrung, Maximalanzahl und Speicherordner
- eigene Kamera-Entität **Letztes Besucherbild**
- Sensor **Besucherbild-Historie**
- manueller Button **Besucherbild jetzt speichern**
- gemeinsame MJPEG-Frame-Leselogik für Livekamera und Historie

### v0.5.2

- Android-Keyguard-Limit korrekt berücksichtigt: Fully kann sich selbst über dem Sperrbildschirm zeigen, aber den Sperrbildschirm nicht für die Siedle-App aufheben.
- Der kurze Fully-Zwischenschritt aus v0.5.1 wurde wieder entfernt.
- Empfohlener Wandtablet-Betrieb: Android-System-Sperre `Keine`, Schutz stattdessen über Fully Kiosk Mode/PIN.
- Wenn lediglich ein Swipe-Lockscreen verwendet wird, kann Fully experimentell **Unlock Swipe Screen Lock** testen; dieser Vorgang kann laut Fully mehrere Sekunden dauern.

### v0.5.1

- Bildschirm-Aktivierung robuster gemacht: Nach `screen_on` wird zuerst Fully in den Vordergrund geholt und erst danach die Siedle-App gestartet.
- Dadurch kann Fully seine konfigurierte **Unlock Screen**-Funktion anwenden, bevor Android die Siedle-App anzeigt.
- Dokumentation um Android-/Fully-Sperrbildschirmhinweise ergänzt.

### v0.5.0

- Siedle-App kann direkt durch den bestehenden SG150-Türruftrigger in den Vordergrund geholt werden
- kein zusätzlicher Android-/Notification-Trigger notwendig
- automatisches Zurückkehren zu Fully/HA nach Ende der SG150-Videosession
- Paketname, Startwiederholungen und Zeitabstände konfigurierbar
- bisherige HA-Türansicht bleibt als Alternative erhalten
- Diagnoseattribute erweitert
- README und Optionsbeschreibungen auf den tatsächlich bestätigten App-vermittelten Sessionablauf korrigiert

Noch offen:

- vollständig lokaler Türruf ohne Siedle-App/Push
- lokales Gegensprechen ohne Siedle-App
- lokaler Türöffner ohne Siedle-App

Der Türöffner wird in dieser Integration nur als explizite Benutzeraktion umgesetzt; keine automatische Türöffnung.

## Hinweis

Dies ist eine unabhängige Community-/Privatintegration und kein offizielles Produkt der S. Siedle & Söhne Telefon- und Telegrafenwerke OHG.

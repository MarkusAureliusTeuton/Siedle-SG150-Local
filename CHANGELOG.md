# Changelog

## 0.5.1

- Beim Türruf wird nach dem Einschalten des Displays zuerst Fully Kiosk in den Vordergrund geholt.
- Erst danach wird die Siedle-App gestartet.
- Das reduziert Fälle, in denen Androids Sperrbildschirm vor der Rufansicht stehen bleibt.
- Für zuverlässigen Betrieb **Fully → Device Management → Unlock Screen** aktivieren.
- Ein sicherer Android-PIN-/Muster-Sperrbildschirm kann von HA/Fully nicht zuverlässig umgangen werden; auf einem dedizierten Wandtablet sollte Android daher ohne System-Sperre laufen und Fully selbst den Kioskzugriff absichern.


## 0.5.0

- Neuer empfohlener Tablet-Modus: Die Integration holt beim **bereits vorhandenen lokalen SG150-Türruftrigger** die offizielle Siedle-App in den Vordergrund.
- Kein zusätzlicher Trigger über Android-Benachrichtigungen, MacroDroid, Tasker o. Ä. notwendig.
- Display wird über Fully Kiosk eingeschaltet, anschließend wird `de.siedle.sus` gestartet.
- Anzahl und Abstand der App-Starts sind konfigurierbar.
- Nach Ende der SG150-Videosession kann automatisch zu Fully/Home Assistant zurückgekehrt werden.
- Die bisherige HA-Türansicht bleibt als alternatives Anzeigeziel erhalten.
- Tablet-Diagnose um Anzeigeziel, Paketname und Rückkehrstatus erweitert.
- Dokumentation korrigiert: In der getesteten Anlage wird Port `20502` nicht allein durch den physischen Klingeltaster geöffnet, sondern durch die von der aktiven Siedle-App vermittelte Ruf-/Videosession.
- Sichtbare Versionsangaben und Optionsbeschreibungen auf `0.5.0` aktualisiert.

## 0.4.1

- Portmonitor gegen hängendes `writer.wait_closed()` abgesichert.
- Unerwartete Probe-Fehler beenden den Hintergrundmonitor nicht mehr.
- Diagnostik um `monitor_running`, `probe_count`, Zeitstempel und Triggerinformationen erweitert.

## 0.4.0

- Hintergrundstart/Bootstrap des Portmonitors korrigiert.

## 0.3.6

- Native MJPEG-Kamera integriert.
- Abhängigkeit vom Home-Assistant-Stream-Worker für den Hauptpfad entfernt.

## 0.3.x

- Fully-Kiosk-Tabletsteuerung, Eventtrigger, Polling und Konfigurationsmigration ergänzt.

## 0.1.x–0.2.x

- Erste lokale Porterkennung, Kamera und Fully-Kiosk-Beispiele.

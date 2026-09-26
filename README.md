# HC Metter-Enz Kalender 2026/27

Eigenständige Spielpläne mit automatischer Aktualisierung aus Handball4all.

## Kalender abonnieren

### Männer 1
https://raw.githubusercontent.com/kevindehabe/HCME-26-27/main/hcme.ics

### Frauen 1
https://raw.githubusercontent.com/kevindehabe/HCME-26-27/main/frauen1.ics

Auf dem iPhone: Kalender → Kalender → Kalender hinzufügen → Kalenderabonnement hinzufügen. Die gewünschte HTTPS-Adresse einfügen.

## Automatische Aktualisierung

GitHub Actions fragt Handball4all alle fünf Minuten ab. Beide Kalender werden unabhängig voneinander erzeugt. Sobald Handball4all für ein Spiel eine SBO-/Liveticker-ID veröffentlicht, wird der Liveticker automatisch in den Termin übernommen.

Ein manueller Start ist über Actions möglich. Änderungen an update.py oder am Workflow starten ebenfalls eine Aktualisierung. Geplante Läufe können von GitHub verzögert oder nach längerer Inaktivität deaktiviert werden.

Die Spiel-UIDs bleiben stabil. Jeder Termin belegt zwei Stunden ab Anwurf.

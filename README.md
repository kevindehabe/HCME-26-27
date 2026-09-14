# HC Metter-Enz Kalender 2026/27

Eigenständiger Spielplan mit automatischer Aktualisierung aus Handball4all.

## Kalender abonnieren

https://raw.githubusercontent.com/kevindehabe/HCME-26-27/main/hcme.ics

Auf dem iPhone: Kalender → Kalender → Kalender hinzufügen → Kalenderabonnement hinzufügen. Die HTTPS-Adresse einfügen. Ein bisheriges SüffIQ-Kalenderabo durch dieses ersetzen.

## Automatische Aktualisierung

GitHub Actions fragt Handball4all alle zwei Stunden zur Minute 17 ab. Ein manueller Start ist über Actions möglich. Änderungen an update.py oder am Workflow starten ebenfalls eine Aktualisierung. Geplante Läufe können von GitHub verzögert oder nach längerer Inaktivität deaktiviert werden.

Die Spiel-UIDs bleiben beim Umzug erhalten. Jeder Termin belegt zwei Stunden ab Anwurf.

# HC Metter-Enz Kalender 2026/27

Eigenständige Spielpläne mit automatischer Aktualisierung aus Handball4all.

## Kalender abonnieren

### Männer 1
https://raw.githubusercontent.com/kevindehabe/HCME-26-27/main/hcme.ics

### Frauen 1
https://raw.githubusercontent.com/kevindehabe/HCME-26-27/main/frauen1.ics

Auf dem iPhone: Kalender → Kalender → Kalender hinzufügen → Kalenderabonnement hinzufügen. Die gewünschte HTTPS-Adresse einfügen.

## Automatische Aktualisierung

GitHub Actions fragt Handball4all alle zwei Stunden ab. Beide Kalender werden unabhängig voneinander erzeugt. Sobald Handball4all für ein Spiel eine SBO-/Liveticker-ID veröffentlicht, wird der Liveticker automatisch in den Termin übernommen. IDs aus bereits veröffentlichten Kalendereinträgen bleiben erhalten, falls eine API-Antwort sie vorübergehend nicht enthält.

Zusätzlich kann der Render-Cronjob aus `render.yaml` das GitHub-Update alle fünf Minuten im Fenster von zwei Stunden vor bis vier Stunden nach einem Männer- oder Frauen-Spiel auslösen. Ohne Spiel startet er einmal täglich um 08:00 UTC. Dafür in Render beim Erstellen des Blueprints `GITHUB_ACTIONS_TOKEN` als geheime Umgebungsvariable setzen: ein auf dieses Repo begrenzter Fine-Grained-GitHub-Token mit **Actions: Read and write**. Der Cronjob kostet mindestens 1 USD pro Monat plus gegebenenfalls weitere Laufzeitkosten. Der GitHub-Zeitplan bleibt als Rückfallebene aktiv und ist nicht minutengenau.

Ein manueller Start ist über Actions möglich. Änderungen an update.py oder am Workflow starten ebenfalls eine Aktualisierung. Geplante Läufe können von GitHub verzögert oder nach längerer Inaktivität deaktiviert werden.

Die Spiel-UIDs bleiben stabil. Jeder Termin belegt zwei Stunden ab Anwurf. Kalender-Apps aktualisieren Abos in ihrem eigenen Intervall; das kann die Anzeige eines neuen Links zusätzlich verzögern.

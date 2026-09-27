# HC Metter-Enz Kalender 2026/27

Eigenständige Spielpläne mit automatischer Aktualisierung aus Handball4all.

## Kalender abonnieren

### Männer 1
https://raw.githubusercontent.com/kevindehabe/HCME-26-27/main/hcme.ics

### Frauen 1
https://raw.githubusercontent.com/kevindehabe/HCME-26-27/main/frauen1.ics

Auf dem iPhone: Kalender → Kalender → Kalender hinzufügen → Kalenderabonnement hinzufügen. Die gewünschte HTTPS-Adresse einfügen.

## Automatische Aktualisierung

GitHub Actions ist für Aktualisierungen alle fünf Minuten eingerichtet (jeweils ab Minute 2). Beide Kalender werden unabhängig voneinander erzeugt. Sobald Handball4all für ein Spiel eine SBO-ID veröffentlicht, wird der PDF-Spielbericht in den Notizen verlinkt und zusätzlich als iCalendar-Anhang (`ATTACH;FMTTYPE=application/pdf`) angegeben. In der iPhone-Kalender-App erscheint dieser Anhang bei abonnierten Terminen offenbar nicht als Datei; der Link unter „Details“ lässt sich öffnen. Im URL-Feld steht bewusst kein Spielbericht, damit die Kalender-App ihn nicht unter „Ort“ anzeigt. Der Bericht bleibt nach dem Spiel erreichbar; IDs aus bereits veröffentlichten Kalendereinträgen bleiben erhalten, falls eine API-Antwort sie vorübergehend nicht enthält. Der PDF-Link ist kein Liveticker. Ein verlässlicher Link zum Liveticker für diese Spiele liegt derzeit nicht vor.

Für einen zusätzlichen, kostenlosen Fünf-Minuten-Auslöser lässt sich auf https://cron-job.org ein HTTP-Job einrichten. Er startet denselben GitHub-Workflow; das bestehende Kalenderabo bleibt gleich. Einstellungen:

- URL: `https://api.github.com/repos/kevindehabe/HCME-26-27/actions/workflows/update-hcme-calendar.yml/dispatches`
- Methode: `POST`; Zeitplan: alle 5 Minuten
- Request-Body (JSON): `{"ref":"main"}`
- Header: `Accept: application/vnd.github+json`, `Content-Type: application/json`, `Authorization: Bearer <TOKEN>`

Der Token wird in GitHub als Fine-Grained-PAT nur für `kevindehabe/HCME-26-27` mit `Actions: Read and write` angelegt und in cron-job.org eingetragen. Keinen Token ins Repository oder in einen Chat kopieren. GitHub Actions bleibt als Rückfallebene aktiv; kein externer Zeitplan kann die Aktualisierung in der Kalender-App erzwingen.

Ein manueller Start ist über Actions möglich. Änderungen an update.py oder am Workflow starten ebenfalls eine Aktualisierung. Geplante Läufe können von GitHub verzögert oder nach längerer Inaktivität deaktiviert werden.

Die Spiel-UIDs bleiben stabil. Jeder Termin belegt zwei Stunden ab Anwurf. Kalender-Apps aktualisieren Abos in ihrem eigenen Intervall; das kann die Anzeige eines neuen Links zusätzlich verzögern.

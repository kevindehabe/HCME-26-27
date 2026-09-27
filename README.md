# HC Metter-Enz Kalender 2026/27

Eigenständige Spielpläne mit automatischer Aktualisierung aus Handball4all.

## Kalender abonnieren

### Männer 1
https://raw.githubusercontent.com/kevindehabe/HCME-26-27/main/hcme.ics

### Frauen 1
https://raw.githubusercontent.com/kevindehabe/HCME-26-27/main/frauen1.ics

Auf dem iPhone: Kalender → Kalender → Kalender hinzufügen → Kalenderabonnement hinzufügen. Die gewünschte HTTPS-Adresse einfügen.

## Automatische Aktualisierung

GitHub Actions ist für Aktualisierungen alle fünf Minuten eingerichtet (jeweils ab Minute 2). Beide Kalender werden unabhängig voneinander erzeugt. Sobald Handball4all einen PDF-Spielbericht zu einem abgeschlossenen Spiel bereitstellt, wird die Datei heruntergeladen, im Repository gespeichert und als Binäranhang im Termin eingebettet (`ATTACH;VALUE=BINARY;ENCODING=BASE64`). Der Link in den Notizen bleibt vorerst als Rückweg erhalten, falls eine Kalender-App eingebettete Anhänge nicht anzeigt. Bei abonnierten iPhone-Kalendern muss die Anzeige des echten Anhangs am Gerät geprüft werden. Im URL-Feld steht bewusst kein Spielbericht, damit die Kalender-App ihn nicht unter „Ort“ anzeigt. Der Bericht bleibt nach dem Spiel erreichbar; IDs aus bereits veröffentlichten Kalendereinträgen bleiben erhalten, falls eine API-Antwort sie vorübergehend nicht enthält. Der PDF-Link ist kein Liveticker. Ein verlässlicher Link zum Liveticker für diese Spiele liegt derzeit nicht vor.

Für einen zusätzlichen, kostenlosen Fünf-Minuten-Auslöser lässt sich auf https://cron-job.org ein HTTP-Job einrichten. Er startet denselben GitHub-Workflow; das bestehende Kalenderabo bleibt gleich. Einstellungen:

- URL: `https://api.github.com/repos/kevindehabe/HCME-26-27/actions/workflows/update-hcme-calendar.yml/dispatches`
- Methode: `POST`; Zeitplan: alle 5 Minuten
- Request-Body (JSON): `{"ref":"main"}`
- Header: `Accept: application/vnd.github+json`, `Content-Type: application/json`, `Authorization: Bearer <TOKEN>`

Der Token wird in GitHub als Fine-Grained-PAT nur für `kevindehabe/HCME-26-27` mit `Actions: Read and write` angelegt und in cron-job.org eingetragen. Keinen Token ins Repository oder in einen Chat kopieren. GitHub Actions bleibt als Rückfallebene aktiv; kein externer Zeitplan kann die Aktualisierung in der Kalender-App erzwingen.

Ein manueller Start ist über Actions möglich. Änderungen an update.py oder am Workflow starten ebenfalls eine Aktualisierung. Geplante Läufe können von GitHub verzögert oder nach längerer Inaktivität deaktiviert werden.

Die Spiel-UIDs bleiben stabil. Jeder Termin belegt zwei Stunden ab Anwurf. Kalender-Apps aktualisieren Abos in ihrem eigenen Intervall; das kann die Anzeige eines neuen Links zusätzlich verzögern.

## Echten iCloud-Dateianhang testen

Der manuelle Workflow `iCloud PDF-Test` prüft eine direkte CalDAV-Verbindung. Der iCloud-Server meldet die Funktion `calendar-managed-attachments`; ob die PDF im persönlichen Kalender auf dem iPhone erscheint, wird mit genau einem Testtermin geprüft. Eine regelmäßige iCloud-Übertragung ist noch nicht aktiviert.

1. In der iPhone-Kalender-App unter dem Account **iCloud** einen normalen Kalender mit dem exakten Namen **HCME PDF Test** erstellen.
2. Auf https://account.apple.com unter **Anmelden und Sicherheit → App-spezifische Passwörter** ein Passwort namens **HCME Kalender** erzeugen. Apple setzt dafür Zwei-Faktor-Authentifizierung voraus.
3. In https://github.com/kevindehabe/HCME-26-27/settings/secrets/actions zwei Repository-Secrets speichern:
   - `ICLOUD_USERNAME`: die E-Mail-Adresse des Apple Accounts.
   - `ICLOUD_APP_PASSWORD`: das gerade erzeugte App-spezifische Passwort.
4. Unter **Actions → iCloud PDF-Test → Run workflow** zuerst den Modus `check` starten. Dabei werden nur Anmeldung, Kalendername und Anhang-Unterstützung geprüft; keine Termine verändert.
5. Bei erfolgreicher Prüfung denselben Workflow mit `upload-test` starten. Er legt im Testkalender den Termin **HCME PDF-Test: TSV Korntal – HC Metter-Enz** am **27.09.2026 um 17:30 Uhr** an und lädt die PDF als serverseitigen Anhang hoch. Dieser Testtermin enthält keinen Bericht-Link. Wiederholte Läufe erzeugen keinen zweiten Termin oder zweiten Anhang.
6. Den Testtermin auf dem iPhone prüfen. Erst wenn die PDF dort sichtbar ist, sollte die wiederkehrende Übertragung für alle Spiele eingerichtet werden.

Die Zugangsdaten gehören ausschließlich in die GitHub-Secrets. Der Test protokolliert weder Kennwörter noch persönliche Kalendernamen oder Kalenderinhalte. Das App-spezifische Passwort ist nicht auf einen einzelnen Kalender beschränkt; das Skript verwendet ausschließlich den genannten Testkalender. Es erstellt keine Einladungen. Der Zugriff lässt sich bei Apple durch Widerruf des App-spezifischen Passworts wieder beenden.

Lokaler Test der Implementierung ohne iCloud-Zugang: `python -m unittest test_icloud_pdf_test.py`.

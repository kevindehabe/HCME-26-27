#!/usr/bin/env python3
"""Manually check iCloud CalDAV, then optionally upload one PDF test event."""

import argparse
import base64
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

DAV = 'DAV:'
CAL = 'urn:ietf:params:xml:ns:caldav'
ROOT = Path(__file__).resolve().parent
TEST_UID = 'hcme-pdf-test-9448591@handball4all.de'
TEST_FILE = 'hcme-pdf-test-9448591.ics'
PDF_NAME = 'Spielbericht_Korntal_HCME_2026-09-27.pdf'


class CalendarError(Exception):
    pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def safe_url(base, reference):
    url = urllib.parse.urljoin(base, reference)
    parts = urllib.parse.urlsplit(url)
    host = (parts.hostname or '').lower()
    if (parts.scheme != 'https' or parts.username or parts.password
            or parts.port not in (None, 443)
            or not (host == 'icloud.com' or host.endswith('.icloud.com'))):
        raise CalendarError('iCloud verweist auf eine unerwartete Serveradresse; Abbruch.')
    return urllib.parse.urlunsplit(parts._replace(fragment=''))


class Client:
    def __init__(self, username, password):
        token = base64.b64encode(f'{username}:{password}'.encode()).decode('ascii')
        self.authorization = 'Basic ' + token
        self.opener = urllib.request.build_opener(NoRedirect())

    def request(self, method, url, body=None, headers=None):
        url = safe_url('https://caldav.icloud.com/', url)
        for _ in range(5):
            request = urllib.request.Request(url, data=body, method=method, headers={
                'Authorization': self.authorization,
                'User-Agent': 'HCME-iCloud-PDF-Test/1.0',
                **(headers or {}),
            })
            try:
                response = self.opener.open(request, timeout=30)
            except urllib.error.HTTPError as exc:
                response = exc
            except urllib.error.URLError:
                raise CalendarError('Der iCloud-Server ist derzeit nicht erreichbar.') from None
            with response:
                status = response.status
                result_headers = response.headers
                data = response.read(4_000_001)
            if len(data) > 4_000_000:
                raise CalendarError('Unerwartet große Serverantwort; Abbruch.')
            if status in (301, 302, 307, 308):
                location = result_headers.get('Location')
                if not location:
                    raise CalendarError('iCloud-Weiterleitung ohne Zieladresse.')
                url = safe_url(url, location)
                continue
            return status, result_headers, data, url
        raise CalendarError('Zu viele iCloud-Weiterleitungen.')


def require_status(result, allowed, operation):
    if result[0] not in allowed:
        if result[0] in (401, 403):
            raise CalendarError(f'{operation}: Anmeldung oder Berechtigung fehlt (HTTP {result[0]}).')
        raise CalendarError(f'{operation}: iCloud antwortete mit HTTP {result[0]}.')
    return result


def propfind(client, url, tags, depth='0'):
    body = ('<?xml version="1.0" encoding="utf-8"?>'
            '<d:propfind xmlns:d="DAV:" xmlns:c="urn:ietf:params:xml:ns:caldav">'
            '<d:prop>' + tags + '</d:prop></d:propfind>').encode()
    result = require_status(client.request('PROPFIND', url, body, {
        'Depth': depth, 'Content-Type': 'application/xml; charset=utf-8',
    }), (207,), 'Kalenderabfrage')
    try:
        root = ET.fromstring(result[2])
    except ET.ParseError:
        raise CalendarError('iCloud lieferte keine gültige Kalenderantwort.') from None
    rows = []
    for response in root.findall(f'{{{DAV}}}response'):
        props = {}
        for propstat in response.findall(f'{{{DAV}}}propstat'):
            status = propstat.findtext(f'{{{DAV}}}status', '')
            if ' 200 ' in status:
                prop = propstat.find(f'{{{DAV}}}prop')
                if prop is not None:
                    props.update({child.tag: child for child in prop})
        rows.append((response.findtext(f'{{{DAV}}}href', ''), props))
    return rows, result[3]


def property_href(rows, name):
    for _, props in rows:
        element = props.get(name)
        if element is not None:
            href = element.findtext(f'{{{DAV}}}href')
            if href:
                return href
    raise CalendarError('iCloud lieferte keinen Kalenderpfad für diesen Account.')


def discover(client, calendar_name):
    rows, base = propfind(client, 'https://caldav.icloud.com/', '<d:current-user-principal/>')
    principal = safe_url(base, property_href(rows, f'{{{DAV}}}current-user-principal'))
    rows, base = propfind(client, principal, '<c:calendar-home-set/>')
    calendar_home = safe_url(base, property_href(rows, f'{{{CAL}}}calendar-home-set'))
    result = require_status(client.request('OPTIONS', calendar_home), (200, 204), 'Funktionsprüfung')
    features = {item.strip().lower() for item in result[1].get('DAV', '').split(',')}
    if 'calendar-managed-attachments' not in features:
        raise CalendarError('Dieser iCloud-Zugang meldet keine Unterstützung für Datei-Anhänge.')
    rows, base = propfind(client, calendar_home,
                         '<d:displayname/><d:resourcetype/><d:current-user-privilege-set/>', '1')
    matches = []
    for href, props in rows:
        resource = props.get(f'{{{DAV}}}resourcetype')
        name = props.get(f'{{{DAV}}}displayname')
        if (resource is not None and resource.find(f'{{{CAL}}}calendar') is not None
                and name is not None and (name.text or '') == calendar_name):
            privileges = props.get(f'{{{DAV}}}current-user-privilege-set')
            if privileges is not None:
                writable = any(privileges.find(f'.//{{{DAV}}}{tag}') is not None
                               for tag in ('write', 'write-content', 'all'))
                if not writable:
                    raise CalendarError('Der Testkalender ist nicht beschreibbar.')
            matches.append(safe_url(base, href))
    if len(matches) != 1:
        raise CalendarError('Genau ein iCloud-Kalender mit dem eingestellten Testnamen muss vorhanden sein.')
    print('Anmeldung erfolgreich. Testkalender gefunden. Datei-Anhänge werden unterstützt.')
    return matches[0]


def fold(line):
    parts, current, length = [], '', 0
    for char in line:
        size = len(char.encode())
        if length + size > 75:
            parts.append(current)
            current, length = ' ', 1
        current += char
        length += size
    parts.append(current)
    return '\r\n'.join(parts)


def test_event():
    calendar = (ROOT / 'hcme.ics').read_text(encoding='utf-8')
    calendar = re.sub(r'\r?\n[ \t]', '', calendar)
    event = next((item.split('END:VEVENT')[0] for item in calendar.split('BEGIN:VEVENT')
                  if 'UID:9448591@handball4all.de' in item), None)
    if event is None:
        raise CalendarError('Der Korntal-Termin fehlt in der Quelldatei.')
    fields = {}
    for line in event.splitlines():
        if ':' in line:
            key, value = line.split(':', 1)
            fields[key.split(';', 1)[0]] = value
    dates = []
    for name in ('DTSTART', 'DTEND'):
        date = datetime.strptime(fields[name], '%Y%m%dT%H%M%S').replace(tzinfo=ZoneInfo('Europe/Berlin'))
        dates.append(f'{name}:{date.astimezone(timezone.utc):%Y%m%dT%H%M%SZ}')
    lines = [
        'BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//HCME//iCloud PDF Test//DE',
        'BEGIN:VEVENT', f'UID:{TEST_UID}', f'DTSTAMP:{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}',
        *dates, 'SEQUENCE:0', 'SUMMARY:HCME PDF-Test: TSV Korntal – HC Metter-Enz',
        'LOCATION:' + fields['LOCATION'],
        'DESCRIPTION:Testtermin mit dem Spielbericht als PDF-Datei.',
        'END:VEVENT', 'END:VCALENDAR',
    ]
    return ('\r\n'.join(fold(line) for line in lines) + '\r\n').encode()


def upload_test(client, calendar_url):
    pdf = (ROOT / 'reports' / '9448591.pdf').read_bytes()
    if not pdf.startswith(b'%PDF-') or len(pdf) > 2_000_000:
        raise CalendarError('Die lokale PDF-Datei ist ungültig oder zu groß.')
    event_url = safe_url(calendar_url.rstrip('/') + '/', TEST_FILE)
    current = client.request('GET', event_url)
    if current[0] == 404:
        require_status(client.request('PUT', event_url, test_event(), {
            'Content-Type': 'text/calendar; charset=utf-8', 'If-None-Match': '*',
        }), (201, 204), 'Testtermin anlegen')
        current = client.request('GET', event_url)
    require_status(current, (200,), 'Testtermin lesen')
    text = re.sub(r'\r?\n[ \t]', '', current[2].decode())
    if f'UID:{TEST_UID}' not in text:
        raise CalendarError('Unter der Testadresse liegt ein fremder Termin; keine Änderung vorgenommen.')
    if re.search(r'^ATTACH;[^\r\n]*MANAGED-ID=', text, re.MULTILINE):
        print('Der PDF-Testtermin besitzt bereits einen Datei-Anhang; kein Duplikat angelegt.')
        return
    headers = {'Content-Type': 'application/pdf',
               'Content-Disposition': f'attachment; filename="{PDF_NAME}"',
               'Prefer': 'return=representation'}
    if current[1].get('ETag'):
        headers['If-Match'] = current[1]['ETag']
    require_status(client.request('POST', event_url + '?action=attachment-add', pdf, headers),
                   (200, 201, 204), 'PDF hochladen')
    result = require_status(client.request('GET', event_url), (200,), 'PDF-Zuordnung prüfen')
    text = re.sub(r'\r?\n[ \t]', '', result[2].decode())
    if not re.search(r'^ATTACH;[^\r\n]*MANAGED-ID=', text, re.MULTILINE):
        raise CalendarError('Upload beantwortet, aber keine serverseitige PDF-Zuordnung gefunden.')
    print('PDF auf iCloud gespeichert und dem Testtermin zugeordnet.')
    print('Am iPhone den 27.09.2026 öffnen und im Testkalender den Termin HCME PDF-Test prüfen.')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=('check', 'upload-test'), default='check')
    args = parser.parse_args()
    username = os.environ.get('ICLOUD_USERNAME', '').strip()
    password = os.environ.get('ICLOUD_APP_PASSWORD', '').strip()
    calendar_name = os.environ.get('ICLOUD_CALENDAR_NAME', 'HCME PDF Test').strip()
    if not username or not password:
        raise CalendarError('Die GitHub-Secrets ICLOUD_USERNAME und ICLOUD_APP_PASSWORD fehlen.')
    if not calendar_name:
        raise CalendarError('Der Name des Testkalenders fehlt.')
    client = Client(username, password)
    calendar_url = discover(client, calendar_name)
    if args.mode == 'upload-test':
        upload_test(client, calendar_url)
    else:
        print('Verbindung geprüft. Es wurden keine Termine oder Dateien verändert.')


if __name__ == '__main__':
    try:
        main()
    except (CalendarError, OSError) as exc:
        print('Test nicht abgeschlossen: ' + str(exc), file=sys.stderr)
        raise SystemExit(1)

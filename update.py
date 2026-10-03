#!/usr/bin/env python3
import base64
import json
import re
import time
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

TZ = ZoneInfo('Europe/Berlin')
TEAM = 'HC Metter-Enz'

CALENDARS = [
    {
        'api': 'https://spo.handball4all.de/service/if_g_json.php?ca=0&cl=161551&cmd=ps&ct=1451606&og=216',
        'file': 'hcme.ics',
        'name': 'HC Metter-Enz 2026/27',
    },
    {
        'api': 'https://spo.handball4all.de/service/if_g_json.php?ca=0&cl=161581&cmd=ps&ct=1451841&og=216',
        'file': 'frauen1.ics',
        'name': 'HCME Frauen 1 2026/27',
    },
]


def esc(s):
    return str(s).replace('\\', '\\\\').replace(';', '\\;').replace(',', '\\,').replace('\n', '\\n')


def fetch_json(url, attempts=3):
    last_error = None
    for attempt in range(1, attempts + 1):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'HCME-calendar/1.0'})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except Exception as exc:
            last_error = exc
            if attempt < attempts:
                time.sleep(3 * attempt)
    raise last_error


def games_from_response(data):
    """Collect all game lists; a live game may move out of futureGames."""
    content = data[0]['content']
    games_by_id = {}
    for key in ('futureGames', 'actualGames'):
        section = content.get(key, [])
        games = section.get('games', []) if isinstance(section, dict) else section
        for game in games or []:
            game_id = str(game.get('gID', ''))
            if not game_id:
                continue
            previous = games_by_id.get(game_id)
            if previous is None:
                games_by_id[game_id] = game
                continue

            # A live game can appear in more than one section. Keep ticker/report
            # identifiers if either copy already contains them.
            if not valid_sgid(previous.get('sGID')) and valid_sgid(game.get('sGID')):
                previous['sGID'] = game.get('sGID')
            if not valid_token(previous.get('gToken')) and valid_token(game.get('gToken')):
                previous['gToken'] = game.get('gToken')
    if not games_by_id:
        raise ValueError('Handball4all lieferte keine Spiele; Kalender wird nicht überschrieben')
    return list(games_by_id.values())


def valid_sgid(value):
    return bool(re.fullmatch(r'[1-9][0-9]*', str(value or '').strip()))


def valid_token(value):
    return bool(re.fullmatch(r'[A-Za-z0-9_-]{16,128}', str(value or '').strip()))


def fold_ascii_line(value):
    """Fold an ASCII iCalendar property at the 75-octet line limit."""
    chunks = [value[:75]]
    for offset in range(75, len(value), 74):
        chunks.append(' ' + value[offset:offset + 74])
    return chunks


def finished_game(game):
    return bool(re.fullmatch(r'\d+', str(game.get('gHomeGoals', '')).strip())
                and re.fullmatch(r'\d+', str(game.get('gGuestGoals', '')).strip()))


def pdf_attachment(game_id, game_number, report_url):
    """Embed a real PDF, downloading it only once per game to the repo cache."""
    reports_dir = Path('reports')
    reports_dir.mkdir(exist_ok=True)
    path = reports_dir / f'{game_id}.pdf'
    if not path.is_file():
        request = urllib.request.Request(report_url, headers={'User-Agent': 'HCME-calendar/1.0'})
        with urllib.request.urlopen(request, timeout=30) as response:
            pdf = response.read(2_000_001)
        if len(pdf) > 2_000_000 or not pdf.startswith(b'%PDF-'):
            raise ValueError(f'Kein gültiger PDF-Spielbericht für Spiel {game_id}')
        path.write_bytes(pdf)
    else:
        pdf = path.read_bytes()
        if not pdf.startswith(b'%PDF-'):
            raise ValueError(f'Ungültiger gespeicherter Spielbericht für Spiel {game_id}')
    encoded = base64.b64encode(pdf).decode('ascii')
    name = f'Spielbericht_{game_number}.pdf'
    return fold_ascii_line(
        f'ATTACH;FMTTYPE=application/pdf;FILENAME={name};ENCODING=BASE64;VALUE=BINARY:{encoded}'
    )


def existing_report_ids(outfile):
    """Keep an already published report ID if the API temporarily omits it."""
    result = {}
    try:
        with open(outfile, encoding='utf-8') as source:
            calendar = source.read()
    except FileNotFoundError:
        return result
    for event in calendar.split('BEGIN:VEVENT')[1:]:
        uid = re.search(r'^UID:([0-9]+)@handball4all\.de\r?$', event, re.MULTILINE)
        report = re.search(r'https://spo\.handball4all\.de/misc/sboPublicReports\.php\?sGID=([0-9]+)', event)
        if uid and report and valid_sgid(report.group(1)):
            result[uid.group(1)] = report.group(1)
    return result


def existing_ticker_tokens(outfile):
    """Keep a ticker token once Handball4all has published it."""
    result = {}
    try:
        with open(outfile, encoding='utf-8') as source:
            calendar = source.read()
    except FileNotFoundError:
        return result
    for event in calendar.split('BEGIN:VEVENT')[1:]:
        uid = re.search(r'^UID:([0-9]+)@handball4all\.de\r?$', event, re.MULTILINE)
        ticker = re.search(
            r'https://spo\.handball4all\.de/service/ticker/index\.html\?token=([A-Za-z0-9_-]+)',
            event,
        )
        if uid and ticker and valid_token(ticker.group(1)):
            result[uid.group(1)] = ticker.group(1)
    return result


def build_calendar(api, outfile, calendar_name):
    games = games_from_response(fetch_json(api))
    saved_reports = existing_report_ids(outfile)
    saved_tickers = existing_ticker_tokens(outfile)

    lines = [
        'BEGIN:VCALENDAR',
        'VERSION:2.0',
        'PRODID:-//HC Metter-Enz//H4A Auto Calendar//DE',
        'CALSCALE:GREGORIAN',
        'METHOD:PUBLISH',
        f'X-WR-CALNAME:{esc(calendar_name)}',
    ]

    count = 0
    for g in games:
        if TEAM not in (g.get('gHomeTeam', ''), g.get('gGuestTeam', '')):
            continue

        start = datetime.strptime(
            g['gDate'] + ' ' + g['gTime'], '%d.%m.%y %H:%M'
        ).replace(tzinfo=TZ)
        end = start + timedelta(hours=2)

        loc = ', '.join(
            x for x in [
                g.get('gGymnasiumName', ''),
                g.get('gGymnasiumStreet', ''),
                (g.get('gGymnasiumPostal', '') + ' ' + g.get('gGymnasiumTown', '')).strip(),
            ] if x
        )

        summary = f"{g.get('gHomeTeam', '')} – {g.get('gGuestTeam', '')}"
        description = f"Spielnummer {g.get('gNo', '')}"

        ticker_token = str(g.get('gToken', '')).strip()
        if not valid_token(ticker_token):
            ticker_token = saved_tickers.get(str(g['gID']), '')
        if ticker_token:
            ticker_url = (
                'https://spo.handball4all.de/service/ticker/'
                f'index.html?token={ticker_token}'
            )
            description += f"\nLiveticker: {ticker_url}"

        sbo_id = str(g.get('sGID', '')).strip()
        if not valid_sgid(sbo_id):
            sbo_id = saved_reports.get(str(g['gID']), '')

        event_lines = [
            'BEGIN:VEVENT',
            f"UID:{g['gID']}@handball4all.de",
            f"DTSTART;TZID=Europe/Berlin:{start.strftime('%Y%m%dT%H%M%S')}",
            f"DTEND;TZID=Europe/Berlin:{end.strftime('%Y%m%dT%H%M%S')}",
            f"SUMMARY:{esc(summary)}",
            f"LOCATION:{esc(loc)}",
        ]

        if sbo_id:
            report_url = f'https://spo.handball4all.de/misc/sboPublicReports.php?sGID={sbo_id}'
            description += f"\nSpielbericht (PDF): {report_url}"
            if finished_game(g):
                try:
                    event_lines.extend(pdf_attachment(str(g['gID']), str(g.get('gNo', g['gID'])), report_url))
                except Exception as exc:
                    print(f"Spiel {g['gID']}: PDF-Anhang vorübergehend nicht verfügbar: {exc}")
        else:
            description += '\nSpielbericht (PDF): wird ergänzt, sobald Handball4all ihn bereitstellt.'

        event_lines += [
            f'DESCRIPTION:{esc(description)}',
            'END:VEVENT',
        ]
        lines += event_lines
        count += 1

    lines.append('END:VCALENDAR')
    with open(outfile, 'w', encoding='utf-8', newline='') as f:
        f.write('\r\n'.join(lines) + '\r\n')

    print(f'{outfile}: {count} zukünftige HCME-Spiele aktualisiert')


if __name__ == '__main__':
    updated = 0
    for calendar in CALENDARS:
        try:
            build_calendar(calendar['api'], calendar['file'], calendar['name'])
            updated += 1
        except Exception as exc:
            print(f"{calendar['file']}: Aktualisierung fehlgeschlagen: {exc}")
    if not updated:
        raise SystemExit('Keine Kalender aktualisiert')

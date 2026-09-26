#!/usr/bin/env python3
import json
import time
import urllib.request
from datetime import datetime, timedelta
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
        'api': 'https://spo.handball4all.de/service/if_g_json.php?ca=0&cl=161581&cmd=ps&og=216',
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


def build_calendar(api, outfile, calendar_name):
    data = fetch_json(api)
    obj = data[0]
    games = obj['content']['futureGames']['games']

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
        sbo_id = str(g.get('sGID', '')).strip()

        event_lines = [
            'BEGIN:VEVENT',
            f"UID:{g['gID']}@handball4all.de",
            f"DTSTART;TZID=Europe/Berlin:{start.strftime('%Y%m%dT%H%M%S')}",
            f"DTEND;TZID=Europe/Berlin:{end.strftime('%Y%m%dT%H%M%S')}",
            f"SUMMARY:{esc(summary)}",
            f"LOCATION:{esc(loc)}",
        ]

        if sbo_id and sbo_id != '0':
            liveticker = f'https://spo.handball4all.de/misc/sboPublicReports.php?sGID={sbo_id}'
            description += f"\nLiveticker: {liveticker}"
            event_lines.append(f'URL:{liveticker}')
        else:
            description += '\nLiveticker: wird automatisch ergänzt, sobald Handball4all ihn freigibt.'

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


for calendar in CALENDARS:
    build_calendar(calendar['api'], calendar['file'], calendar['name'])

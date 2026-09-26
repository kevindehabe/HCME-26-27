#!/usr/bin/env python3
import json, urllib.request
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

API='https://spo.handball4all.de/service/if_g_json.php?ca=0&cl=161551&cmd=ps&ct=1451606&og=216'
TEAM='HC Metter-Enz'
TZ=ZoneInfo('Europe/Berlin')

def esc(s):
    return str(s).replace('\\','\\\\').replace(';','\\;').replace(',','\\,').replace('\n','\\n')

with urllib.request.urlopen(API, timeout=30) as r:
    data=json.load(r)
obj=data[0]
games=obj['content']['futureGames']['games']
lines=['BEGIN:VCALENDAR','VERSION:2.0','PRODID:-//HC Metter-Enz//H4A Auto Calendar//DE','CALSCALE:GREGORIAN','METHOD:PUBLISH','X-WR-CALNAME:HC Metter-Enz 2026/27']
for g in games:
    if TEAM not in (g.get('gHomeTeam',''), g.get('gGuestTeam','')):
        continue
    start=datetime.strptime(g['gDate']+' '+g['gTime'],'%d.%m.%y %H:%M').replace(tzinfo=TZ)
    end=start+timedelta(hours=2)
    loc=', '.join(x for x in [g.get('gGymnasiumName',''), g.get('gGymnasiumStreet',''), (g.get('gGymnasiumPostal','')+' '+g.get('gGymnasiumTown','')).strip()] if x)
    summary=f"{g.get('gHomeTeam','')} – {g.get('gGuestTeam','')}"
    description=f"Spielnummer {g.get('gNo','')}"
    if g.get('sGID'):
        liveticker=f"https://spo.handball4all.de/misc/sboPublicReports.php?sGID={g['sGID']}"
        description += f"\nLiveticker: {liveticker}"
    lines += ['BEGIN:VEVENT',f"UID:{g['gID']}@handball4all.de",f"DTSTART;TZID=Europe/Berlin:{start.strftime('%Y%m%dT%H%M%S')}",f"DTEND;TZID=Europe/Berlin:{end.strftime('%Y%m%dT%H%M%S')}",f"SUMMARY:{esc(summary)}",f"LOCATION:{esc(loc)}",f"DESCRIPTION:{esc(description)}",'END:VEVENT']
lines.append('END:VCALENDAR')
open('hcme.ics','w',encoding='utf-8',newline='').write('\r\n'.join(lines)+'\r\n')

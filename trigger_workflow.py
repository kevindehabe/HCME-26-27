#!/usr/bin/env python3
"""Render cron: start the existing GitHub workflow around HCME matches."""
import json
import os
import urllib.request
from datetime import datetime, timedelta, timezone

from update import CALENDARS, TEAM, TZ, fetch_json, games_from_response

WORKFLOW_URL = ('https://api.github.com/repos/kevindehabe/HCME-26-27/'
                'actions/workflows/update-hcme-calendar.yml/dispatches')


def matches_near_now(now):
    starts = []
    for calendar in CALENDARS:
        try:
            games = games_from_response(fetch_json(calendar['api'], attempts=1))
        except Exception as exc:
            print(f"{calendar['file']}: Handball4all nicht erreichbar: {exc}")
            continue
        for game in games:
            if TEAM not in (game.get('gHomeTeam'), game.get('gGuestTeam')):
                continue
            start = datetime.strptime(game['gDate'] + ' ' + game['gTime'],
                                      '%d.%m.%y %H:%M').replace(tzinfo=TZ)
            if start - timedelta(hours=2) <= now <= start + timedelta(hours=4):
                starts.append((calendar['file'], game['gID']))
    return starts


def main():
    now = datetime.now(timezone.utc)
    matches = matches_near_now(now)
    # Also pick up schedule changes once a day, even on days without a match.
    if not matches and not (now.hour == 8 and now.minute < 5):
        print('Kein Spiel im Zeitfenster; kein Workflow-Start')
        return
    token = os.environ['GITHUB_ACTIONS_TOKEN']
    request = urllib.request.Request(
        WORKFLOW_URL,
        data=json.dumps({'ref': 'main'}).encode('utf-8'),
        headers={
            'Accept': 'application/vnd.github+json',
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
            'X-GitHub-Api-Version': '2022-11-28',
            'User-Agent': 'HCME-calendar-trigger/1.0',
        },
        method='POST',
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        if response.status not in (200, 204):
            raise RuntimeError(f'GitHub workflow_dispatch: HTTP {response.status}')
    print(f"Workflow gestartet; passende Spiele: {matches}")


if __name__ == '__main__':
    main()

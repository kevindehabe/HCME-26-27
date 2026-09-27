import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import icloud_pdf_test as app


HOME = 'https://p01-caldav.icloud.com/account/calendars/'
TARGET = HOME + 'test/'


def multistatus(inner):
    return ('<d:multistatus xmlns:d="DAV:" xmlns:c="urn:ietf:params:xml:ns:caldav">'
            + inner + '</d:multistatus>').encode()


def resource(href, properties):
    return ('<d:response><d:href>' + href + '</d:href><d:propstat><d:prop>'
            + properties + '</d:prop><d:status>HTTP/1.1 200 OK</d:status>'
            '</d:propstat></d:response>')


class FakeClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def request(self, method, url, body=None, headers=None):
        self.calls.append((method, url, body, headers or {}))
        expected, status, result_headers, data = self.responses.pop(0)
        if method != expected:
            raise AssertionError(f'Expected {expected}, got {method}')
        return status, result_headers, data, url


def discovery_client(managed=True, duplicates=False):
    calendar = resource(TARGET,
                        '<d:displayname>HCME PDF Test</d:displayname>'
                        '<d:resourcetype><d:collection/><c:calendar/></d:resourcetype>'
                        '<d:current-user-privilege-set><d:privilege><d:write-content/>'
                        '</d:privilege></d:current-user-privilege-set>')
    return FakeClient([
        ('PROPFIND', 207, {}, multistatus(resource('/',
            '<d:current-user-principal><d:href>/account/principal/</d:href></d:current-user-principal>'))),
        ('PROPFIND', 207, {}, multistatus(resource('/account/principal/',
            '<c:calendar-home-set><d:href>' + HOME + '</d:href></c:calendar-home-set>'))),
        ('OPTIONS', 200, {'DAV': 'calendar-access, calendar-managed-attachments' if managed else 'calendar-access'}, b''),
        ('PROPFIND', 207, {}, multistatus(calendar * (2 if duplicates else 1))),
    ])


class ICloudTests(unittest.TestCase):
    def test_discovery_is_read_only_and_targets_exact_calendar(self):
        client = discovery_client()
        with patch('builtins.print'):
            self.assertEqual(app.discover(client, 'HCME PDF Test'), TARGET)
        self.assertEqual([call[0] for call in client.calls], ['PROPFIND', 'PROPFIND', 'OPTIONS', 'PROPFIND'])
        self.assertNotIn('calendar-data', str(client.calls))

    def test_missing_attachment_support_stops_before_writes(self):
        client = discovery_client(managed=False)
        with self.assertRaises(app.CalendarError):
            app.discover(client, 'HCME PDF Test')
        self.assertEqual(len(client.calls), 3)

    def test_ambiguous_calendar_name_is_rejected(self):
        with self.assertRaises(app.CalendarError):
            app.discover(discovery_client(duplicates=True), 'HCME PDF Test')

    def test_credentials_cannot_follow_untrusted_redirect(self):
        for url in ('https://icloud.com.attacker.example/x', 'http://caldav.icloud.com/x',
                    'https://user:pass@caldav.icloud.com/x', 'https://caldav.icloud.com:444/x'):
            with self.subTest(url=url), self.assertRaises(app.CalendarError):
                app.safe_url(HOME, url)
        self.assertEqual(app.safe_url(HOME, '../principal/'),
                         'https://p01-caldav.icloud.com/account/principal/')

    def write_fixture(self, directory):
        root = Path(directory)
        (root / 'reports').mkdir()
        pdf = b'%PDF-1.4\nPDF test fixture\n%%EOF'
        (root / 'reports/9448591.pdf').write_bytes(pdf)
        (root / 'hcme.ics').write_text(
            'BEGIN:VCALENDAR\nBEGIN:VEVENT\nUID:9448591@handball4all.de\n'
            'DTSTART;TZID=Europe/Berlin:20260927T173000\n'
            'DTEND;TZID=Europe/Berlin:20260927T193000\nLOCATION:Sporthalle Korntal\n'
            'DESCRIPTION:Old report URL\nEND:VEVENT\nEND:VCALENDAR\n', encoding='utf-8')
        return root, pdf

    def test_new_event_uploads_real_pdf_with_conditional_writes(self):
        event = ('BEGIN:VEVENT\r\nUID:' + app.TEST_UID + '\r\nEND:VEVENT\r\n').encode()
        attached = event.replace(b'END:VEVENT', b'ATTACH;MANAGED-ID=123;FMTTYPE=application/pdf:https://p01-caldav.icloud.com/file.pdf\r\nEND:VEVENT')
        client = FakeClient([
            ('GET', 404, {}, b''), ('PUT', 201, {}, b''),
            ('GET', 200, {'ETag': '"v1"'}, event),
            ('POST', 201, {}, attached), ('GET', 200, {}, attached),
        ])
        with tempfile.TemporaryDirectory() as directory:
            root, pdf = self.write_fixture(directory)
            with patch.object(app, 'ROOT', root), patch('builtins.print'):
                app.upload_test(client, TARGET)
        put, post = client.calls[1], client.calls[3]
        self.assertEqual(put[3]['If-None-Match'], '*')
        self.assertIn(b'DTSTART:20260927T153000Z', put[2])
        self.assertNotIn(b'http', put[2])
        self.assertEqual(post[2], pdf)
        self.assertEqual(post[3]['If-Match'], '"v1"')
        self.assertEqual(post[3]['Content-Type'], 'application/pdf')
        self.assertTrue(post[1].endswith('?action=attachment-add'))

    def test_existing_attachment_is_not_added_twice(self):
        event = ('UID:' + app.TEST_UID + '\r\nATTACH;MANAGED-ID=id:https://p01-caldav.icloud.com/file.pdf\r\n').encode()
        client = FakeClient([('GET', 200, {}, event)])
        with tempfile.TemporaryDirectory() as directory:
            root, _ = self.write_fixture(directory)
            with patch.object(app, 'ROOT', root), patch('builtins.print'):
                app.upload_test(client, TARGET)
        self.assertEqual(len(client.calls), 1)

    def test_unrelated_event_is_never_overwritten(self):
        client = FakeClient([('GET', 200, {}, b'UID:some-other-event\r\n')])
        with tempfile.TemporaryDirectory() as directory:
            root, _ = self.write_fixture(directory)
            with patch.object(app, 'ROOT', root), self.assertRaises(app.CalendarError):
                app.upload_test(client, TARGET)
        self.assertEqual(len(client.calls), 1)


if __name__ == '__main__':
    unittest.main()

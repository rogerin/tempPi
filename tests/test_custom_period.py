"""Regression tests for the current feature/temp-control APIs; no real database."""
import os
import sqlite3
import tempfile
import time
import unittest
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

# Keep Matplotlib's cache out of the user's home directory.
os.environ.setdefault('MPLCONFIGDIR', str(Path(tempfile.gettempdir()) / 'temppi-test-matplotlib'))
os.environ.setdefault('MPLBACKEND', 'Agg')

import sensor_server


class CustomPeriodTest(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.db = str(Path(temp.name) / 'sensors.db')
        db_patch = patch.object(sensor_server, 'DATABASE_PATH', self.db)
        db_patch.start()
        self.addCleanup(db_patch.stop)
        with closing(sqlite3.connect(self.db)) as conn:
            conn.execute('''CREATE TABLE sensor_readings (
                id INTEGER PRIMARY KEY, timestamp TEXT, sensor_name TEXT,
                temperature REAL, pressure REAL, velocity REAL, sensor_type TEXT,
                pins TEXT, mode TEXT)''')
            conn.executemany('''INSERT INTO sensor_readings
                (timestamp, sensor_name, temperature, sensor_type, mode)
                VALUES (?, ?, 25, 'temperature', 'simulation')''', [
                ('2026-10-14 09:59:59', 'Temp Forno'),
                ('2026-10-14 10:00:00', 'Temp Forno'),
                ('2026-10-14 10:30:00', 'Temp Tanque'),
                ('2026-10-14 11:00:59', 'Temp Forno'),
                ('2026-10-14 11:01:00', 'Temp Tanque'),
            ])
            conn.commit()
        self.client = sensor_server.app.test_client()

    def test_all_sensors_custom_period_includes_final_minute(self):
        response = self.client.get('/api/all-sensors/data', query_string={
            'start_time': '2026-10-14T10:00', 'end_time': '2026-10-14T11:00'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual([row['timestamp'] for row in response.json],
                         ['2026-10-14 10:00:00', '2026-10-14 10:30:00',
                          '2026-10-14 11:00:59'])
        self.assertEqual(response.json[1]['temp_tanque'], 25)

    def test_utc_and_offsets_are_converted_to_database_brazil_time(self):
        for start, end in [
            ('2026-10-14T13:00:00Z', '2026-10-14T14:00:59Z'),
            ('2026-10-14T15:00:00+02:00', '2026-10-14T16:00:59+02:00'),
        ]:
            with self.subTest(start=start):
                response = self.client.get('/api/all-sensors/data', query_string={
                    'start_time': start, 'end_time': end})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(len(response.json), 3)

    def test_invalid_reversed_and_incomplete_custom_periods_return_400(self):
        for filters in [
            {'start_time': 'invalid', 'end_time': '2026-10-14T11:00'},
            {'start_time': '2026-02-30T10:00', 'end_time': '2026-10-14T11:00'},
            {'start_time': '2026-10-14T12:00', 'end_time': '2026-10-14T11:00'},
            {'start_time': '2026-10-14T10:00'},
            {'start_time': '', 'end_time': ''},
        ]:
            with self.subTest(filters=filters):
                response = self.client.get('/api/all-sensors/data', query_string=filters)
                self.assertEqual(response.status_code, 400)
                self.assertIn('error', response.json)

    def test_grouping_does_not_shift_brazil_timestamps_again(self):
        previous_tz = os.environ.get('TZ')
        os.environ['TZ'] = 'America/Recife'
        time.tzset()
        try:
            response = self.client.get('/api/all-sensors/data', query_string={
                'start_time': '2026-10-14 10:00:00',
                'end_time': '2026-10-14 11:00:59', 'group_by': '1min'})
            self.assertEqual(response.status_code, 200)
            self.assertEqual([row['timestamp'] for row in response.json],
                             ['2026-10-14 10:00:00', '2026-10-14 10:30:00',
                              '2026-10-14 11:00:00'])
        finally:
            if previous_tz is None:
                os.environ.pop('TZ', None)
            else:
                os.environ['TZ'] = previous_tz
            time.tzset()

    def test_readings_and_csv_use_the_same_custom_period(self):
        filters = {'start': '2026-10-14T10:00', 'end': '2026-10-14T11:00'}
        response = self.client.get('/api/readings', query_string=filters)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['total'], 3)
        response = self.client.get('/api/readings/export', query_string=filters)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.text.splitlines()), 4)
        self.assertIn('2026-10-14 11:00:59', response.text)

    def test_hour_presets_and_empty_result_still_work(self):
        with patch.object(sensor_server, 'get_brazil_time', return_value=
                          datetime(2026, 10, 14, 11, 30, tzinfo=timezone(timedelta(hours=-3)))):
            response = self.client.get('/api/all-sensors/data?hours=1')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(response.json), 3)
        response = self.client.get('/api/all-sensors/data', query_string={
            'start_time': '2027-01-01T00:00', 'end_time': '2027-01-01T23:59'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, [])

    def test_pdf_includes_the_last_minute_like_the_screen(self):
        # Two readings in the same minute, as in the collector's normal cadence.
        with closing(sqlite3.connect(self.db)) as conn:
            conn.execute('''INSERT INTO sensor_readings
                (timestamp, sensor_name, temperature, sensor_type, mode)
                VALUES ('2026-10-14 11:00:30', 'Temp Forno', 24, 'temperature', 'simulation')''')
            conn.commit()
        response = self.client.post('/api/reports/generate-pdf', json={
            'timeRange': 'custom', 'startTime': '2026-10-14T11:00',
            'endTime': '2026-10-14T11:00', 'selectedSensors': ['temp_forno']})
        self.assertEqual(response.status_code, 200, response.json)
        self.assertTrue(response.data.startswith(b'%PDF'))


if __name__ == '__main__':
    unittest.main()

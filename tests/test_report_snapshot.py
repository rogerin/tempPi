"""The screen, downloaded PDF and email attachment must use one frozen dataset."""
import sqlite3
import unittest
from contextlib import closing
from datetime import datetime, timezone, timedelta
from email import message_from_string
from unittest.mock import patch

import sensor_server
import test_custom_period


class ReportSnapshotTest(unittest.TestCase):
    setUp = test_custom_period.CustomPeriodTest.setUp

    def snapshot(self, **filters):
        response = self.client.get('/api/all-sensors/data', query_string={
            'start_time': '2026-10-14T10:00', 'end_time': '2026-10-14T11:00',
            'sensors': 'temp_forno,temp_tanque', 'snapshot': '1', **filters})
        self.assertEqual(response.status_code, 200, response.json)
        self.assertIsInstance(response.json, dict)
        self.assertIn('snapshotToken', response.json)
        return response.json

    def test_snapshot_and_normal_endpoint_contain_the_same_data(self):
        snapshot = self.snapshot(group_by='5min')
        plain = self.client.get('/api/all-sensors/data', query_string={
            'start_time': '2026-10-14T10:00', 'end_time': '2026-10-14T11:00',
            'group_by': '5min'}).json
        self.assertEqual(snapshot['data'], plain)
        self.assertEqual(snapshot['filters']['groupBy'], '5min')
        self.assertEqual(snapshot['filters']['selectedSensors'], ['temp_forno', 'temp_tanque'])

    def test_download_and_email_are_identical_even_after_readings_change(self):
        snapshot = self.snapshot()
        payload = {'snapshotToken': snapshot['snapshotToken'],
                   'operation_name': 'Lote & teste', 'comments': 'Dados <conferidos>'}
        downloaded = self.client.post('/api/reports/generate-pdf', json=payload)
        self.assertEqual(downloaded.status_code, 200, downloaded.json)
        with closing(sqlite3.connect(self.db)) as conn:
            conn.execute('UPDATE sensor_readings SET temperature = 999')
            conn.execute('''CREATE TABLE smtp_config (
                id INTEGER PRIMARY KEY, smtp_host TEXT, smtp_port INTEGER,
                smtp_user TEXT, smtp_password TEXT, sender_email TEXT, sender_name TEXT)''')
            conn.execute("INSERT INTO smtp_config VALUES (1, 'smtp.example.invalid', 587, 'test', 'test', 'sender@example.invalid', 'TempPi')")
            conn.commit()
        # No real messages leave the test process.
        with patch('smtplib.SMTP') as smtp:
            sent = self.client.post('/api/reports/send-consolidated-email', json={
                **payload, 'recipient_email': 'receiver@example.invalid'})
        self.assertEqual(sent.status_code, 200, sent.json)
        message = message_from_string(smtp.return_value.sendmail.call_args.args[2])
        attachment = next(part for part in message.walk() if part.get_content_type() == 'application/octet-stream')
        self.assertEqual(attachment.get_payload(decode=True), downloaded.data)

    def test_relative_period_is_frozen_at_screen_load(self):
        now = datetime(2026, 10, 14, 11, 30, tzinfo=timezone(timedelta(hours=-3)))
        with patch.object(sensor_server, 'get_brazil_time', return_value=now):
            response = self.client.get('/api/all-sensors/data?snapshot=1&hours=1&sensors=temp_forno')
        self.assertIsInstance(response.json, dict)
        snapshot = response.json
        self.assertEqual(snapshot['filters']['startTime'], '2026-10-14 10:30:00')
        self.assertEqual(snapshot['filters']['endTime'], '2026-10-14 11:30:00')
        with patch.object(sensor_server, 'get_brazil_time', return_value=now + timedelta(days=1)):
            pdf = self.client.post('/api/reports/generate-pdf', json={'snapshotToken': snapshot['snapshotToken']})
        self.assertEqual(pdf.status_code, 200, pdf.json)

    def test_invalid_snapshot_never_falls_back_to_a_new_query(self):
        response = self.client.post('/api/reports/generate-pdf', json={
            'snapshotToken': 'invalid', 'timeRange': 'custom',
            'startTime': '2026-10-14T10:00', 'endTime': '2026-10-14T11:00',
            'selectedSensors': ['temp_forno']})
        self.assertEqual(response.status_code, 400)
        self.assertIn('Atualizar', response.json['error'])

    def test_expired_snapshot_requires_refresh_without_sending_email(self):
        snapshot = self.snapshot()
        import time
        with patch('itsdangerous.timed.time.time', return_value=time.time() + 86401), patch('smtplib.SMTP') as smtp:
            response = self.client.post('/api/reports/send-consolidated-email', json={
                'snapshotToken': snapshot['snapshotToken'], 'recipient_email': 'client@example.invalid'})
        self.assertEqual(response.status_code, 400)
        self.assertIn('Atualizar', response.json['error'])
        smtp.assert_not_called()

    def test_bar_conversion_is_the_same_in_chart_statistics_and_table(self):
        with closing(sqlite3.connect(self.db)) as conn:
            conn.execute("INSERT INTO sensor_readings (timestamp, sensor_name, pressure) VALUES ('2026-10-14 10:00:00', 'Pressão Gases', 10)")
            conn.execute("INSERT INTO sensor_readings (timestamp, sensor_name, pressure) VALUES ('2026-10-14 10:30:00', 'Pressão Gases', 20)")
            conn.commit()
        from matplotlib.axes import Axes
        from reportlab.platypus import Table
        original_plot = Axes.plot
        plotted = []

        def capture_plot(axis, x, y, *args, **kwargs):
            plotted.extend(y)
            return original_plot(axis, x, y, *args, **kwargs)

        with patch.object(Axes, 'plot', capture_plot), patch('reportlab.platypus.Table', wraps=Table) as table:
            response = self.client.post('/api/reports/generate-pdf', json={
                'timeRange': 'custom', 'startTime': '2026-10-14T10:00',
                'endTime': '2026-10-14T11:00', 'pressureUnit': 'bar',
                'selectedSensors': ['pressao_gases']})
        self.assertEqual(response.status_code, 200, response.json)
        self.assertAlmostEqual(plotted[0], 10 * 0.0689476)
        self.assertAlmostEqual(plotted[1], 20 * 0.0689476)
        stats = table.call_args_list[0].args[0]
        self.assertEqual(stats[1][1:], ['0.69', '1.38', '1.03'])
        details = table.call_args_list[1].args[0]
        self.assertEqual([row[1] for row in details[1:]], ['0.69', '1.38', '-'])

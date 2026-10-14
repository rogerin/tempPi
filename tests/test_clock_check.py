import io
import subprocess
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from check_server_time import check_server_time


class ClockCheckTest(unittest.TestCase):
    def check_with_result(self, output='', error=None):
        stream = io.StringIO()
        with patch('check_server_time.subprocess.run') as run, redirect_stdout(stream):
            run.return_value = subprocess.CompletedProcess([], 0, stdout=output, stderr='')
            run.side_effect = error
            result = check_server_time()
        self.assertEqual(run.call_args.args[0],
                         ['timedatectl', 'show', '--property=NTPSynchronized', '--value'])
        self.assertLessEqual(run.call_args.kwargs['timeout'], 5)
        self.assertIn('UTC', stream.getvalue())
        return result, stream.getvalue()

    def test_synchronized_clock(self):
        result, output = self.check_with_result('yes\n')
        self.assertTrue(result)
        self.assertIn('sincronizado', output)

    def test_unsynchronized_clock_has_instructions(self):
        result, output = self.check_with_result('no\n')
        self.assertFalse(result)
        self.assertIn('sudo timedatectl set-ntp true', output)

    def test_unavailable_status_is_not_reported_as_correct(self):
        for error in [FileNotFoundError(), subprocess.TimeoutExpired('timedatectl', 5),
                      subprocess.CalledProcessError(1, 'timedatectl')]:
            with self.subTest(error=error):
                result, output = self.check_with_result(error=error)
                self.assertFalse(result)
                self.assertIn('Não foi possível confirmar', output)

    def test_unexpected_output_is_unknown(self):
        result, output = self.check_with_result('')
        self.assertFalse(result)
        self.assertIn('Não foi possível confirmar', output)

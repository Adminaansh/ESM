# monitoring/tests.py
from django.test import SimpleTestCase
from .log_parser import count_exceptions

class LogParserTests(SimpleTestCase):
    def test_example(self):
        self.assertEqual(count_exceptions(["ValueError", "TypeError", "ValueError"]),
                         {"ValueError": 2, "TypeError": 1})

    def test_real_log_lines(self):
        lines = [
            "2026-10-09 10:15:02 ERROR ValueError: invalid literal for int()",
            "2026-10-09 10:15:03 INFO request ok",
            "django.db.utils.OperationalError: database is locked",
            'File "views.py", line 12, in get',
        ]
        self.assertEqual(count_exceptions(lines),
                         {"ValueError": 1, "OperationalError": 1})

    def test_empty(self):
        self.assertEqual(count_exceptions([]), {})
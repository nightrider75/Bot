import unittest
from datetime import datetime as real_datetime
from datetime import timezone
from unittest.mock import patch


from bot.bot_hub import node_template_utils


class CurrentDateTimeTests(unittest.TestCase):
    def test_current_time_respects_custom_format_and_timezone(self):
        now = real_datetime(2023, 1, 2, 14, 15, 16, tzinfo=timezone.utc)
        with patch.object(
            node_template_utils, "ZoneInfo", side_effect=lambda name: timezone.utc
        ) as fake_zone:
            with patch.object(node_template_utils, "datetime") as fake_datetime:
                fake_datetime.now.return_value = now
                result = node_template_utils.current_time(
                    "America/Los_Angeles", "%H:%M"
                )

        self.assertEqual(result, "14:15")
        fake_zone.assert_called_once_with("America/Los_Angeles")
        fake_datetime.now.assert_called_once_with(timezone.utc)

    def test_current_time_invalid_format_falls_back_to_iso(self):
        now = real_datetime(2023, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
        with patch.object(node_template_utils, "datetime") as fake_datetime:
            fake_datetime.now.return_value = now
            result = node_template_utils.current_time(output_format="")

        self.assertEqual(result, "03:04:05+00:00")
        fake_datetime.now.assert_called_once()


class TemplateGlobalHelpersTests(unittest.TestCase):
    def test_helpers_are_exposed_on_template_globals(self):
        class FakeTemplate:
            last_instance = None

            def __init__(self, text):
                self.text = text
                self.globals = {}
                FakeTemplate.last_instance = self

            def render(self, context):
                return "rendered"

        with patch.object(node_template_utils, "Template", FakeTemplate, create=True):
            rendered = node_template_utils.templatize("{}", {})

        self.assertEqual(rendered, "rendered")
        self.assertIs(
            FakeTemplate.last_instance.globals["to_words"],
            node_template_utils.num_to_words,
        )
        self.assertIs(
            FakeTemplate.last_instance.globals["current_time"],
            node_template_utils.current_time,
        )

    def test_end_to_end_templatize_with_timezone_and_helpers(self):
        from datetime import datetime as real_datetime

        template = (
            "Hello {{ name }}, today is {{ current_date }} and the weekday is {{ current_weekday }}. "
            "Number: {{ to_words(123, language='en') }}. "
            "Time in IST: {{ current_time('Asia/Kolkata', '%H:%M') }}"
        )
        test_data = {"name": "Alex"}

        # Patch datetime to always return fixed UTC time (2023-01-02 14:15:16 UTC)
        class FixedDatetime(real_datetime):
            @classmethod
            def now(cls, tz=None):
                # # Always return 2023-01-02 14:15:16 UTC
                dt = real_datetime(2025, 11, 2, 14, 15, 16)
                if tz:
                    dt = dt.astimezone(tz=tz)
                return dt

        with patch(
            "bot.bot_hub.node_template_utils.datetime",
            FixedDatetime,
        ):
            result = node_template_utils.templatize(template, dict(test_data))

        # Number in words output
        assert "one hundred and twenty three" in result
        # Name, date, and weekday
        assert "Hello Alex" in result
        assert "2025-November-02" in result
        assert "Sunday" in result
        assert "Time in IST: 14:15" in result

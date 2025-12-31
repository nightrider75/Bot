import unittest
from unittest.mock import patch

import jinja2  # noqa: F401
import loguru  # noqa: F401

from bot.bot_hub import node_template_utils


class NumToWordsTests(unittest.TestCase):
    def test_indic_language_uses_indic_library(self):
        called = {}

        def fake_indic(number, lang="en", to="cardinal"):
            called["args"] = (number, lang, to)
            return "indic"

        with patch.object(
            node_template_utils, "_indic_num2words", fake_indic, create=True
        ):
            result = node_template_utils.num_to_words("12", "hi")

        self.assertEqual(result, "indic")
        self.assertEqual(called["args"], (12.0, "hi", "cardinal"))

    def test_generic_language_uses_generic_library(self):
        called = {}

        def fake_generic(number, lang="en", to="cardinal"):
            called["args"] = (number, lang, to)
            return "generic"

        with patch.object(
            node_template_utils, "_generic_num2words", fake_generic, create=True
        ):
            result = node_template_utils.num_to_words(" 1,234 % ", "fr-CA", "cardinal")

        self.assertEqual(result, "generic")
        self.assertEqual(called["args"], (1234.0, "fr-ca", "cardinal"))

    def test_invalid_format_returns_empty_string(self):
        with patch.object(
            node_template_utils, "_generic_num2words", create=True
        ) as fake_generic:
            result = node_template_utils.num_to_words(5, "en", "bad-format")
        self.assertEqual(result, "")
        fake_generic.assert_not_called()

    def test_invalid_number_string_returns_empty_string(self):
        with patch.object(
            node_template_utils, "_generic_num2words", create=True
        ) as fake_generic:
            result = node_template_utils.num_to_words("not-a-number", "en", "cardinal")
        self.assertEqual(result, "")
        fake_generic.assert_not_called()

    def test_non_numeric_type_returns_empty_string(self):
        with patch.object(
            node_template_utils, "_generic_num2words", create=True
        ) as fake_generic:
            result = node_template_utils.num_to_words(None, "en", "cardinal")
        self.assertEqual(result, "")
        fake_generic.assert_not_called()

    def test_missing_language_defaults_to_english(self):
        called = {}

        def fake_indic(number, lang="en", to="cardinal"):
            called["args"] = (number, lang, to)
            return "indic"

        with patch.object(
            node_template_utils, "_indic_num2words", fake_indic, create=True
        ):
            result = node_template_utils.num_to_words(1, "   ")

        self.assertEqual(result, "indic")
        self.assertEqual(called["args"], (1, "en", "cardinal"))

    def test_template_global_to_words(self):
        class FakeTemplate:
            last_instance = None

            def __init__(self, text):
                self.text = text
                self.globals = {}
                FakeTemplate.last_instance = self

            def render(self, context):
                return "rendered"

        with patch.object(node_template_utils, "Template", FakeTemplate, create=True):
            rendered = node_template_utils.templatize(
                "{{ to_words(42, language='fr', format='cardinal') }}", {}
            )

        self.assertEqual(rendered, "rendered")
        self.assertIs(
            FakeTemplate.last_instance.globals["to_words"],
            node_template_utils.num_to_words,
        )

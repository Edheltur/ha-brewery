"""Regression tests for formats used in saved data."""

from copy import deepcopy
import unittest

from scripts.validate_catalogs import DATA, load_validators, read_json


class SchemaFormatsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.validators = load_validators()

    def test_rejects_invalid_profile_source_uri(self):
        profiles = read_json(DATA / "water_profiles.json")
        profiles["profiles"][0]["source_url"] = "not a URL"
        self.assertFalse(self.validators["water_profiles.json"].is_valid(profiles))

    def test_rejects_invalid_journal_timestamp(self):
        validator = self.validators["brew.json"]
        brew = deepcopy(validator.schema["examples"][0])
        brew["journal"][0]["occurred_at"] = "yesterday"
        self.assertFalse(validator.is_valid(brew))

    def test_rejects_invalid_start_timestamp(self):
        validator = self.validators["brew.json"]
        brew = {**validator.schema["examples"][0], "journal": []}
        self.assertTrue(validator.is_valid(brew))
        brew["started_at"] = "yesterday"
        self.assertFalse(validator.is_valid(brew))

    def test_planned_start_requires_time_and_offset(self):
        validator = self.validators["batch.json"]
        for target in ("brew", "packaging"):
            for value in ("2026-12-05", "2026-12-05T10:00:00"):
                with self.subTest(target=target, value=value):
                    batch = deepcopy(validator.schema["examples"][0])
                    operation = batch["brew"] if target == "brew" else batch["packagings"][0]
                    operation["planned_at"] = value
                    self.assertFalse(validator.is_valid(batch))

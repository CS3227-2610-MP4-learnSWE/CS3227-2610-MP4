import tempfile
import unittest
from pathlib import Path

from speccheck import waivers
from speccheck.waivers import load_waivers


class WaiverFileCase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)

    def load(self, text):
        path = self.dir / "waivers.txt"
        path.write_text(text, encoding="utf-8")
        return load_waivers(path)

    def bad_line(self, text):
        with self.assertRaises(waivers.WaiverError) as ctx:
            self.load(text)
        return ctx.exception


class ValidWaiverTests(WaiverFileCase):
    def test_chk01_ac14_valid_lines_load_into_a_dict_keyed_by_spec_id(self):
        loaded = self.load("STU-01 | all | predates the rule\nTEA-02 | added-items | no item labels\n")
        self.assertEqual(set(loaded), {"STU-01", "TEA-02"})
        self.assertEqual(loaded["STU-01"].spec_id, "STU-01")
        self.assertEqual(loaded["STU-01"].scope, "all")
        self.assertEqual(loaded["STU-01"].reason, "predates the rule")
        self.assertEqual(loaded["TEA-02"].scope, "added-items")

    def test_chk01_ac15_fields_are_trimmed(self):
        loaded = self.load("   STU-01   |   all   |   old spec   \n")
        waiver = loaded["STU-01"]
        self.assertEqual((waiver.spec_id, waiver.scope, waiver.reason), ("STU-01", "all", "old spec"))

    def test_chk01_ac15_comments_and_blank_lines_are_ignored(self):
        text = "# header comment\n\n   # indented comment\nSTU-01 | all | old\n\n"
        self.assertEqual(set(self.load(text)), {"STU-01"})

    def test_chk01_ac15_empty_file_gives_no_waivers(self):
        self.assertEqual(self.load(""), {})

    def test_chk01_ac15_only_comments_gives_no_waivers(self):
        self.assertEqual(self.load("# nothing here\n"), {})

    def test_chk01_ac15_spec_ids_are_case_sensitive(self):
        loaded = self.load("STU-01 | all | a\nstu-01 | all | b\n")
        self.assertEqual(set(loaded), {"STU-01", "stu-01"})

    def test_chk01_ac15_reason_may_contain_punctuation_and_colons(self):
        loaded = self.load("STU-01 | all | old: see notes, 2026.\n")
        self.assertEqual(loaded["STU-01"].reason, "old: see notes, 2026.")

    def test_chk01_ac16_missing_file_raises_file_not_found(self):
        with self.assertRaises(FileNotFoundError):
            load_waivers(self.dir / "absent.txt")


class BadWaiverTests(WaiverFileCase):
    def test_chk01_ac15_line_with_two_fields_is_rejected(self):
        error = self.bad_line("STU-01 | all\n")
        self.assertEqual(error.line, 1)

    def test_chk01_ac15_line_with_one_field_is_rejected(self):
        self.assertEqual(self.bad_line("STU-01\n").line, 1)

    def test_chk01_ac15_line_with_four_fields_is_rejected(self):
        self.assertEqual(self.bad_line("STU-01 | all | a | b\n").line, 1)

    def test_chk01_ac15_empty_reason_is_rejected(self):
        self.assertEqual(self.bad_line("STU-01 | all |   \n").line, 1)

    def test_chk01_ac15_empty_spec_id_is_rejected(self):
        self.assertEqual(self.bad_line(" | all | reason\n").line, 1)

    def test_chk01_ac15_empty_scope_is_rejected(self):
        self.assertEqual(self.bad_line("STU-01 |  | reason\n").line, 1)

    def test_chk01_ac15_unknown_scope_is_rejected_and_named(self):
        error = self.bad_line("STU-01 | partial | reason\n")
        self.assertEqual(error.line, 1)
        self.assertIn("partial", error.message)

    def test_chk01_ac14_only_two_scopes_exist(self):
        for scope in ("none", "section", "items", "ALL-ITEMS"):
            with self.subTest(scope=scope):
                self.bad_line(f"STU-01 | {scope} | reason\n")

    def test_chk01_ac15_duplicate_id_is_rejected_at_the_second_line(self):
        error = self.bad_line("STU-01 | all | a\nTEA-01 | all | b\nSTU-01 | added-items | c\n")
        self.assertEqual(error.line, 3)
        self.assertIn("STU-01", error.message)

    def test_chk01_ac15_line_number_counts_comments_and_blank_lines(self):
        error = self.bad_line("# c\n\nSTU-01 | all | ok\n\n# c2\nTEA-01 | bogus | reason\n")
        self.assertEqual(error.line, 6)

    def test_chk01_ac15_first_bad_line_is_reported(self):
        error = self.bad_line("STU-01 | all\nTEA-01 | bogus | reason\n")
        self.assertEqual(error.line, 1)


class BomTests(WaiverFileCase):
    def load_bytes(self, data):
        path = self.dir / "waivers.txt"
        path.write_bytes(data)
        return load_waivers(path)

    def test_chk01_ac15_bom_before_a_waiver_on_line_1_is_handled(self):
        loaded = self.load_bytes(b"\xef\xbb\xbfSTU-01 | all | old spec\n")
        self.assertEqual(set(loaded), {"STU-01"})
        self.assertEqual(loaded["STU-01"].scope, "all")

    def test_chk01_ac15_bom_before_a_comment_on_line_1_is_handled(self):
        loaded = self.load_bytes(b"\xef\xbb\xbf# comment\nSTU-01 | all | old spec\n")
        self.assertEqual(set(loaded), {"STU-01"})


if __name__ == "__main__":
    unittest.main()

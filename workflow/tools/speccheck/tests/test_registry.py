import re
import unittest
from pathlib import Path

from helpers import ITEM_LABELS, SECURITY_ITEMS, SPEC_REQUIRED, PLAN_REQUIRED, UI_ITEMS, run_main
from speccheck.registry import RULES

TOOL_DIR = Path(__file__).resolve().parents[1]

RULE_RE = re.compile(
    r'^RULE (?P<id>.+) tier=(?P<tier>[12]) file=(?P<file>\S+(?: or \S+)?) where="(?P<where>.*)" '
    r'skip_no_screen=(?P<sns>yes|no) skip_added_items=(?P<sai>yes|no) source="(?P<source>.*)"$'
)
FILE_CODES = ("SPEC_MISSING", "PLAN_MISSING", "TASKS_MISSING")
OTHER_CODES = (
    "TASKS_NO_ROLE",
    "NO_SCREEN",
    "PLACEHOLDER",
    "UI_SECTION_MISSING",
    "UI_TABLE_EMPTY",
    "UI_TABLE_CELL_EMPTY",
    "UI_CONTRACT_MISSING",
    "UI_CONTRACT_EMPTY",
)


def item_rule(code):
    pattern = re.compile(rf"(?<![A-Z_]){code}(?![A-Z_])")
    matches = [r for r in RULES if r.kind == "item" and pattern.search(r.id)]
    assert len(matches) == 1, f"expected one item rule for {code}, got {len(matches)}"
    return matches[0]


def label_matches(code, label):
    """Apply the matcher: groups OR'd, regexes inside a group AND'd, on the lowercased label."""
    label = label.lower()
    for group in item_rule(code).groups:
        regexes = [re.compile(g) if isinstance(g, str) else g for g in group]
        if all(rx.search(label) for rx in regexes):
            return True
    return False


class RegistryTableTests(unittest.TestCase):
    def test_chk01_ac19_rules_is_a_nonempty_tuple_with_unique_ids(self):
        self.assertIsInstance(RULES, tuple)
        self.assertGreater(len(RULES), 0)
        ids = [r.id for r in RULES]
        self.assertEqual(len(ids), len(set(ids)))

    def test_chk01_ac19_rule_fields_have_the_documented_shape(self):
        kinds = {"file", "section", "ac-item", "task-role", "table", "item"}
        for rule in RULES:
            with self.subTest(rule=rule.id):
                self.assertIn(rule.tier, (1, 2))
                self.assertIn(rule.kind, kinds)
                self.assertIsInstance(rule.skip_no_screen, bool)
                self.assertIsInstance(rule.skip_added_items, bool)
                self.assertTrue(rule.source)

    def test_chk01_ac19_every_file_and_other_code_is_in_the_registry(self):
        haystack = repr(RULES)
        for code in FILE_CODES + OTHER_CODES:
            with self.subTest(code=code):
                self.assertIn(code, haystack)

    def test_chk01_ac19_every_required_section_has_a_rule(self):
        wheres = {(r.file, r.where.lower()) for r in RULES if r.kind == "section"}
        for name in SPEC_REQUIRED:
            self.assertIn(("spec.md", name.lower()), wheres)
        for name in PLAN_REQUIRED:
            self.assertIn(("plan.md", name.lower()), wheres)

    def test_chk01_ac19_one_item_rule_per_item_code(self):
        item_rules = [r for r in RULES if r.kind == "item"]
        self.assertEqual(len(item_rules), len(UI_ITEMS) + len(SECURITY_ITEMS))
        for code in UI_ITEMS + SECURITY_ITEMS:
            with self.subTest(code=code):
                item_rule(code)

    def test_chk01_ac14_item_rules_are_skipped_by_added_items_and_other_rules_are_not(self):
        for rule in RULES:
            with self.subTest(rule=rule.id):
                self.assertEqual(rule.skip_added_items, rule.kind == "item")

    def test_chk01_ac9_ui_items_are_skipped_by_no_screen_and_security_items_are_not(self):
        for code in UI_ITEMS:
            self.assertTrue(item_rule(code).skip_no_screen, code)
        for code in SECURITY_ITEMS:
            self.assertFalse(item_rule(code).skip_no_screen, code)

    def test_chk01_ac9_tier_one_section_rules_are_not_skipped_by_no_screen(self):
        for rule in RULES:
            if rule.kind in ("file", "section", "ac-item", "task-role") and rule.tier == 1:
                with self.subTest(rule=rule.id):
                    self.assertFalse(rule.skip_no_screen)

    def test_chk01_ac2_table_rules_are_skipped_by_no_screen(self):
        tables = [r for r in RULES if r.kind == "table"]
        self.assertTrue(tables)
        for rule in tables:
            self.assertTrue(rule.skip_no_screen, rule.id)


class ItemMatcherTests(unittest.TestCase):
    CASES = {
        "REQUESTS": (["requests per load and per retry", "requests per load or retry"], ["requests sent", "per load"]),
        "WRONG_ROLE": (["wrong role", "wrong-role", "what a wrong role user sees"], ["wrongrole", "role"]),
        "HISTORY": (["link history", "push or replace", "link history: push"], ["push", "history", "replace"]),
        "REFRESH": (["refresh", "page refresh"], ["reload", "back"]),
        "BACK_FORWARD": (["back and forward", "forward and back"], ["back", "forward"]),
        "EXPIRED_SESSION": (["expired session or logout", "logout", "expired session"], ["session", "login"]),
        "BACKEND_DOWN": (["backend down", "with the backend down"], ["backend", "down"]),
        "LONGEST_WAIT": (["longest wait before an error", "timeout"], ["wait", "longest"]),
        "NO_GENERIC_FAILURE": (["no generic failure message", "generic"], ["failure", "no message"]),
        "CONCURRENT_REQUESTS": (["concurrent requests (same time)", "same time", "concurrent"], ["requests", "time"]),
        "NORMALISATION": (["normalisation", "input normalisation"], ["normal", "validation"]),
    }

    def test_chk01_ac7_every_item_has_a_matcher_case(self):
        self.assertEqual(set(self.CASES), set(UI_ITEMS) | set(SECURITY_ITEMS))

    def test_chk01_ac5_item_matchers_accept_their_labels(self):
        for code, (good, _) in self.CASES.items():
            for label in good:
                with self.subTest(code=code, label=label):
                    self.assertTrue(label_matches(code, label))

    def test_chk01_ac5_item_matchers_reject_other_labels(self):
        for code, (_, bad) in self.CASES.items():
            for label in bad:
                with self.subTest(code=code, label=label):
                    self.assertFalse(label_matches(code, label))

    def test_chk01_ac5_example_label_from_the_plan_matches_its_own_item(self):
        for code, label in ITEM_LABELS.items():
            with self.subTest(code=code):
                self.assertTrue(label_matches(code, label))

    def test_chk01_ac5_no_example_label_matches_another_item(self):
        for code, label in ITEM_LABELS.items():
            for other in ITEM_LABELS:
                if other != code:
                    with self.subTest(label=label, other=other):
                        self.assertFalse(label_matches(other, label))


class ListRulesTests(unittest.TestCase):
    def run_list(self):
        return run_main(["--list-rules"])

    def parsed(self):
        code, out, err = self.run_list()
        self.assertEqual(code, 0, err)
        lines = [line for line in out.splitlines() if line.strip()]
        matches = [RULE_RE.match(line) for line in lines]
        for line, match in zip(lines, matches):
            self.assertIsNotNone(match, line)
        return lines, matches

    def test_chk01_ac19_list_rules_exits_zero_with_nothing_on_stderr(self):
        code, _, err = self.run_list()
        self.assertEqual(code, 0)
        self.assertEqual(err, "")

    def test_chk01_ac19_list_rules_prints_only_rule_lines_in_the_documented_format(self):
        lines, matches = self.parsed()
        self.assertTrue(lines)
        self.assertTrue(all(matches))
        self.assertTrue(all(line.startswith("RULE ") for line in lines))

    def test_chk01_ac19_one_rule_line_per_registry_row_in_registry_order(self):
        _, matches = self.parsed()
        self.assertEqual([m["id"] for m in matches], [r.id for r in RULES])

    def test_chk01_ac19_rule_line_fields_match_the_registry_row(self):
        _, matches = self.parsed()
        yn = {True: "yes", False: "no"}
        for m, rule in zip(matches, RULES):
            with self.subTest(rule=rule.id):
                self.assertEqual(int(m["tier"]), rule.tier)
                self.assertEqual(m["sns"], yn[rule.skip_no_screen])
                self.assertEqual(m["sai"], yn[rule.skip_added_items])
                self.assertEqual(m["where"], rule.where)
                self.assertEqual(m["source"], rule.source)

    def test_chk01_ac19_listing_names_every_code_and_item(self):
        _, out, _ = self.run_list()
        for code in FILE_CODES + OTHER_CODES + UI_ITEMS + SECURITY_ITEMS:
            with self.subTest(code=code):
                self.assertIn(code, out)

    def test_chk01_ac19_listing_names_every_required_section(self):
        _, out, _ = self.run_list()
        for name in SPEC_REQUIRED + PLAN_REQUIRED:
            with self.subTest(section=name):
                self.assertIn(name.lower(), out.lower())

    def test_chk01_ac19_listing_is_identical_on_every_run(self):
        self.assertEqual(self.run_list(), self.run_list())


class ReadmeTests(unittest.TestCase):
    def verifier_only_section(self):
        readme = (TOOL_DIR / "README.md").read_text(encoding="utf-8")
        match = re.search(r"^(#{1,6})[ \t]+verifier only[ \t]*:?[ \t]*$", readme, re.I | re.M)
        self.assertIsNotNone(match, 'README has no "Verifier only" heading')
        rest = readme[match.end() :]
        level = len(match.group(1))
        end = re.search(rf"^#{{1,{level}}}[ \t]+\S", rest, re.M)
        return (rest[: end.start()] if end else rest).lower()

    def test_chk01_ac20_readme_has_a_verifier_only_section(self):
        self.assertTrue(self.verifier_only_section().strip())

    def test_chk01_ac20_verifier_only_section_names_what_cannot_be_checked(self):
        text = self.verifier_only_section()
        for word in ("quality", "user stor", "contract", "copied", "sensible"):
            with self.subTest(word=word):
                self.assertIn(word, text)


if __name__ == "__main__":
    unittest.main()

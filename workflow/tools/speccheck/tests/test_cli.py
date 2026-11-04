import subprocess
import sys
import unittest
from pathlib import Path

from helpers import (
    FAIL_RE,
    OMIT,
    SPEC_ID,
    SUMMARY_RE,
    SpecCase,
    format_finding,
    plan_text,
    run_main,
    spec_text,
)

TOOL_DIR = Path(__file__).resolve().parents[1]
REPO_SPECS = Path(__file__).resolve().parents[3] / "specs"
WAIVER_NAME = "speccheck-waivers.txt"


def lines_of(text):
    return [line for line in text.splitlines() if line.strip()]


def broken_spec():
    return spec_text(omit=["Goal"])


class CliCase(SpecCase):
    def run_cli(self, *argv, specs_dir=True):
        args = ["--specs-dir", self.specs] if specs_dir else []
        return run_main(args + list(argv))

    def assert_usage_error(self, code, out, err):
        self.assertEqual(code, 2, err)
        self.assertEqual(out, "")
        self.assertTrue(err.strip())


class OutputFormatTests(CliCase):
    def test_chk01_ac18_passing_spec_prints_ok_and_summary(self):
        folder = self.write()
        code, out, err = self.run_cli(folder)
        self.assertEqual(code, 0)
        self.assertEqual(err, "")
        self.assertEqual(lines_of(out), [f"OK {SPEC_ID}", "speccheck: 1 checked, 0 failed, 0 waived"])

    def test_chk01_ac18_failing_spec_prints_fail_lines_in_the_documented_format(self):
        from speccheck.rules import check_spec_dir

        folder = self.write(spec=broken_spec(), tasks=OMIT)
        expected = [format_finding(f) for f in check_spec_dir(folder, {})]
        self.assertGreaterEqual(len(expected), 2)
        code, out, _ = self.run_cli(folder)
        self.assertEqual(code, 1)
        lines = lines_of(out)
        self.assertEqual(lines[:-1], expected)
        for line in lines[:-1]:
            self.assertRegex(line, FAIL_RE)

    def test_chk01_ac18_exact_line_for_a_missing_file(self):
        folder = self.write(tasks=OMIT)
        _, out, _ = self.run_cli(folder)
        self.assertIn(f'FAIL {SPEC_ID} tasks.md: section "(file)": tasks.md not found [TASKS_MISSING]', lines_of(out))

    def test_chk01_ac18_exact_line_for_a_missing_section(self):
        folder = self.write(spec=spec_text(omit=["Goal"]))
        _, out, _ = self.run_cli(folder)
        self.assertIn(f'FAIL {SPEC_ID} spec.md: section "(file)": no "Goal" section [SECTION_MISSING]', lines_of(out))

    def test_chk01_ac18_last_line_is_the_summary_with_counts(self):
        self.write("A-01")
        self.write("B-01", spec=broken_spec())
        self.write("C-01", plan=OMIT)
        code, out, _ = self.run_cli("--all")
        self.assertEqual(code, 1)
        match = SUMMARY_RE.match(lines_of(out)[-1])
        self.assertIsNotNone(match, out)
        self.assertEqual(match.groups(), ("3", "2", "0"))

    def test_chk01_ac18_specs_are_sorted_by_id_whatever_the_argument_order(self):
        folders = [self.write("C-01"), self.write("A-01", spec=broken_spec()), self.write("B-01")]
        code, out, _ = self.run_cli(*folders)
        self.assertEqual(code, 1)
        ids = []
        for line in lines_of(out)[:-1]:
            ids.append(line.split()[1].rstrip(":"))
        self.assertEqual(ids, sorted(ids))
        self.assertEqual(ids[0], "A-01")
        self.assertEqual(ids[-1], "C-01")

    def test_chk01_ac18_fail_lines_within_a_spec_follow_the_order_of_the_findings(self):
        from speccheck.rules import check_spec_dir

        spec = spec_text(omit=["Out of scope"], bodies={"Goal": "TBD here", "Behaviour": "more TODO"})
        folder = self.write(spec=spec, plan=plan_text(omit=["Test plan"]))
        findings = check_spec_dir(folder, {})
        _, out, _ = self.run_cli(folder)
        self.assertEqual(lines_of(out)[:-1], [format_finding(f) for f in findings])

    def test_chk01_ac18_fail_lines_are_ordered_by_file_then_position(self):
        spec = spec_text(omit=["Out of scope"], bodies={"Goal": "TBD here", "Behaviour": "more TODO"})
        folder = self.write(spec=spec, plan=plan_text(omit=["Test plan"]))
        _, out, _ = self.run_cli(folder)
        files = [FAIL_RE.match(line).group(2) for line in lines_of(out)[:-1]]
        self.assertEqual(files, sorted(files))

    def test_chk01_ac18_output_is_identical_on_repeated_runs(self):
        folder = self.write(spec=broken_spec())
        self.assertEqual(self.run_cli(folder), self.run_cli(folder))

    def test_chk01_ac23_a_run_writes_no_files(self):
        folder = self.write(spec=broken_spec())

        def snapshot():
            return {p: (p.read_bytes() if p.is_file() else None) for p in self.root.rglob("*")}

        before = snapshot()
        self.run_cli(folder)
        self.run_cli("--all")
        self.assertEqual(snapshot(), before)

    def test_chk01_ac23_binary_spec_files_do_not_crash_the_cli(self):
        folder = self.write(spec=bytes(range(256)) * 20)
        code, out, _ = self.run_cli(folder)
        self.assertEqual(code, 1)
        self.assertTrue(SUMMARY_RE.match(lines_of(out)[-1]))


class DiscoveryTests(CliCase):
    def test_chk01_ac16_all_checks_every_subfolder_and_ignores_plain_files(self):
        self.write("A-01")
        self.write("B-01")
        (self.specs / "README.md").write_text("# index\n", encoding="utf-8")
        (self.specs / WAIVER_NAME).write_text("# no waivers yet\n", encoding="utf-8")
        code, out, _ = self.run_cli("--all")
        self.assertEqual(code, 0)
        self.assertEqual(lines_of(out), ["OK A-01", "OK B-01", "speccheck: 2 checked, 0 failed, 0 waived"])

    def test_chk01_ac16_all_on_an_empty_specs_dir_checks_nothing(self):
        code, out, _ = self.run_cli("--all")
        self.assertEqual(code, 0)
        self.assertEqual(lines_of(out), ["speccheck: 0 checked, 0 failed, 0 waived"])

    def test_chk01_ac16_specs_dir_option_overrides_the_default(self):
        self.write("ONLY-01")
        code, out, _ = run_main(["--all", "--specs-dir", self.specs])
        self.assertEqual(code, 0)
        self.assertIn("OK ONLY-01", lines_of(out))
        self.assertNotIn("CHK-01", out)

    def test_chk01_ac16_explicit_folders_are_checked_wherever_they_are(self):
        elsewhere = self.root / "elsewhere"
        elsewhere.mkdir()
        folder = self.write()
        moved = elsewhere / "MOVED-01"
        folder.rename(moved)
        code, out, _ = self.run_cli(moved)
        self.assertEqual(code, 0)
        self.assertIn("OK MOVED-01", lines_of(out))

    def test_chk01_ac16_options_may_follow_the_folders(self):
        folder = self.write()
        code, out, _ = run_main([folder, "--specs-dir", self.specs])
        self.assertEqual(code, 0, out)

    def test_chk01_ac16_missing_default_waiver_file_means_no_waivers(self):
        self.write()
        code, out, err = self.run_cli("--all")
        self.assertEqual(code, 0, err)
        self.assertNotIn("WAIVED", out)

    def test_chk01_ac16_default_waiver_file_in_the_specs_dir_is_used(self):
        self.write(spec=broken_spec())
        (self.specs / WAIVER_NAME).write_text(f"{SPEC_ID} | all | predates the rule\n", encoding="utf-8")
        code, out, _ = self.run_cli("--all")
        self.assertEqual(code, 0)
        self.assertIn(f"WAIVED {SPEC_ID} (all): predates the rule", lines_of(out))

    def test_chk01_ac16_default_waiver_file_follows_the_specs_dir_for_explicit_folders(self):
        folder = self.write(spec=broken_spec())
        (self.specs / WAIVER_NAME).write_text(f"{SPEC_ID} | all | predates the rule\n", encoding="utf-8")
        code, out, _ = self.run_cli(folder)
        self.assertEqual(code, 0)
        self.assertIn(f"WAIVED {SPEC_ID} (all): predates the rule", lines_of(out))

    def test_chk01_ac16_waivers_option_overrides_the_default_file(self):
        self.write(spec=broken_spec())
        (self.specs / WAIVER_NAME).write_text(f"{SPEC_ID} | all | predates the rule\n", encoding="utf-8")
        other = self.waiver_file("OTHER-01 | all | unrelated\n")
        code, out, _ = self.run_cli("--all", "--waivers", other)
        self.assertEqual(code, 1)
        self.assertNotIn("WAIVED", out)

    def test_chk01_ac16_waivers_option_can_point_outside_the_specs_dir(self):
        folder = self.write(spec=broken_spec())
        other = self.waiver_file(f"{SPEC_ID} | all | predates the rule\n")
        code, out, _ = self.run_cli(folder, "--waivers", other)
        self.assertEqual(code, 0)
        self.assertIn(f"WAIVED {SPEC_ID} (all): predates the rule", lines_of(out))

    def test_chk01_ac16_missing_explicit_waiver_file_exits_2(self):
        self.write()
        result = self.run_cli("--all", "--waivers", self.root / "absent.txt")
        self.assert_usage_error(*result)


class WaiverOutputTests(CliCase):
    def test_chk01_ac14_scope_all_prints_waived_and_counts_it_as_waived_not_checked(self):
        self.write(spec=broken_spec())
        self.write("OK-01")
        (self.specs / WAIVER_NAME).write_text(f"{SPEC_ID} | all | predates the rule\n", encoding="utf-8")
        code, out, _ = self.run_cli("--all")
        self.assertEqual(code, 0)
        self.assertEqual(
            lines_of(out),
            ["OK OK-01", f"WAIVED {SPEC_ID} (all): predates the rule", "speccheck: 1 checked, 0 failed, 1 waived"],
        )

    def test_chk01_ac14_scope_all_produces_no_fail_lines_for_that_spec(self):
        self.write(spec=OMIT, plan=OMIT, tasks=OMIT)
        (self.specs / WAIVER_NAME).write_text(f"{SPEC_ID} | all | predates the rule\n", encoding="utf-8")
        _, out, _ = self.run_cli("--all")
        self.assertNotIn("FAIL", out)

    def test_chk01_ac14_added_items_prints_waived_then_the_normal_ok_line(self):
        self.write(plan=plan_text(bodies={"UI contract": "Nothing listed."}))
        (self.specs / WAIVER_NAME).write_text(f"{SPEC_ID} | added-items | no item labels yet\n", encoding="utf-8")
        code, out, _ = self.run_cli("--all")
        self.assertEqual(code, 0)
        self.assertEqual(
            lines_of(out),
            [
                f"WAIVED {SPEC_ID} (added-items): no item labels yet",
                f"OK {SPEC_ID}",
                "speccheck: 1 checked, 0 failed, 0 waived",
            ],
        )

    def test_chk01_ac14_added_items_still_fails_for_other_findings(self):
        self.write(spec=broken_spec())
        (self.specs / WAIVER_NAME).write_text(f"{SPEC_ID} | added-items | no item labels yet\n", encoding="utf-8")
        code, out, _ = self.run_cli("--all")
        self.assertEqual(code, 1)
        lines = lines_of(out)
        self.assertEqual(lines[0], f"WAIVED {SPEC_ID} (added-items): no item labels yet")
        self.assertRegex(lines[1], FAIL_RE)
        self.assertEqual(lines[-1], "speccheck: 1 checked, 1 failed, 0 waived")

    def test_chk01_ac15_unknown_waiver_id_under_all_warns_without_changing_exit_code(self):
        self.write()
        (self.specs / WAIVER_NAME).write_text("GHOST-01 | all | old spec\n", encoding="utf-8")
        code, out, _ = self.run_cli("--all")
        self.assertEqual(code, 0)
        lines = lines_of(out)
        self.assertEqual(
            lines,
            [
                f"OK {SPEC_ID}",
                "WARN GHOST-01: waiver for a spec folder that does not exist [WAIVER_UNKNOWN_ID]",
                "speccheck: 1 checked, 0 failed, 0 waived",
            ],
        )

    def test_chk01_ac15_unknown_waiver_id_does_not_hide_a_failure(self):
        self.write(spec=broken_spec())
        (self.specs / WAIVER_NAME).write_text("GHOST-01 | all | old spec\n", encoding="utf-8")
        code, out, _ = self.run_cli("--all")
        self.assertEqual(code, 1)
        self.assertIn("[WAIVER_UNKNOWN_ID]", out)

    def test_chk01_ac15_unknown_waiver_id_is_not_reported_for_explicit_folders(self):
        folder = self.write()
        (self.specs / WAIVER_NAME).write_text("GHOST-01 | all | old spec\n", encoding="utf-8")
        code, out, _ = self.run_cli(folder)
        self.assertEqual(code, 0)
        self.assertNotIn("WAIVER_UNKNOWN_ID", out)

    def test_chk01_ac15_malformed_waiver_line_exits_2_naming_code_and_line(self):
        self.write()
        bad = self.waiver_file("# comment\n\nSTU-01 | all\n")
        code, out, err = self.run_cli("--all", "--waivers", bad)
        self.assert_usage_error(code, out, err)
        self.assertIn("WAIVER_BAD_LINE", err)
        self.assertRegex(err, r"line 3\b")
        self.assertIn("speccheck: error:", err)

    def test_chk01_ac15_unknown_scope_exits_2(self):
        self.write()
        bad = self.waiver_file("STU-01 | partial | reason\n")
        code, out, err = self.run_cli("--all", "--waivers", bad)
        self.assert_usage_error(code, out, err)
        self.assertIn("WAIVER_BAD_LINE", err)
        self.assertRegex(err, r"line 1\b")

    def test_chk01_ac15_empty_reason_exits_2(self):
        self.write()
        bad = self.waiver_file("STU-01 | all |\n")
        code, out, err = self.run_cli("--all", "--waivers", bad)
        self.assert_usage_error(code, out, err)
        self.assertIn("WAIVER_BAD_LINE", err)

    def test_chk01_ac15_duplicate_id_exits_2_at_the_second_line(self):
        self.write()
        bad = self.waiver_file("STU-01 | all | a\nSTU-01 | added-items | b\n")
        code, out, err = self.run_cli("--all", "--waivers", bad)
        self.assert_usage_error(code, out, err)
        self.assertIn("WAIVER_BAD_LINE", err)
        self.assertRegex(err, r"line 2\b")

    def test_chk01_ac15_bad_default_waiver_file_exits_2(self):
        self.write()
        (self.specs / WAIVER_NAME).write_text("STU-01 | all\n", encoding="utf-8")
        self.assert_usage_error(*self.run_cli("--all"))

    def test_chk01_ac15_comments_and_blank_lines_are_ignored(self):
        self.write()
        waivers = self.waiver_file("# a comment\n\n   # another\n\n")
        code, out, _ = self.run_cli("--all", "--waivers", waivers)
        self.assertEqual(code, 0)
        self.assertNotIn("WAIVED", out)


class ExitCodeTests(CliCase):
    def test_chk01_ac17_exit_0_when_all_pass(self):
        self.write("A-01")
        self.write("B-01")
        self.assertEqual(self.run_cli("--all")[0], 0)

    def test_chk01_ac17_exit_0_when_everything_is_waived(self):
        self.write(spec=broken_spec())
        (self.specs / WAIVER_NAME).write_text(f"{SPEC_ID} | all | predates the rule\n", encoding="utf-8")
        self.assertEqual(self.run_cli("--all")[0], 0)

    def test_chk01_ac17_exit_1_when_any_spec_has_a_finding(self):
        self.write("A-01")
        self.write("B-01", spec=broken_spec())
        self.assertEqual(self.run_cli("--all")[0], 1)

    def test_chk01_ac17_no_arguments_exits_2(self):
        code, out, err = run_main([])
        self.assert_usage_error(code, out, err)

    def test_chk01_ac17_all_combined_with_folders_exits_2(self):
        folder = self.write()
        self.assert_usage_error(*self.run_cli("--all", folder))

    def test_chk01_ac17_unknown_option_exits_2(self):
        folder = self.write()
        self.assert_usage_error(*self.run_cli("--bogus", folder))

    def test_chk01_ac17_folder_that_does_not_exist_exits_2(self):
        result = self.run_cli(self.specs / "NOPE-01")
        self.assert_usage_error(*result)
        self.assertIn("speccheck: error:", result[2])

    def test_chk01_ac17_path_that_is_a_file_exits_2(self):
        (self.specs / "README.md").write_text("# index\n", encoding="utf-8")
        self.assert_usage_error(*self.run_cli(self.specs / "README.md"))

    def test_chk01_ac17_one_missing_folder_among_valid_ones_exits_2_without_partial_output(self):
        folder = self.write()
        self.assert_usage_error(*self.run_cli(folder, self.specs / "NOPE-01"))

    def test_chk01_ac17_all_with_a_missing_specs_dir_exits_2(self):
        self.assert_usage_error(*run_main(["--all", "--specs-dir", self.root / "nowhere"]))

    def test_chk01_ac17_specs_dir_without_a_value_exits_2(self):
        self.assert_usage_error(*run_main(["--all", "--specs-dir"]))

    def test_chk01_ac19_list_rules_combined_with_folders_exits_2(self):
        folder = self.write()
        self.assert_usage_error(*run_main(["--list-rules", folder]))

    def test_chk01_ac19_list_rules_combined_with_all_exits_2(self):
        self.assert_usage_error(*self.run_cli("--list-rules", "--all"))

    def test_chk01_ac17_spec_text_that_looks_like_options_or_commands_is_only_read(self):
        marker = self.root / "pwned.txt"
        evil = spec_text(bodies={"Goal": f"--all; echo x > {marker.as_posix()}\n$(touch {marker.as_posix()})"})
        folder = self.write("WEIRD-01", spec=evil)
        code, _, _ = self.run_cli(folder)
        self.assertIn(code, (0, 1))
        self.assertFalse(marker.exists())


class RepoLevelTests(unittest.TestCase):
    """Run against this repository's real specs; meaningful once the shipped waiver file exists."""

    def test_chk01_ac21_checker_passes_its_own_spec(self):
        code, out, err = run_main([REPO_SPECS / "CHK-01"])
        self.assertEqual(code, 0, out + err)
        self.assertIn("OK CHK-01", lines_of(out))

    def test_chk01_ac22_all_on_the_real_specs_dir_exits_0(self):
        code, out, err = run_main(["--all", "--specs-dir", REPO_SPECS])
        self.assertEqual(code, 0, out + err)

    def test_chk01_ac22_all_with_the_default_specs_dir_exits_0(self):
        code, out, err = run_main(["--all"])
        self.assertEqual(code, 0, out + err)
        self.assertNotIn("WAIVER_UNKNOWN_ID", out)
        self.assertRegex(lines_of(out)[-1], SUMMARY_RE)

    def test_chk01_ac22_shipped_waiver_file_exists_is_valid_and_does_not_list_chk01(self):
        from speccheck.waivers import load_waivers

        path = REPO_SPECS / WAIVER_NAME
        self.assertTrue(path.is_file(), "workflow/specs/speccheck-waivers.txt is missing")
        loaded = load_waivers(path)
        self.assertNotIn("CHK-01", loaded)
        for spec_id, waiver in loaded.items():
            with self.subTest(spec_id=spec_id):
                self.assertTrue((REPO_SPECS / spec_id).is_dir(), "waiver for a folder that does not exist")
                self.assertIn(waiver.scope, ("all", "added-items"))
                self.assertTrue(waiver.reason)

    def run_module(self, *args):
        return subprocess.run(
            [sys.executable, "-m", "speccheck", *args],
            cwd=TOOL_DIR,
            capture_output=True,
            text=True,
            timeout=300,
        )

    def test_chk01_ac21_python_dash_m_speccheck_passes_its_own_spec(self):
        result = self.run_module(str(REPO_SPECS / "CHK-01"))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_chk01_ac22_python_dash_m_speccheck_all_exits_0(self):
        result = self.run_module("--all")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertRegex(lines_of(result.stdout)[-1], SUMMARY_RE)

    def test_chk01_ac17_python_dash_m_speccheck_without_arguments_exits_2(self):
        result = self.run_module()
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")

    def test_chk01_ac19_python_dash_m_speccheck_list_rules_exits_0(self):
        result = self.run_module("--list-rules")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(lines_of(result.stdout))
        self.assertTrue(all(line.startswith("RULE ") for line in lines_of(result.stdout)))


if __name__ == "__main__":
    unittest.main()

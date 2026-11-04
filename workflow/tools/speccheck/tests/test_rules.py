import socket
import time
import unittest
from unittest import mock

from helpers import (
    CONTRACT_HEADING,
    ITEM_LABELS,
    OMIT,
    PLAN_REQUIRED,
    ROLES,
    SECURITY_HEADING,
    SECURITY_ITEMS,
    SPEC_ID,
    SPEC_REQUIRED,
    UI_HEADING,
    UI_ITEMS,
    UI_TABLE,
    SpecCase,
    codes,
    item_line,
    line_of,
    plan_text,
    replace_once,
    security_body,
    spec_text,
    tasks_text,
    ui_body,
    with_code,
)

PLACEHOLDER_SAMPLES = ("TBD", "TODO", "TBC", "FIXME", "XXX", "???", "<describe this>")


def others(code, pool=UI_ITEMS):
    return [c for c in pool if c != code]


class BaselineTests(SpecCase):
    def test_chk01_ac21_complete_screen_spec_passes(self):
        self.assertEqual(self.check(), [])

    def test_chk01_ac9_complete_no_screen_spec_passes(self):
        findings = self.check(spec=spec_text(screen=False), plan=plan_text(screen=False))
        self.assertEqual(findings, [])

    def test_chk01_ac18_finding_fields_are_populated(self):
        findings = self.check(spec=spec_text(omit=["Goal"]))
        (finding,) = findings
        self.assertEqual(finding.spec_id, SPEC_ID)
        self.assertEqual(finding.file, "spec.md")
        self.assertEqual(finding.heading, "(file)")
        self.assertEqual(finding.code, "SECTION_MISSING")

    def test_chk01_ac18_same_input_gives_identical_findings(self):
        spec = spec_text(omit=["Goal"], bodies={"Behaviour": "TBD"})
        self.assertEqual(self.check(spec=spec), self.check(spec=spec))

    def test_chk01_ac18_findings_are_sorted_by_file_then_line(self):
        spec = spec_text(
            omit=["Out of scope"],
            bodies={"Goal": "TBD here", "Behaviour": "more TODO text", UI_HEADING: UI_TABLE + "\n| Third | |"},
        )
        plan = plan_text(omit=["Test plan"], bodies={"Data model": "FIXME"})
        tasks = tasks_text(row="| 1 | Build it | nobody | none | TBC |")
        findings = self.check(spec=spec, plan=plan, tasks=tasks)
        self.assertGreaterEqual(len(findings), 5)
        keys = [(f.file, f.line) for f in findings]
        self.assertEqual(keys, sorted(keys))


class PlaceholderTests(SpecCase):
    def placeholder_findings(self, **kwargs):
        return with_code(self.check(**kwargs), "PLACEHOLDER")

    def test_chk01_ac1_placeholder_tbd(self):
        spec = spec_text(bodies={"Goal": "Show the page TBD later."})
        (finding,) = self.placeholder_findings(spec=spec)
        self.assertEqual(finding.file, "spec.md")
        self.assertIn("TBD", finding.message)
        self.assertRegex(finding.message, rf"line {line_of(spec, 'TBD')}\b")

    def test_chk01_ac1_placeholder_each_word_and_slot_in_a_section_line(self):
        for sample in PLACEHOLDER_SAMPLES:
            with self.subTest(sample=sample):
                spec = spec_text(bodies={"Goal": f"Show the page {sample} later."})
                findings = self.check(spec=spec)
                self.assertEqual(codes(findings), ["PLACEHOLDER"])
                self.assertIn(sample.lower(), findings[0].message.lower())
                self.assertRegex(findings[0].message, rf"line {line_of(spec, sample)}\b")

    def test_chk01_ac1_placeholder_is_case_insensitive(self):
        for sample in ("tbd", "Todo", "fixMe", "tbc", "xXx"):
            with self.subTest(sample=sample):
                spec = spec_text(bodies={"Goal": f"Show the page {sample} later."})
                self.assertEqual(codes(self.check(spec=spec)), ["PLACEHOLDER"])

    def test_chk01_ac1_placeholder_in_table_cell(self):
        for sample in PLACEHOLDER_SAMPLES:
            with self.subTest(sample=sample):
                spec = spec_text(bodies={UI_HEADING: UI_TABLE + f"\n| Retry | {sample} |"})
                findings = self.check(spec=spec)
                self.assertEqual(codes(findings), ["PLACEHOLDER"])
                self.assertEqual(findings[0].file, "spec.md")

    def test_chk01_ac1_placeholder_in_item_content_is_reported_once(self):
        for sample in PLACEHOLDER_SAMPLES:
            with self.subTest(sample=sample):
                body = ui_body(others("REFRESH")) + "\n" + item_line("REFRESH", f"reloads {sample}")
                findings = self.check(plan=plan_text(bodies={CONTRACT_HEADING: body}))
                self.assertEqual(codes(findings), ["PLACEHOLDER"])
                self.assertEqual(findings[0].file, "plan.md")

    def test_chk01_ac1_placeholder_in_no_screen_reason(self):
        for sample in PLACEHOLDER_SAMPLES:
            with self.subTest(sample=sample):
                spec = spec_text(no_screen=f"No screen: {sample}", screen=False)
                findings = self.check(spec=spec, plan=plan_text(screen=False))
                self.assertIn("PLACEHOLDER", codes(findings))
                found = with_code(findings, "PLACEHOLDER")[0]
                self.assertEqual(found.file, "spec.md")
                self.assertEqual(found.heading, "(file)")

    def test_chk01_ac1_placeholder_in_first_heading_line_of_each_file(self):
        cases = {
            "spec": ("spec.md", {"spec": spec_text(title="Spec: <feature id> Demo")}),
            "plan": ("plan.md", {"plan": plan_text(title="Plan: <feature id> Demo")}),
            "tasks": ("tasks.md", {"tasks": tasks_text(title="Tasks: <feature id> Demo")}),
        }
        for name, (filename, kwargs) in cases.items():
            with self.subTest(file=name):
                findings = with_code(self.check(**kwargs), "PLACEHOLDER")
                self.assertEqual(len(findings), 1)
                self.assertEqual(findings[0].file, filename)
                self.assertEqual(findings[0].heading, "(file)")
                self.assertRegex(findings[0].message, r"line 1\b")

    def test_chk01_ac1_placeholder_in_tasks_md_is_found(self):
        findings = self.check(tasks=tasks_text(row="| 1 | Build TBD | developer | none | todo |"))
        self.assertEqual(codes(findings), ["PLACEHOLDER"])
        self.assertEqual(findings[0].file, "tasks.md")

    def test_chk01_ac1_two_placeholders_on_one_line_give_one_finding_naming_the_first(self):
        spec = spec_text(bodies={"Goal": "Show TBD and TODO here."})
        (finding,) = self.placeholder_findings(spec=spec)
        self.assertIn("TBD", finding.message)

    def test_chk01_ac1_each_placeholder_line_gets_its_own_finding(self):
        spec = spec_text(bodies={"Goal": "first TBD\nsecond TODO"})
        self.assertEqual(len(self.placeholder_findings(spec=spec)), 2)

    def test_chk01_ac1_backtick_code_span_is_not_a_placeholder(self):
        for sample in ("TBD", "TODO", "TBC", "FIXME", "XXX", "???", "<slot>"):
            with self.subTest(sample=sample):
                spec = spec_text(bodies={"Goal": f"Write `{sample}` to mark gaps."})
                self.assertEqual(self.check(spec=spec), [])

    def test_chk01_ac1_fenced_block_is_not_scanned(self):
        goal = "Example:\n```\nTBD\nTODO <slot> ???\n```\nDone."
        self.assertEqual(self.check(spec=spec_text(bodies={"Goal": goal})), [])

    def test_chk01_ac1_tilde_fenced_block_is_not_scanned(self):
        goal = "Example:\n~~~\nTBD\n~~~\nDone."
        self.assertEqual(self.check(spec=spec_text(bodies={"Goal": goal})), [])

    def test_chk01_ac1_word_inside_longer_word_is_not_a_placeholder(self):
        spec = spec_text(bodies={"Goal": "Keep TODOS lists and TBDs and XXXL sizes."})
        self.assertEqual(self.check(spec=spec), [])

    def test_chk01_ac1_br_tag_is_not_a_slot(self):
        spec = spec_text(bodies={"Goal": "line one<br>line two<br/>end"})
        self.assertEqual(self.check(spec=spec), [])

    def test_chk01_ac1_todo_status_in_tasks_md_is_not_a_placeholder(self):
        for status in ("todo", "TODO", "Todo"):
            with self.subTest(status=status):
                tasks = tasks_text(row=f"| 1 | Build the page | developer | none | {status} |")
                self.assertEqual(self.check(tasks=tasks), [])

    def test_chk01_ac12_decisions_placeholder_is_found(self):
        plan = plan_text() + "\n## Decisions\n- Pick the store TBD\n"
        findings = self.check(plan=plan)
        self.assertEqual(codes(findings), ["PLACEHOLDER"])
        self.assertEqual(findings[0].file, "plan.md")

    def test_chk01_ac12_clean_decisions_section_is_fine_and_absent_one_is_fine(self):
        self.assertEqual(self.check(plan=plan_text() + "\n## Decisions\n- Use the file store.\n"), [])
        self.assertEqual(self.check(plan=plan_text()), [])


class UiScreenRuleTests(SpecCase):
    def test_chk01_ac2_missing_ui_section_gives_ui_section_missing(self):
        findings = self.check(spec=spec_text(omit=[UI_HEADING]))
        self.assertEqual(codes(findings), ["UI_SECTION_MISSING"])
        self.assertEqual((findings[0].file, findings[0].heading), ("spec.md", "(file)"))

    def test_chk01_ac2_header_and_separator_only_gives_ui_table_empty(self):
        spec = spec_text(bodies={UI_HEADING: "| State | Copy |\n|---|---|"})
        findings = self.check(spec=spec)
        self.assertEqual(codes(findings), ["UI_TABLE_EMPTY"])
        self.assertEqual((findings[0].file, findings[0].heading), ("spec.md", UI_HEADING))

    def test_chk01_ac2_section_with_prose_and_no_table_gives_ui_table_empty(self):
        spec = spec_text(bodies={UI_HEADING: "The page loads and shows text."})
        self.assertEqual(codes(self.check(spec=spec)), ["UI_TABLE_EMPTY"])

    def test_chk01_ac2_empty_ui_section_is_reported(self):
        spec = spec_text(bodies={UI_HEADING: ""})
        self.assertIn("UI_TABLE_EMPTY", codes(self.check(spec=spec)))

    def test_chk01_ac2_ui_heading_matches_case_insensitively(self):
        spec = replace_once(spec_text(), f"## {UI_HEADING}", "### UI STATES AND COPY")
        self.assertEqual(self.check(spec=spec), [])

    def test_chk01_ac3_empty_cell_names_row_number_and_column_header(self):
        spec = spec_text(bodies={UI_HEADING: "| State | Copy |\n|---|---|\n| Loading | Loading |\n| Error |  |"})
        findings = self.check(spec=spec)
        self.assertEqual(codes(findings), ["UI_TABLE_CELL_EMPTY"])
        message = findings[0].message
        self.assertIn("2", message)
        self.assertIn("Copy", message)
        self.assertEqual((findings[0].file, findings[0].heading), ("spec.md", UI_HEADING))

    def test_chk01_ac3_empty_first_column_cell_names_that_column(self):
        spec = spec_text(bodies={UI_HEADING: "| State | Copy |\n|---|---|\n|  | Loading |"})
        findings = self.check(spec=spec)
        self.assertEqual(codes(findings), ["UI_TABLE_CELL_EMPTY"])
        self.assertIn("State", findings[0].message)
        self.assertIn("1", findings[0].message)

    def test_chk01_ac3_every_empty_cell_is_reported(self):
        spec = spec_text(bodies={UI_HEADING: "| State | Copy |\n|---|---|\n|  |  |\n| A |  |"})
        self.assertEqual(len(with_code(self.check(spec=spec), "UI_TABLE_CELL_EMPTY")), 3)

    def test_chk01_ac3_not_applicable_cell_counts_as_content(self):
        spec = spec_text(bodies={UI_HEADING: "| State | Copy |\n|---|---|\n| Loading | not applicable |"})
        self.assertEqual(self.check(spec=spec), [])

    def test_chk01_ac4_missing_ui_contract_gives_ui_contract_missing(self):
        plan = plan_text(omit=[CONTRACT_HEADING])
        spec = spec_text(bodies={UI_HEADING: UI_TABLE + "\n\n" + ui_body()})
        findings = self.check(spec=spec, plan=plan)
        self.assertEqual(codes(findings), ["UI_CONTRACT_MISSING"])
        self.assertEqual((findings[0].file, findings[0].heading), ("plan.md", "(file)"))

    def test_chk01_ac4_ui_contract_heading_with_no_text_gives_ui_contract_empty(self):
        spec = spec_text(bodies={UI_HEADING: UI_TABLE + "\n\n" + ui_body()})
        findings = self.check(spec=spec, plan=plan_text(bodies={CONTRACT_HEADING: ""}))
        self.assertEqual(codes(findings), ["UI_CONTRACT_EMPTY"])
        self.assertEqual((findings[0].file, findings[0].heading), ("plan.md", CONTRACT_HEADING))

    def test_chk01_ac4_missing_contract_with_items_absent_also_reports_items(self):
        findings = self.check(plan=plan_text(omit=[CONTRACT_HEADING]))
        self.assertIn("UI_CONTRACT_MISSING", codes(findings))
        self.assertEqual(len(with_code(findings, "ITEM_MISSING")), len(UI_ITEMS))


class ItemTests(SpecCase):
    def plan_with(self, body):
        return plan_text(bodies={CONTRACT_HEADING: body})

    def spec_with_security(self, body):
        return spec_text(bodies={SECURITY_HEADING: body})

    def test_chk01_ac5_ui_item_missing_names_item_and_accepted_labels(self):
        for code in UI_ITEMS:
            with self.subTest(code=code):
                findings = self.check(plan=self.plan_with(ui_body(others(code))))
                self.assertEqual(codes(findings), ["ITEM_MISSING"])
                finding = findings[0]
                self.assertEqual((finding.file, finding.heading), ("plan.md", CONTRACT_HEADING))
                self.assertIn(code, finding.message)
                self.assertIn("label", finding.message.lower())

    def test_chk01_ac5_ui_item_label_without_content_gives_item_empty(self):
        for code in UI_ITEMS:
            with self.subTest(code=code):
                body = ui_body(others(code)) + f"\n\n- {ITEM_LABELS[code]}:"
                findings = self.check(plan=self.plan_with(body))
                self.assertEqual(codes(findings), ["ITEM_EMPTY"])
                self.assertIn(code, findings[0].message)
                self.assertEqual(findings[0].file, "plan.md")

    def test_chk01_ac5_ui_item_with_placeholder_content_gives_one_placeholder(self):
        for code in UI_ITEMS:
            with self.subTest(code=code):
                body = ui_body(others(code)) + "\n" + item_line(code, "TBD")
                findings = self.check(plan=self.plan_with(body))
                self.assertEqual(codes(findings), ["PLACEHOLDER"])
                self.assertIn("TBD", findings[0].message)

    def test_chk01_ac5_ui_item_with_content_passes(self):
        for code in UI_ITEMS:
            with self.subTest(code=code):
                body = ui_body(others(code)) + "\n" + item_line(code, "one request per load, none on retry")
                self.assertEqual(self.check(plan=self.plan_with(body)), [])

    def test_chk01_ac5_ui_item_not_applicable_with_reason_passes(self):
        body = ui_body(others("HISTORY")) + "\n" + item_line("HISTORY", "not applicable: the page has no links")
        self.assertEqual(self.check(plan=self.plan_with(body)), [])

    def test_chk01_ac6_ui_item_in_spec_ui_section_only_passes(self):
        for code in UI_ITEMS:
            with self.subTest(code=code):
                spec = spec_text(bodies={UI_HEADING: UI_TABLE + "\n\n" + item_line(code)})
                plan = self.plan_with(ui_body(others(code)))
                self.assertEqual(self.check(spec=spec, plan=plan), [])

    def test_chk01_ac6_all_items_in_spec_ui_section_with_prose_only_contract_passes(self):
        spec = spec_text(bodies={UI_HEADING: UI_TABLE + "\n\n" + ui_body()})
        self.assertEqual(self.check(spec=spec, plan=self.plan_with("See the UI states section of the spec.")), [])

    def test_chk01_ac6_ui_item_in_plan_ui_contract_only_passes(self):
        self.assertEqual(self.check(), [])

    def test_chk01_ac6_ui_item_under_another_plan_heading_does_not_count(self):
        for code in UI_ITEMS:
            with self.subTest(code=code):
                plan = plan_text(
                    bodies={CONTRACT_HEADING: ui_body(others(code)), "Test plan": "One test.\n\n" + item_line(code)}
                )
                self.assertEqual(codes(self.check(plan=plan)), ["ITEM_MISSING"])

    def test_chk01_ac6_ui_item_under_another_spec_heading_does_not_count(self):
        plan = self.plan_with(ui_body(others("REFRESH")))
        spec = spec_text(bodies={"Behaviour": "1. The page loads.\n\n" + item_line("REFRESH")})
        self.assertEqual(codes(self.check(spec=spec, plan=plan)), ["ITEM_MISSING"])

    def test_chk01_ac7_label_forms_are_accepted(self):
        forms = {
            "dash list": "- Wrong role: 403 page",
            "star list": "* Wrong role: 403 page",
            "plus list": "+ Wrong role: 403 page",
            "numbered list": "1. Wrong role: 403 page",
            "table first cell": "| Item | Text |\n|---|---|\n| Wrong role | 403 page |",
            "bold colon inside": "**Wrong role:** 403 page",
            "bold colon outside": "**Wrong role**: 403 page",
            "heading": "### Wrong role\n403 page",
            "list next line": "- Wrong role:\n  403 page",
            "bold next line": "**Wrong role:**\n403 page",
            "heading multi line": "### Wrong role\nshows a 403 page\nand a link back",
        }
        for name, block in forms.items():
            with self.subTest(form=name):
                body = ui_body(others("WRONG_ROLE")) + "\n\n" + block
                self.assertEqual(self.check(plan=self.plan_with(body)), [])

    def test_chk01_ac7_label_forms_without_content_give_item_empty(self):
        forms = {
            "list": "- Wrong role:",
            "bold": "**Wrong role:**",
            "heading": "### Wrong role",
            "table": "| Item | Text |\n|---|---|\n| Wrong role |  |",
            "list then heading": "- Wrong role:\n#### Next\nwords",
        }
        for name, block in forms.items():
            with self.subTest(form=name):
                body = ui_body(others("WRONG_ROLE")) + "\n\n" + block
                self.assertEqual(codes(self.check(plan=self.plan_with(body))), ["ITEM_EMPTY"])

    def test_chk01_ac7_matching_is_case_insensitive(self):
        for label in ("WRONG ROLE", "wrong role", "WrOnG rOlE"):
            with self.subTest(label=label):
                body = ui_body(others("WRONG_ROLE")) + f"\n- {label}: 403 page"
                self.assertEqual(self.check(plan=self.plan_with(body)), [])

    def test_chk01_ac7_wrong_role_with_hyphen_or_space_matches(self):
        for label in ("Wrong-role", "Wrong role", "wrong-role users"):
            with self.subTest(label=label):
                body = ui_body(others("WRONG_ROLE")) + f"\n- {label}: 403 page"
                self.assertEqual(self.check(plan=self.plan_with(body)), [])

    def test_chk01_ac7_label_over_80_characters_does_not_match(self):
        body = ui_body(others("WRONG_ROLE")) + "\n- Wrong role " + "x" * 100 + ": 403 page"
        self.assertEqual(codes(self.check(plan=self.plan_with(body))), ["ITEM_MISSING"])

    def test_chk01_ac7_label_well_under_80_characters_still_matches(self):
        body = ui_body(others("WRONG_ROLE")) + "\n- Wrong role " + "x" * 40 + ": 403 page"
        self.assertEqual(self.check(plan=self.plan_with(body)), [])

    def test_chk01_ac7_label_text_in_the_middle_of_a_sentence_is_not_a_label_unless_listed(self):
        body = ui_body(others("WRONG_ROLE")) + "\n\nA wrong role user sees a 403 page."
        self.assertEqual(codes(self.check(plan=self.plan_with(body))), ["ITEM_MISSING"])

    def test_chk01_ac8_security_item_missing_names_item_in_security_section(self):
        for code in SECURITY_ITEMS:
            with self.subTest(code=code):
                findings = self.check(spec=self.spec_with_security(security_body(others(code, SECURITY_ITEMS))))
                self.assertEqual(codes(findings), ["ITEM_MISSING"])
                self.assertEqual((findings[0].file, findings[0].heading), ("spec.md", SECURITY_HEADING))
                self.assertIn(code, findings[0].message)

    def test_chk01_ac8_security_item_label_without_content_gives_item_empty(self):
        for code in SECURITY_ITEMS:
            with self.subTest(code=code):
                body = security_body(others(code, SECURITY_ITEMS)) + f"\n\n- {ITEM_LABELS[code]}:"
                findings = self.check(spec=self.spec_with_security(body))
                self.assertEqual(codes(findings), ["ITEM_EMPTY"])
                self.assertIn(code, findings[0].message)

    def test_chk01_ac8_security_item_with_not_applicable_reason_passes(self):
        self.assertEqual(self.check(), [])

    def test_chk01_ac8_security_item_with_real_content_passes(self):
        body = (
            "- Read-only tool.\n"
            "- Concurrent requests (same time): two submits for one record keep the first answer.\n"
            "- Normalisation: ids are trimmed and compared exactly."
        )
        self.assertEqual(self.check(spec=self.spec_with_security(body)), [])

    def test_chk01_ac8_security_item_with_placeholder_content_gives_placeholder(self):
        body = "- Read-only tool.\n" + item_line("CONCURRENT_REQUESTS", "TBD") + "\n" + item_line("NORMALISATION", "none")
        findings = self.check(spec=self.spec_with_security(body))
        self.assertEqual(codes(findings), ["PLACEHOLDER"])

    def test_chk01_ac8_security_items_in_another_section_do_not_count(self):
        spec = spec_text(
            bodies={SECURITY_HEADING: "- Read-only tool.", "Open questions": "None.\n\n" + security_body()}
        )
        findings = self.check(spec=spec)
        self.assertEqual(codes(findings), ["ITEM_MISSING", "ITEM_MISSING"])
        self.assertEqual({f.file for f in findings}, {"spec.md"})

    def test_chk01_ac8_security_items_in_the_plan_do_not_count(self):
        plan = plan_text(bodies={"Test plan": "One test.\n\n" + security_body()})
        spec = spec_text(bodies={SECURITY_HEADING: "- Read-only tool."})
        self.assertEqual(codes(self.check(spec=spec, plan=plan)), ["ITEM_MISSING", "ITEM_MISSING"])

    def test_chk01_ac8_security_items_are_required_for_no_screen_specs(self):
        spec = spec_text(screen=False, bodies={SECURITY_HEADING: "- Read-only tool."})
        findings = self.check(spec=spec, plan=plan_text(screen=False))
        self.assertEqual(codes(findings), ["ITEM_MISSING", "ITEM_MISSING"])

    def test_chk01_ac8_security_section_missing_reports_items_on_the_file(self):
        findings = self.check(spec=spec_text(omit=[SECURITY_HEADING]))
        self.assertIn("SECTION_MISSING", codes(findings))
        self.assertEqual(len(with_code(findings, "ITEM_MISSING")), 2)


class NoScreenTests(SpecCase):
    def no_screen_findings(self, line, **spec_kwargs):
        spec = spec_text(screen=False, no_screen=line, **spec_kwargs)
        return self.check(spec=spec, plan=plan_text(screen=False))

    def test_chk01_ac9_no_screen_forms_with_a_reason_pass(self):
        lines = [
            "No screen: command-line tool",
            "- No screen: command-line tool",
            "* No screen: command-line tool",
            "**No screen**: command-line tool",
            "**No screen:** command-line tool",
            "no screen: command-line tool",
            "NO SCREEN: command-line tool",
        ]
        for line in lines:
            with self.subTest(line=line):
                self.assertEqual(self.no_screen_findings(line), [])

    def test_chk01_ac9_no_screen_skips_ui_section_contract_and_ui_items(self):
        findings = self.check(spec=spec_text(screen=False), plan=plan_text(screen=False))
        self.assertEqual(findings, [])

    def test_chk01_ac9_no_screen_skips_an_empty_ui_contract_heading(self):
        spec = spec_text(screen=False)
        plan = plan_text(bodies={CONTRACT_HEADING: ""})
        self.assertEqual(self.check(spec=spec, plan=plan), [])

    def test_chk01_ac9_no_screen_still_enforces_tier_one_sections(self):
        findings = self.no_screen_findings("No screen: cli", omit=["Goal"])
        self.assertEqual(codes(findings), ["SECTION_MISSING"])

    def test_chk01_ac9_no_screen_still_enforces_security_items(self):
        findings = self.no_screen_findings("No screen: cli", bodies={SECURITY_HEADING: "- Read-only tool."})
        self.assertEqual(codes(findings), ["ITEM_MISSING", "ITEM_MISSING"])

    def test_chk01_ac9_empty_reason_gives_no_screen_reason_empty(self):
        for line in ("No screen:", "No screen:    ", "- No screen:", "**No screen:**"):
            with self.subTest(line=line):
                findings = self.no_screen_findings(line)
                self.assertIn("NO_SCREEN_REASON_EMPTY", codes(findings))
                found = with_code(findings, "NO_SCREEN_REASON_EMPTY")[0]
                self.assertEqual((found.file, found.heading), ("spec.md", "(file)"))

    def test_chk01_ac9_placeholder_reason_gives_placeholder(self):
        findings = self.no_screen_findings("No screen: TBD")
        self.assertIn("PLACEHOLDER", codes(findings))

    def test_chk01_ac9_no_screen_without_colon_is_not_a_declaration(self):
        findings = self.no_screen_findings("No screen here, the page is a CLI")
        self.assertIn("UI_SECTION_MISSING", codes(findings))

    def test_chk01_ac9_no_screen_line_inside_a_fence_is_not_a_declaration(self):
        findings = self.no_screen_findings("```\nNo screen: cli\n```")
        self.assertIn("UI_SECTION_MISSING", codes(findings))

    def test_chk01_ac9_sentence_that_only_mentions_no_screen_is_not_a_declaration(self):
        findings = self.no_screen_findings("There is no screen: it is a cli")
        self.assertIn("UI_SECTION_MISSING", codes(findings))

    def test_chk01_ac9_no_screen_line_may_sit_under_the_ui_states_heading(self):
        spec = spec_text(bodies={UI_HEADING: "No screen: command-line tool, output contract in plan.md"})
        self.assertEqual(self.check(spec=spec, plan=plan_text(screen=False)), [])


class FileAndSectionTests(SpecCase):
    def test_chk01_ac10_missing_files_give_codes_naming_the_spec_id(self):
        cases = {"spec": ("SPEC_MISSING", "spec.md"), "plan": ("PLAN_MISSING", "plan.md"), "tasks": ("TASKS_MISSING", "tasks.md")}
        for arg, (code, filename) in cases.items():
            with self.subTest(file=filename):
                folder_id = f"M-{arg}"
                findings = self.check(spec_id=folder_id, **{arg: OMIT})
                found = with_code(findings, code)
                self.assertEqual(len(found), 1)
                self.assertEqual(found[0].spec_id, folder_id)
                self.assertEqual((found[0].file, found[0].heading), (filename, "(file)"))
                self.assertIn(filename, found[0].message)

    def test_chk01_ac10_missing_tasks_file_is_the_only_finding(self):
        self.assertEqual(codes(self.check(tasks=OMIT)), ["TASKS_MISSING"])

    def test_chk01_ac10_missing_plan_skips_plan_checks(self):
        findings = self.check(plan=OMIT)
        self.assertIn("PLAN_MISSING", codes(findings))
        for finding in findings:
            self.assertNotIn(finding.code, ("SECTION_MISSING", "SECTION_EMPTY", "UI_CONTRACT_MISSING", "UI_CONTRACT_EMPTY"))

    def test_chk01_ac10_missing_spec_skips_spec_checks(self):
        findings = self.check(spec=OMIT)
        self.assertIn("SPEC_MISSING", codes(findings))
        self.assertEqual([f for f in findings if f.file == "spec.md" and f.code != "SPEC_MISSING"], [])

    def test_chk01_ac10_all_three_files_missing(self):
        findings = self.check(spec=OMIT, plan=OMIT, tasks=OMIT)
        for code in ("SPEC_MISSING", "PLAN_MISSING", "TASKS_MISSING"):
            self.assertEqual(len(with_code(findings, code)), 1)

    def test_chk01_ac10_empty_folder_does_not_crash(self):
        folder = self.specs / "EMPTY-01"
        folder.mkdir()
        from speccheck.rules import check_spec_dir

        found = set(codes(check_spec_dir(folder, {})))
        self.assertTrue({"SPEC_MISSING", "PLAN_MISSING", "TASKS_MISSING"} <= found)

    def test_chk01_ac11_missing_spec_section_gives_section_missing_naming_it(self):
        for name in SPEC_REQUIRED:
            with self.subTest(section=name):
                findings = with_code(self.check(spec=spec_text(omit=[name])), "SECTION_MISSING")
                self.assertEqual(len(findings), 1)
                self.assertEqual((findings[0].file, findings[0].heading), ("spec.md", "(file)"))
                self.assertIn(name, findings[0].message)

    def test_chk01_ac11_empty_spec_section_gives_section_empty(self):
        for name in SPEC_REQUIRED:
            with self.subTest(section=name):
                findings = with_code(self.check(spec=spec_text(bodies={name: ""})), "SECTION_EMPTY")
                self.assertEqual(len(findings), 1)
                self.assertEqual((findings[0].file, findings[0].heading), ("spec.md", name))

    def test_chk01_ac11_whitespace_only_section_is_empty(self):
        findings = self.check(spec=spec_text(bodies={"Goal": "   \n\t\n  "}))
        self.assertEqual(codes(findings), ["SECTION_EMPTY"])

    def test_chk01_ac11_short_text_such_as_none_passes(self):
        for name in ("Open questions", "Out of scope"):
            for text in ("None", "none.", "N/A"):
                with self.subTest(section=name, text=text):
                    self.assertEqual(self.check(spec=spec_text(bodies={name: text})), [])

    def test_chk01_ac11_acceptance_criteria_without_checklist_item_gives_ac_item_missing(self):
        spec = spec_text(bodies={"Acceptance criteria": "The page must work.\n- AC1: no checkbox here"})
        findings = self.check(spec=spec)
        self.assertEqual(codes(findings), ["AC_ITEM_MISSING"])
        self.assertEqual((findings[0].file, findings[0].heading), ("spec.md", "Acceptance criteria"))

    def test_chk01_ac11_single_checklist_item_is_enough(self):
        spec = spec_text(bodies={"Acceptance criteria": "- [ ] AC1: The page works."})
        self.assertEqual(self.check(spec=spec), [])

    def test_chk01_ac11_headings_match_case_insensitively_at_any_level(self):
        spec = spec_text()
        spec = replace_once(spec, "## Goal", "#### GOAL")
        spec = replace_once(spec, "## Behaviour", "# behaviour")
        spec = replace_once(spec, "## Out of scope", "### OUT OF SCOPE")
        spec = replace_once(spec, "## Open questions", "## Open Questions:")
        self.assertEqual(self.check(spec=spec), [])

    def test_chk01_ac12_missing_plan_section_gives_section_missing_naming_it(self):
        for name in PLAN_REQUIRED:
            with self.subTest(section=name):
                findings = with_code(self.check(plan=plan_text(omit=[name])), "SECTION_MISSING")
                self.assertEqual(len(findings), 1)
                self.assertEqual((findings[0].file, findings[0].heading), ("plan.md", "(file)"))
                self.assertIn(name, findings[0].message)

    def test_chk01_ac12_empty_plan_section_gives_section_empty(self):
        for name in PLAN_REQUIRED:
            with self.subTest(section=name):
                findings = with_code(self.check(plan=plan_text(bodies={name: ""})), "SECTION_EMPTY")
                self.assertEqual(len(findings), 1)
                self.assertEqual((findings[0].file, findings[0].heading), ("plan.md", name))

    def test_chk01_ac12_not_applicable_with_reason_passes_for_every_plan_section(self):
        for name in PLAN_REQUIRED:
            with self.subTest(section=name):
                plan = plan_text(bodies={name: "Not applicable: command-line tool."})
                self.assertEqual(self.check(plan=plan), [])

    def test_chk01_ac12_missing_decisions_section_gives_nothing(self):
        self.assertEqual(self.check(plan=plan_text()), [])

    def test_chk01_ac13_each_role_in_a_table_row_passes(self):
        for role in ROLES:
            with self.subTest(role=role):
                tasks = tasks_text(row=f"| 1 | Build the page | {role} | none | todo |")
                self.assertEqual(self.check(tasks=tasks), [])

    def test_chk01_ac13_role_matching_is_case_insensitive(self):
        for role in ("Developer", "TEST-DESIGNER", "Spec-Writer"):
            with self.subTest(role=role):
                self.assertEqual(self.check(tasks=tasks_text(row=f"| 1 | Build | {role} | none | todo |")), [])

    def test_chk01_ac13_list_item_naming_a_role_passes(self):
        tasks = "# Tasks: ZZ-01 Demo\n\n- Build the page (owner developer)\n- Check it (verifier)\n"
        self.assertEqual(self.check(tasks=tasks), [])

    def test_chk01_ac13_no_role_gives_tasks_no_role(self):
        tasks = tasks_text(row="| 1 | Build the page | nobody | none | todo |")
        findings = self.check(tasks=tasks)
        self.assertEqual(codes(findings), ["TASKS_NO_ROLE"])
        self.assertEqual((findings[0].file, findings[0].heading), ("tasks.md", "(file)"))

    def test_chk01_ac13_role_words_must_match_whole_words(self):
        for word in ("developers", "username", "superuser", "humanoid", "sessions"):
            with self.subTest(word=word):
                tasks = tasks_text(row=f"| 1 | Build the page | {word} | none | todo |")
                self.assertEqual(codes(self.check(tasks=tasks)), ["TASKS_NO_ROLE"])

    def test_chk01_ac13_role_in_prose_outside_rows_and_list_items_does_not_count(self):
        tasks = tasks_text(row="| 1 | Build the page | nobody | none | todo |") + "\nThe developer builds it.\n"
        self.assertEqual(codes(self.check(tasks=tasks)), ["TASKS_NO_ROLE"])

    def test_chk01_ac13_empty_tasks_file_gives_tasks_no_role(self):
        self.assertEqual(codes(self.check(tasks="")), ["TASKS_NO_ROLE"])

    def test_chk01_ac13_one_row_naming_a_role_is_enough(self):
        tasks = tasks_text(row="| 1 | Build | nobody | none | todo |\n| 2 | Check | verifier | 1 | todo |")
        self.assertEqual(self.check(tasks=tasks), [])


class StructureTests(SpecCase):
    def test_chk01_ac24_heading_inside_fence_is_not_a_section(self):
        goal = "Show the page.\n```\n## Behaviour\nfake\n```"
        findings = self.check(spec=spec_text(omit=["Behaviour"], bodies={"Goal": goal}))
        self.assertEqual(codes(findings), ["SECTION_MISSING"])
        self.assertIn("Behaviour", findings[0].message)

    def test_chk01_ac24_heading_inside_tilde_fence_is_not_a_section(self):
        goal = "Show the page.\n~~~\n## Behaviour\nfake\n~~~"
        findings = self.check(spec=spec_text(omit=["Behaviour"], bodies={"Goal": goal}))
        self.assertEqual(codes(findings), ["SECTION_MISSING"])

    def test_chk01_ac24_sub_heading_text_counts_as_the_parent_sections_text(self):
        body = "### Detail\nShow the page to the learner."
        self.assertEqual(self.check(spec=spec_text(bodies={"Goal": body})), [])

    def test_chk01_ac24_parent_with_only_an_empty_sub_heading_is_empty(self):
        findings = self.check(spec=spec_text(bodies={"Goal": "### Detail"}))
        self.assertEqual(codes(findings), ["SECTION_EMPTY"])

    def test_chk01_ac24_same_level_heading_ends_the_section(self):
        findings = self.check(spec=spec_text(bodies={"Goal": ""}))
        self.assertEqual(codes(findings), ["SECTION_EMPTY"])

    def test_chk01_ac24_sub_heading_is_inside_a_section_for_item_search(self):
        body = ui_body(others("WRONG_ROLE")) + "\n\n### Detail\n- Wrong role: 403 page"
        self.assertEqual(self.check(plan=plan_text(bodies={CONTRACT_HEADING: body})), [])


class WaiverRuleTests(SpecCase):
    def broken(self):
        """Spec, plan, tasks with a Tier 1 gap, a table gap, a contract gap and missing items."""
        spec = spec_text(
            omit=["Out of scope"],
            bodies={UI_HEADING: "| State | Copy |\n|---|---|\n| Error |  |", SECURITY_HEADING: "- Read-only tool."},
        )
        plan = plan_text(bodies={CONTRACT_HEADING: "Nothing listed."})
        return {"spec": spec, "plan": plan}

    def test_chk01_ac14_unwaived_broken_spec_has_items_and_other_findings(self):
        found = codes(self.check(**self.broken()))
        self.assertIn("ITEM_MISSING", found)
        self.assertIn("SECTION_MISSING", found)
        self.assertIn("UI_TABLE_CELL_EMPTY", found)

    def test_chk01_ac14_scope_all_gives_no_findings(self):
        waivers = self.waivers(f"{SPEC_ID} | all | predates the rule\n")
        self.assertEqual(self.check(waivers=waivers, **self.broken()), [])

    def test_chk01_ac14_scope_all_skips_even_missing_files(self):
        waivers = self.waivers(f"{SPEC_ID} | all | predates the rule\n")
        self.assertEqual(self.check(spec=OMIT, plan=OMIT, tasks=OMIT, waivers=waivers), [])

    def test_chk01_ac14_scope_added_items_keeps_other_rules_but_drops_item_findings(self):
        waivers = self.waivers(f"{SPEC_ID} | added-items | no item labels yet\n")
        found = codes(self.check(waivers=waivers, **self.broken()))
        self.assertIn("SECTION_MISSING", found)
        self.assertIn("UI_TABLE_CELL_EMPTY", found)
        self.assertEqual([c for c in found if c.startswith("ITEM_")], [])

    def test_chk01_ac14_scope_added_items_drops_item_empty_too(self):
        body = ui_body(others("REFRESH")) + "\n\n- Refresh:"
        waivers = self.waivers(f"{SPEC_ID} | added-items | no item labels yet\n")
        findings = self.check(plan=plan_text(bodies={CONTRACT_HEADING: body}), waivers=waivers)
        self.assertEqual(findings, [])

    def test_chk01_ac14_scope_added_items_keeps_contract_and_tier_one_findings(self):
        waivers = self.waivers(f"{SPEC_ID} | added-items | no item labels yet\n")
        findings = self.check(
            spec=spec_text(omit=[UI_HEADING]),
            plan=plan_text(bodies={CONTRACT_HEADING: ""}, omit=["Test plan"]),
            waivers=waivers,
        )
        found = codes(findings)
        self.assertIn("UI_SECTION_MISSING", found)
        self.assertIn("UI_CONTRACT_EMPTY", found)
        self.assertIn("SECTION_MISSING", found)

    def test_chk01_ac14_waiver_for_another_spec_id_does_not_apply(self):
        waivers = self.waivers("OTHER-01 | all | predates the rule\n")
        self.assertNotEqual(self.check(waivers=waivers, **self.broken()), [])

    def test_chk01_ac14_waiver_spec_id_is_compared_case_sensitively(self):
        waivers = self.waivers(f"{SPEC_ID.lower()} | all | predates the rule\n")
        self.assertNotEqual(self.check(waivers=waivers, **self.broken()), [])


class RobustnessTests(SpecCase):
    def test_chk01_ac23_binary_files_do_not_crash(self):
        blob = bytes(range(256)) * 40 + b"\x00\x00## Goal\n\xff\xfe"
        for name in ("spec", "plan", "tasks"):
            with self.subTest(file=name):
                findings = self.check(spec_id=f"BIN-{name}", **{name: blob})
                self.assertIsInstance(findings, list)

    def test_chk01_ac23_all_three_files_binary(self):
        blob = bytes(range(256)) * 10
        findings = self.check(spec=blob, plan=blob, tasks=blob)
        self.assertIsInstance(findings, list)
        self.assertTrue(findings)

    def test_chk01_ac23_invalid_utf8_bytes_are_replaced_not_fatal(self):
        spec = spec_text(bodies={"Goal": "Show the café page."}).encode("latin-1", errors="replace")
        self.assertIn(b"\xe9", spec)
        self.assertEqual(self.check(spec=spec), [])

    def test_chk01_ac23_five_megabyte_file_does_not_crash(self):
        filler = "Some filler text for the goal section.\n"
        goal = filler * (5 * 1024 * 1024 // len(filler))
        start = time.monotonic()
        findings = self.check(spec=spec_text(bodies={"Goal": goal}))
        self.assertEqual(findings, [])
        self.assertLess(time.monotonic() - start, 60)

    def test_chk01_ac23_five_megabyte_single_line_does_not_crash(self):
        start = time.monotonic()
        findings = self.check(spec=spec_text(bodies={"Goal": "a" * (5 * 1024 * 1024)}))
        self.assertEqual(findings, [])
        self.assertLess(time.monotonic() - start, 60)

    def test_chk01_ac23_regex_stress_lines_finish_quickly(self):
        stress = "\n".join(
            [
                "<" * 200_000,
                "<a" * 100_000,
                "?" * 200_000,
                "|" * 200_000,
                "| a " * 50_000 + "|",
                "*" * 200_000,
                "- " + "x" * 200_000 + ":",
            ]
        )
        start = time.monotonic()
        findings = self.check(spec=spec_text(bodies={"Goal": stress, UI_HEADING: stress}))
        self.assertIsInstance(findings, list)
        self.assertLess(time.monotonic() - start, 60)

    def test_chk01_ac23_checker_writes_no_files(self):
        folder = self.write()

        def snapshot():
            return {p: (p.read_bytes() if p.is_file() else None) for p in self.root.rglob("*")}

        before = snapshot()
        from speccheck.rules import check_spec_dir

        check_spec_dir(folder, {})
        self.assertEqual(snapshot(), before)

    def test_chk01_ac23_checker_opens_no_network_connection(self):
        with mock.patch.object(socket.socket, "connect", side_effect=AssertionError("network used")), mock.patch(
            "socket.create_connection", side_effect=AssertionError("network used")
        ):
            self.assertEqual(self.check(), [])

    def test_chk01_ac23_spec_content_is_never_executed(self):
        marker = self.root / "marker.txt"
        evil = (
            "```python\n"
            f"open({str(marker)!r}, 'w').write('x')\n"
            "```\n"
            f"__import__('os').system('echo x > {marker.as_posix()}')\n"
            f"$(touch {marker.as_posix()}) `touch {marker.as_posix()}`\n"
        )
        findings = self.check(spec=spec_text(bodies={"Goal": evil}), tasks=tasks_text(row="| 1 | `rm -rf /` | developer | none | todo |"))
        self.assertIsInstance(findings, list)
        self.assertFalse(marker.exists())


if __name__ == "__main__":
    unittest.main()

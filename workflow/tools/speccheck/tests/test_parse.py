import unittest

from speccheck.parse import find_section, labelled_entries, placeholders, sections, tables


def body_text(section):
    return [text.strip() for _, text in section.lines if text.strip()]


def entries_of(text, name):
    return labelled_entries(find_section(sections(text), name))


class SectionsTests(unittest.TestCase):
    def test_chk01_ac24_sections_levels_order_and_lines(self):
        text = "# Title\n\n## Goal\nfirst\n\n### Detail\nsecond\n\n## Behaviour\nthird\n"
        secs = sections(text)
        self.assertEqual([s.level for s in secs], [1, 2, 3, 2])
        self.assertEqual([s.heading.strip() for s in secs], ["Title", "Goal", "Detail", "Behaviour"])
        self.assertEqual([s.line for s in secs], [1, 3, 6, 9])

    def test_chk01_ac24_subheadings_belong_to_parent(self):
        text = "## Goal\nfirst\n### Detail\nsecond\n## Behaviour\nthird\n"
        goal, detail, behaviour = sections(text)
        self.assertEqual(body_text(goal), ["first", "### Detail", "second"])
        self.assertEqual(body_text(detail), ["second"])
        self.assertEqual(body_text(behaviour), ["third"])

    def test_chk01_ac24_higher_level_heading_ends_section(self):
        text = "## A\nx\n### B\ny\n# Top\nz\n"
        a, b, top = sections(text)
        self.assertEqual(body_text(a), ["x", "### B", "y"])
        self.assertEqual(body_text(b), ["y"])
        self.assertEqual(body_text(top), ["z"])

    def test_chk01_ac24_same_level_heading_ends_section(self):
        goal, behaviour = sections("## Goal\n## Behaviour\ntext\n")
        self.assertEqual(body_text(goal), [])
        self.assertEqual(body_text(behaviour), ["text"])

    def test_chk01_ac24_heading_inside_backtick_fence_is_not_a_heading(self):
        text = "## Goal\n```\n## Fake\n```\nafter\n## Behaviour\nx\n"
        secs = sections(text)
        self.assertEqual([s.heading.strip() for s in secs], ["Goal", "Behaviour"])
        self.assertIn("after", body_text(secs[0]))

    def test_chk01_ac24_heading_inside_tilde_fence_is_not_a_heading(self):
        text = "## Goal\n~~~\n## Fake\n~~~\nafter\n## Behaviour\nx\n"
        self.assertEqual([s.heading.strip() for s in sections(text)], ["Goal", "Behaviour"])

    def test_chk01_ac24_fence_with_language_tag_toggles(self):
        text = "## Goal\n```python\n# comment\n```\n## Behaviour\nx\n"
        self.assertEqual([s.heading.strip() for s in sections(text)], ["Goal", "Behaviour"])

    def test_chk01_ac24_hash_without_space_or_seven_hashes_is_not_a_heading(self):
        text = "##Goal\n####### Seven\n## Real\n"
        self.assertEqual([s.heading.strip() for s in sections(text)], ["Real"])

    def test_chk01_ac11_all_six_heading_levels_are_headings(self):
        text = "\n".join("#" * n + f" H{n}" for n in range(1, 7)) + "\n"
        self.assertEqual([s.level for s in sections(text)], [1, 2, 3, 4, 5, 6])

    def test_chk01_ac24_no_headings_gives_no_sections(self):
        self.assertEqual(sections("just text\nmore\n"), [])


class FindSectionTests(unittest.TestCase):
    def test_chk01_ac11_find_section_is_case_insensitive_at_any_level(self):
        secs = sections("#### GOAL\ntext\n")
        self.assertIsNotNone(find_section(secs, "goal"))

    def test_chk01_ac11_find_section_strips_bold_backticks_and_trailing_punctuation(self):
        for heading in ("## **Goal**", "## `Goal`", "### Goal:", "## Goal.", "## Goal?", "##   Goal  "):
            with self.subTest(heading=heading):
                self.assertIsNotNone(find_section(sections(heading + "\ntext\n"), "goal"))

    def test_chk01_ac11_find_section_multiword(self):
        secs = sections("## Security and AI safeguards\ntext\n")
        self.assertIsNotNone(find_section(secs, "security and ai safeguards"))

    def test_chk01_ac11_find_section_absent_gives_none(self):
        self.assertIsNone(find_section(sections("## Goal\ntext\n"), "behaviour"))

    def test_chk01_ac11_find_section_returns_first_of_duplicates(self):
        secs = sections("## Goal\nfirst\n## Goal\nsecond\n")
        self.assertEqual(body_text(find_section(secs, "goal")), ["first"])

    def test_chk01_ac11_find_section_requires_whole_heading_match(self):
        self.assertIsNone(find_section(sections("## Goals\ntext\n"), "goal"))


class TablesTests(unittest.TestCase):
    def tables_in(self, text):
        return tables(sections("## S\n" + text)[0])

    def test_chk01_ac2_table_header_and_data_rows(self):
        (table,) = self.tables_in("| A | B |\n|---|---|\n| 1 | 2 |\n| 3 | 4 |\n")
        self.assertEqual(table.header, ["A", "B"])
        self.assertEqual([cells for _, cells in table.rows], [["1", "2"], ["3", "4"]])

    def test_chk01_ac3_data_row_numbers_are_one_based_and_skip_header_and_separator(self):
        (table,) = self.tables_in("| A | B |\n|---|---|\n| 1 | 2 |\n| 3 | 4 |\n")
        self.assertEqual([n for n, _ in table.rows], [1, 2])

    def test_chk01_ac2_header_only_table_has_no_data_rows(self):
        (table,) = self.tables_in("| A | B |\n|---|---|\n")
        self.assertEqual(table.rows, [])

    def test_chk01_ac3_empty_cell_is_kept_as_empty_string(self):
        (table,) = self.tables_in("| A | B |\n|---|---|\n| 1 |  |\n")
        self.assertEqual(table.rows[0][1], ["1", ""])

    def test_chk01_ac2_alignment_separator_cells_are_accepted(self):
        (table,) = self.tables_in("| A | B | C |\n|:--|:-:|--:|\n| 1 | 2 | 3 |\n")
        self.assertEqual(len(table.rows), 1)

    def test_chk01_ac2_lines_without_separator_row_are_not_a_table(self):
        self.assertEqual(self.tables_in("| A | B |\n| 1 | 2 |\n"), [])

    def test_chk01_ac2_prose_is_not_a_table(self):
        self.assertEqual(self.tables_in("just words\nmore words\n"), [])

    def test_chk01_ac3_escaped_pipe_does_not_split_a_cell(self):
        (table,) = self.tables_in("| A | B |\n|---|---|\n| x \\| y | z |\n")
        self.assertEqual(len(table.rows[0][1]), 2)
        self.assertEqual(table.rows[0][1][1], "z")

    def test_chk01_ac2_two_tables_separated_by_text(self):
        text = "| A |\n|---|\n| 1 |\n\nwords\n\n| B |\n|---|\n| 2 |\n"
        first, second = self.tables_in(text)
        self.assertEqual(first.header, ["A"])
        self.assertEqual(second.header, ["B"])


class PlaceholdersTests(unittest.TestCase):
    def found(self, line):
        return [m.lower() for m in placeholders(line)]

    def test_chk01_ac1_each_placeholder_word(self):
        for word in ("TBD", "TODO", "TBC", "FIXME", "XXX"):
            with self.subTest(word=word):
                self.assertEqual(self.found(f"value is {word} for now"), [word.lower()])

    def test_chk01_ac1_placeholder_words_are_case_insensitive(self):
        for word in ("tbd", "Todo", "fixMe", "xxx"):
            with self.subTest(word=word):
                self.assertEqual(self.found(f"value {word} here"), [word.lower()])

    def test_chk01_ac1_question_marks(self):
        self.assertEqual(placeholders("copy is ???"), ["???"])

    def test_chk01_ac1_angle_bracket_slot_returns_the_slot(self):
        self.assertEqual(placeholders("Spec: <feature id> here"), ["<feature id>"])

    def test_chk01_ac1_br_tags_are_not_slots(self):
        self.assertEqual(placeholders("line one<br>line two<br/>end"), [])

    def test_chk01_ac1_word_inside_longer_word_is_not_a_placeholder(self):
        for word in ("TODOS", "TBDs", "XXXL", "mixxxed", "ATBD"):
            with self.subTest(word=word):
                self.assertEqual(placeholders(f"see {word} list"), [])

    def test_chk01_ac1_backtick_code_span_is_ignored(self):
        self.assertEqual(placeholders("write `TBD` or `<slot>` or `???` here"), [])

    def test_chk01_ac1_text_outside_a_code_span_still_counts(self):
        self.assertEqual(self.found("`TBD` but also FIXME"), ["fixme"])

    def test_chk01_ac1_two_matches_in_one_line(self):
        self.assertEqual(self.found("TBD and TODO"), ["tbd", "todo"])

    def test_chk01_ac1_clean_line_has_no_matches(self):
        self.assertEqual(placeholders("A normal sentence, with 3 < 4 maths."), [])


class LabelledEntriesTests(unittest.TestCase):
    def test_chk01_ac7_list_item_label_and_same_line_content(self):
        text = "## S\n- Wrong role: shows a 403 page\n"
        (entry,) = entries_of(text, "s")
        self.assertEqual(entry.label.strip().lower(), "wrong role")
        self.assertEqual(entry.content.strip(), "shows a 403 page")
        self.assertEqual(entry.line, 2)

    def test_chk01_ac7_all_list_markers(self):
        for marker in ("-", "*", "+", "1."):
            with self.subTest(marker=marker):
                (entry,) = entries_of(f"## S\n{marker} Refresh: reloads\n", "s")
                self.assertEqual(entry.label.strip().lower(), "refresh")
                self.assertEqual(entry.content.strip(), "reloads")

    def test_chk01_ac7_label_is_text_before_first_colon(self):
        (entry,) = entries_of("## S\n- Link history: push: or replace\n", "s")
        self.assertEqual(entry.label.strip().lower(), "link history")
        self.assertIn("push: or replace", entry.content)

    def test_chk01_ac7_table_row_first_cell_is_label_and_rest_is_content(self):
        text = "## S\n| Item | Text |\n|---|---|\n| Refresh | reloads | now |\n"
        entries = entries_of(text, "s")
        labels = [e.label.strip().lower() for e in entries]
        self.assertIn("refresh", labels)
        self.assertNotIn("item", labels)
        entry = entries[labels.index("refresh")]
        self.assertEqual(entry.content.split(), ["reloads", "now"])

    def test_chk01_ac7_bold_label_with_colon_inside_or_outside(self):
        for line in ("**Refresh:** reloads", "**Refresh**: reloads"):
            with self.subTest(line=line):
                (entry,) = entries_of(f"## S\n{line}\n", "s")
                self.assertEqual(entry.label.strip().lower(), "refresh")
                self.assertIn("reloads", entry.content)

    def test_chk01_ac7_heading_is_a_label_with_following_lines_as_content(self):
        (entry,) = entries_of("## S\n### Refresh\nreloads the view\nand keeps state\n", "s")
        self.assertEqual(entry.label.strip().lower(), "refresh")
        self.assertEqual(entry.content.split(), "reloads the view and keeps state".split())

    def test_chk01_ac7_content_on_following_lines_stops_at_blank_line(self):
        entries = entries_of("## S\n- Refresh:\n  reloads\n  the view\n\nunrelated words\n", "s")
        entry = [e for e in entries if e.label.strip().lower() == "refresh"][0]
        self.assertEqual(entry.content.split(), ["reloads", "the", "view"])

    def test_chk01_ac7_content_on_following_lines_stops_at_heading(self):
        entries = entries_of("## S\n- Refresh:\n#### Next\nwords\n", "s")
        entry = [e for e in entries if e.label.strip().lower() == "refresh"][0]
        self.assertEqual(entry.content.strip(), "")

    def test_chk01_ac7_label_without_content_has_empty_content(self):
        (entry,) = entries_of("## S\n- Refresh:\n\nlater text\n", "s")
        self.assertEqual(entry.content.strip(), "")

    def test_chk01_ac7_list_item_without_colon_uses_whole_text_as_label(self):
        entries = entries_of("## S\n- Refresh\n  reloads\n", "s")
        entry = [e for e in entries if e.label.strip().lower() == "refresh"][0]
        self.assertEqual(entry.content.strip(), "reloads")

    def test_chk01_ac7_backticks_and_stars_are_stripped_from_label(self):
        (entry,) = entries_of("## S\n- `Refresh`: reloads\n", "s")
        self.assertEqual(entry.label.strip().lower(), "refresh")

    def test_chk01_ac24_sub_headings_of_the_section_are_scanned(self):
        text = "## S\nintro\n### Detail\n- Refresh: reloads\n"
        labels = [e.label.strip().lower() for e in entries_of(text, "s")]
        self.assertIn("refresh", labels)

    def test_chk01_ac7_entries_carry_file_line_numbers(self):
        text = "## S\n\n- A: one\n- B: two\n"
        lines = {e.label.strip().lower(): e.line for e in entries_of(text, "s")}
        self.assertEqual(lines["a"], 3)
        self.assertEqual(lines["b"], 4)


if __name__ == "__main__":
    unittest.main()

import tempfile
import unittest
from pathlib import Path

from tracker.model import UsageRow
from tracker.run_report import AttributionError, ManifestError, read_manifest, render_report


RUN_ID = "2026-11-05-STU04-01"
FIELDS = "feature_run_id,invocation_id,role,effort,tool,session_id,agent_id,started_at,finished_at"


def manifest_row(invocation_id, role, session_id, agent_id, start, finish, effort="light", tool="codex"):
    if not invocation_id.startswith(RUN_ID + "-"):
        role_slug = {"dev": "developer", "verify": "verifier"}.get(invocation_id.split("-")[0], role)
        suffix = invocation_id.rsplit("-", 1)[-1]
        invocation_id = f"{RUN_ID}-{role_slug}-{suffix}"
    return f"{RUN_ID},{invocation_id},{role},{effort},{tool},{session_id},{agent_id},{start},{finish}"


def usage_row(session, agent, timestamp, *, model="gpt-test", output=10, cost=0.25, tool="codex"):
    return UsageRow(
        tool=tool,
        session_id=session,
        agent_id=agent,
        agent_type="subagent",
        is_subagent=True,
        model=model,
        branch="feat/trk02",
        cwd="C:\\repo",
        timestamp=timestamp,
        input_tokens=20,
        cache_read_tokens=5,
        cache_write_5m_tokens=2,
        cache_write_1h_tokens=1,
        output_tokens=output,
        reasoning_tokens=3,
        cost_usd=cost,
    )


class RunReportTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "invocations.csv"

    def write_manifest(self, rows):
        self.path.write_text(FIELDS + "\n" + "\n".join(rows) + "\n", encoding="utf-8")
        return self.path

    def test_manifest_rejects_duplicate_invocation_id(self):
        row = manifest_row("dev-01", "developer", "s1", "a1", "2026-11-05T12:00:00+00:00", "2026-11-05T12:01:00+00:00")
        self.write_manifest([row, row])
        with self.assertRaisesRegex(ManifestError, "duplicate invocation_id"):
            read_manifest(self.path)

    def test_manifest_rejects_invalid_tool_and_time_order(self):
        bad_tool = manifest_row("dev-01", "developer", "s1", "a1", "2026-11-05T12:00:00+00:00", "2026-11-05T12:01:00+00:00", tool="other")
        self.write_manifest([bad_tool])
        with self.assertRaisesRegex(ManifestError, "tool"):
            read_manifest(self.path)

        reversed_time = manifest_row("dev-02", "developer", "s2", "a2", "2026-11-05T12:02:00+00:00", "2026-11-05T12:01:00+00:00")
        self.write_manifest([reversed_time])
        with self.assertRaisesRegex(ManifestError, "finished_at"):
            read_manifest(self.path)

    def test_repeated_roles_are_separate_and_total_is_correct(self):
        self.write_manifest(
            [
                manifest_row("dev-01", "developer", "s1", "a1", "2026-11-05T12:00:00+00:00", "2026-11-05T12:02:00+00:00"),
                manifest_row("verify-01", "verifier", "s2", "a2", "2026-11-05T12:01:00+00:00", "2026-11-05T12:03:00+00:00", effort="high", tool="claude"),
                manifest_row("dev-02", "developer", "s3", "a3", "2026-11-05T12:04:00+00:00", "2026-11-05T12:09:00+00:00", effort="light"),
            ]
        )
        run_id, invocations = read_manifest(self.path)
        rows = [
            usage_row("s1", "a1", "2026-11-05T12:01:00+00:00", model="gpt-small", output=10),
            usage_row("s2", "a2", "2026-11-05T12:02:00+00:00", model="claude-opus", output=20, tool="claude"),
            usage_row("s3", "a3", "2026-11-05T12:05:00+00:00", model="gpt-small", output=30),
        ]

        report = render_report(run_id, invocations, rows)
        self.assertEqual(report.count("| invocation |"), 3)
        self.assertIn("dev-01", report)
        self.assertIn("verify-01", report)
        self.assertIn("dev-02", report)
        self.assertIn("claude-opus", report)
        self.assertIn("high", report)
        self.assertIn("0:02:00", report)
        self.assertIn("0:05:00", report)
        self.assertIn("0:09:00", report)  # Run wall time, not summed parallel agent time.
        self.assertIn("feature_run_total", report)
        self.assertIn("60", report)  # Total output tokens: 10 + 20 + 30.

    def test_reused_source_ids_are_separated_by_time(self):
        self.write_manifest(
            [
                manifest_row("dev-01", "developer", "same", "agent", "2026-11-05T12:00:00+00:00", "2026-11-05T12:01:00+00:00"),
                manifest_row("dev-02", "developer", "same", "agent", "2026-11-05T12:02:00+00:00", "2026-11-05T12:03:00+00:00"),
            ]
        )
        run_id, invocations = read_manifest(self.path)
        report = render_report(
            run_id,
            invocations,
            [
                usage_row("same", "agent", "2026-11-05T12:00:30+00:00", output=11),
                usage_row("same", "agent", "2026-11-05T12:02:30+00:00", output=22),
            ],
        )
        self.assertIn("dev-01", report)
        self.assertIn("dev-02", report)
        self.assertIn("33", report)

    def test_ambiguous_and_out_of_window_source_records_fail(self):
        overlapping = [
            manifest_row("dev-01", "developer", "same", "agent", "2026-11-05T12:00:00+00:00", "2026-11-05T12:02:00+00:00"),
            manifest_row("dev-02", "developer", "same", "agent", "2026-11-05T12:01:00+00:00", "2026-11-05T12:03:00+00:00"),
        ]
        self.write_manifest(overlapping)
        run_id, invocations = read_manifest(self.path)
        with self.assertRaisesRegex(AttributionError, "multiple invocations"):
            render_report(run_id, invocations, [usage_row("same", "agent", "2026-11-05T12:01:30+00:00")])

        self.write_manifest([overlapping[0]])
        run_id, invocations = read_manifest(self.path)
        with self.assertRaisesRegex(AttributionError, "outside its time range"):
            render_report(run_id, invocations, [usage_row("same", "agent", "2026-11-05T12:05:00+00:00")])

    def test_unrelated_local_usage_is_ignored(self):
        self.write_manifest([manifest_row("dev-01", "developer", "s1", "a1", "2026-11-05T12:00:00+00:00", "2026-11-05T12:01:00+00:00")])
        run_id, invocations = read_manifest(self.path)
        report = render_report(run_id, invocations, [usage_row("other-session", "other-agent", "2026-11-05T12:00:30+00:00")])
        self.assertIn("dev-01", report)
        self.assertIn("0:01:00", report)  # Duration is recorded even when no model usage was logged.

    def test_report_is_deterministic_and_escapes_markdown_cells(self):
        self.write_manifest([manifest_row("dev-01", "developer|role", "s1", "a1", "2026-11-05T12:00:00+00:00", "2026-11-05T12:00:01+00:00")])
        run_id, invocations = read_manifest(self.path)
        first = render_report(run_id, invocations, [usage_row("s1", "a1", "2026-11-05T12:00:00+00:00")])
        second = render_report(run_id, invocations, [usage_row("s1", "a1", "2026-11-05T12:00:00+00:00")])
        self.assertEqual(first, second)
        self.assertIn("2026-11-05-STU04-01-developer-01", first)
        self.assertIn("developer\\|role", first)
        self.assertIn("invocation-v1", first)
        self.assertNotIn("SECRET_PROMPT_TEXT", first)


if __name__ == "__main__":
    unittest.main()

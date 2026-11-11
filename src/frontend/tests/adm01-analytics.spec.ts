import { test, expect, type Page, type Locator } from "@playwright/test";
import {
  STUDENT,
  TEACHER,
  logOutWithConfirmation,
  expectNoSecretsInBrowser,
} from "./authApi";
import {
  API,
  PATH,
  defaultPeriod,
  isoDay,
  run,
  setup,
  type AnalyticsMock,
  type Step,
} from "./adm01Api";

/**
 * ADM-01 AC40-AC45 and the "UI states and copy" table of workflow/specs/ADM-01/spec.md.
 * Roles, names and copy come only from plan.md "UI contract" / spec.md. The API is mocked (adm01Api.ts):
 * every analytics request is recorded so request counts, URL changes and failure copy can be asserted.
 */

const MSG = {
  network: "Could not reach the server. Check your connection and try again.",
  timeout: "The request timed out after 15 seconds. Try again.",
  forbidden: "You do not have access to analytics.",
  http: (subject: string, status: number) =>
    `${subject} could not be loaded: the server returned an error (${status}). Try again.`,
  period: {
    format: "Enter dates as YYYY-MM-DD.",
    order: "The start date must be on or before the end date.",
    long: "The period can be at most 366 days.",
  },
  start: {
    conflict: "A grading run is already in progress.",
    quota: "Grading run limit reached. Try again later.",
    forbidden: "You do not have access to analytics.",
    network:
      "Could not reach the server. Reload to check whether grading started.",
    timeout:
      "The request timed out after 15 seconds. Reload to check whether grading started.",
  },
  poll: {
    network: "Could not reach the server. Grading may still be running.",
    timeout:
      "The request timed out after 15 seconds. Grading may still be running.",
    http: (status: number) =>
      `Grading progress could not be checked: the server returned an error (${status}).`,
  },
  notice:
    "Grades are AI assessments, not verified facts. They do not change access or application content.",
  purpose:
    "Review how chatbot, practice and AI generation features are used. Periods use UTC dates.",
};

const RUN_FAILURE_COPY: Record<string, string> = {
  ai_rate_limited: "the AI service is rate-limited, try again in a few minutes",
  ai_timeout: "the AI service took too long to respond",
  ai_unavailable: "the AI service is unavailable, try again later",
  context_load_failed: "the stored response data could not be loaded",
  save_failed: "the grades could not be saved",
  run_expired: "the run exceeded its 15-minute limit",
};

// ---- locators (roles and names as in plan.md "UI contract")

const title = (p: Page) =>
  p.getByRole("heading", { level: 1, name: "Feature analytics", exact: true });
const region = (p: Page, name: string) =>
  p.getByRole("region", { name, exact: true });
const periodPanel = (p: Page) => region(p, "Reporting period");
const usagePanel = (p: Page) => region(p, "Feature usage");
const generationPanel = (p: Page) => region(p, "Generation reliability");
const qualityPanel = (p: Page) => region(p, "AI quality and session activity");
const usageTable = (p: Page) =>
  p.getByRole("table", { name: "Chatbot requests by user", exact: true });
const generationTable = (p: Page) =>
  p.getByRole("table", { name: "Generation success rates", exact: true });
const itemsTable = (p: Page) =>
  p.getByRole("table", { name: "Assessed responses", exact: true });
const fromField = (p: Page) => p.getByLabel("From date", { exact: true });
const toField = (p: Page) => p.getByLabel("To date", { exact: true });
const apply = (p: Page) =>
  p.getByRole("button", { name: "Apply period", exact: true });
const tab = (p: Page, name: string) =>
  p.getByRole("tab", { name, exact: true });
const retry = (p: Page, what: string) =>
  p.getByRole("button", { name: `Retry ${what}`, exact: true });
const alertWith = (scope: Page | Locator, text: string) =>
  scope.getByRole("alert").filter({ hasText: text });
const gradeButton = (p: Page) =>
  p.getByRole("button", { name: "Grade ungraded responses", exact: true });
const dialog = (p: Page) =>
  p.getByRole("dialog", { name: "Grade responses with AI?", exact: true });
const progress = (p: Page, text: string | RegExp) =>
  p.getByRole("status").filter({ hasText: text });
const next = (p: Page) =>
  p.getByRole("button", { name: "Next page", exact: true });
const previous = (p: Page) =>
  p.getByRole("button", { name: "Previous page", exact: true });

async function loaded(page: Page) {
  await expect(usageTable(page)).toBeVisible();
  await expect(generationTable(page)).toBeVisible();
  await expect(
    itemsTable(page).or(
      qualityPanel(page).getByText("No assessed responses in this period.", {
        exact: true,
      }),
    ),
  ).toBeVisible();
}

async function ready(page: Page, configure?: (mock: AnalyticsMock) => void) {
  const mock = await setup(page);
  configure?.(mock);
  await page.goto(PATH);
  await loaded(page);
  return mock;
}

async function applyPeriod(page: Page, from: string, to: string) {
  await fromField(page).fill(from);
  await toField(page).fill(to);
  await apply(page).click();
}

async function setHeldClock(page: Page) {
  // Let routing and Suspense finish before freezing timers (the pattern of adm06-usage.spec.ts).
  const now = new Date();
  await page.clock.install({ time: now });
  await page.clock.pauseAt(new Date(now.getTime() + 1000));
}

async function openAndStartGrading(page: Page) {
  await gradeButton(page).click();
  await dialog(page)
    .getByRole("button", { name: "Start grading", exact: true })
    .click();
}

// ================================================================== AC40: structure, load, requests

test("adm01 AC40 page title, purpose, panels, period fields and the navigation links", async ({
  page,
}) => {
  await ready(page);
  await expect(title(page)).toBeVisible();
  await expect(page.getByText(MSG.purpose, { exact: true })).toBeVisible();
  for (const name of [
    "Reporting period",
    "Feature usage",
    "Generation reliability",
    "AI quality and session activity",
  ])
    await expect(region(page, name)).toBeVisible();
  await expect(fromField(page)).toBeVisible();
  await expect(toField(page)).toBeVisible();
  await expect(apply(page)).toBeVisible();
  await expect(
    periodPanel(page).getByText("Periods use UTC dates. Maximum 366 days.", {
      exact: true,
    }),
  ).toBeVisible();
  // ADM-07 P2-5 (reason: the legacy page has no nav link; the hub link "Feature Analytics" now owns
  // /admin/analytics). The demo-dashboard link "Analytics" is unchanged.
  await expect(
    page.getByRole("link", { name: "Feature Analytics", exact: true }),
  ).toHaveAttribute("href", "/admin/analytics");
  await expect(
    page.getByRole("link", { name: "Analytics", exact: true }),
  ).toHaveAttribute("href", "/admin/overview");
});

test("adm01 AC40 loading sends exactly three requests, in parallel, for the default last 30 days", async ({
  page,
}) => {
  const mock = await ready(page);
  expect(mock.count()).toBe(3);
  expect([...new Set(mock.requests.map((r) => r.kind))].sort()).toEqual([
    "generation",
    "quality",
    "usage",
  ]);
  const { from, to } = defaultPeriod();
  for (const r of mock.requests) {
    expect(r.url.searchParams.get("period_start")).toBe(from);
    expect(r.url.searchParams.get("period_end")).toBe(to);
  }
  const quality = mock.of("quality")[0].url.searchParams;
  expect(quality.get("workflow")).toBe("student_exercise");
  expect(quality.get("limit")).toBe("25");
  expect(quality.get("offset")).toBe("0");
  await expect(fromField(page)).toHaveValue(from);
  await expect(toField(page)).toHaveValue(to);
  await expect(tab(page, "Student exercises")).toHaveAttribute(
    "aria-selected",
    "true",
  );
});

test("adm01 AC40 each panel shows its own loading status and the others are not blocked", async ({
  page,
}) => {
  const mock = await setup(page);
  mock.next("usage", { hold: true });
  mock.next("generation", { hold: true });
  mock.next("quality", { hold: true });
  await page.goto(PATH);
  await expect(progress(page, "Loading feature usage...")).toBeVisible();
  await expect(
    progress(page, "Loading generation reliability..."),
  ).toBeVisible();
  await expect(progress(page, "Loading quality results...")).toBeVisible();
  await expect(tab(page, "Student exercises")).toBeVisible(); // the tab list stays while loading
  await expect(apply(page)).toBeEnabled(); // "Apply period" is not disabled by loading
  expect(mock.count()).toBe(3);
  mock.release();
  await loaded(page);
  await expect(progress(page, /Loading /)).toHaveCount(0);
  expect(mock.count()).toBe(3); // no duplicate requests (StrictMode) after the load
});

test("adm01 AC40 usage panel: tables, subtotals, grand total and the completion sentence", async ({
  page,
}) => {
  await ready(page);
  const panel = usagePanel(page);
  await expect(
    panel.getByRole("heading", { name: "Chatbot requests", exact: true }),
  ).toBeVisible();
  await expect(
    panel.getByRole("heading", {
      name: "Practice-set completion",
      exact: true,
    }),
  ).toBeVisible();
  const table = usageTable(page);
  for (const name of ["Name", "Successful", "Unsuccessful"])
    await expect(
      table.getByRole("columnheader", { name, exact: true }).first(),
    ).toBeVisible();
  await expect(table.getByText("Students", { exact: true })).toBeVisible();
  await expect(table.getByText("Teachers", { exact: true })).toBeVisible();
  await expect(
    table.getByRole("row").filter({ hasText: "Alice Tan" }),
  ).toContainText("5");
  await expect(
    table.getByRole("row").filter({ hasText: "Bob Lim" }),
  ).toContainText("7");
  const studentsTotal = table
    .getByRole("row")
    .filter({ hasText: "Students total" });
  await expect(studentsTotal).toContainText("12");
  await expect(studentsTotal).toContainText("3");
  // no teacher chatbot exists: its group and the grand total are unavailable, never 0
  await expect(
    table.getByRole("row").filter({ hasText: "Teachers total" }),
  ).toContainText("Unavailable: this activity is not recorded");
  await expect(
    table.getByRole("row").filter({ hasText: "All users total" }),
  ).toContainText("Unavailable: this activity is not recorded");
  await expect(
    panel.getByText(
      "66.7% (2 of 3 attempts submitted by the end of the period)",
      { exact: true },
    ),
  ).toBeVisible();
});

test("adm01 AC40 usage panel empty and not-applicable states", async ({
  page,
}) => {
  await ready(page, (mock) => {
    mock.tweak.usage = (body) => {
      Object.assign(body.chatbot.student, {
        successful: 0,
        unsuccessful: 0,
        rows: [],
      });
      Object.assign(body.practice_completion, {
        state: "not_applicable",
        reason: "no_practice_attempts",
        started: 0,
        submitted: 0,
        percentage: null,
      });
    };
  });
  const panel = usagePanel(page);
  await expect(
    panel.getByText("No chatbot requests in this period.", { exact: true }),
  ).toBeVisible();
  await expect(
    usageTable(page).getByRole("row").filter({ hasText: "Students total" }),
  ).toContainText("0");
  await expect(
    panel.getByText(
      "Not applicable: no practice attempts were started in this period.",
      { exact: true },
    ),
  ).toBeVisible();
  await expect(panel).not.toContainText("%");
});

for (const [reason, text] of [
  [
    "period_before_recording",
    "Unavailable: recording began on 2026-11-09, after this period started",
  ],
  ["no_source", "Unavailable: this activity is not recorded"],
  ["read_failed", "Unavailable: the value could not be read reliably"],
] as const) {
  test(`adm01 AC40 usage panel unavailable reason ${reason} is shown instead of a number`, async ({
    page,
  }) => {
    await ready(page, (mock) => {
      mock.tweak.usage = (body) => {
        body.recording_started_on = "2026-11-09";
        for (const group of ["student", "teacher", "total"])
          Object.assign(body.chatbot[group], {
            state: "unavailable",
            reason,
            successful: null,
            unsuccessful: null,
            rows: group === "total" ? undefined : [],
          });
        Object.assign(body.practice_completion, {
          state: "unavailable",
          reason,
          started: null,
          submitted: null,
          percentage: null,
        });
      };
    });
    const panel = usagePanel(page);
    await expect(panel).toContainText(text);
    await expect(
      panel.getByText("No chatbot requests in this period.", { exact: true }),
    ).toHaveCount(0);
    await expect(panel).not.toContainText("%");
  });
}

test("adm01 AC40 usage panel more than 500 users shows the truncation note", async ({
  page,
}) => {
  await ready(page, (mock) => {
    mock.tweak.usage = (body) => {
      body.chatbot.student.rows_truncated = true;
    };
  });
  await expect(
    usagePanel(page).getByText(
      "Showing the first 500 users; totals include all users.",
      { exact: true },
    ),
  ).toBeVisible();
});

test("adm01 AC40 generation panel: both workflows, rates and the no-rate message", async ({
  page,
}) => {
  await ready(page);
  const table = generationTable(page);
  for (const name of [
    "Workflow",
    "Attempts",
    "Successful",
    "Unsuccessful",
    "Success rate",
  ])
    await expect(
      table.getByRole("columnheader", { name, exact: true }),
    ).toBeVisible();
  const notes = table.getByRole("row").filter({ hasText: "Study notes" });
  await expect(notes).toContainText("66.7%");
  await expect(notes).toContainText("9");
  const mcq = table.getByRole("row").filter({ hasText: "MCQ batches" });
  await expect(mcq).toContainText(
    "No rate can be calculated: no generation attempts in this period.",
  );
  await expect(mcq).not.toContainText("%");
  await expect(mcq.getByRole("cell", { name: "0", exact: true })).toHaveCount(
    3,
  );
});

test("adm01 AC40 generation panel unavailable rows show their reason", async ({
  page,
}) => {
  await ready(page, (mock) => {
    mock.tweak.generation = (body) => {
      for (const row of body.workflows)
        Object.assign(row, {
          state: "unavailable",
          reason: "read_failed",
          attempts: null,
          successful: null,
          unsuccessful: null,
          rate_percent: null,
        });
    };
  });
  await expect(generationTable(page)).toContainText(
    "Unavailable: the value could not be read reliably",
  );
  await expect(generationTable(page)).not.toContainText("%");
});

test("adm01 AC40 quality panel: tabs, notice, sections, averages, times and the responses table", async ({
  page,
}) => {
  await ready(page);
  const panel = qualityPanel(page);
  await expect(
    page.getByRole("tablist", { name: "Assessment workflow", exact: true }),
  ).toBeVisible();
  await expect(tab(page, "Student exercises")).toHaveAttribute(
    "aria-selected",
    "true",
  );
  await expect(tab(page, "Teacher lesson planning")).toHaveAttribute(
    "aria-selected",
    "false",
  );
  await expect(panel.getByText(MSG.notice, { exact: true })).toBeVisible();
  await expect(panel).toContainText(
    "12 assessed, 5 waiting to be graded, 1 could not be graded",
  );
  for (const name of [
    "Quality grades",
    "Response time",
    "Session activity",
    "Associated activity time",
    "Assessed responses",
  ])
    await expect(
      panel.getByRole("heading", { name, exact: true }),
    ).toBeVisible();
  await expect(panel).toContainText("4.25 of 5 (12 graded, 0 unassessable)");
  await expect(panel).toContainText("3.50 of 5 (6 graded, 6 unassessable)");
  await expect(panel).toContainText("4.00 of 5 (12 graded, 0 unassessable)");
  await expect(panel).toContainText("5.00 of 5 (12 graded, 0 unassessable)");
  await expect(panel).toContainText(
    "Mean 2.4 s, median 2.1 s (40 successful responses); 3 failed or incomplete requests (no response time)",
  );
  await expect(panel).toContainText(
    "9 sessions, 6.50 messages per session (user and AI messages)",
  );
  await expect(panel).toContainText(
    /912\.5 s average elapsed time from Practice attempt started to Practice attempt submitted, 7\.14 messages per session, 7 linked sessions, 6 distinct activities, 2 sessions excluded \(activity has no recorded end\)\. Elapsed time includes idle time\./,
  );
  const table = itemsTable(page);
  for (const name of [
    "Received",
    "Response time",
    "Status",
    "Relevance",
    "Factual accuracy",
    "Clarity",
    "Safety",
  ])
    await expect(
      table.getByRole("columnheader", { name, exact: true }),
    ).toBeVisible();
  await expect(
    table.locator('time[datetime="2026-11-08T09:12:44Z"]'),
  ).toHaveCount(2);
  await expect(
    table.getByRole("row").filter({ hasText: "Graded" }).first(),
  ).toContainText("Reason relevance 1.");
  await expect(
    table.getByRole("row").filter({ hasText: "Waiting to be graded" }),
  ).toHaveCount(1);
  await expect(
    panel.getByText("Showing 1 to 2 of 2", { exact: true }),
  ).toBeVisible();
});

test("adm01 AC40 quality panel item statuses and unassessable grades use the exact labels", async ({
  page,
}) => {
  await ready(page, (mock) => {
    mock.total = 4;
    mock.tweak.quality = (body) => {
      const base = body.items.rows[0];
      body.items.rows = [
        {
          ...base,
          grades: base.grades.map((g: { dimension: string }) =>
            g.dimension === "factual_accuracy"
              ? {
                  dimension: g.dimension,
                  state: "unassessable",
                  score: null,
                  reason: "No authorised context was available.",
                }
              : g,
          ),
        },
        {
          ...base,
          item_id: 2001,
          status: "grading_failed",
          failure_code: "invalid_ai_output",
          grades: [],
          graded_at: null,
        },
        {
          ...base,
          item_id: 2002,
          status: "content_expired",
          grades: [],
          graded_at: null,
        },
        {
          ...base,
          item_id: 2003,
          status: "pending",
          grades: [],
          graded_at: null,
        },
      ];
    };
  });
  const table = itemsTable(page);
  await expect(table).toContainText("Unassessable");
  await expect(table).toContainText("No authorised context was available.");
  await expect(
    table.getByText("Could not be graded", { exact: true }),
  ).toBeVisible();
  await expect(
    table.getByText("Content no longer retained; not graded", { exact: true }),
  ).toBeVisible();
  await expect(
    table.getByText("Waiting to be graded", { exact: true }),
  ).toBeVisible();
  await expect(table.getByText("Graded", { exact: true })).toBeVisible();
});

test("adm01 AC40 quality panel empty states use the exact messages", async ({
  page,
}) => {
  await ready(page, (mock) => {
    mock.total = 0;
    mock.tweak.quality = (body) => {
      Object.assign(body.grades, {
        state: "not_applicable",
        reason: "none_graded",
        assessed_count: 0,
        pending_count: 0,
        dimensions: body.grades.dimensions.map((d: object) => ({
          ...d,
          average: null,
          graded_count: 0,
          unassessable_count: 0,
        })),
      });
      for (const key of ["response_time", "sessions", "activity_time"])
        Object.assign(body[key], {
          state: "not_applicable",
          reason: "no_eligible_records",
        });
    };
  });
  const panel = qualityPanel(page);
  await expect(
    panel.getByText("No responses have been graded for this period yet.", {
      exact: true,
    }),
  ).toBeVisible();
  await expect(
    panel.getByText("No assessed responses in this period.", { exact: true }),
  ).toBeVisible();
  await expect(
    panel
      .getByText(
        "No average can be calculated: no eligible records in this period.",
        { exact: true },
      )
      .first(),
  ).toBeVisible();
});

test("adm01 AC32 timing and counts are described as measurements, never as time saved or a no-AI comparison", async ({
  page,
}) => {
  await ready(page);
  const text = (await qualityPanel(page).innerText()).toLowerCase();
  expect(text).toContain("descriptive");
  expect(text).not.toContain("time saved");
  expect(text).not.toMatch(
    /baseline|without ai|no-ai|compared with|compared to/,
  );
});

test("adm01 AC40 teacher tab: sessions and activity time are unavailable with the exact reason", async ({
  page,
}) => {
  const mock = await ready(page);
  await tab(page, "Teacher lesson planning").click();
  await expect(tab(page, "Teacher lesson planning")).toHaveAttribute(
    "aria-selected",
    "true",
  );
  const panel = qualityPanel(page);
  await expect(
    panel
      .getByText(
        "Unavailable: no conversation sessions are recorded for this workflow.",
        { exact: true },
      )
      .first(),
  ).toBeVisible();
  await expect(
    panel.getByRole("heading", { name: "Session activity", exact: true }),
  ).toBeVisible();
  await expect(
    panel.getByRole("heading", {
      name: "Associated activity time",
      exact: true,
    }),
  ).toBeVisible();
  expect(mock.of("quality").at(-1)!.url.searchParams.get("workflow")).toBe(
    "teacher_lesson_planning",
  );
});

test("adm01 AC11 AC40 names and reasons render as plain text, never as markup", async ({
  page,
}) => {
  await ready(page, (mock) => {
    mock.tweak.usage = (body) => {
      body.chatbot.student.rows[0].name = "<img src=x onerror=alert(1)>";
    };
    mock.tweak.quality = (body) => {
      body.items.rows[0].grades[0].reason =
        "<script>window.__pwned = 1</script>";
    };
  });
  await expect(page.locator("img[src=x]")).toHaveCount(0);
  await expect(usagePanel(page)).toContainText("<img src=x onerror=alert(1)>");
  await expect(itemsTable(page)).toContainText(
    "<script>window.__pwned = 1</script>",
  );
  expect(
    await page.evaluate(
      () => (window as unknown as { __pwned?: number }).__pwned,
    ),
  ).toBeUndefined();
});

test("adm01 AC40 the page stores no analytics data in the browser", async ({
  page,
}) => {
  await ready(page);
  await expectNoSecretsInBrowser(page, [
    "Alice Tan",
    "Bob Lim",
    "u-3f9a1c2b",
    "66.7",
  ]);
});

// ================================================================== AC40: failure states

for (const [panelName, subject, kind, name, what] of [
  ["usage", "Feature usage", "usage", "Feature usage", "feature usage"],
  [
    "generation",
    "Generation reliability",
    "generation",
    "Generation reliability",
    "generation reliability",
  ],
  [
    "quality",
    "Quality results",
    "quality",
    "AI quality and session activity",
    "quality results",
  ],
] as const) {
  const panelOf = (p: Page) => region(p, name);

  test(`adm01 AC40 ${panelName} panel network failure: exact message, own Retry, one request, others unaffected`, async ({
    page,
  }) => {
    const mock = await setup(page);
    mock.next(kind, { abort: true });
    await page.goto(PATH);
    await expect(alertWith(panelOf(page), MSG.network)).toBeVisible();
    await expect(retry(page, what)).toBeVisible();
    for (const other of [usageTable, generationTable, itemsTable].filter(
      (_, i) => ["usage", "generation", "quality"][i] !== kind,
    ))
      await expect(other(page)).toBeVisible(); // one failed panel does not hide the others
    await expect(title(page)).toBeVisible();
    await expect(periodPanel(page)).toBeVisible();
    const before = mock.count();
    await retry(page, what).click();
    await loaded(page);
    expect(mock.count() - before).toBe(1); // Retry sends exactly that panel's request
    expect(mock.count(kind)).toBe(2);
    expect(mock.count()).toBe(4);
  });

  for (const status of [500, 502, 503, 504, 404]) {
    test(`adm01 AC40 ${panelName} panel HTTP ${status}: exact copy with the status, server message ignored`, async ({
      page,
    }) => {
      const mock = await setup(page);
      mock.next(kind, {
        status,
        code: "boom",
        message: "Traceback: private server detail",
      });
      await page.goto(PATH);
      await expect(
        alertWith(panelOf(page), MSG.http(subject, status)),
      ).toBeVisible();
      await expect(page.getByText("private server detail")).toHaveCount(0);
      await expect(page.getByText(/something went wrong/i)).toHaveCount(0);
      await expect(page.getByText("Could not reach the server.")).toHaveCount(
        0,
      ); // network copy only for a network failure
      await expect(retry(page, what)).toBeVisible();
    });
  }

  test(`adm01 AC40 ${panelName} panel 403: the access message`, async ({
    page,
  }) => {
    const mock = await setup(page);
    mock.next(kind, { status: 403, code: "forbidden" });
    await page.goto(PATH);
    await expect(alertWith(panelOf(page), MSG.forbidden)).toBeVisible();
  });
}

test("adm01 AC40 backend down: every panel says so with its own Retry, the title and period panel stay", async ({
  page,
}) => {
  const mock = await setup(page);
  for (const kind of ["usage", "generation", "quality"] as const)
    mock.next(kind, { abort: true });
  await page.goto(PATH);
  for (const name of [
    "Feature usage",
    "Generation reliability",
    "AI quality and session activity",
  ])
    await expect(alertWith(region(page, name), MSG.network)).toBeVisible();
  for (const what of [
    "feature usage",
    "generation reliability",
    "quality results",
  ])
    await expect(retry(page, what)).toBeVisible();
  await expect(title(page)).toBeVisible();
  await expect(periodPanel(page)).toBeVisible();
  // recovery by "Apply period" with a changed period
  await applyPeriod(page, "2026-01-01", "2026-01-31");
  await loaded(page);
  expect(mock.count()).toBe(6);
});

test("adm01 AC40 a malformed 200 body is a failure with the status-style copy, never a blank panel", async ({
  page,
}) => {
  const mock = await setup(page);
  mock.next("usage", { malformed: true });
  await page.goto(PATH);
  await expect(usagePanel(page).getByRole("alert")).toBeVisible();
  await expect(usageTable(page)).toHaveCount(0);
  await expect(retry(page, "feature usage")).toBeVisible();
  await expect(generationTable(page)).toBeVisible();
});

test("adm01 AC40 a 15 second wait ends in the exact timeout message and no automatic retry", async ({
  page,
}) => {
  const mock = await ready(page);
  await setHeldClock(page);
  mock.next("usage", { hold: true });
  await applyPeriod(page, "2026-01-01", "2026-01-31");
  await expect.poll(() => mock.count("usage")).toBe(2);
  await expect(progress(page, "Loading feature usage...")).toBeVisible();
  await page.clock.fastForward(14_900);
  await expect(alertWith(usagePanel(page), MSG.timeout)).toHaveCount(0);
  await page.clock.fastForward(200);
  await expect(alertWith(usagePanel(page), MSG.timeout)).toBeVisible();
  expect(mock.count("usage")).toBe(2); // no automatic retry
  await expect(retry(page, "feature usage")).toBeVisible();
  mock.release();
});

test("adm01 AC40 assessed-responses page failure keeps the current page and shows the message above the table", async ({
  page,
}) => {
  const mock = await ready(page, (m) => {
    m.total = 30;
  });
  await expect(
    qualityPanel(page).getByText("Showing 1 to 25 of 30", { exact: true }),
  ).toBeVisible();
  mock.next("quality", { status: 500 });
  await next(page).click();
  await expect(
    alertWith(qualityPanel(page), MSG.http("Assessed responses", 500)),
  ).toBeVisible();
  await expect(
    qualityPanel(page).getByText("Showing 1 to 25 of 30", { exact: true }),
  ).toBeVisible();
  await expect(itemsTable(page)).toBeVisible();
  await expect(tab(page, "Student exercises")).toBeVisible();
  await expect(
    qualityPanel(page).getByText(MSG.notice, { exact: true }),
  ).toBeVisible(); // notice and tabs stay
});

test("adm01 AC40 a failed tab switch selects the clicked tab and shows the failure with Retry quality results", async ({
  page,
}) => {
  const mock = await ready(page);
  mock.next("quality", { status: 503 });
  await tab(page, "Teacher lesson planning").click();
  await expect(tab(page, "Teacher lesson planning")).toHaveAttribute(
    "aria-selected",
    "true",
  );
  await expect(
    alertWith(qualityPanel(page), MSG.http("Quality results", 503)),
  ).toBeVisible();
  await expect(usageTable(page)).toBeVisible();
  await expect(generationTable(page)).toBeVisible();
  const before = mock.count();
  await retry(page, "quality results").click();
  await expect(
    alertWith(qualityPanel(page), "could not be loaded"),
  ).toHaveCount(0);
  expect(mock.count() - before).toBe(1);
  expect(mock.of("quality").at(-1)!.url.searchParams.get("workflow")).toBe(
    "teacher_lesson_planning",
  );
});

// ================================================================== AC40/AC42: requests per action, URL, history

test("adm01 AC42 Apply period: a changed period sends three requests and pushes, an unchanged one sends none", async ({
  page,
}) => {
  const mock = await ready(page);
  const entries = await page.evaluate(() => history.length);
  await applyPeriod(page, "2026-01-01", "2026-01-31");
  await expect.poll(() => mock.count()).toBe(6);
  await expect(page).toHaveURL(/from=2026-01-01/);
  await expect(page).toHaveURL(/to=2026-01-31/);
  expect(await page.evaluate(() => history.length)).toBe(entries + 1); // push
  for (const r of mock.requests.slice(3)) {
    expect(r.url.searchParams.get("period_start")).toBe("2026-01-01");
    expect(r.url.searchParams.get("period_end")).toBe("2026-01-31");
  }
  await loaded(page);
  await apply(page).click(); // unchanged
  await page.waitForTimeout(400);
  expect(mock.count()).toBe(6);
  expect(await page.evaluate(() => history.length)).toBe(entries + 1);
});

test("adm01 AC42 Back and Forward restore the period and reload from the URL", async ({
  page,
}) => {
  const mock = await ready(page);
  const { from, to } = defaultPeriod();
  await applyPeriod(page, "2026-01-01", "2026-01-31");
  await loaded(page);
  await expect.poll(() => mock.count()).toBe(6);
  await page.goBack();
  await expect(fromField(page)).toHaveValue(from);
  await expect(toField(page)).toHaveValue(to);
  await expect.poll(() => mock.count()).toBe(9); // the period changed: three requests
  await page.goForward();
  await expect(fromField(page)).toHaveValue("2026-01-01");
  await expect(toField(page)).toHaveValue("2026-01-31");
  await expect.poll(() => mock.count()).toBe(12);
});

test("adm01 AC42 switching the workflow tab sends one quality request and replaces the URL", async ({
  page,
}) => {
  const mock = await setup(page);
  await page.goto("/admin/overview");
  // ADM-07 P2-5 (reason: no nav link to the legacy page): enter it by a push navigation instead.
  await page.evaluate((to) => {
    window.history.pushState({}, "", to);
    window.dispatchEvent(new PopStateEvent("popstate"));
  }, PATH); // push
  await expect(page).toHaveURL(/\/admin\/feature-analytics-legacy/);
  await loaded(page);
  const before = mock.count();
  await tab(page, "Teacher lesson planning").click();
  await expect(tab(page, "Teacher lesson planning")).toHaveAttribute(
    "aria-selected",
    "true",
  );
  await expect(page).toHaveURL(/workflow=teacher_lesson_planning/);
  await expect.poll(() => mock.count() - before).toBe(1);
  expect(mock.of("quality").at(-1)!.url.searchParams.get("workflow")).toBe(
    "teacher_lesson_planning",
  );
  await page.goBack(); // replace: the tab switch added no history entry
  await expect(page).toHaveURL(/\/admin\/overview/);
});

test("adm01 AC42 only the workflow changing in history reloads one request", async ({
  page,
}) => {
  const mock = await ready(page);
  await applyPeriod(page, "2026-01-01", "2026-01-31"); // push
  await loaded(page);
  await expect.poll(() => mock.count()).toBe(6);
  await tab(page, "Teacher lesson planning").click(); // replace
  await expect.poll(() => mock.count()).toBe(7);
  await page.reload();
  await loaded(page);
  await expect(tab(page, "Teacher lesson planning")).toHaveAttribute(
    "aria-selected",
    "true",
  );
  await expect(fromField(page)).toHaveValue("2026-01-01");
  await expect.poll(() => mock.count()).toBe(10); // refresh: three requests
  const last = mock.of("quality").at(-1)!.url.searchParams;
  expect(last.get("workflow")).toBe("teacher_lesson_planning");
  expect(last.get("period_start")).toBe("2026-01-01");
});

test("adm01 AC42 Retry on one panel sends exactly one request", async ({
  page,
}) => {
  const mock = await setup(page);
  mock.next("generation", { status: 500 });
  await page.goto(PATH);
  await expect(
    alertWith(generationPanel(page), "could not be loaded"),
  ).toBeVisible();
  expect(mock.count()).toBe(3);
  await retry(page, "generation reliability").click();
  await loaded(page);
  expect(mock.count()).toBe(4);
  expect(mock.count("generation")).toBe(2);
});

test("adm01 AC42 pagination sends one request per click, keeps the URL and disables the end buttons", async ({
  page,
}) => {
  const mock = await ready(page, (m) => {
    m.total = 30;
  });
  const url = page.url();
  const panel = qualityPanel(page);
  await expect(
    panel.getByText("Showing 1 to 25 of 30", { exact: true }),
  ).toBeVisible();
  await expect(previous(page)).toBeDisabled();
  await expect(next(page)).toBeEnabled();
  const before = mock.count();
  await next(page).click();
  await expect(
    panel.getByText("Showing 26 to 30 of 30", { exact: true }),
  ).toBeVisible();
  expect(mock.count() - before).toBe(1);
  expect(mock.of("quality").at(-1)!.url.searchParams.get("offset")).toBe("25");
  await expect(next(page)).toBeDisabled();
  await expect(previous(page)).toBeEnabled();
  expect(page.url()).toBe(url); // no URL change
  await previous(page).click();
  await expect(
    panel.getByText("Showing 1 to 25 of 30", { exact: true }),
  ).toBeVisible();
  expect(mock.of("quality").at(-1)!.url.searchParams.get("offset")).toBe("0");
});

test("adm01 AC42 pagination buttons are disabled while the page request is pending", async ({
  page,
}) => {
  const mock = await ready(page, (m) => {
    m.total = 60;
  });
  mock.next("quality", { hold: true });
  await next(page).click();
  await expect(next(page)).toBeDisabled();
  await expect(previous(page)).toBeDisabled();
  mock.release();
  await expect(
    qualityPanel(page).getByText("Showing 26 to 50 of 60", { exact: true }),
  ).toBeVisible();
});

test("adm01 AC42 the URL query restores the period and workflow on load", async ({
  page,
}) => {
  const mock = await setup(page);
  await page.goto(
    `${PATH}?from=2026-10-01&to=2026-10-31&workflow=teacher_lesson_planning`,
  );
  await loaded(page);
  await expect(fromField(page)).toHaveValue("2026-10-01");
  await expect(toField(page)).toHaveValue("2026-10-31");
  await expect(tab(page, "Teacher lesson planning")).toHaveAttribute(
    "aria-selected",
    "true",
  );
  expect(mock.count()).toBe(3);
  for (const r of mock.requests) {
    expect(r.url.searchParams.get("period_start")).toBe("2026-10-01");
    expect(r.url.searchParams.get("period_end")).toBe("2026-10-31");
  }
  expect(mock.of("quality")[0].url.searchParams.get("workflow")).toBe(
    "teacher_lesson_planning",
  );
});

for (const query of [
  "?from=2026-13-45&to=abc&workflow=nope",
  "?from=2026-10-31&to=2026-10-01",
  "?from=2024-01-01&to=2026-01-01",
  "?from=2026-10-01",
  "?workflow=STUDENT_EXERCISE",
]) {
  test(`adm01 AC42 an invalid or incomplete URL query ${query} falls back to the defaults without a message`, async ({
    page,
  }) => {
    const mock = await setup(page);
    await page.goto(PATH + query);
    await loaded(page);
    const { from, to } = defaultPeriod();
    await expect(fromField(page)).toHaveValue(from);
    await expect(toField(page)).toHaveValue(to);
    await expect(tab(page, "Student exercises")).toHaveAttribute(
      "aria-selected",
      "true",
    );
    await expect(page.getByRole("alert")).toHaveCount(0);
    expect(mock.count()).toBe(3);
  });
}

// ================================================================== AC41: client-side period validation

for (const [label, from, to, field, message] of [
  ["empty start", "", "2026-01-31", "from", MSG.period.format],
  ["empty end", "2026-01-01", "", "to", MSG.period.format],
  ["start after end", "2026-02-01", "2026-01-01", "from", MSG.period.order],
  ["367 days", "2025-01-01", "2026-01-02", "to", MSG.period.long],
] as const) {
  test(`adm01 AC41 ${label}: exact message, no request, values kept, focus on the first invalid field`, async ({
    page,
  }) => {
    const mock = await ready(page);
    await applyPeriod(page, from, to);
    const invalid = field === "from" ? fromField(page) : toField(page);
    await expect(invalid).toHaveAttribute("aria-invalid", "true");
    await expect(invalid).toHaveAccessibleDescription(
      new RegExp(message.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")),
    );
    await expect(
      periodPanel(page).getByText(message, { exact: true }),
    ).toBeVisible();
    await expect(invalid).toBeFocused();
    await expect(fromField(page)).toHaveValue(from);
    await expect(toField(page)).toHaveValue(to);
    await expect(usageTable(page)).toBeVisible(); // the previous results stay
    expect(mock.count()).toBe(3);
  });
}

test("adm01 AC41 two invalid fields: focus goes to the first, and a corrected period then loads", async ({
  page,
}) => {
  const mock = await ready(page);
  await applyPeriod(page, "", "");
  await expect(fromField(page)).toBeFocused();
  await expect(
    periodPanel(page).getByText(MSG.period.format, { exact: true }),
  ).toHaveCount(2);
  await applyPeriod(page, "2025-01-01", "2026-01-01"); // exactly 366 days is valid
  await expect.poll(() => mock.count()).toBe(6);
  await expect(
    periodPanel(page).getByText(MSG.period.format, { exact: true }),
  ).toHaveCount(0);
  await expect(fromField(page)).not.toHaveAttribute("aria-invalid", "true");
});

// ================================================================== AC44: roles, anonymous, 401

for (const [who, user, home] of [
  ["student", STUDENT, /\/student\/overview$/],
  ["teacher", TEACHER, /\/teacher\/overview$/],
] as const) {
  test(`adm01 AC44 a ${who} is redirected with replace to their own home and no analytics request is sent`, async ({
    page,
  }) => {
    const mock = await setup(page, { user });
    await page.goto(
      user === STUDENT ? "/student/overview" : "/teacher/overview",
    );
    const entries = await page.evaluate(() => history.length);
    await page.goto(PATH);
    await expect(page).toHaveURL(home);
    expect(await page.evaluate(() => history.length)).toBe(entries + 1); // replaced, not pushed
    expect(mock.count()).toBe(0);
    await expect(title(page)).toHaveCount(0);
    await expect(usageTable(page)).toHaveCount(0);
    await page.goBack();
    await expect(page).not.toHaveURL(/\/admin\/analytics/);
  });
}

test("adm01 AC44 an anonymous visitor is sent to the sign-in page with replace and no analytics request", async ({
  page,
}) => {
  const mock = await setup(page, { user: null });
  await page.goto("/login");
  const entries = await page.evaluate(() => history.length);
  await page.goto(PATH);
  await expect(page).toHaveURL(/\/login$/);
  expect(await page.evaluate(() => history.length)).toBe(entries + 1);
  expect(mock.count()).toBe(0);
  await expect(usageTable(page)).toHaveCount(0);
  await page.goBack();
  await expect(page).not.toHaveURL(/\/admin\/analytics/);
});

test("adm01 AC44 an anonymous visitor with the query string also sends nothing", async ({
  page,
}) => {
  const mock = await setup(page, { user: null });
  await page.goto(
    `${PATH}?from=2026-01-01&to=2026-01-31&workflow=teacher_lesson_planning`,
  );
  await expect(page).toHaveURL(/\/login/);
  await page.waitForTimeout(300);
  expect(mock.count()).toBe(0);
});

test("adm01 AC44 a 401 from an analytics request ends the session at sign-in and leaves no data on screen", async ({
  page,
}) => {
  const mock = await ready(page);
  mock.auth.expire();
  mock.next("usage", { status: 401, code: "unauthenticated" });
  await applyPeriod(page, "2026-01-01", "2026-01-31");
  await expect(page).toHaveURL(/\/login/);
  await expect(
    page.getByText("Your session has expired. Sign in again.", { exact: true }),
  ).toBeVisible();
  await expect(usageTable(page)).toHaveCount(0);
  await expect(page.getByText("Alice Tan")).toHaveCount(0);
  await page.goBack();
  await expect(usageTable(page)).toHaveCount(0);
  await expect(page.getByText("Alice Tan")).toHaveCount(0);
});

test("adm01 AC44 logging out clears the report and Back shows sign-in, not stale analytics", async ({
  page,
}) => {
  await ready(page);
  await logOutWithConfirmation(page);
  await expect(page).toHaveURL(/\/login/);
  await page.goBack();
  await expect(usageTable(page)).toHaveCount(0);
  await expect(page.getByText("Alice Tan")).toHaveCount(0);
});

// ================================================================== AC43: grading dialog, start, progress, failures

test("adm01 AC43 the grading dialog has the exact title, text and buttons; Cancel and Escape send nothing and return focus", async ({
  page,
}) => {
  const mock = await ready(page);
  await expect(gradeButton(page)).toBeEnabled();
  await gradeButton(page).click();
  const d = dialog(page);
  await expect(d).toBeVisible();
  await expect(
    d.getByText(
      "Up to 20 ungraded responses from this workflow and period will be sent to the SoC LLM service for grading. Grades are advisory.",
      { exact: true },
    ),
  ).toBeVisible();
  await expect(
    d.getByRole("button", { name: "Start grading", exact: true }),
  ).toBeVisible();
  await d.getByRole("button", { name: "Cancel", exact: true }).click();
  await expect(d).toHaveCount(0);
  await expect(gradeButton(page)).toBeFocused();
  await gradeButton(page).click();
  await page.keyboard.press("Escape");
  await expect(d).toHaveCount(0);
  await expect(gradeButton(page)).toBeFocused();
  expect(mock.count("start")).toBe(0);
  expect(mock.count()).toBe(3);
});

test("adm01 AC43 starting sends one POST with the workflow and period, then polls until the run finishes and reloads quality once", async ({
  page,
}) => {
  test.setTimeout(60_000);
  const mock = await ready(page);
  mock.startRun = { items_total: 3 };
  mock.runStates = [
    {
      status: "running",
      items_graded: 1,
      items_total: 3,
      started_at: "2026-11-09T05:00:01Z",
    },
    {
      status: "completed",
      items_graded: 2,
      items_failed: 1,
      items_total: 3,
      finished_at: "2026-11-09T05:00:07Z",
    },
  ];
  const qualityBefore = mock.count("quality");
  await openAndStartGrading(page);
  await expect(dialog(page)).toHaveCount(0);
  expect(mock.count("start")).toBe(1);
  const post = mock.of("start")[0];
  expect(post.url.pathname).toBe(`${API}/grading-runs`);
  const { from, to } = defaultPeriod();
  expect(post.body).toEqual({
    workflow: "student_exercise",
    period_start: from,
    period_end: to,
  });
  await expect(
    progress(page, "Grading is running: 0 of 3 responses graded."),
  ).toBeVisible();
  await expect(gradeButton(page)).toBeDisabled(); // while a run is queued or running
  await expect(
    progress(page, "Grading is running: 1 of 3 responses graded."),
  ).toBeVisible({ timeout: 8000 });
  await expect(
    progress(page, "Grading finished: 2 graded, 1 could not be graded."),
  ).toBeVisible({ timeout: 8000 });
  await expect(gradeButton(page)).toBeEnabled();
  await expect.poll(() => mock.count("quality")).toBe(qualityBefore + 1); // the quality panel reloads once
  expect(mock.count("start")).toBe(1);
  const polls = mock.count("run");
  await page.waitForTimeout(3500);
  expect(mock.count("run")).toBe(polls); // polling stopped in the terminal state
  for (const r of mock.of("run"))
    expect(r.url.pathname).toBe(`${API}/grading-runs/12`);
});

test("adm01 AC43 the start button is disabled while the start request is pending", async ({
  page,
}) => {
  const mock = await ready(page);
  mock.next("start", { hold: true });
  await openAndStartGrading(page);
  await expect(gradeButton(page)).toBeDisabled();
  expect(mock.count("start")).toBe(1);
  mock.release();
  await expect(
    progress(page, /Grading is running: 0 of 3 responses graded\./),
  ).toBeVisible();
});

test("adm01 AC43 a run with nothing to grade says so", async ({ page }) => {
  test.setTimeout(30_000);
  const mock = await ready(page);
  mock.startRun = { status: "queued", items_total: 0, items_graded: 0 }; // as the server returns it (plan)
  mock.runStates = [
    {
      status: "completed",
      items_total: 0,
      items_graded: 0,
      finished_at: "2026-11-09T05:00:02Z",
    },
  ];
  await openAndStartGrading(page);
  await expect(
    progress(page, "No ungraded responses are available for this period."),
  ).toBeVisible({ timeout: 8000 });
  await expect(gradeButton(page)).toBeEnabled();
});

for (const [code, copy] of Object.entries(RUN_FAILURE_COPY)) {
  test(`adm01 AC43 a failed run (${code}) is reported with its copy and the number graded`, async ({
    page,
  }) => {
    test.setTimeout(30_000);
    const mock = await ready(page);
    mock.startRun = { items_total: 3 };
    mock.runStates = [
      {
        status: "failed",
        failure_code: code,
        items_graded: 1,
        items_total: 3,
        finished_at: "2026-11-09T05:00:05Z",
      },
    ];
    await openAndStartGrading(page);
    await expect(
      progress(
        page,
        `Grading stopped: ${copy}. 1 of 3 responses were graded before it stopped.`,
      ),
    ).toBeVisible({ timeout: 8000 });
    await expect(gradeButton(page)).toBeEnabled();
  });
}

for (const [label, step, message] of [
  ["409", { status: 409, code: "grading_run_active" }, MSG.start.conflict],
  ["429", { status: 429, code: "grading_quota" }, MSG.start.quota],
  ["403", { status: 403, code: "forbidden" }, MSG.start.forbidden],
  [
    "422",
    {
      status: 422,
      code: "invalid_workflow",
      message: "Choose student_exercise or teacher_lesson_planning.",
    },
    "Choose student_exercise or teacher_lesson_planning.",
  ],
  ["network", { abort: true }, MSG.start.network],
] as [string, Step, string][]) {
  test(`adm01 AC43 a failed start (${label}) shows its exact message, closes the dialog, keeps results and the period, sends once`, async ({
    page,
  }) => {
    const mock = await ready(page);
    const { from, to } = defaultPeriod();
    if (label === "409") {
      mock.tweak.quality = (body) => {
        body.active_run = run({ status: "running", items_total: 3 });
      };
    }
    mock.next("start", step);
    await openAndStartGrading(page);
    await expect(
      page.getByText(message, { exact: true }).first(),
    ).toBeVisible();
    await expect(dialog(page)).toHaveCount(0);
    await expect(itemsTable(page)).toBeVisible();
    await expect(fromField(page)).toHaveValue(from);
    await expect(toField(page)).toHaveValue(to);
    if (label === "409")
      await expect(gradeButton(page)).toBeDisabled(); // a run is active
    else await expect(gradeButton(page)).toBeEnabled();
    await page.waitForTimeout(300);
    expect(mock.count("start")).toBe(1); // no automatic retry
    expect(mock.count("run")).toBe(0);
  });
}

test("adm01 AC43 a start that times out after 15 seconds says to reload and does not retry", async ({
  page,
}) => {
  const mock = await ready(page);
  await setHeldClock(page);
  mock.next("start", { hold: true });
  await openAndStartGrading(page);
  await expect.poll(() => mock.count("start")).toBe(1);
  await page.clock.fastForward(15_100);
  await expect(alertWith(qualityPanel(page), MSG.start.timeout)).toBeVisible();
  expect(mock.count("start")).toBe(1);
  mock.release();
});

test("adm01 AC43 a polling network failure stops polling and Check progress sends exactly one request", async ({
  page,
}) => {
  test.setTimeout(40_000);
  const mock = await ready(page);
  mock.startRun = { items_total: 3 };
  mock.next("run", { abort: true });
  await openAndStartGrading(page);
  await expect(page.getByText(MSG.poll.network, { exact: true })).toBeVisible({
    timeout: 8000,
  });
  const check = page.getByRole("button", {
    name: "Check progress",
    exact: true,
  });
  await expect(check).toBeVisible();
  const polls = mock.count("run");
  await page.waitForTimeout(3500);
  expect(mock.count("run")).toBe(polls); // polling stopped after the failure
  mock.runStates = [
    {
      status: "completed",
      items_graded: 3,
      items_total: 3,
      finished_at: "2026-11-09T05:00:09Z",
    },
  ];
  await check.click();
  await expect.poll(() => mock.count("run")).toBe(polls + 1);
  await expect(
    progress(page, "Grading finished: 3 graded, 0 could not be graded."),
  ).toBeVisible();
});

test("adm01 AC43 a polling HTTP error uses the progress copy with the status", async ({
  page,
}) => {
  test.setTimeout(30_000);
  const mock = await ready(page);
  mock.startRun = { items_total: 3 };
  mock.next("run", { status: 500 });
  await openAndStartGrading(page);
  await expect(page.getByText(MSG.poll.http(500), { exact: true })).toBeVisible(
    { timeout: 8000 },
  );
  await expect(
    page.getByRole("button", { name: "Check progress", exact: true }),
  ).toBeVisible();
  await expect(page.getByText(/something went wrong/i)).toHaveCount(0);
});

test("adm01 AC43 a polling request that takes 15 seconds says grading may still be running", async ({
  page,
}) => {
  const mock = await ready(page);
  mock.startRun = { items_total: 3 };
  await openAndStartGrading(page);
  await expect(
    progress(page, "Grading is running: 0 of 3 responses graded."),
  ).toBeVisible();
  await setHeldClock(page);
  mock.next("run", { hold: true });
  await page.clock.fastForward(3100);
  await expect.poll(() => mock.count("run")).toBe(1);
  await page.clock.fastForward(15_100);
  await expect(page.getByText(MSG.poll.timeout, { exact: true })).toBeVisible();
  expect(mock.count("run")).toBe(1);
  mock.release();
});

test("adm01 AC43 AC44 a 401 while polling ends the session and stops polling", async ({
  page,
}) => {
  test.setTimeout(30_000);
  const mock = await ready(page);
  mock.startRun = { items_total: 3 };
  mock.auth.expire();
  mock.next("run", { status: 401, code: "unauthenticated" });
  await openAndStartGrading(page);
  await expect(page).toHaveURL(/\/login/, { timeout: 8000 });
  const polls = mock.count("run");
  await page.waitForTimeout(3500);
  expect(mock.count("run")).toBe(polls);
});

test("adm01 AC42 an active run in the quality response is shown again and resumes polling without a start request", async ({
  page,
}) => {
  test.setTimeout(30_000);
  const mock = await ready(page, (m) => {
    m.tweak.quality = (body) => {
      body.active_run = run({
        status: "running",
        items_graded: 1,
        items_total: 3,
        started_at: "2026-11-09T05:00:01Z",
      });
    };
    m.runStates = [{ status: "running", items_graded: 2, items_total: 3 }];
  });
  await expect(
    progress(page, "Grading is running: 1 of 3 responses graded."),
  ).toBeVisible();
  await expect(gradeButton(page)).toBeDisabled();
  expect(mock.count("start")).toBe(0);
  expect(mock.count("run")).toBe(0); // the first poll comes after the interval, not on load
  await expect(
    progress(page, "Grading is running: 2 of 3 responses graded."),
  ).toBeVisible({ timeout: 8000 });
  expect(mock.count("start")).toBe(0);
});

// ================================================================== AC45: keyboard, accessibility

test("adm01 AC45 the period controls are reachable in reading order and Apply works from the keyboard", async ({
  page,
}) => {
  const mock = await ready(page);
  await fromField(page).focus();
  for (
    let i = 0;
    i < 5 &&
    !(await toField(page).evaluate((el) => el === document.activeElement));
    i++
  )
    await page.keyboard.press("Tab");
  await expect(toField(page)).toBeFocused();
  for (
    let i = 0;
    i < 5 &&
    !(await apply(page).evaluate((el) => el === document.activeElement));
    i++
  )
    await page.keyboard.press("Tab");
  await expect(apply(page)).toBeFocused();
  await fromField(page).fill("2026-03-01");
  await toField(page).fill("2026-03-31");
  await apply(page).focus();
  await page.keyboard.press("Enter");
  await expect.poll(() => mock.count()).toBe(6);
});

test("adm01 AC45 the workflow tabs move with the arrow keys and the grade dialog traps focus", async ({
  page,
}) => {
  await ready(page);
  await tab(page, "Student exercises").focus();
  await page.keyboard.press("ArrowRight");
  await expect(tab(page, "Teacher lesson planning")).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(tab(page, "Teacher lesson planning")).toHaveAttribute(
    "aria-selected",
    "true",
  );
  await gradeButton(page).focus();
  await page.keyboard.press("Enter");
  await expect(dialog(page)).toBeVisible();
  for (let i = 0; i < 6; i++) {
    await page.keyboard.press("Tab");
    expect(
      await dialog(page).evaluate((el) => el.contains(document.activeElement)),
    ).toBe(true);
  }
  await page.keyboard.press("Escape");
  await expect(dialog(page)).toHaveCount(0);
  await expect(gradeButton(page)).toBeFocused();
});

test("adm01 AC45 every named control and landmark is exposed by role and name", async ({
  page,
}) => {
  await ready(page);
  await expect(
    page.getByRole("tablist", { name: "Assessment workflow", exact: true }),
  ).toBeVisible();
  await expect(page.getByRole("tabpanel")).toBeVisible();
  for (const control of [
    fromField(page),
    toField(page),
    apply(page),
    gradeButton(page),
  ]) {
    await control.focus();
    await expect(control).toBeFocused();
  }
  await expect(
    usageTable(page)
      .getByRole("rowheader")
      .or(usageTable(page).getByRole("row"))
      .first(),
  ).toBeVisible();
});

// ================================================================== AC45: responsive, themes, motion

async function outlined(page: Page, label: string) {
  const field = page.getByLabel(label, { exact: true });
  const outline = field.locator("..").locator("fieldset");
  await expect(field).toBeVisible();
  await expect(outline).toHaveCSS("border-top-style", "solid");
  const contrast = await outline.evaluate((el) => {
    const rgba = (color: string) => {
      const channels = color.match(/[\d.]+/g)!.map(Number);
      return [...channels.slice(0, 3), channels[3] ?? 1];
    };
    const over = (front: number[], back: number[]) =>
      front
        .slice(0, 3)
        .map(
          (channel, index) => channel * front[3] + back[index] * (1 - front[3]),
        );
    const ancestors: Element[] = [];
    for (let node = el.parentElement; node; node = node.parentElement)
      ancestors.unshift(node);
    let background = [255, 255, 255];
    for (const node of ancestors)
      background = over(
        rgba(getComputedStyle(node).backgroundColor),
        background,
      );
    const luminance = (color: number[]) => {
      const channels = color.map((value) => {
        const channel = value / 255;
        return channel <= 0.04045
          ? channel / 12.92
          : ((channel + 0.055) / 1.055) ** 2.4;
      });
      return channels[0] * 0.2126 + channels[1] * 0.7152 + channels[2] * 0.0722;
    };
    const border = luminance(
      over(rgba(getComputedStyle(el).borderTopColor), background),
    );
    const surface = luminance(background);
    return (
      (Math.max(border, surface) + 0.05) / (Math.min(border, surface) + 0.05)
    );
  });
  expect(contrast).toBeGreaterThanOrEqual(3);
}

for (const theme of ["light", "dark"] as const) {
  for (const width of [320, 390]) {
    test(`adm01 AC45 ${theme} ${width}px: no horizontal page scroll, controls visible and outlined`, async ({
      page,
    }) => {
      await page.setViewportSize({ width, height: 900 });
      await page.emulateMedia({ colorScheme: theme, reducedMotion: "reduce" });
      await ready(page, (m) => {
        m.total = 30;
        m.tweak.usage = (body) => {
          body.chatbot.student.rows[0].name =
            "A very long display name that has to wrap instead of widening the page";
        };
      });
      expect(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= window.innerWidth,
        ),
      ).toBe(true);
      for (const control of [
        fromField(page),
        toField(page),
        apply(page),
        gradeButton(page),
        tab(page, "Student exercises"),
      ]) {
        await control.scrollIntoViewIfNeeded();
        const box = await control.boundingBox();
        expect(box!.x).toBeGreaterThanOrEqual(0);
        expect(box!.x + box!.width).toBeLessThanOrEqual(width + 1);
      }
      await outlined(page, "From date");
      await outlined(page, "To date");
      // wide tables scroll inside their own container, never the page
      const wide = await itemsTable(page).evaluate((table) => {
        let parent = table.parentElement;
        while (parent && parent !== document.body) {
          const overflow = getComputedStyle(parent).overflowX;
          if (overflow === "auto" || overflow === "scroll") return true;
          parent = parent.parentElement;
        }
        return table.scrollWidth <= window.innerWidth;
      });
      expect(wide).toBe(true);
      expect(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= window.innerWidth,
        ),
      ).toBe(true);
      await page.screenshot({
        path: `node_modules/.cache/adm01-analytics-${theme}-${width}.png`,
        fullPage: true,
      });
    });
  }
}

test("adm01 AC45 error and dialog states also fit 320px in the dark theme", async ({
  page,
}) => {
  await page.setViewportSize({ width: 320, height: 900 });
  await page.emulateMedia({ colorScheme: "dark", reducedMotion: "reduce" });
  const mock = await setup(page);
  mock.next("usage", { abort: true });
  mock.next("generation", { status: 503 });
  await page.goto(PATH);
  await expect(alertWith(usagePanel(page), MSG.network)).toBeVisible();
  await expect(
    alertWith(generationPanel(page), MSG.http("Generation reliability", 503)),
  ).toBeVisible();
  await expect(itemsTable(page)).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await gradeButton(page).click();
  await expect(dialog(page)).toBeVisible();
  const box = await dialog(page).boundingBox();
  expect(box!.x).toBeGreaterThanOrEqual(0);
  expect(box!.x + box!.width).toBeLessThanOrEqual(321);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
});

test("adm01 AC45 the received time renders as a time element with the ISO value", async ({
  page,
}) => {
  await ready(page);
  const time = itemsTable(page).locator("time").first();
  await expect(time).toHaveAttribute("datetime", "2026-11-08T09:12:44Z");
  expect((await time.innerText()).trim().length).toBeGreaterThan(0);
  expect(isoDay(0)).toMatch(/^\d{4}-\d{2}-\d{2}$/);
});

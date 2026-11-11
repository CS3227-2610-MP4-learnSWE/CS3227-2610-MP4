import { test, expect, type Locator, type Page } from "@playwright/test";
import {
  STUDENT,
  TEACHER,
  logOutWithConfirmation,
  expectNoSecretsInBrowser,
} from "./authApi";
import { HUB, isoDay, setup, type HubMock, type Step } from "./adm07Api";
import { itemRows, run } from "./adm07Fixtures";

/**
 * ADM-07 phase 5: assertions of the deleted ADM-01 screen tests (adm01-analytics.spec.ts,
 * adm01-privacy.spec.ts) that the hub tests in adm07-analytics.spec.ts did not cover, ported to the hub
 * route /admin/analytics and its Quality, Feature outcomes and Generation reliability blocks. The
 * meaning of every assertion is unchanged; locators and request counts follow workflow/specs/ADM-07/
 * spec.md "UI states and copy". Mapping: workflow/specs/ADM-07/phase5-test-mapping.md.
 */

const MSG = {
  network: "Could not reach the server. Check your connection and try again.",
  timeout: "The request timed out after 15 seconds. Try again.",
  forbidden: "You do not have access to analytics.",
  http: (subject: string, status: number) =>
    `${subject} could not be loaded: the server returned an error (${status}). Try again.`,
  format: "Enter dates as YYYY-MM-DD.",
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
  scanner:
    "AI grading is unavailable because the local privacy scanner is not ready. Try again later.",
  strict:
    "AI grading is disabled until free-text privacy protection is approved. Counts and timings remain available.",
  strictAlert:
    "AI grading is disabled because free-text privacy protection has not been approved.",
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
const h1 = (p: Page) =>
  p.getByRole("heading", { level: 1, name: "Feature Analytics", exact: true });
const region = (p: Page | Locator, name: string) =>
  p.getByRole("region", { name, exact: true });
const quality = (p: Page) => region(p, "Quality");
const outcomes = (p: Page) => region(p, "Feature outcomes");
const group = (p: Page | Locator, name: string) =>
  p.getByRole("group", { name, exact: true });
const periodSelect = (p: Page) =>
  p.getByRole("combobox", { name: "Reporting period", exact: true });
const refresh = (p: Page) =>
  p.getByRole("button", { name: "Refresh", exact: true });
const rangeDialog = (p: Page) =>
  p.getByRole("dialog", { name: "Custom range", exact: true });
const usersTable = (p: Page) =>
  p.getByRole("table", { name: "Chatbot requests by user", exact: true });
const generationTable = (p: Page) =>
  p.getByRole("table", { name: "Generation success rates", exact: true });
const itemsTable = (p: Page) =>
  p.getByRole("table", { name: "Assessed responses", exact: true });
const tab = (p: Page | Locator, name: string) =>
  p.getByRole("tab", { name, exact: true });
const alertWith = (scope: Page | Locator, text: string) =>
  scope.getByRole("alert").filter({ hasText: text });
const gradeButton = (p: Page) =>
  p.getByRole("button", { name: "Grade ungraded responses", exact: true });
const gradeDialog = (p: Page) =>
  p.getByRole("dialog", { name: "Grade responses with AI?", exact: true });
const progress = (p: Page, text: string | RegExp) =>
  p.getByRole("status").filter({ hasText: text });
const next = (p: Page) =>
  quality(p).getByRole("button", { name: "Next page", exact: true });
const previous = (p: Page) =>
  quality(p).getByRole("button", { name: "Previous page", exact: true });
const retry = (p: Page, what: string) =>
  p.getByRole("button", { name: `Retry ${what}`, exact: true });

async function loaded(page: Page) {
  await expect(group(page, "Chatbot failure rate")).toBeVisible();
  await expect(usersTable(page)).toBeVisible();
  await expect(generationTable(page)).toBeVisible();
  await expect(
    itemsTable(page).or(
      quality(page).getByText("No assessed responses in this period.", {
        exact: true,
      }),
    ),
  ).toBeVisible();
  await expect(progress(page, /^Loading /)).toHaveCount(0);
}

async function ready(
  page: Page,
  configure?: (mock: HubMock) => void,
  url = HUB,
) {
  const mock = await setup(page);
  configure?.(mock);
  await page.goto(url);
  await loaded(page);
  return mock;
}

async function applyRange(page: Page, from: string, to: string) {
  await periodSelect(page).selectOption({ label: "Custom range" });
  const dialog = rangeDialog(page);
  await expect(dialog).toBeVisible();
  await dialog.getByLabel("From date", { exact: true }).fill(from);
  await dialog.getByLabel("To date", { exact: true }).fill(to);
  await dialog
    .getByRole("button", { name: "Apply period", exact: true })
    .click();
}

async function setHeldClock(page: Page) {
  // Let routing and Suspense finish before freezing timers.
  const now = new Date();
  await page.clock.install({ time: now });
  await page.clock.pauseAt(new Date(now.getTime() + 1000));
}

async function openAndStartGrading(page: Page) {
  await gradeButton(page).click();
  await gradeDialog(page)
    .getByRole("button", { name: "Start grading", exact: true })
    .click();
}

/** Records the JSON bodies of grading starts (the hub mock keeps only the URL). */
function recordStarts(page: Page) {
  const bodies: unknown[] = [];
  page.on("request", (r) => {
    if (r.method() === "POST" && r.url().includes("/grading-runs"))
      bodies.push(r.postDataJSON());
  });
  return bodies;
}

const fits = (page: Page) =>
  page.evaluate(
    () => document.documentElement.scrollWidth <= window.innerWidth,
  );

/** Quality items with a given total, honouring limit and offset in the URL. */
const withItems = (total: number) => (m: HubMock) => {
  m.tweak.quality = (b, url) => {
    const limit = Number(url.searchParams.get("limit") ?? 25);
    const offset = Number(url.searchParams.get("offset") ?? 0);
    b.items = { total, limit, offset, rows: itemRows(offset, limit, total) };
  };
};

// ============================================================ Quality block: data (ADM-01 AC20-AC32)

test("adm07 retained AC27 quality: tabs, notice, sections, averages, times and the responses table", async ({
  page,
}) => {
  await ready(page);
  const panel = quality(page);
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

test("adm07 retained AC27 quality: item statuses and unassessable grades use the exact labels", async ({
  page,
}) => {
  await ready(page, (mock) => {
    mock.tweak.quality = (body) => {
      const base = body.items.rows[0];
      body.items = {
        ...body.items,
        total: 4,
        rows: [
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
        ],
      };
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

test("adm07 retained AC27 quality: empty states use the exact messages", async ({
  page,
}) => {
  await ready(page, (mock) => {
    mock.tweak.quality = (body) => {
      body.items = { total: 0, limit: 25, offset: 0, rows: [] };
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
  const panel = quality(page);
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

test("adm07 retained AC32 timing and counts are described as measurements, never as time saved or a no-AI comparison", async ({
  page,
}) => {
  await ready(page);
  const text = (await quality(page).innerText()).toLowerCase();
  expect(text).toContain("descriptive");
  expect(text).not.toContain("time saved");
  expect(text).not.toMatch(
    /baseline|without ai|no-ai|compared with|compared to/,
  );
});

test("adm07 retained AC31 teacher tab: sessions and activity time are unavailable with the exact reason", async ({
  page,
}) => {
  const mock = await ready(page);
  await tab(quality(page), "Teacher lesson planning").click();
  await expect(tab(page, "Teacher lesson planning")).toHaveAttribute(
    "aria-selected",
    "true",
  );
  const panel = quality(page);
  await expect(
    panel
      .getByText(
        "Unavailable: no conversation sessions are recorded for this workflow.",
        { exact: true },
      )
      .first(),
  ).toBeVisible();
  for (const name of ["Session activity", "Associated activity time"])
    await expect(
      panel.getByRole("heading", { name, exact: true }),
    ).toBeVisible();
  expect(mock.of("quality").at(-1)!.url.searchParams.get("workflow")).toBe(
    "teacher_lesson_planning",
  );
});

test("adm07 retained AC11 names and reasons render as plain text, never as markup", async ({
  page,
}) => {
  await ready(page, (mock) => {
    mock.tweak.users = (body) => {
      body.rows[0].name = "<img src=x onerror=alert(1)>";
    };
    mock.tweak.quality = (body) => {
      body.items.rows[0].grades[0].reason =
        "<script>window.__pwned = 1</script>";
    };
  });
  await expect(page.locator("img[src=x]")).toHaveCount(0);
  await expect(outcomes(page)).toContainText("<img src=x onerror=alert(1)>");
  await expect(itemsTable(page)).toContainText(
    "<script>window.__pwned = 1</script>",
  );
  expect(
    await page.evaluate(
      () => (window as unknown as { __pwned?: number }).__pwned,
    ),
  ).toBeUndefined();
});

test("adm07 retained AC31 the page stores no analytics data in the browser", async ({
  page,
}) => {
  await ready(page);
  await expectNoSecretsInBrowser(page, [
    "Alice Tan",
    "Bob Lim",
    "u-00000000",
    "Reason relevance 1.",
  ]);
});

test("adm07 retained AC27 the received time renders as a time element with the ISO value", async ({
  page,
}) => {
  await ready(page);
  const time = itemsTable(page).locator("time").first();
  await expect(time).toHaveAttribute("datetime", "2026-11-08T09:12:44Z");
  expect((await time.innerText()).trim().length).toBeGreaterThan(0);
});

test("adm07 retained AC27 default workflow tab is Student exercises with limit 25 and the loading status keeps the tabs", async ({
  page,
}) => {
  const mock = await setup(page);
  mock.next("quality", { hold: true });
  await page.goto(HUB);
  await expect(progress(page, "Loading quality results...")).toBeVisible();
  await expect(tab(page, "Student exercises")).toBeVisible(); // notice and tabs stay while loading
  await expect(tab(page, "Student exercises")).toHaveAttribute(
    "aria-selected",
    "true",
  );
  await expect(
    quality(page).getByText(MSG.notice, { exact: true }),
  ).toBeVisible();
  mock.release();
  await loaded(page);
});

test("adm07 retained AC27 generation: the MCQ row shows zero counts and no percentage; unavailable rows show their reason", async ({
  page,
}) => {
  await ready(page);
  const mcq = generationTable(page)
    .getByRole("row")
    .filter({ hasText: "MCQ batches" });
  await expect(mcq).toContainText(
    "No rate can be calculated: no generation requests in this period.",
  );
  await expect(mcq).not.toContainText("%");
  await expect(mcq.getByRole("cell", { name: "0", exact: true })).toHaveCount(
    3,
  );
});

test("adm07 retained AC27 generation: an unavailable workflow shows its reason and no percentage", async ({
  page,
}) => {
  await ready(page, (mock) => {
    mock.tweak.generation = (body) => {
      for (const row of body.workflows)
        Object.assign(row, {
          state: "unavailable",
          reason: "read_failed",
          attempts: null,
          requests: null,
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

// ============================================================ failure states per block (ADM-01 AC40)

const BLOCKS = [
  ["users", "Chatbot users", "chatbot users", "Feature outcomes"],
  [
    "generation",
    "Generation reliability",
    "generation reliability",
    "Feature outcomes",
  ],
  ["quality", "Quality results", "quality results", "Quality"],
] as const;

for (const [kind, subject, what, regionName] of BLOCKS) {
  test(`adm07 retained AC29 ${kind} network failure: exact message, own Retry, one request, others unaffected`, async ({
    page,
  }) => {
    const mock = await setup(page);
    mock.next(kind, { abort: true });
    await page.goto(HUB);
    await expect(
      alertWith(region(page, regionName), MSG.network),
    ).toBeVisible();
    await expect(retry(page, what)).toBeVisible();
    await expect(group(page, "Chatbot failure rate")).toBeVisible(); // other blocks stay
    await expect(h1(page)).toBeVisible();
    await expect(periodSelect(page)).toBeEnabled();
    const before = mock.count();
    await retry(page, what).click();
    await loaded(page);
    expect(mock.count() - before).toBe(1);
    expect(mock.count(kind)).toBe(2);
  });

  for (const status of [500, 502, 504, 404]) {
    test(`adm07 retained AC29 ${kind} HTTP ${status}: exact copy with the status, server message ignored`, async ({
      page,
    }) => {
      const mock = await setup(page);
      mock.next(kind, {
        status,
        json: {
          detail: { code: "boom", message: "Traceback: private server detail" },
        },
      });
      await page.goto(HUB);
      await expect(
        alertWith(region(page, regionName), MSG.http(subject, status)),
      ).toBeVisible();
      await expect(page.getByText("private server detail")).toHaveCount(0);
      await expect(page.getByText(/something went wrong/i)).toHaveCount(0);
      await expect(page.getByText("Could not reach the server.")).toHaveCount(
        0,
      );
      await expect(retry(page, what)).toBeVisible();
    });
  }

  test(`adm07 retained AC29 ${kind} 403: the access message`, async ({
    page,
  }) => {
    const mock = await setup(page);
    mock.next(kind, { status: 403 });
    await page.goto(HUB);
    await expect(
      alertWith(region(page, regionName), MSG.forbidden),
    ).toBeVisible();
  });

  test(`adm07 retained AC29 ${kind} malformed 200 body is a failure, never a blank block`, async ({
    page,
  }) => {
    const mock = await setup(page);
    mock.next(kind, { malformed: true });
    await page.goto(HUB);
    await expect(region(page, regionName).getByRole("alert")).toBeVisible();
    await expect(retry(page, what)).toBeVisible();
    await expect(group(page, "Chatbot failure rate")).toBeVisible();
  });
}

test("adm07 retained AC29 a 15 second wait on quality ends in the exact timeout message and no automatic retry", async ({
  page,
}) => {
  const mock = await ready(page);
  await setHeldClock(page);
  mock.next("quality", { hold: true });
  await periodSelect(page).selectOption({ label: "Last 30 days" });
  await expect.poll(() => mock.count("quality")).toBe(2);
  await expect(progress(page, "Loading quality results...")).toBeVisible();
  await page.clock.fastForward(14_900);
  await expect(alertWith(quality(page), MSG.timeout)).toHaveCount(0);
  await page.clock.fastForward(200);
  await expect(alertWith(quality(page), MSG.timeout)).toBeVisible();
  expect(mock.count("quality")).toBe(2);
  await expect(retry(page, "quality results")).toBeVisible();
  mock.release();
});

test("adm07 retained AC29 assessed-responses page failure keeps the current page and shows the message above the table", async ({
  page,
}) => {
  const mock = await ready(page, withItems(30));
  await expect(
    quality(page).getByText("Showing 1 to 25 of 30", { exact: true }),
  ).toBeVisible();
  mock.next("quality", { status: 500 });
  await next(page).click();
  await expect(
    alertWith(quality(page), MSG.http("Assessed responses", 500)),
  ).toBeVisible();
  await expect(
    quality(page).getByText("Showing 1 to 25 of 30", { exact: true }),
  ).toBeVisible();
  await expect(itemsTable(page)).toBeVisible();
  await expect(tab(page, "Student exercises")).toBeVisible();
  await expect(
    quality(page).getByText(MSG.notice, { exact: true }),
  ).toBeVisible();
});

test("adm07 retained AC29 a failed workflow tab switch selects the clicked tab and shows the failure with Retry quality results", async ({
  page,
}) => {
  const mock = await ready(page);
  mock.next("quality", { status: 503 });
  await tab(quality(page), "Teacher lesson planning").click();
  await expect(tab(page, "Teacher lesson planning")).toHaveAttribute(
    "aria-selected",
    "true",
  );
  await expect(
    alertWith(quality(page), MSG.http("Quality results", 503)),
  ).toBeVisible();
  await expect(usersTable(page)).toBeVisible();
  await expect(generationTable(page)).toBeVisible();
  const before = mock.count();
  await retry(page, "quality results").click();
  await expect(alertWith(quality(page), "could not be loaded")).toHaveCount(0);
  expect(mock.count() - before).toBe(1);
  expect(mock.of("quality").at(-1)!.url.searchParams.get("workflow")).toBe(
    "teacher_lesson_planning",
  );
});

// ============================================================ requests per action, URL, history (ADM-01 AC42)

test("adm07 retained AC30 quality pagination: one request per click, no URL change, end buttons disabled", async ({
  page,
}) => {
  const mock = await ready(page, withItems(30));
  const url = page.url();
  const panel = quality(page);
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
  expect(page.url()).toBe(url);
  await previous(page).click();
  await expect(
    panel.getByText("Showing 1 to 25 of 30", { exact: true }),
  ).toBeVisible();
  expect(mock.of("quality").at(-1)!.url.searchParams.get("offset")).toBe("0");
});

test("adm07 retained AC30 quality pagination buttons are disabled while the page request is pending", async ({
  page,
}) => {
  const mock = await ready(page, withItems(60));
  mock.next("quality", { hold: true });
  await next(page).click();
  await expect(next(page)).toBeDisabled();
  await expect(previous(page)).toBeDisabled();
  mock.release();
  await expect(
    quality(page).getByText("Showing 26 to 50 of 60", { exact: true }),
  ).toBeVisible();
});

test("adm07 retained AC30 Back and Forward restore the period and reload all seven blocks from the URL", async ({
  page,
}) => {
  const mock = await ready(page);
  await periodSelect(page).selectOption({ label: "Last 30 days" });
  await expect.poll(() => mock.count()).toBe(14);
  await expect(page).toHaveURL(/range=30d/);
  await page.goBack();
  await expect(periodSelect(page)).toContainText("Last 7 days");
  await expect.poll(() => mock.count()).toBe(21);
  expect(mock.of("health").at(-1)!.url.searchParams.get("period_start")).toBe(
    isoDay(6),
  );
  await page.goForward();
  await expect(periodSelect(page)).toContainText("Last 30 days");
  await expect.poll(() => mock.count()).toBe(28);
  expect(mock.of("health").at(-1)!.url.searchParams.get("period_start")).toBe(
    isoDay(29),
  );
});

test("adm07 retained AC30 Back to a URL that differs only by workflow reloads only quality and restores the tab", async ({
  page,
}) => {
  const mock = await ready(page, undefined, `${HUB}?range=7d`);
  await expect(tab(page, "Student exercises")).toHaveAttribute(
    "aria-selected",
    "true",
  );
  await page.evaluate((to) => {
    window.history.pushState({}, "", to);
    window.dispatchEvent(new PopStateEvent("popstate"));
  }, `${HUB}?range=7d&workflow=teacher_lesson_planning`);
  await expect(tab(page, "Teacher lesson planning")).toHaveAttribute(
    "aria-selected",
    "true",
  );
  await expect.poll(() => mock.count()).toBe(8);
  await page.goBack();
  await expect(tab(page, "Student exercises")).toHaveAttribute(
    "aria-selected",
    "true",
  );
  await expect.poll(() => mock.count()).toBe(9);
  expect(mock.count("quality")).toBe(3);
  expect(mock.of("quality").at(-1)!.url.searchParams.get("workflow")).toBe(
    "student_exercise",
  );
  expect(mock.count("health")).toBe(1);
});

test("adm07 retained AC30 a workflow switch after a period change survives a browser refresh", async ({
  page,
}) => {
  const mock = await ready(page);
  await applyRange(page, "2026-10-01", "2026-10-20");
  await expect.poll(() => mock.count()).toBe(14);
  await tab(quality(page), "Teacher lesson planning").click(); // replace
  await expect.poll(() => mock.count()).toBe(15);
  await page.reload();
  await loaded(page);
  await expect(tab(page, "Teacher lesson planning")).toHaveAttribute(
    "aria-selected",
    "true",
  );
  await expect(periodSelect(page)).toContainText("2026-10-01 to 2026-10-20");
  await expect.poll(() => mock.count()).toBe(22);
  const last = mock.of("quality").at(-1)!.url.searchParams;
  expect(last.get("workflow")).toBe("teacher_lesson_planning");
  expect(last.get("period_start")).toBe("2026-10-01");
});

for (const query of [
  "?from=2026-13-45&to=abc&workflow=nope",
  "?from=2026-10-31&to=2026-10-01",
  "?from=2024-01-01&to=2026-01-01",
  "?from=2026-10-01",
  "?workflow=STUDENT_EXERCISE",
]) {
  test(`adm07 retained AC30 an invalid or incomplete URL query ${query} falls back to the defaults without a message`, async ({
    page,
  }) => {
    const mock = await setup(page);
    await page.goto(HUB + query);
    await loaded(page);
    await expect(periodSelect(page)).toContainText("Last 7 days");
    expect(mock.of("health")[0].url.searchParams.get("period_start")).toBe(
      isoDay(6),
    );
    await expect(tab(page, "Student exercises")).toHaveAttribute(
      "aria-selected",
      "true",
    );
    await expect(page.getByRole("alert")).toHaveCount(0);
    expect(mock.count()).toBe(7);
  });
}

test("adm07 retained AC30 two invalid custom-range fields: focus goes to the first, and a corrected period then loads", async ({
  page,
}) => {
  const mock = await ready(page);
  await applyRange(page, "", "");
  const dialog = rangeDialog(page);
  await expect(dialog.getByLabel("From date", { exact: true })).toBeFocused();
  await expect(dialog.getByText(MSG.format, { exact: true })).toHaveCount(2);
  expect(mock.count()).toBe(7);
  await dialog.getByLabel("From date", { exact: true }).fill("2025-01-01");
  await dialog.getByLabel("To date", { exact: true }).fill("2026-01-01"); // exactly 366 days is valid
  await dialog
    .getByRole("button", { name: "Apply period", exact: true })
    .click();
  await expect(rangeDialog(page)).toHaveCount(0);
  await expect.poll(() => mock.count()).toBe(13); // 6 blocks: over 31 days sends no AI usage request
  await expect(group(page, "Chatbot failure rate")).toBeVisible();
});

// ============================================================ roles, anonymous, 401 (ADM-01 AC44)

for (const [who, user, url, home] of [
  ["student", STUDENT, "/student/overview", /\/student\/overview$/],
  ["teacher", TEACHER, "/teacher/overview", /\/teacher\/overview$/],
] as const) {
  test(`adm07 retained AC31 a ${who} is redirected with replace to their own home and nothing from the hub renders`, async ({
    page,
  }) => {
    const mock = await setup(page, { user });
    await page.goto(url);
    const entries = await page.evaluate(() => history.length);
    await page.goto(HUB);
    await expect(page).toHaveURL(home);
    expect(await page.evaluate(() => history.length)).toBe(entries + 1); // replaced, not pushed
    expect(mock.count()).toBe(0);
    await expect(h1(page)).toHaveCount(0);
    await expect(usersTable(page)).toHaveCount(0);
    await page.goBack();
    await expect(page).not.toHaveURL(/\/admin\/analytics/);
  });
}

test("adm07 retained AC31 an anonymous visitor with a query string is sent to sign-in with replace and no request", async ({
  page,
}) => {
  const mock = await setup(page, { user: null });
  await page.goto("/login");
  const entries = await page.evaluate(() => history.length);
  await page.goto(
    `${HUB}?from=2026-01-01&to=2026-01-31&workflow=teacher_lesson_planning`,
  );
  await expect(page).toHaveURL(/\/login/);
  expect(await page.evaluate(() => history.length)).toBe(entries + 1);
  await page.waitForTimeout(300);
  expect(mock.count()).toBe(0);
  await expect(usersTable(page)).toHaveCount(0);
});

test("adm07 retained AC31 a 401 shows the session-expired message at sign-in and Back shows no analytics data", async ({
  page,
}) => {
  const mock = await ready(page);
  mock.auth.expire();
  mock.next("users", { status: 401 });
  await applyRange(page, "2026-01-01", "2026-01-31");
  await expect(page).toHaveURL(/\/login/);
  await expect(
    page.getByText("Your session has expired. Sign in again.", { exact: true }),
  ).toBeVisible();
  await expect(usersTable(page)).toHaveCount(0);
  await expect(page.getByText("Alice Tan")).toHaveCount(0);
  await page.goBack();
  await expect(usersTable(page)).toHaveCount(0);
  await expect(page.getByText("Alice Tan")).toHaveCount(0);
});

test("adm07 retained AC31 logging out clears the report and Back shows sign-in, not stale analytics", async ({
  page,
}) => {
  await ready(page);
  await logOutWithConfirmation(page);
  await expect(page).toHaveURL(/\/login/);
  await page.goBack();
  await expect(usersTable(page)).toHaveCount(0);
  await expect(page.getByText("Alice Tan")).toHaveCount(0);
  await expect(itemsTable(page)).toHaveCount(0);
});

// ============================================================ grading dialog, start, progress (ADM-01 AC43, AC33-AC36)

test("adm07 retained AC28 the grading dialog has the exact title, text and buttons; Cancel and Escape send nothing and return focus", async ({
  page,
}) => {
  const mock = await ready(page);
  await expect(gradeButton(page)).toBeEnabled();
  await gradeButton(page).click();
  const d = gradeDialog(page);
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
  expect(mock.count()).toBe(7);
});

test("adm07 retained AC28 starting sends one POST with the workflow and period, polls until the run finishes and reloads quality once", async ({
  page,
}) => {
  test.setTimeout(60_000);
  const bodies = recordStarts(page);
  const mock = await ready(page, (m) => {
    m.runStates = [
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
  });
  const qualityBefore = mock.count("quality");
  await openAndStartGrading(page);
  await expect(gradeDialog(page)).toHaveCount(0);
  expect(mock.count("start")).toBe(1);
  expect(mock.of("start")[0].url.pathname).toBe(
    "/api/admin/analytics/grading-runs",
  );
  expect(bodies).toEqual([
    {
      workflow: "student_exercise",
      period_start: isoDay(6),
      period_end: isoDay(0),
    },
  ]);
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
  await expect.poll(() => mock.count("quality")).toBe(qualityBefore + 1);
  expect(mock.count("start")).toBe(1);
  const polls = mock.count("run");
  await page.waitForTimeout(3500);
  expect(mock.count("run")).toBe(polls); // polling stopped in the terminal state
  for (const r of mock.of("run"))
    expect(r.url.pathname).toBe("/api/admin/analytics/grading-runs/12");
});

test("adm07 retained AC28 the start button is disabled while the start request is pending", async ({
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

test("adm07 retained AC28 a run with nothing to grade says so", async ({
  page,
}) => {
  test.setTimeout(30_000);
  const mock = await ready(page, (m) => {
    m.runStates = [
      {
        status: "completed",
        items_total: 0,
        items_graded: 0,
        finished_at: "2026-11-09T05:00:02Z",
      },
    ];
  });
  mock.next("start", {
    json: run({ status: "queued", items_total: 0, items_graded: 0 }),
  });
  await openAndStartGrading(page);
  await expect(
    progress(page, "No ungraded responses are available for this period."),
  ).toBeVisible({ timeout: 8000 });
  await expect(gradeButton(page)).toBeEnabled();
});

for (const [code, copy] of Object.entries(RUN_FAILURE_COPY)) {
  test(`adm07 retained AC28 a failed run (${code}) is reported with its copy and the number graded`, async ({
    page,
  }) => {
    test.setTimeout(30_000);
    await ready(page, (m) => {
      m.runStates = [
        {
          status: "failed",
          failure_code: code,
          items_graded: 1,
          items_total: 3,
          finished_at: "2026-11-09T05:00:05Z",
        },
      ];
    });
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

test("adm07 retained AC28 a scanner failure during a run shows the privacy alert (spec: 'mid-run scanner failure alert')", async ({
  page,
}) => {
  // Contract note: spec.md also lists "Grading stopped: the local privacy scanner is not ready" in the run
  // failure copy by code; the Quality: start grading row says a mid-run scanner failure is an alert. The
  // hub renders the alert, which is asserted here.
  test.setTimeout(30_000);
  await ready(page, (m) => {
    m.runStates = [
      {
        status: "failed",
        failure_code: "privacy_scanner_unavailable",
        items_graded: 1,
        items_total: 3,
        finished_at: "2026-11-09T05:00:05Z",
      },
    ];
  });
  await openAndStartGrading(page);
  await expect(
    page.getByRole("alert").filter({ hasText: MSG.scanner }),
  ).toBeVisible({ timeout: 8000 });
  await expect(gradeButton(page)).toBeEnabled();
});

for (const [label, step, message] of [
  [
    "409",
    {
      status: 409,
      json: { detail: { code: "grading_run_active", message: "x" } },
    },
    MSG.start.conflict,
  ],
  [
    "429",
    { status: 429, json: { detail: { code: "grading_quota", message: "x" } } },
    MSG.start.quota,
  ],
  [
    "403",
    { status: 403, json: { detail: { code: "forbidden", message: "x" } } },
    MSG.start.forbidden,
  ],
  [
    "422",
    {
      status: 422,
      json: {
        detail: {
          code: "invalid_workflow",
          message: "Choose student_exercise or teacher_lesson_planning.",
        },
      },
    },
    "Choose student_exercise or teacher_lesson_planning.",
  ],
  ["network", { abort: true }, MSG.start.network],
] as [string, Step, string][]) {
  test(`adm07 retained AC28 a failed start (${label}) shows its exact message, closes the dialog, keeps results and the period, sends once`, async ({
    page,
  }) => {
    const mock = await ready(page);
    if (label === "409")
      mock.tweak.quality = (body) => {
        body.active_run = run({ status: "running", items_total: 3 });
      };
    mock.next("start", step);
    await openAndStartGrading(page);
    await expect(
      page.getByText(message, { exact: true }).first(),
    ).toBeVisible();
    await expect(gradeDialog(page)).toHaveCount(0);
    await expect(itemsTable(page)).toBeVisible();
    await expect(periodSelect(page)).toContainText("Last 7 days");
    if (label === "409") await expect(gradeButton(page)).toBeDisabled();
    else await expect(gradeButton(page)).toBeEnabled();
    await page.waitForTimeout(300);
    expect(mock.count("start")).toBe(1); // no automatic retry
    expect(mock.count("run")).toBe(0);
    if (label === "409") expect(mock.count("quality")).toBe(2); // one GET discovers the active run
  });
}

test("adm07 retained AC28 a start that times out after 15 seconds says to reload and does not retry", async ({
  page,
}) => {
  const mock = await ready(page);
  await setHeldClock(page);
  mock.next("start", { hold: true });
  await openAndStartGrading(page);
  await expect.poll(() => mock.count("start")).toBe(1);
  await page.clock.fastForward(15_100);
  await expect(alertWith(quality(page), MSG.start.timeout)).toBeVisible();
  expect(mock.count("start")).toBe(1);
  mock.release();
});

test("adm07 retained AC28 a polling network failure stops polling and Check progress sends exactly one request", async ({
  page,
}) => {
  test.setTimeout(40_000);
  const mock = await ready(page);
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

test("adm07 retained AC28 a polling HTTP error uses the progress copy with the status", async ({
  page,
}) => {
  test.setTimeout(30_000);
  const mock = await ready(page);
  mock.next("run", { status: 500 });
  await openAndStartGrading(page);
  await expect(page.getByText(MSG.poll.http(500), { exact: true })).toBeVisible(
    {
      timeout: 8000,
    },
  );
  await expect(
    page.getByRole("button", { name: "Check progress", exact: true }),
  ).toBeVisible();
  await expect(page.getByText(/something went wrong/i)).toHaveCount(0);
});

test("adm07 retained AC28 a polling request that takes 15 seconds says grading may still be running", async ({
  page,
}) => {
  const mock = await ready(page);
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

test("adm07 retained AC28 AC31 a 401 while polling ends the session and stops polling", async ({
  page,
}) => {
  test.setTimeout(30_000);
  const mock = await ready(page);
  mock.auth.expire();
  mock.next("run", { status: 401 });
  await openAndStartGrading(page);
  await expect(page).toHaveURL(/\/login/, { timeout: 8000 });
  const polls = mock.count("run");
  await page.waitForTimeout(3500);
  expect(mock.count("run")).toBe(polls);
});

test("adm07 retained AC28 an active run in the quality response is shown again and resumes polling without a start request", async ({
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

// ============================================================ privacy UI (adm01-privacy.spec.ts)

test("adm07 retained AC28 privacy strict mode shows counts and disables grading without extra requests", async ({
  page,
}) => {
  const mock = await ready(page, (m) => {
    m.tweak.quality = (body) => {
      body.grades.privacy_mode = "strict";
      body.grades.privacy_blocked_count = 7;
    };
  });
  await expect(progress(page, MSG.strict)).toBeVisible();
  await expect(gradeButton(page)).toBeDisabled();
  await expect(
    page.getByText("7 responses excluded by privacy protection.", {
      exact: true,
    }),
  ).toBeVisible();
  expect(mock.count()).toBe(7);
  expect(mock.count("start")).toBe(0);
});

for (const status of [409, 503]) {
  test(`adm07 retained AC28 privacy ${status} start preserves results and uses exact privacy copy`, async ({
    page,
  }) => {
    const disabled = status === 409;
    const mock = await ready(page);
    mock.next("start", {
      status,
      json: {
        detail: {
          code: disabled
            ? "privacy_grading_disabled"
            : "privacy_scanner_unavailable",
          message: "ignored",
        },
      },
    });
    await expect(gradeButton(page)).toBeEnabled();
    const original = page.url();
    if (disabled)
      mock.tweak.quality = (body) => {
        body.grades.privacy_mode = "strict";
      };
    await openAndStartGrading(page);
    await expect(
      page.getByRole("alert").filter({
        hasText: disabled ? MSG.strictAlert : MSG.scanner,
      }),
    ).toBeVisible();
    expect(page.url()).toBe(original);
    expect(mock.count("start")).toBe(1);
    await expect(itemsTable(page)).toBeVisible();
    if (disabled) {
      await expect(gradeButton(page)).toBeDisabled();
      expect(mock.count("quality")).toBe(2);
    } else {
      await expect(gradeButton(page)).toBeEnabled();
      expect(mock.count("quality")).toBe(1);
    }
  });
}

test("adm07 retained AC28 privacy blocked count remains visible when no responses are eligible", async ({
  page,
}) => {
  const mock = await ready(page, (m) => {
    m.tweak.quality = (body) => {
      body.grades.privacy_blocked_count = 4;
      body.grades.pending_count = 0;
      body.grades.assessed_count = 0;
    };
  });
  await expect(
    page.getByText("4 responses excluded by privacy protection.", {
      exact: true,
    }),
  ).toBeVisible();
  expect(mock.count("start")).toBe(0);
});

// ============================================================ keyboard, accessibility, layout (ADM-01 AC45)

test("adm07 retained AC32 the workflow tabs move with the arrow keys and the grade dialog traps focus", async ({
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
  await expect(gradeDialog(page)).toBeVisible();
  for (let i = 0; i < 6; i++) {
    await page.keyboard.press("Tab");
    expect(
      await gradeDialog(page).evaluate((el) =>
        el.contains(document.activeElement),
      ),
    ).toBe(true);
  }
  await page.keyboard.press("Escape");
  await expect(gradeDialog(page)).toHaveCount(0);
  await expect(gradeButton(page)).toBeFocused();
});

test("adm07 retained AC32 every named control and landmark is exposed by role and name", async ({
  page,
}) => {
  await ready(page);
  await expect(
    page.getByRole("tablist", { name: "Assessment workflow", exact: true }),
  ).toBeVisible();
  await expect(quality(page).getByRole("tabpanel")).toBeVisible();
  for (const control of [
    periodSelect(page),
    refresh(page),
    gradeButton(page),
  ]) {
    await control.focus();
    await expect(control).toBeFocused();
  }
  await expect(
    usersTable(page)
      .getByRole("rowheader")
      .or(usersTable(page).getByRole("row"))
      .first(),
  ).toBeVisible();
});

/** The control draws a visible solid outline with at least 3:1 contrast against its surface. */
async function outlined(control: Locator) {
  await expect(control).toBeVisible();
  const contrast = await control.evaluate((el) => {
    const own = getComputedStyle(el);
    const fieldset = el.parentElement?.querySelector("fieldset") ?? null;
    const box = fieldset ?? el;
    const style = fieldset ? getComputedStyle(fieldset) : own;
    if (style.borderTopStyle !== "solid") return 0;
    const rgba = (color: string) => {
      const c = color.match(/[\d.]+/g)!.map(Number);
      return [c[0], c[1], c[2], c[3] ?? 1];
    };
    const over = (front: number[], back: number[]) =>
      front.slice(0, 3).map((v, i) => v * front[3] + back[i] * (1 - front[3]));
    const chain: Element[] = [];
    for (let n = box.parentElement; n; n = n.parentElement) chain.unshift(n);
    let background = [255, 255, 255];
    for (const n of chain)
      background = over(rgba(getComputedStyle(n).backgroundColor), background);
    const lum = (c: number[]) => {
      const [r, g, b] = c.map((v) => {
        const x = v / 255;
        return x <= 0.04045 ? x / 12.92 : ((x + 0.055) / 1.055) ** 2.4;
      });
      return r * 0.2126 + g * 0.7152 + b * 0.0722;
    };
    const border = lum(over(rgba(style.borderTopColor), background));
    const surface = lum(background);
    return (
      (Math.max(border, surface) + 0.05) / (Math.min(border, surface) + 0.05)
    );
  });
  expect(contrast).toBeGreaterThanOrEqual(3);
}

for (const theme of ["light", "dark"] as const) {
  for (const width of [320, 390]) {
    test(`adm07 retained AC32 ${theme} ${width}px: quality controls fit, outlined and its wide table scrolls inside its container`, async ({
      page,
    }) => {
      await page.setViewportSize({ width, height: 900 });
      await page.emulateMedia({ colorScheme: theme, reducedMotion: "reduce" });
      await ready(page, withItems(30));
      expect(await fits(page)).toBe(true);
      for (const control of [
        periodSelect(page),
        refresh(page),
        gradeButton(page),
        tab(page, "Student exercises"),
      ]) {
        await control.scrollIntoViewIfNeeded();
        const box = await control.boundingBox();
        expect(box!.x).toBeGreaterThanOrEqual(0);
        expect(box!.x + box!.width).toBeLessThanOrEqual(width + 1);
      }
      await outlined(periodSelect(page));
      const scrolls = await itemsTable(page).evaluate((table) => {
        for (
          let p = table.parentElement;
          p && p !== document.body;
          p = p.parentElement
        ) {
          const o = getComputedStyle(p).overflowX;
          if (o === "auto" || o === "scroll") return true;
        }
        return table.scrollWidth <= window.innerWidth;
      });
      expect(scrolls).toBe(true);
      expect(await fits(page)).toBe(true);
    });
  }
}

test("adm07 retained AC32 error and dialog states also fit 320px in the dark theme", async ({
  page,
}) => {
  await page.setViewportSize({ width: 320, height: 900 });
  await page.emulateMedia({ colorScheme: "dark", reducedMotion: "reduce" });
  const mock = await setup(page);
  mock.next("users", { abort: true });
  mock.next("generation", { status: 503 });
  await page.goto(HUB);
  await expect(alertWith(outcomes(page), MSG.network)).toBeVisible();
  await expect(
    alertWith(outcomes(page), MSG.http("Generation reliability", 503)),
  ).toBeVisible();
  await expect(itemsTable(page)).toBeVisible();
  expect(await fits(page)).toBe(true);
  await gradeButton(page).click();
  await expect(gradeDialog(page)).toBeVisible();
  const box = await gradeDialog(page).boundingBox();
  expect(box!.x).toBeGreaterThanOrEqual(0);
  expect(box!.x + box!.width).toBeLessThanOrEqual(321);
  expect(await fits(page)).toBe(true);
});

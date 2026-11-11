import { test, expect, type Locator, type Page } from "@playwright/test";
import { HUB, setup, type HubMock } from "./adm07Api";

/**
 * ADM-07 phase 4 frontend regression (task P4-8, test-designer part): metrics that were `unavailable /
 * not_collected` in phase 2 now show REAL values when the API returns them. The API is mocked (adm07Api.ts);
 * the same shapes as plan.md "[P4]" are returned. Copy comes only from spec.md "UI states and copy".
 * The phase 2 spec (adm07-analytics.spec.ts) keeps asserting the unavailable rendering on the phase 2 mock;
 * these tests assert the real-value rendering and never touch those assertions.
 */

const ONE_DAY = `${HUB}?from=2026-11-09&to=2026-11-09`;
const THREE_DAYS = `${HUB}?from=2026-11-07&to=2026-11-09`;
const NOT_COLLECTED = "collection of this metric has not started";

const region = (p: Page, name: string) =>
  p.getByRole("region", { name, exact: true });
const group = (p: Page | Locator, name: string) =>
  p.getByRole("group", { name, exact: true });
const expand = (p: Page, chart: string) =>
  p.getByRole("button", { name: `Expand ${chart}`, exact: true });
const modal = (p: Page, title: string) =>
  p.getByRole("dialog", { name: title, exact: true });

async function ready(
  page: Page,
  configure?: (mock: HubMock) => void,
  url = HUB,
) {
  const mock = await setup(page);
  configure?.(mock);
  await page.goto(url);
  await expect(group(page, "Chatbot failure rate")).toBeVisible();
  await expect(
    page.getByRole("status").filter({ hasText: /^Loading / }),
  ).toHaveCount(0);
  return mock;
}

const day = (d: string, over: Record<string, unknown> = {}) => ({
  date: d,
  student_logins: 0,
  teacher_logins: 0,
  total_logins: 0,
  active_students: 0,
  active_teachers: 0,
  active_users_total: 0,
  ...over,
});

// ================================================================== Health: rate-limited and generation tiles

test("adm07 p4 AC10 rate-limited tile shows the count next to the total, not Unavailable", async ({
  page,
}) => {
  await ready(page, (m) => {
    m.tweak.health = (b) => {
      b.rate_limited = {
        state: "available",
        reason: null,
        since: "2026-11-01",
        count: 4,
        total_requests: 200,
        data_starts_on: null,
      };
    };
  });
  const tile = group(page, "Rate-limited requests");
  await expect(tile).toContainText("4");
  await expect(tile).toContainText("of 200 requests");
  await expect(tile).not.toContainText("Unavailable");
  await expect(tile).not.toContainText(NOT_COLLECTED);
});

test("adm07 p4 AC10 rate-limited count 0 with total 0 is a real 0", async ({
  page,
}) => {
  await ready(page, (m) => {
    m.tweak.health = (b) => {
      b.rate_limited = {
        state: "available",
        reason: null,
        since: "2026-11-01",
        count: 0,
        total_requests: 0,
        data_starts_on: null,
      };
    };
  });
  const tile = group(page, "Rate-limited requests");
  await expect(tile).not.toContainText("Unavailable");
  await expect(tile).toContainText(/(^|\s)0(\s|$)/);
});

test("adm07 p4 AC10 a partly covered rate-limited tile shows the data-starts note", async ({
  page,
}) => {
  await ready(page, (m) => {
    m.tweak.health = (b) => {
      b.data_starts_on = "2026-11-05";
      b.rate_limited = {
        state: "available",
        reason: null,
        since: "2026-11-05",
        count: 2,
        total_requests: 50,
        data_starts_on: "2026-11-05",
      };
    };
  });
  await expect(
    page.getByText(
      "Data starts on 2026-11-05. Earlier days in this period are not included.",
    ),
  ).toBeVisible();
});

test("adm07 p4 AC40 generation tile detail line includes rate-limited requests", async ({
  page,
}) => {
  await ready(page, (m) => {
    m.tweak.health = (b) => {
      b.generation_failure.includes_rate_limited = true;
      b.generation_failure.total = 30;
      b.generation_failure.failed = 4;
      b.generation_failure.rate_percent = 13.3;
      b.generation_failure.severity = "critical";
    };
  });
  const tile = group(page, "Generation failure rate");
  await expect(tile).toContainText(
    "4 of 30 generation requests, including rate-limited ones",
  );
  await expect(tile).not.toContainText("are not recorded yet");
});

// ================================================================== Generation reliability table

test("adm07 p4 AC40 generation table counts refused requests and drops the not-recorded note", async ({
  page,
}) => {
  await ready(page, (m) => {
    m.tweak.generation = (b) => {
      const w = b.workflows[0];
      w.attempts = 9;
      w.rate_limited = 3;
      w.rate_limited_state = { state: "available", reason: null };
      w.requests = 12;
      w.successful = 6;
      w.unsuccessful = 6;
      w.rate_percent = 50.0;
      const other = b.workflows[1];
      other.rate_limited = 0;
      other.rate_limited_state = { state: "available", reason: null };
      other.requests = other.attempts;
    };
  });
  const feature = region(page, "Feature outcomes");
  const row = feature
    .getByRole("table", { name: "Generation success rates", exact: true })
    .getByRole("row", { name: /Study notes/ });
  await expect(row).toContainText("12");
  await expect(row).toContainText("50.0%");
  await expect(
    feature.getByText(
      "Requests include those refused by the rate limiter, which count as unsuccessful.",
    ),
  ).toBeVisible();
  await expect(
    feature.getByText("Rate-limited requests are not recorded yet."),
  ).toHaveCount(0);
});

// ================================================================== Daily activity cards

test("adm07 p4 AC22 logins card shows real values, the admin note and the data table", async ({
  page,
}) => {
  await ready(
    page,
    (m) => {
      m.tweak.daily = (b) => {
        b.logins = {
          state: "available",
          reason: null,
          since: "2026-11-01",
          data_starts_on: null,
          total_logins: 15,
          per_day: [
            day("2026-11-07"),
            day("2026-11-08"),
            day("2026-11-09", {
              student_logins: 12,
              teacher_logins: 3,
              total_logins: 15,
              active_students: 8,
              active_teachers: 2,
              active_users_total: 10,
            }),
          ],
        };
      };
    },
    THREE_DAYS,
  );
  const card = group(region(page, "Daily activity"), "Logins per day");
  await expect(card).not.toContainText("Unavailable");
  await expect(card).not.toContainText(NOT_COLLECTED);
  await expect(card).not.toContainText("No logins in this period.");
  await expect(card).toContainText("Admin sign-ins are not counted.");
  await card
    .getByRole("button", { name: "Show data table", exact: true })
    .click();
  const table = card.getByRole("table", { name: "Logins per day data" });
  for (const col of [
    "Date",
    "Student logins",
    "Teacher logins",
    "Total logins",
    "Active students",
    "Active teachers",
    "Active users total",
  ])
    await expect(
      table.getByRole("columnheader", { name: col, exact: true }),
    ).toBeVisible();
  const row = table.getByRole("row", { name: /2026-11-09/ });
  for (const cell of ["12", "3", "15", "8", "2", "10"])
    await expect(
      row.getByRole("cell", { name: cell, exact: true }).first(),
    ).toBeVisible();
});

test("adm07 p4 AC22 a period with no logins shows the empty message, not Unavailable and not a missing chart", async ({
  page,
}) => {
  await ready(
    page,
    (m) => {
      m.tweak.daily = (b) => {
        b.logins = {
          state: "available",
          reason: null,
          since: "2026-11-01",
          data_starts_on: null,
          total_logins: 0,
          per_day: [day("2026-11-09")],
        };
      };
    },
    ONE_DAY,
  );
  const card = group(region(page, "Daily activity"), "Logins per day");
  await expect(card).toContainText("No logins in this period.");
  await expect(card).not.toContainText("Unavailable");
});

test("adm07 p4 AC41 drafts started and published are two cards with their own values and notes", async ({
  page,
}) => {
  await ready(
    page,
    (m) => {
      m.tweak.daily = (b) => {
        b.practice_drafts_started = {
          state: "available",
          reason: null,
          since: "2026-11-01",
          data_starts_on: null,
          total: 5,
          per_day: [{ date: "2026-11-09", drafts_started: 5 }],
        };
        b.practice_published = {
          state: "available",
          reason: null,
          since: "2026-11-01",
          data_starts_on: null,
          total: 2,
          per_day: [{ date: "2026-11-09", published: 2 }],
        };
      };
    },
    ONE_DAY,
  );
  const daily = region(page, "Daily activity");
  const drafts = group(daily, "Practice drafts started per day");
  const pub = group(daily, "Practice sets published per day");
  for (const card of [drafts, pub]) {
    await expect(card).not.toContainText("Unavailable");
    await expect(card).not.toContainText(NOT_COLLECTED);
    await card
      .getByRole("button", { name: "Show data table", exact: true })
      .click();
  }
  await expect(drafts).toContainText(
    "A set is counted once, on the day its first draft was saved.",
  );
  await expect(pub).toContainText(
    "A set is counted once, on the day it was first published. Unpublishing and republishing do not change the count.",
  );
  const dt = drafts.getByRole("table", {
    name: "Practice drafts started per day data",
  });
  await expect(
    dt.getByRole("columnheader", { name: "Drafts started" }),
  ).toBeVisible();
  await expect(dt.getByRole("cell", { name: "5", exact: true })).toBeVisible();
  const pt = pub.getByRole("table", {
    name: "Practice sets published per day data",
  });
  await expect(
    pt.getByRole("columnheader", { name: "Published" }),
  ).toBeVisible();
  await expect(pt.getByRole("cell", { name: "2", exact: true })).toBeVisible();
});

test("adm07 p4 AC23 a partly covered series shows the data-starts note on its own card only", async ({
  page,
}) => {
  await ready(
    page,
    (m) => {
      m.tweak.daily = (b) => {
        b.logins = {
          state: "available",
          reason: null,
          since: "2026-11-08",
          data_starts_on: "2026-11-08",
          total_logins: 1,
          per_day: [
            day("2026-11-08"),
            day("2026-11-09", {
              student_logins: 1,
              total_logins: 1,
              active_students: 1,
              active_users_total: 1,
            }),
          ],
        };
      };
    },
    THREE_DAYS,
  );
  const note =
    "Data starts on 2026-11-08. Earlier days in this period are not included.";
  const daily = region(page, "Daily activity");
  await expect(group(daily, "Logins per day")).toContainText(note);
  await expect(
    group(daily, "Practice drafts started per day").getByText(note),
  ).toHaveCount(0);
});

test("adm07 p4 AC23 a series wholly before its start is still the specified unavailable state, never zero", async ({
  page,
}) => {
  await ready(page, (m) => {
    m.tweak.daily = (b) => {
      b.logins = {
        state: "unavailable",
        reason: "period_before_recording",
        since: "2026-12-01",
        data_starts_on: null,
        total_logins: null,
        per_day: [],
      };
    };
  });
  const card = group(region(page, "Daily activity"), "Logins per day");
  await expect(card).toContainText("Unavailable");
  await expect(card).toContainText(", after this period ended");
  await expect(card).not.toContainText("No logins in this period.");
});

// ================================================================== Hourly categories (AC13)

test("adm07 p4 AC13 modal table and CSV carry real category counts", async ({
  page,
}) => {
  const mock = await ready(
    page,
    (m) => {
      m.tweak.hourly = (b) => {
        b.category_breakdown = { state: "available", reason: null };
        const h16 = b.buckets.find(
          (x: { hour_start: string }) =>
            x.hour_start === "2026-11-09T16:00:00Z",
        );
        h16.failed_by_category = {
          timeout: 0,
          rate_limited: 1,
          invalid_output: 0,
          upstream: 0,
          unclassified: 0,
        };
      };
    },
    ONE_DAY,
  );
  const before = mock.count();
  await expand(page, "Requests per hour").click();
  const dialog = modal(page, "Requests per hour");
  const table = dialog.getByRole("table", { name: "Requests per hour data" });
  await expect(table.getByText("Unavailable")).toHaveCount(0);
  const [download] = await Promise.all([
    page.waitForEvent("download"),
    dialog.getByRole("button", { name: "Download CSV", exact: true }).click(),
  ]);
  const fs = await import("node:fs/promises");
  const csv = await fs.readFile((await download.path())!, "utf8");
  const lines = csv.split("\r\n");
  const line = lines.find((l) => l.startsWith("2026-11-09T16:00:00Z"))!;
  expect(line.endsWith(",0,1,0,0,0")).toBe(true); // timeout,rate_limited,invalid_output,upstream,unclassified
  const empty = lines.find((l) => l.startsWith("2026-11-09T00:00:00Z"))!;
  expect(empty.endsWith(",0,0,0,0,0")).toBe(true); // real zeros, not empty cells
  await page.keyboard.press("Escape");
  expect(mock.count()).toBe(before);
});

test("adm07 p4 AC13 rate-limited generation counted in an hour is visible in the chart data table", async ({
  page,
}) => {
  await ready(
    page,
    (m) => {
      m.tweak.hourly = (b) => {
        b.category_breakdown = { state: "available", reason: null };
        const h = b.buckets.find(
          (x: { hour_start: string }) =>
            x.hour_start === "2026-11-09T17:00:00Z",
        );
        h.successful = 0;
        h.failed = 2;
        h.total = 2;
        h.failure_rate_percent = 100.0;
        h.failed_by_category = {
          timeout: 0,
          rate_limited: 2,
          invalid_output: 0,
          upstream: 0,
          unclassified: 0,
        };
        b.totals = { successful: 3, failed: 3, total: 6 };
      };
    },
    ONE_DAY,
  );
  await expect(
    page.getByRole("img", {
      name: /Requests per hour chart: 6 requests, 3 failed/,
    }),
  ).toBeVisible();
});

// ================================================================== Phase 2 unavailable states stay reachable

test("adm07 p4 the unavailable states stay renderable: whole period beyond retention for the hourly block", async ({
  page,
}) => {
  await ready(page, (m) => {
    m.tweak.hourly = (b) => {
      b.state = "unavailable";
      b.reason = "beyond_retention";
      b.buckets = [];
      b.totals = null;
      b.category_breakdown = {
        state: "unavailable",
        reason: "beyond_retention",
      };
    };
  });
  await expect(region(page, "Health")).toContainText(
    "hourly data is kept for 30 days and this period starts earlier",
  );
});

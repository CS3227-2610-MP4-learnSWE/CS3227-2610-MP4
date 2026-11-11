import { test, expect, type Locator, type Page } from "@playwright/test";
import { STUDENT, TEACHER } from "./authApi";
import { HUB, isoDay, setup, type HubMock } from "./adm07Api";

/**
 * ADM-07 hub at /admin/analytics, phase 2 (existing data). Roles, names and copy come only from
 * workflow/specs/ADM-07/plan.md "UI contract" and spec.md "UI states and copy". The API is mocked
 * (adm07Api.ts). Metrics without a source in phase 2 are asserted as the specified unavailable state.
 * [P4] behaviour (real logins, drafts, published, categories, rate-limited counts) is not tested here.
 */

const MSG = {
  network: "Could not reach the server. Check your connection and try again.",
  timeout: "The request timed out after 15 seconds. Try again.",
  forbidden: "You do not have access to analytics.",
  http: (subject: string, status: number) =>
    `${subject} could not be loaded: the server returned an error (${status}). Try again.`,
  dates: {
    format: "Enter dates as YYYY-MM-DD.",
    order: "The start date must be on or before the end date.",
    long: "The period can be at most 366 days.",
    future: "The end date cannot be in the future (UTC).",
  },
  muted: (tz: string) =>
    `Recorded data only. Dates are UTC; chart times are shown in your local time (${tz}).`,
  partial:
    "Data starts on 2026-11-05. Earlier days in this period are not included.",
  notCollected: "collection of this metric has not started",
};

const BLOCKS = [
  ["health", "Health", "Loading health..."],
  ["hourly", "Hourly charts", "Loading hourly charts..."],
  ["daily", "Daily activity", "Loading daily activity..."],
  ["users", "Chatbot users", "Loading chatbot users..."],
  ["generation", "Generation reliability", "Loading generation reliability..."],
  ["aiusage", "AI usage", "Loading AI usage..."],
  ["quality", "Quality results", "Loading quality results..."],
] as const;
const RETRY: Record<string, string> = {
  health: "Retry health",
  hourly: "Retry hourly charts",
  daily: "Retry daily activity",
  users: "Retry chatbot users",
  generation: "Retry generation reliability",
  aiusage: "Retry AI usage",
  quality: "Retry quality results",
};

// ---- locators
const h1 = (p: Page) =>
  p.getByRole("heading", { level: 1, name: "Feature Analytics", exact: true });
const region = (p: Page, name: string) =>
  p.getByRole("region", { name, exact: true });
const group = (p: Page | Locator, name: string) =>
  p.getByRole("group", { name, exact: true });
const periodSelect = (p: Page) =>
  p.getByRole("combobox", { name: "Reporting period", exact: true });
const refresh = (p: Page) =>
  p.getByRole("button", { name: "Refresh", exact: true });
const rangeDialog = (p: Page) =>
  p.getByRole("dialog", { name: "Custom range", exact: true });
const alertWith = (scope: Page | Locator, text: string) =>
  scope.getByRole("alert").filter({ hasText: text });
const expand = (p: Page, chart: string) =>
  p.getByRole("button", { name: `Expand ${chart}`, exact: true });
const modal = (p: Page, title: string) =>
  p.getByRole("dialog", { name: title, exact: true });
const usersTable = (p: Page) =>
  p.getByRole("table", { name: "Chatbot requests by user", exact: true });
const tab = (p: Page | Locator, name: string) =>
  p.getByRole("tab", { name, exact: true });

async function ready(
  page: Page,
  configure?: (mock: HubMock) => void,
  url = HUB,
) {
  const mock = await setup(page);
  configure?.(mock);
  await page.goto(url);
  await expect(group(page, "Chatbot success rate")).toBeVisible();
  await expect(
    page.getByRole("status").filter({ hasText: /^Loading / }),
  ).toHaveCount(0);
  return mock;
}

async function openCustom(page: Page) {
  await periodSelect(page).selectOption({ label: "Custom range" });
  await expect(rangeDialog(page)).toBeVisible();
}

async function applyRange(page: Page, from: string, to: string) {
  await openCustom(page);
  await rangeDialog(page).getByLabel("From date", { exact: true }).fill(from);
  await rangeDialog(page).getByLabel("To date", { exact: true }).fill(to);
  await rangeDialog(page)
    .getByRole("button", { name: "Apply period", exact: true })
    .click();
}

const KINDS = [
  "health",
  "hourly",
  "daily",
  "users",
  "generation",
  "quality",
  "aiusage",
] as const;

// ================================================================== structure (US-ADM-07-08)

test("adm07 header, muted line, sections, period options and controls", async ({
  page,
}) => {
  await ready(page);
  await expect(h1(page)).toBeVisible();
  const tz = await page.evaluate(
    () => Intl.DateTimeFormat().resolvedOptions().timeZone,
  );
  await expect(page.getByText(MSG.muted(tz), { exact: true })).toBeVisible();
  for (const name of ["Health", "Feature outcomes", "AI usage", "Quality"]) {
    await expect(
      page.getByRole("heading", { level: 2, name, exact: true }),
    ).toBeVisible();
    await expect(region(page, name)).toBeVisible();
  }
  const options = await periodSelect(page).locator("option").allInnerTexts();
  expect(options).toEqual([
    "Today (UTC)",
    "Last 7 days",
    "Last 30 days",
    "Custom range",
  ]);
  await expect(periodSelect(page)).toContainText("Last 7 days");
  await expect(refresh(page)).toBeEnabled();
  await expect(page.getByText(/^Last updated /)).toBeVisible();
});

test("adm07 nav link Feature Analytics is distinct from the demo Analytics link", async ({
  page,
}) => {
  await ready(page);
  await expect(
    page.getByRole("link", { name: "Feature Analytics", exact: true }),
  ).toHaveAttribute("href", HUB);
  await expect(
    page.getByRole("link", { name: "Analytics", exact: true }),
  ).toHaveAttribute("href", "/admin/overview");
});

test("adm07 AC29 load sends exactly seven parallel requests with the exact URLs", async ({
  page,
}) => {
  const mock = await ready(page);
  expect(mock.count()).toBe(7);
  expect(mock.requests.map((r) => r.kind).sort()).toEqual([...KINDS].sort());
  const from = isoDay(6);
  const to = isoDay(0);
  for (const kind of [
    "health",
    "hourly",
    "daily",
    "users",
    "generation",
    "quality",
  ] as const) {
    const q = mock.of(kind)[0].url.searchParams;
    expect([q.get("period_start"), q.get("period_end")]).toEqual([from, to]);
  }
  const users = mock.of("users")[0].url.searchParams;
  expect(users.get("role")).toBe("student");
  expect(users.get("sort")).toBe("unsuccessful");
  expect(users.get("order")).toBe("desc");
  expect(users.get("limit")).toBe("10");
  expect(users.get("offset")).toBe("0");
  const quality = mock.of("quality")[0].url.searchParams;
  expect(quality.get("workflow")).toBe("student_exercise");
  expect(quality.get("limit")).toBe("25");
  expect(quality.get("offset")).toBe("0");
  const ai = mock.of("aiusage")[0].url.searchParams;
  expect([ai.get("feature"), ai.get("start_date"), ai.get("end_date")]).toEqual(
    ["all", from, to],
  );
  for (const r of mock.requests) expect(r.method).toBe("GET");
});

test("adm07 AC29 each block shows its own loading text and one slow block does not hide the others", async ({
  page,
}) => {
  const mock = await setup(page);
  for (const [kind] of BLOCKS) mock.next(kind, { hold: true });
  await page.goto(HUB);
  for (const [, , text] of BLOCKS)
    await expect(
      page.getByRole("status").filter({ hasText: text }),
    ).toBeVisible();
  await expect(refresh(page)).toBeDisabled(); // Refresh is disabled while a load is pending
  expect(mock.count()).toBe(7);
  mock.release();
  await expect(usersTable(page)).toBeVisible();
  expect(mock.count()).toBe(7); // no duplicate requests after the load
});

test("adm07 AC29 a period longer than 31 days sends six requests and explains the AI usage limit", async ({
  page,
}) => {
  const mock = await ready(
    page,
    undefined,
    `${HUB}?from=2026-01-01&to=2026-03-15`,
  );
  await expect(
    page.getByText(
      "AI usage covers at most 31 days ending today or earlier. Choose a shorter period to see AI usage.",
      { exact: true },
    ),
  ).toBeVisible();
  await expect(usersTable(page)).toBeVisible(); // every block has rendered before requests are counted
  expect(mock.count()).toBe(6);
  expect(mock.count("aiusage")).toBe(0);
});

// ================================================================== KPI tiles (AC5-AC8)

const TILES = [
  "Chatbot success rate",
  "Generation success rate",
  "Rate-limited requests",
  "Chatbot response time",
  "Generation response time",
  "Practice completion",
];

test("adm07 AC5 six KPI tiles in order with values, details and chips", async ({
  page,
}) => {
  await ready(page);
  const kpi = group(region(page, "Health"), "KPI tiles");
  for (const name of TILES) await expect(group(kpi, name)).toBeVisible();
  const chatbot = group(kpi, "Chatbot success rate");
  await expect(chatbot).toContainText("92.5%");
  await expect(chatbot).toContainText("111 of 120 chatbot requests succeeded");
  await expect(chatbot).toContainText("Critical: below 95%");
  const generation = group(kpi, "Generation success rate");
  await expect(generation).toContainText("96.7%");
  await expect(generation).toContainText("Warning: 95% to 98%");
  await expect(generation).toContainText(
    "29 of 30 generation attempts succeeded; rate-limited requests are not recorded yet",
  );
  await expect(group(kpi, "Practice completion")).toContainText(/70(\.0)?%/);
  await expect(group(kpi, "Practice completion")).toContainText(
    "7 of 10 attempts submitted by the end of the period",
  );
});

test("adm07 AC10 phase 2 rate-limited tile is the unavailable not-collected state, never zero", async ({
  page,
}) => {
  await ready(page);
  const tile = group(page, "Rate-limited requests");
  await expect(tile).toContainText("Unavailable");
  await expect(tile).toContainText(`${MSG.notCollected}.`);
});

const SEVERITIES = [
  ["low_sample", 19, 19, "Low sample: fewer than 20 requests"],
  ["ok", 100, 1, "Healthy: 98% or above"],
  ["warning", 100, 3, "Warning: 95% to 98%"],
  ["critical", 100, 6, "Critical: below 95%"],
] as const;

for (const [severity, total, failed, chip] of SEVERITIES) {
  test(`adm07 AC7 ${severity} chip shows icon, words and data-severity`, async ({
    page,
  }) => {
    await ready(page, (m) => {
      m.tweak.health = (b) => {
        b.chatbot_failure.severity = severity;
        b.chatbot_failure.total = total;
        b.chatbot_failure.failed = failed;
        b.chatbot_failure.rate_percent = (failed * 100) / total;
      };
    });
    const tile = group(page, "Chatbot success rate");
    await expect(tile.getByText(chip, { exact: true })).toBeVisible();
    await expect(
      page.locator(`[data-severity="${severity}"]`).first(),
    ).toBeAttached();
    // the icon is decorative (aria-hidden) and sits with the visible words
    expect(await tile.locator("[aria-hidden='true']").count()).toBeGreaterThan(
      0,
    );
  });
}

for (const theme of ["light", "dark"] as const) {
  for (const [severity, total, failed, chip] of SEVERITIES) {
    test(`adm07 AC7 ${severity} chip text meets 4.5:1 contrast in the ${theme} theme`, async ({
      page,
    }) => {
      await page.emulateMedia({ colorScheme: theme });
      const mock = await setup(page);
      mock.tweak.health = (b) => {
        b.chatbot_failure.severity = severity;
        b.chatbot_failure.total = total;
        b.chatbot_failure.failed = failed;
      };
      await page.goto(HUB);
      const text = group(page, "Chatbot success rate").getByText(chip, {
        exact: true,
      });
      await expect(text).toBeVisible();
      const ratio = await text.evaluate((el, dark) => {
        const parse = (c: string) => (c.match(/[\d.]+/g) ?? []).map(Number);
        const lum = ([r, g, b]: number[]) => {
          const f = (v: number) => {
            const s = v / 255;
            return s <= 0.03928
              ? s / 12.92
              : Math.pow((s + 0.055) / 1.055, 2.4);
          };
          return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b);
        };
        let bg = dark ? [0, 0, 0] : [255, 255, 255];
        for (let n: Element | null = el; n; n = n.parentElement) {
          const c = parse(getComputedStyle(n).backgroundColor);
          if (c.length >= 3 && (c.length === 3 || c[3] > 0.9)) {
            bg = c.slice(0, 3);
            break;
          }
        }
        const fg = parse(getComputedStyle(el).color).slice(0, 3);
        const [hi, lo] = [lum(fg), lum(bg)].sort((x, y) => y - x);
        return (hi + 0.05) / (lo + 0.05);
      }, theme === "dark");
      expect(ratio, `${severity} ${theme}`).toBeGreaterThanOrEqual(4.5);
    });
  }
}

test("adm07 AC8 response-time tiles: separate per workflow, default All, radios switch sets with no request", async ({
  page,
}) => {
  const mock = await ready(page);
  const tile = group(page, "Chatbot response time");
  const radios = tile; // radios found by role inside the tile (radio group role is not pinned)
  await expect(
    radios.getByRole("radio", { name: "All", exact: true }),
  ).toBeChecked();
  await expect(tile.getByTestId("response-time-median")).toHaveText(/2\.10 s/);
  await expect(tile.getByTestId("response-time-p95")).toHaveText(/5\.40 s/);
  await expect(tile).toContainText("120 requests, 9 failed or timed out");
  const before = mock.count();
  await radios.getByRole("radio", { name: "Successful", exact: true }).check();
  await expect(tile.getByTestId("response-time-median")).toHaveText(/2\.00 s/);
  await expect(tile.getByTestId("response-time-p95")).toHaveText(/4\.10 s/);
  await expect(tile).toContainText("111 successful requests");
  await radios.getByRole("radio", { name: "Failed", exact: true }).check();
  await expect(tile.getByTestId("response-time-median")).toHaveText(
    /120\.00 s/,
  );
  await expect(tile).toContainText(
    "9 failed or timed-out requests (timeouts count as 120 s)",
  );
  expect(mock.count()).toBe(before);
  // the generation tile has its own selector and figures
  const gen = group(page, "Generation response time");
  await expect(
    gen.getByRole("radio", {
      name: "All",
    }),
  ).toBeChecked();
  await expect(gen.getByTestId("response-time-median")).toHaveText(/14\.20 s/);
  await expect(gen.getByTestId("response-time-p95")).toHaveText(/31\.80 s/);
});

test("adm07 AC8 selection survives Refresh and period change and resets on browser reload", async ({
  page,
}) => {
  const mock = await ready(page);
  const radios = group(page, "Chatbot response time");
  await radios.getByRole("radio", { name: "Failed", exact: true }).check();
  await refresh(page).click();
  await expect.poll(() => mock.count()).toBe(14);
  await expect(
    radios.getByRole("radio", { name: "Failed", exact: true }),
  ).toBeChecked();
  await periodSelect(page).selectOption({ label: "Last 30 days" });
  await expect.poll(() => mock.count()).toBe(21);
  await expect(
    radios.getByRole("radio", { name: "Failed", exact: true }),
  ).toBeChecked();
  await page.reload();
  await expect(group(page, "Chatbot success rate")).toBeVisible();
  await expect(
    radios.getByRole("radio", { name: "All", exact: true }),
  ).toBeChecked();
});

test("adm07 AC8 an empty selected set says No requests, never 0 or a time", async ({
  page,
}) => {
  await ready(page, (m) => {
    m.tweak.health = (b) => {
      b.chatbot_response_time.failed = {
        count: 0,
        median_ms: null,
        p95_ms: null,
      };
      b.chatbot_response_time.all = {
        count: 111,
        median_ms: 2000,
        p95_ms: 4100,
      };
    };
  });
  const tile = group(page, "Chatbot response time");
  await tile.getByRole("radio", { name: "Failed", exact: true }).check();
  await expect(tile).toContainText("No requests");
  await expect(tile).toContainText("No failed requests in this period.");
  await expect(tile.getByTestId("response-time-median")).toHaveCount(0);
  await expect(tile).not.toContainText(/0\.00 s/);
});

test("adm07 AC38 in-progress note appears on the chatbot tile and the charts", async ({
  page,
}) => {
  await ready(page, (m) => {
    m.tweak.health = (b) => {
      b.chatbot_failure.in_progress = 2;
    };
    m.tweak.hourly = (b) => {
      b.in_progress = 2;
    };
  });
  await expect(group(page, "Chatbot success rate")).toContainText(
    "2 in progress",
  );
  await expect(region(page, "Hourly activity")).toContainText("2 in progress");
});

test("adm07 not-applicable and unavailable tiles use the specified words", async ({
  page,
}) => {
  await ready(page, (m) => {
    m.tweak.health = (b) => {
      b.chatbot_failure = {
        state: "not_applicable",
        reason: "no_chat_requests",
        total: 0,
        failed: 0,
        in_progress: 0,
        rate_percent: null,
        severity: null,
      };
      b.practice_completion = {
        state: "unavailable",
        reason: "read_failed",
        started: null,
        submitted: null,
        percentage: null,
      };
    };
  });
  const chat = group(page, "Chatbot success rate");
  await expect(chat).toContainText("Not applicable");
  await expect(chat).toContainText("no chatbot requests in this period.");
  const pc = group(page, "Practice completion");
  await expect(pc).toContainText("Unavailable");
  await expect(pc).toContainText("the value could not be read reliably.");
});

test("adm07 AC39 partial coverage notes under the strip, charts and blocks", async ({
  page,
}) => {
  await ready(page, (m) => {
    const note = (b: { data_starts_on: string | null }) => {
      b.data_starts_on = "2026-11-05";
    };
    m.tweak.health = note;
    m.tweak.hourly = note;
    m.tweak.users = note;
  });
  expect(
    await page.getByText(MSG.partial, { exact: true }).count(),
  ).toBeGreaterThanOrEqual(2);
  await expect(region(page, "Hourly activity")).toContainText(MSG.partial);
});

// ================================================================== charts (AC14-AC18)

const CHARTS = ["Requests per hour", "Failure rate per hour", "Peak hours"];
const ONE_DAY = `${HUB}?from=2026-11-09&to=2026-11-09`;

test("adm07 AC18 three charts are images with the specified accessible names", async ({
  page,
}) => {
  await ready(page, undefined, ONE_DAY);
  const hourly = region(page, "Hourly activity");
  for (const chart of CHARTS) await expect(group(hourly, chart)).toBeVisible();
  await expect(
    hourly.getByRole("img", {
      name: "Requests per hour chart: 6 requests, 1 failed over 24 hours",
    }),
  ).toBeVisible();
  await expect(
    hourly.getByRole("img", {
      name: "Failure rate per hour chart: 2 hours with requests, 5% reference line",
    }),
  ).toBeVisible();
  await expect(
    hourly.getByRole("img", {
      name: /^Peak hours heatmap: busiest hour .* with \d+ requests$/,
    }),
  ).toBeVisible();
  await expect(hourly.getByText("Fewer requests")).toBeVisible();
  await expect(hourly.getByText("More requests")).toBeVisible();
});

test("adm07 AC15 reference line only on the failure-rate chart; tooltips by test id", async ({
  page,
}) => {
  await ready(page, undefined, ONE_DAY);
  const hourly = region(page, "Hourly activity");
  await expect(
    group(hourly, "Failure rate per hour").getByTestId("reference-5"),
  ).toHaveCount(1);
  await expect(
    group(hourly, "Requests per hour").getByTestId("reference-5"),
  ).toHaveCount(0);
  await expect(
    group(hourly, "Peak hours").getByTestId("reference-5"),
  ).toHaveCount(0);
  await group(hourly, "Requests per hour")
    .getByTestId("bar-2026-11-09T16:00:00Z")
    .hover();
  await expect(page.getByRole("tooltip")).toContainText(
    "4 requests (3 successful, 1 failed, 25.0% failed)",
  );
  await group(hourly, "Failure rate per hour")
    .getByTestId("point-2026-11-09T16:00:00Z")
    .hover();
  await expect(page.getByRole("tooltip")).toContainText(
    "25.0% failed (1 of 4 requests)",
  );
});

test("adm07 AC15 an hour without requests says no requests in its tooltip", async ({
  page,
}) => {
  await ready(page, undefined, ONE_DAY);
  const bar = group(
    region(page, "Hourly activity"),
    "Requests per hour",
  ).getByTestId("bar-2026-11-09T05:00:00Z");
  await bar.hover({ force: true });
  await expect(page.getByRole("tooltip")).toContainText(": no requests");
});

const ZONES = [
  [
    "Asia/Singapore",
    "2026-11-10T00:00:00+08:00",
    "cell-1-0",
    "Tuesday 00:00: 4 requests, 1 failed",
  ],
  [
    "America/New_York",
    "2026-11-09T11:00:00-05:00",
    "cell-0-11",
    "Monday 11:00: 4 requests, 1 failed",
  ],
] as const;

for (const [timezoneId, local, cell, tip] of ZONES) {
  test.describe(`timezone ${timezoneId}`, () => {
    test.use({ timezoneId });

    test(`adm07 AC14 heatmap cell, axis note and CSV move to ${timezoneId}`, async ({
      page,
    }) => {
      await ready(page, undefined, ONE_DAY);
      const hourly = region(page, "Hourly activity");
      await expect(
        page.getByText(MSG.muted(timezoneId), { exact: true }),
      ).toBeVisible();
      await expect(
        hourly.getByText(`Times shown in ${timezoneId}`).first(),
      ).toBeVisible();
      await group(hourly, "Peak hours").getByTestId(cell).hover();
      await expect(page.getByRole("tooltip")).toContainText(tip);
      await expand(page, "Requests per hour").click();
      const dialog = modal(page, "Requests per hour");
      await expect(dialog).toBeVisible();
      const row = dialog
        .getByRole("table", { name: "Requests per hour data" })
        .getByRole("row")
        .filter({ hasText: "25.0%" });
      await expect(row.first()).toBeVisible();
      const [download] = await Promise.all([
        page.waitForEvent("download"),
        dialog
          .getByRole("button", { name: "Download CSV", exact: true })
          .click(),
      ]);
      const fs = await import("node:fs/promises");
      const csv = await fs.readFile((await download.path())!, "utf8");
      expect(csv).toContain(`2026-11-09T16:00:00Z,${local},3,1,4,25,,,,,`);
    });
  });
}

test("adm07 AC16 modal: initial focus, focus trap, Esc, backdrop, focus return, no requests", async ({
  page,
}) => {
  const mock = await ready(page, undefined, ONE_DAY);
  const before = mock.count();
  for (const chart of CHARTS) {
    const opener = expand(page, chart);
    await opener.click();
    const dialog = modal(page, chart);
    await expect(dialog).toBeVisible();
    await expect(dialog).toHaveAttribute("aria-modal", "true");
    await expect(
      dialog.getByRole("button", { name: "Close", exact: true }),
    ).toBeFocused();
    await expect(
      dialog.getByRole("table", { name: `${chart} data` }),
    ).toBeAttached();
    for (let i = 0; i < 12; i++) {
      await page.keyboard.press("Tab");
      expect(
        await dialog.evaluate((d) => d.contains(document.activeElement)),
      ).toBe(true);
    }
    await page.keyboard.press("Shift+Tab");
    expect(
      await dialog.evaluate((d) => d.contains(document.activeElement)),
    ).toBe(true);
    await page.keyboard.press("Escape");
    await expect(dialog).toHaveCount(0);
    await expect(opener).toBeFocused();
  }
  await expand(page, "Peak hours").click();
  await modal(page, "Peak hours")
    .getByRole("button", { name: "Close", exact: true })
    .click();
  await expect(modal(page, "Peak hours")).toHaveCount(0);
  await expand(page, "Peak hours").click();
  await page.mouse.click(2, 2); // backdrop
  await expect(modal(page, "Peak hours")).toHaveCount(0);
  await expect(expand(page, "Peak hours")).toBeFocused();
  expect(mock.count()).toBe(before); // opening and closing the modal sends nothing
});

test("adm07 AC17 CSV: filename, exact header, 24 rows, CRLF, empty category cells, no request", async ({
  page,
}) => {
  const mock = await ready(page, undefined, ONE_DAY);
  const before = mock.count();
  const cases = [
    [
      "Requests per hour",
      "requests-per-hour_2026-11-09_2026-11-09.csv",
      "hour_utc,hour_local,successful,failed,total,failure_rate_percent,timeout,rate_limited,invalid_output,upstream,unclassified",
      24,
    ],
    [
      "Failure rate per hour",
      "failure-rate-per-hour_2026-11-09_2026-11-09.csv",
      "hour_utc,hour_local,requests,failed,failure_rate_percent",
      24,
    ],
    [
      "Peak hours",
      "peak-hours_2026-11-09_2026-11-09.csv",
      "weekday,hour_local,requests,failed",
      168,
    ],
  ] as const;
  for (const [chart, filename, header, rows] of cases) {
    await expand(page, chart).click();
    const dialog = modal(page, chart);
    const [download] = await Promise.all([
      page.waitForEvent("download"),
      dialog.getByRole("button", { name: "Download CSV", exact: true }).click(),
    ]);
    expect(download.suggestedFilename()).toBe(filename);
    const fs = await import("node:fs/promises");
    const csv = await fs.readFile((await download.path())!, "utf8");
    expect(csv.charCodeAt(0)).not.toBe(0xfeff);
    const lines = csv.split("\r\n");
    expect(lines[0]).toBe(header);
    expect(lines.filter((l) => l.length > 0).length).toBe(rows + 1);
    expect(csv).not.toMatch(/(?<!\r)\n/);
    if (chart === "Requests per hour") {
      expect(lines[1]).toMatch(/^2026-11-09T00:00:00Z,[^,]+,0,0,0,,,,,,$/); // null rate and unavailable categories are empty
    }
    if (chart === "Peak hours") {
      expect(lines[1].startsWith("Monday,")).toBe(true);
      expect(lines[168].startsWith("Sunday,")).toBe(true);
    }
    await page.keyboard.press("Escape");
  }
  expect(mock.count()).toBe(before);
});

test("adm07 AC16 modal table shows Unavailable in category cells while the breakdown is unavailable", async ({
  page,
}) => {
  await ready(page, undefined, ONE_DAY);
  await expand(page, "Requests per hour").click();
  const table = modal(page, "Requests per hour").getByRole("table", {
    name: "Requests per hour data",
  });
  for (const col of [
    "Hour (local)",
    "Successful",
    "Failed",
    "Total",
    "Failure rate",
    "Timeout",
    "Rate-limited",
    "Invalid output",
    "Upstream",
    "Unclassified",
  ])
    await expect(
      table.getByRole("columnheader", { name: col, exact: true }),
    ).toBeVisible();
  await expect(table.getByText("Unavailable").first()).toBeVisible();
  await expect(table.getByText("No requests").first()).toBeVisible();
});

test("adm07 AC15 zero requests: empty text replaces charts and Expand is disabled", async ({
  page,
}) => {
  await ready(page, (m) => {
    m.tweak.hourly = (b) => {
      for (const x of b.buckets)
        Object.assign(x, {
          successful: 0,
          failed: 0,
          total: 0,
          failure_rate_percent: null,
        });
      b.totals = { successful: 0, failed: 0, total: 0 };
    };
  });
  await expect(
    region(page, "Hourly activity")
      .getByText("No requests in this period.")
      .first(),
  ).toBeVisible();
  for (const chart of CHARTS) await expect(expand(page, chart)).toBeDisabled();
});

test("adm07 AC13 hourly unavailable reason is shown in each card", async ({
  page,
}) => {
  await ready(page, (m) => {
    m.tweak.hourly = (b) => {
      b.state = "unavailable";
      b.reason = "beyond_retention";
      b.buckets = [];
      b.totals = null;
    };
  });
  await expect(
    region(page, "Hourly activity")
      .getByText(
        "Unavailable: hourly data is kept for 30 days and this period starts earlier.",
      )
      .first(),
  ).toBeVisible();
});

test("adm07 AC18 reduced motion removes transitions on charts and modal", async ({
  page,
}) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await ready(page, undefined, ONE_DAY);
  await expand(page, "Peak hours").click();
  const durations = await modal(page, "Peak hours").evaluate((d) =>
    [d, ...Array.from(d.querySelectorAll("*"))].map((e) => {
      const s = getComputedStyle(e);
      return [s.transitionDuration, s.animationDuration].join("|");
    }),
  );
  // reduced motion may use a near-zero duration (1e-5 s) instead of exactly 0
  for (const d of durations)
    for (const v of d.split(/[|,]/).map((x) => parseFloat(x)))
      expect(v).toBeLessThanOrEqual(0.001);
});

// ================================================================== daily activity (AC19-AC23, AC41)

test("adm07 AC41 five daily cards; drafts started and published are two cards", async ({
  page,
}) => {
  await ready(page);
  const daily = region(page, "Daily activity");
  for (const name of [
    "Logins per day",
    "Practice drafts started per day",
    "Practice sets published per day",
    "Attempts started and submitted per day",
    "Attempts per student per day",
  ])
    await expect(group(daily, name)).toBeVisible();
});

test("adm07 AC23 phase 2: logins, drafts and published are unavailable, not zero", async ({
  page,
}) => {
  await ready(page);
  const daily = region(page, "Daily activity");
  for (const name of [
    "Logins per day",
    "Practice drafts started per day",
    "Practice sets published per day",
  ]) {
    const card = group(daily, name);
    await expect(card).toContainText("Unavailable");
    await expect(card).toContainText(MSG.notCollected);
    await expect(card).not.toContainText("No logins in this period.");
    await expect(card).not.toContainText(
      "No practice drafts were started in this period.",
    );
    await expect(card).not.toContainText(
      "No practice sets were published in this period.",
    );
  }
});

test("adm07 AC19 funnel and attempts-per-student cards: summary, notes and data tables", async ({
  page,
}) => {
  const mock = await ready(page);
  const daily = region(page, "Daily activity");
  const before = mock.count();
  const funnel = group(daily, "Attempts started and submitted per day");
  await expect(funnel).toContainText(
    "In this period: 10 attempts started; 7 of them submitted by the end of the period.",
  );
  await expect(funnel).toContainText(
    "Submitted counts use the day of submission, so they can include attempts started earlier.",
  );
  const toggle = funnel.getByRole("button", {
    name: "Show data table",
    exact: true,
  });
  await expect(toggle).toHaveAttribute("aria-expanded", "false");
  await toggle.click();
  await expect(
    funnel.getByRole("button", { name: "Hide data table", exact: true }),
  ).toHaveAttribute("aria-expanded", "true");
  const table = funnel.getByRole("table", {
    name: "Attempts started and submitted per day data",
  });
  for (const col of ["Date", "Started", "Submitted"])
    await expect(
      table.getByRole("columnheader", { name: col, exact: true }),
    ).toBeVisible();
  const per = group(daily, "Attempts per student per day");
  await per
    .getByRole("button", { name: "Show data table", exact: true })
    .click();
  const ptable = per.getByRole("table", {
    name: "Attempts per student per day data",
  });
  for (const col of [
    "Date",
    "Students",
    "Median attempts",
    "1 attempt",
    "2 attempts",
    "3 attempts",
    "4 attempts",
    "5 or more",
  ])
    await expect(
      ptable.getByRole("columnheader", { name: col, exact: true }),
    ).toBeVisible();
  await expect(ptable).toContainText("1.5");
  await expect(daily.getByText("Days are UTC dates.").first()).toBeVisible();
  expect(mock.count()).toBe(before); // the disclosure sends nothing
});

test("adm07 AC21 no attempts started: not applicable and the empty student text", async ({
  page,
}) => {
  await ready(page, (m) => {
    m.tweak.daily = (b) => {
      b.attempts_funnel.state = "not_applicable";
      b.attempts_funnel.reason = "no_practice_attempts";
      b.attempts_per_student.state = "not_applicable";
      b.attempts_per_student.reason = "no_practice_attempts";
    };
  });
  const daily = region(page, "Daily activity");
  await expect(
    daily
      .getByText(
        "Not applicable: no practice attempts were started in this period.",
      )
      .first(),
  ).toBeVisible();
});

// ================================================================== chatbot users (AC24-AC26)

test("adm07 AC25 users table: columns, summary, paging text, sort and role tabs", async ({
  page,
}) => {
  const mock = await ready(page);
  const users = region(page, "Feature outcomes");
  await expect(usersTable(page)).toBeVisible();
  for (const col of ["Name", "Successful", "Unsuccessful", "Failure rate"])
    await expect(
      usersTable(page).getByRole("columnheader", { name: new RegExp(col) }),
    ).toBeVisible();
  await expect(
    usersTable(page).getByRole("columnheader", { name: /Unsuccessful/ }),
  ).toHaveAttribute("aria-sort", "descending");
  await expect(
    users.getByText("Students total: 120 successful, 9 unsuccessful"),
  ).toBeVisible();
  await expect(
    users.getByText(
      "Teachers total: Unavailable: this activity is not recorded.",
    ),
  ).toBeVisible();
  await expect(
    users.getByText(
      "All users total: Unavailable: this activity is not recorded.",
    ),
  ).toBeVisible();
  await expect(
    users.getByText("Showing 1 to 10 of 23 users", { exact: true }),
  ).toBeVisible();
  await expect(usersTable(page).getByRole("row")).toHaveCount(11); // header + 10
  // next page: 1 request
  const n0 = mock.count();
  await users.getByRole("button", { name: "Next page", exact: true }).click();
  await expect.poll(() => mock.count()).toBe(n0 + 1);
  expect(mock.of("users").at(-1)!.url.searchParams.get("offset")).toBe("10");
  await expect(
    users.getByText("Showing 11 to 20 of 23 users", { exact: true }),
  ).toBeVisible();
  // sort: 1 request
  await users
    .getByRole("button", { name: "Sort by Name", exact: true })
    .click();
  await expect.poll(() => mock.count()).toBe(n0 + 2);
  expect(mock.of("users").at(-1)!.url.searchParams.get("sort")).toBe("name");
  // teachers tab: 1 request, no table
  await tab(users, "Teachers").click();
  await expect.poll(() => mock.count()).toBe(n0 + 3);
  expect(mock.of("users").at(-1)!.url.searchParams.get("role")).toBe("teacher");
  await expect(
    users.getByText("Unavailable: this activity is not recorded.").first(),
  ).toBeVisible();
  await expect(usersTable(page)).toHaveCount(0);
});

test("adm07 AC25 students with no requests show the empty text and zero totals", async ({
  page,
}) => {
  await ready(page, (m) => {
    m.usersTotal = 0;
    m.tweak.users = (b) => {
      b.totals = { successful: 0, unsuccessful: 0 };
    };
  });
  const users = region(page, "Feature outcomes");
  await expect(
    users.getByText("No chatbot requests in this period."),
  ).toBeVisible();
  await expect(
    users.getByText("Students total: 0 successful, 0 unsuccessful"),
  ).toBeVisible();
});

test("adm07 AC25 a failed page change keeps the table and shows the message above it", async ({
  page,
}) => {
  const mock = await ready(page);
  const users = region(page, "Feature outcomes");
  mock.next("users", { status: 500 });
  await users.getByRole("button", { name: "Next page", exact: true }).click();
  await expect(alertWith(users, MSG.http("Chatbot users", 500))).toBeVisible();
  await expect(usersTable(page)).toBeVisible();
  await expect(
    users.getByText("Showing 1 to 10 of 23 users", { exact: true }),
  ).toBeVisible();
});

// ================================================================== carried blocks (AC27, AC28)

test("adm07 AC27 generation table keeps its strings and the phase 2 note", async ({
  page,
}) => {
  await ready(page);
  const table = page.getByRole("table", {
    name: "Generation success rates",
    exact: true,
  });
  for (const col of [
    "Workflow",
    "Requests",
    "Successful",
    "Unsuccessful",
    "Success rate",
  ])
    await expect(
      table.getByRole("columnheader", { name: col, exact: true }),
    ).toBeVisible();
  await expect(table.getByRole("row", { name: /Study notes/ })).toContainText(
    "66.7%",
  );
  await expect(table.getByRole("row", { name: /MCQ batches/ })).toContainText(
    "No rate can be calculated: no generation requests in this period.",
  );
  await expect(
    region(page, "Feature outcomes").getByText(
      "Rate-limited requests are not recorded yet.",
    ),
  ).toBeVisible();
});

test("adm07 AC27 AI usage section: feature combobox, table, caption, note, one request per change", async ({
  page,
}) => {
  const mock = await ready(page);
  const ai = region(page, "AI usage");
  const table = ai.getByRole("table", {
    name: "AI usage by feature",
    exact: true,
  });
  for (const col of [
    "Feature",
    "Requests",
    "Failures",
    "Rate-limit failures",
    "Other failures",
    "Input tokens",
    "Output tokens",
    "Total tokens",
  ])
    await expect(
      table.getByRole("columnheader", { name: col, exact: true }),
    ).toBeVisible();
  await expect(
    ai.getByText(
      "Service limits: Unavailable. The SoC LLM service does not report quotas or remaining limits.",
    ),
  ).toBeVisible();
  await expect(
    ai.getByText(
      /Service-call attempts, including retries\. Dates are UTC\. Local quota rejections are excluded\./,
    ),
  ).toBeVisible();
  await expect(
    ai.getByRole("region", { name: "AI usage results" }),
  ).toBeAttached();
  const n0 = mock.count();
  await ai
    .getByRole("combobox", { name: "Feature", exact: true })
    .selectOption({ label: "Teacher generation" });
  await expect.poll(() => mock.count()).toBe(n0 + 1);
  expect(mock.of("aiusage").at(-1)!.url.searchParams.get("feature")).toBe(
    "TEA-02",
  );
});

test("adm07 AC27 quality section: notice, tabs, tables and the workflow tab replaces the URL", async ({
  page,
}) => {
  const mock = await ready(page);
  const q = region(page, "Quality");
  await expect(
    q.getByText(
      "Grades are AI assessments, not verified facts. They do not change access or application content.",
      { exact: true },
    ),
  ).toBeVisible();
  await expect(
    q.getByRole("tablist", { name: "Assessment workflow" }),
  ).toBeVisible();
  await expect(
    q.getByRole("table", { name: "Assessed responses", exact: true }),
  ).toBeVisible();
  const n0 = mock.count();
  const history = await page.evaluate(() => window.history.length);
  await tab(q, "Teacher lesson planning").click();
  await expect(page).toHaveURL(/workflow=teacher_lesson_planning/);
  await expect.poll(() => mock.count()).toBe(n0 + 1);
  expect(mock.count("quality")).toBe(2);
  expect(await page.evaluate(() => window.history.length)).toBe(history); // replace, not push
});

test("adm07 AC28 grading flow: confirm, 202, progress, completion and one quality reload", async ({
  page,
}) => {
  const mock = await ready(page, (m) => {
    m.runStates = [
      { status: "running", items_graded: 1 },
      { status: "completed", items_graded: 3 },
    ];
  });
  const q = region(page, "Quality");
  await q
    .getByRole("button", { name: "Grade ungraded responses", exact: true })
    .click();
  const dialog = page.getByRole("dialog", {
    name: "Grade responses with AI?",
    exact: true,
  });
  await expect(
    dialog.getByText(
      "Up to 20 ungraded responses from this workflow and period will be sent to the SoC LLM service for grading. Grades are advisory.",
    ),
  ).toBeVisible();
  await dialog
    .getByRole("button", { name: "Start grading", exact: true })
    .click();
  expect(mock.count("start")).toBe(1);
  await expect(
    page.getByRole("status").filter({ hasText: "Grading is running:" }),
  ).toBeVisible();
  await expect(
    page.getByRole("status").filter({
      hasText: /Grading finished: 3 graded, 0 could not be graded\./,
    }),
  ).toBeVisible({ timeout: 15_000 });
});

test("adm07 AC28 grading 409 shows the exact conflict message", async ({
  page,
}) => {
  const mock = await ready(page);
  mock.next("start", { status: 409 });
  const q = region(page, "Quality");
  await q
    .getByRole("button", { name: "Grade ungraded responses", exact: true })
    .click();
  await page
    .getByRole("dialog", { name: "Grade responses with AI?" })
    .getByRole("button", { name: "Start grading" })
    .click();
  await expect(
    page.getByText("A grading run is already in progress.").first(),
  ).toBeVisible();
});

test("adm07 AC28 strict privacy mode disables grading and sends no POST", async ({
  page,
}) => {
  const mock = await ready(page, (m) => {
    m.tweak.quality = (b) => {
      b.grades.privacy_mode = "strict";
      b.grades.privacy_blocked_count = 7;
    };
  });
  const q = region(page, "Quality");
  await expect(
    q.getByRole("button", { name: "Grade ungraded responses", exact: true }),
  ).toBeDisabled();
  await expect(
    q.getByText(
      "AI grading is disabled until free-text privacy protection is approved. Counts and timings remain available.",
    ),
  ).toBeVisible();
  await expect(
    q.getByText("7 responses excluded by privacy protection."),
  ).toBeVisible();
  expect(mock.count("start")).toBe(0);
});

// ================================================================== period, URL, history (AC30)

test("adm07 AC30 preset change pushes history, reloads seven blocks and updates the URL", async ({
  page,
}) => {
  const mock = await ready(page);
  await periodSelect(page).selectOption({ label: "Last 30 days" });
  await expect.poll(() => mock.count()).toBe(14);
  await expect(page).toHaveURL(/range=30d/);
  expect(mock.of("health").at(-1)!.url.searchParams.get("period_start")).toBe(
    isoDay(29),
  );
  await periodSelect(page).selectOption({ label: "Today (UTC)" });
  await expect.poll(() => mock.count()).toBe(21);
  const q = mock.of("health").at(-1)!.url.searchParams;
  expect([q.get("period_start"), q.get("period_end")]).toEqual([
    isoDay(0),
    isoDay(0),
  ]);
  await page.goBack();
  await expect(page).toHaveURL(/range=30d/);
  await expect(periodSelect(page)).toContainText("Last 30 days");
  await expect.poll(() => mock.count()).toBe(28);
  await page.goForward();
  await expect(page).toHaveURL(/range=today/);
  await expect.poll(() => mock.count()).toBe(35);
});

test("adm07 AC30 selecting the already selected period sends nothing", async ({
  page,
}) => {
  const mock = await ready(page);
  await periodSelect(page).selectOption({ label: "Last 7 days" });
  await page.waitForTimeout(300);
  expect(mock.count()).toBe(7);
});

test("adm07 AC30 custom range: valid apply pushes, shows the range and reloads once", async ({
  page,
}) => {
  const mock = await ready(page);
  await applyRange(page, "2026-11-01", "2026-11-09");
  await expect(rangeDialog(page)).toHaveCount(0);
  await expect.poll(() => mock.count()).toBe(14);
  await expect(page).toHaveURL(/from=2026-11-01&to=2026-11-09/);
  await expect(periodSelect(page)).toContainText("2026-11-01 to 2026-11-09");
  await page.goBack();
  await expect(page).not.toHaveURL(/from=/);
  // applying an unchanged range sends nothing
  await page.goForward();
  await expect.poll(() => mock.count()).toBeGreaterThanOrEqual(21);
  const n = mock.count();
  await applyRange(page, "2026-11-01", "2026-11-09");
  await page.waitForTimeout(300);
  expect(mock.count()).toBe(n);
});

const INVALID = [
  ["", "2026-11-09", "From date", MSG.dates.format],
  ["2026-1-5", "2026-11-09", "From date", MSG.dates.format],
  ["2026-11-09", "", "To date", MSG.dates.format],
  ["2026-11-09", "2026-11-01", "From date", MSG.dates.order],
  ["2024-01-01", "2026-11-09", "To date", MSG.dates.long],
  ["2026-11-01", isoDay(-3), "To date", MSG.dates.future],
] as const;

for (const [from, to, field, message] of INVALID) {
  test(`adm07 AC30 custom range ${from || "empty"}..${to || "empty"} shows the exact message and sends nothing`, async ({
    page,
  }) => {
    const mock = await ready(page);
    await openCustom(page);
    const dialog = rangeDialog(page);
    await dialog.getByLabel("From date", { exact: true }).fill(from);
    await dialog.getByLabel("To date", { exact: true }).fill(to);
    await dialog
      .getByRole("button", { name: "Apply period", exact: true })
      .click();
    await expect(
      dialog.getByText(message, { exact: true }).first(),
    ).toBeVisible();
    const input = dialog.getByLabel(field, { exact: true });
    await expect(input).toHaveAttribute("aria-invalid", "true");
    await expect(input).toHaveAttribute("aria-describedby", /.+/);
    await expect(dialog.getByLabel("From date", { exact: true })).toHaveValue(
      from,
    ); // typed values stay
    await expect(dialog.getByLabel("To date", { exact: true })).toHaveValue(to);
    if (field === "From date" || !from)
      await expect(
        dialog.getByLabel("From date", { exact: true }),
      ).toBeFocused();
    else await expect(input).toBeFocused();
    expect(mock.count()).toBe(7);
    await page.keyboard.press("Escape"); // Esc closes and restores the previous selection
    await expect(dialog).toHaveCount(0);
    await expect(periodSelect(page)).toContainText("Last 7 days");
    expect(mock.count()).toBe(7);
  });
}

test("adm07 AC30 Cancel closes the custom dialog and restores the previous selection", async ({
  page,
}) => {
  const mock = await ready(page);
  await openCustom(page);
  await rangeDialog(page)
    .getByRole("button", { name: "Cancel", exact: true })
    .click();
  await expect(rangeDialog(page)).toHaveCount(0);
  await expect(periodSelect(page)).toContainText("Last 7 days");
  expect(mock.count()).toBe(7);
});

test("adm07 AC30 URL state: invalid values fall back to the default, valid range wins over bad pair", async ({
  page,
}) => {
  const mock = await ready(page, undefined, `${HUB}?range=bogus&from=x&to=y`);
  expect(mock.of("health")[0].url.searchParams.get("period_start")).toBe(
    isoDay(6),
  );
  await expect(periodSelect(page)).toContainText("Last 7 days");
});

test("adm07 AC30 browser refresh restores the period and workflow from the URL", async ({
  page,
}) => {
  const mock = await ready(
    page,
    undefined,
    `${HUB}?from=2026-10-01&to=2026-10-20&workflow=teacher_lesson_planning`,
  );
  await page.reload();
  await expect(usersTable(page)).toBeVisible();
  expect(mock.count()).toBe(14);
  const last = mock.of("quality").at(-1)!.url.searchParams;
  expect([last.get("workflow"), last.get("period_start")]).toEqual([
    "teacher_lesson_planning",
    "2026-10-01",
  ]);
  await expect(
    tab(region(page, "Quality"), "Teacher lesson planning"),
  ).toHaveAttribute("aria-selected", "true");
});

test("adm07 AC30 Refresh reloads seven blocks, updates Last updated and is disabled while pending", async ({
  page,
}) => {
  const mock = await ready(page);
  const stamp = await page.getByText(/^Last updated /).innerText();
  expect(stamp).not.toContain("Not updated yet");
  mock.next("health", { hold: true });
  await refresh(page).click();
  await expect(refresh(page)).toBeDisabled();
  mock.release();
  await expect(refresh(page)).toBeEnabled();
  expect(mock.count()).toBe(14);
});

test("adm07 AC30 Last updated mentions partial failure and failed blocks keep a message", async ({
  page,
}) => {
  const mock = await setup(page);
  mock.next("daily", { status: 500 });
  await page.goto(HUB);
  await expect(
    page.getByText(/Last updated .*\. Some sections could not be loaded\./),
  ).toBeVisible();
});

test("adm07 AC30 a block that fails on Refresh shows its failure message", async ({
  page,
}) => {
  const mock = await ready(page);
  mock.next("health", { status: 500 });
  await refresh(page).click();
  await expect(
    alertWith(region(page, "Health"), MSG.http("Health", 500)),
  ).toBeVisible();
});

// ================================================================== failures (AC29)

for (const [kind, subject, ,] of BLOCKS) {
  if (kind === "aiusage") continue;
  test(`adm07 AC29 ${kind}: server error shows the exact message and Retry sends exactly one request`, async ({
    page,
  }) => {
    const mock = await setup(page);
    mock.next(kind, { status: 503 });
    await page.goto(HUB);
    await expect(
      page.getByRole("alert").filter({ hasText: MSG.http(subject, 503) }),
    ).toBeVisible();
    const n = mock.count();
    await page.getByRole("button", { name: RETRY[kind], exact: true }).click();
    await expect.poll(() => mock.count()).toBe(n + 1);
    expect(mock.count(kind)).toBe(2);
    await expect(
      page.getByRole("alert").filter({ hasText: "could not be loaded" }),
    ).toHaveCount(0);
    await expect(h1(page)).toBeVisible(); // other blocks and header unaffected
  });
}

const AI_FAILURES = [
  [403, "You do not have access to AI usage."],
  [429, "Too many report requests. Try again shortly."],
  [503, "AI usage data is temporarily unavailable. Try again."],
  [500, MSG.http("AI usage", 500)],
] as const;

for (const [status, text] of AI_FAILURES) {
  test(`adm07 AC29 AI usage ${status} shows its own copy and the others stay`, async ({
    page,
  }) => {
    const mock = await setup(page);
    mock.next("aiusage", { status });
    await page.goto(HUB);
    await expect(alertWith(region(page, "AI usage"), text)).toBeVisible();
    await expect(usersTable(page)).toBeVisible();
  });
}

test("adm07 AC29 AI usage malformed body has its own copy", async ({
  page,
}) => {
  const mock = await setup(page);
  mock.next("aiusage", { malformed: true });
  await page.goto(HUB);
  await expect(
    alertWith(
      region(page, "AI usage"),
      "The server returned an invalid AI usage report. Try again.",
    ),
  ).toBeVisible();
});

test("adm07 AC29 403 on a block uses the access message", async ({ page }) => {
  const mock = await setup(page);
  mock.next("hourly", { status: 403 });
  await page.goto(HUB);
  await expect(alertWith(region(page, "Health"), MSG.forbidden)).toBeVisible();
});

test("adm07 AC29 backend down: every block shows the network message with its own Retry; header stays", async ({
  page,
}) => {
  const mock = await setup(page);
  for (const [kind] of BLOCKS) mock.next(kind, { abort: true });
  await page.goto(HUB);
  for (const [kind] of BLOCKS)
    await expect(
      page.getByRole("button", { name: RETRY[kind], exact: true }),
    ).toBeVisible();
  expect(
    await page.getByRole("alert").filter({ hasText: MSG.network }).count(),
  ).toBeGreaterThanOrEqual(7);
  await expect(h1(page)).toBeVisible();
  await expect(periodSelect(page)).toBeEnabled();
  await expect(refresh(page)).toBeEnabled();
  await expect(page.getByText("Something went wrong")).toHaveCount(0);
  // recovery with Refresh
  await refresh(page).click();
  await expect(usersTable(page)).toBeVisible();
});

test("adm07 AC29 a 15 second wait ends in the exact timeout message, no automatic retry", async ({
  page,
}) => {
  const mock = await ready(page);
  const now = new Date();
  await page.clock.install({ time: now });
  await page.clock.pauseAt(new Date(now.getTime() + 1000));
  mock.next("health", { hold: true });
  await periodSelect(page).selectOption({ label: "Last 30 days" });
  await expect.poll(() => mock.count("health")).toBe(2);
  await expect(
    page.getByRole("status").filter({ hasText: "Loading health..." }),
  ).toBeVisible();
  await page.clock.fastForward(14_900);
  await expect(alertWith(region(page, "Health"), MSG.timeout)).toHaveCount(0);
  await page.clock.fastForward(200);
  await expect(alertWith(region(page, "Health"), MSG.timeout)).toBeVisible();
  expect(mock.count("health")).toBe(2);
  mock.release();
});

// ================================================================== roles and session (AC31)

for (const [label, user, home] of [
  ["student", STUDENT, /\/student\/overview$/],
  ["teacher", TEACHER, /\/teacher\/overview$/],
] as const) {
  test(`adm07 AC31 a ${label} is redirected with replace and sends no analytics request`, async ({
    page,
  }) => {
    const mock = await setup(page, { user });
    await page.goto(HUB);
    await expect(page).toHaveURL(home);
    await page.goBack();
    await expect(page).not.toHaveURL(/\/admin\/analytics/);
    expect(mock.count()).toBe(0);
  });
}

test("adm07 AC31 an anonymous visitor goes to sign-in (replace) with no analytics request", async ({
  page,
}) => {
  const mock = await setup(page, { user: null });
  await page.goto(HUB);
  await expect(page).toHaveURL(/\/login$/);
  await page.goBack();
  await expect(page).not.toHaveURL(/\/admin\/analytics/);
  expect(mock.count()).toBe(0);
});

test("adm07 AC31 a 401 mid-session ends at sign-in and leaves no analytics data on screen", async ({
  page,
}) => {
  const mock = await ready(page);
  mock.auth.expire();
  mock.next("health", { status: 401 });
  await refresh(page).click();
  await expect(page).toHaveURL(/\/login$/);
  await expect(page.getByText("Students total")).toHaveCount(0);
  const storage = await page.evaluate(() =>
    JSON.stringify([{ ...localStorage }, { ...sessionStorage }]),
  );
  expect(storage).not.toMatch(/Alice Tan|chatbot_failure|Critical/);
});

test("adm07 AC31 no analytics data is kept in browser storage", async ({
  page,
}) => {
  await ready(page);
  const storage = await page.evaluate(() =>
    JSON.stringify([{ ...localStorage }, { ...sessionStorage }]),
  );
  expect(storage).not.toMatch(/Alice Tan|u-0000|median_ms|buckets/);
});

// ================================================================== keyboard, mobile, themes (AC32)

test("adm07 AC32 keyboard only: period, Refresh, Expand, modal, sort and tabs", async ({
  page,
}) => {
  const mock = await ready(page);
  await periodSelect(page).focus();
  await page.keyboard.press("ArrowDown");
  await page.keyboard.press("ArrowDown"); // Last 30 days
  await expect.poll(() => mock.count()).toBeGreaterThanOrEqual(14);
  await refresh(page).focus();
  await page.keyboard.press("Enter");
  await expand(page, "Requests per hour").focus();
  await page.keyboard.press("Enter");
  await expect(modal(page, "Requests per hour")).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(expand(page, "Requests per hour")).toBeFocused();
  await expand(page, "Failure rate per hour").focus();
  await page.keyboard.press(" ");
  await expect(modal(page, "Failure rate per hour")).toBeVisible();
  await page.keyboard.press("Escape");
  const sort = page.getByRole("button", {
    name: "Sort by Successful",
    exact: true,
  });
  await sort.focus();
  await page.keyboard.press("Enter");
  await expect
    .poll(() => mock.of("users").at(-1)!.url.searchParams.get("sort"))
    .toBe("successful");
  const t = tab(region(page, "Quality"), "Teacher lesson planning");
  await t.focus();
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/workflow=teacher_lesson_planning/);
});

for (const theme of ["light", "dark"] as const) {
  for (const width of [320, 390]) {
    test(`adm07 AC32 ${theme} ${width}px: no horizontal page scroll; success, unavailable and failure states`, async ({
      page,
    }) => {
      await page.setViewportSize({ width, height: 900 });
      await page.emulateMedia({ colorScheme: theme, reducedMotion: "reduce" });
      const mock = await setup(page);
      mock.next("quality", { status: 500 });
      mock.tweak.users = (b) => {
        b.rows[0].name =
          "A very long display name that has to wrap instead of widening the page";
      };
      await page.goto(ONE_DAY);
      await expect(usersTable(page)).toBeVisible();
      await expect(page.getByRole("alert").first()).toBeVisible();
      const fits = () =>
        page.evaluate(
          () => document.documentElement.scrollWidth <= window.innerWidth,
        );
      expect(await fits()).toBe(true);
      await expand(page, "Peak hours").click();
      const box = await modal(page, "Peak hours").boundingBox();
      expect(box!.x).toBeGreaterThanOrEqual(0);
      expect(box!.x + box!.width).toBeLessThanOrEqual(width + 1);
      expect(await fits()).toBe(true);
      await page.screenshot({
        path: `node_modules/.cache/adm07-hub-${theme}-${width}.png`,
        fullPage: true,
      });
    });
  }
}

test("adm07 AC32 wide tables scroll inside a focusable container, never the page", async ({
  page,
}) => {
  await page.setViewportSize({ width: 320, height: 900 });
  await ready(page);
  const ok = await usersTable(page).evaluate((table) => {
    for (
      let p = table.parentElement;
      p && p !== document.body;
      p = p.parentElement
    ) {
      const o = getComputedStyle(p).overflowX;
      if (
        (o === "auto" || o === "scroll") &&
        p.getAttribute("tabindex") === "0"
      )
        return true;
    }
    return table.scrollWidth <= window.innerWidth;
  });
  expect(ok).toBe(true);
});

test("adm07 no private text: only display names and ids from the users endpoint render, no email", async ({
  page,
}) => {
  await ready(page);
  const body = await page.locator("body").innerText();
  expect(body).not.toMatch(/@example\.com/);
  expect(body).toContain("Alice Tan");
});

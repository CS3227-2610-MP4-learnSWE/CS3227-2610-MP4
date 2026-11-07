import { test, expect, type Page, type Route } from "@playwright/test";
import {
  ADMIN,
  STUDENT,
  TEACHER,
  mockAuthApi,
  logOutWithConfirmation,
  signInThroughForm,
  expectNoSecretsInBrowser,
} from "./authApi";

const PATH = "/admin/ai-usage";
const API = "/api/admin/ai-usage";
const METRICS = [
  "requests",
  "failures",
  "rate_limit_failures",
  "other_failures",
  "input_tokens",
  "output_tokens",
  "total_tokens",
] as const;
type Metric = { value: number | null; reason: string | null };
type UsageRow = {
  feature: string;
  coverage_start: string | null;
} & Record<(typeof METRICS)[number], Metric>;
const LABELS: Record<string, string> = {
  "STU-03": "Student assistant (STU-03)",
  "TEA-02": "Teacher generation (TEA-02)",
  "ADM-03": "Feedback analysis (ADM-03)",
};
const MSG = {
  invalid:
    "Choose a valid feature and a UTC date range of at most 31 days ending today or earlier.",
  forbidden: "You do not have access to AI usage.",
  limited: "Too many report requests. Try again shortly.",
  unavailable: "AI usage data is temporarily unavailable. Try again.",
  network: "Could not reach the server. Check your connection and retry.",
  timeout: "AI usage request timed out. Try again.",
  malformed: "The server returned an invalid AI usage report. Try again.",
};

function metric(value: number | null, reason: string | null = null): Metric {
  return { value, reason };
}

function sampleRow(feature: string): UsageRow {
  const row = {
    feature,
    coverage_start: "2020-01-01T00:00:00Z",
    requests: metric(731),
    failures: metric(3),
    rate_limit_failures: metric(1),
    other_failures: metric(2),
    input_tokens: metric(12),
    output_tokens: metric(7),
    total_tokens: metric(99),
  };
  if (feature === "ADM-03") {
    for (const key of METRICS) row[key] = metric(null, "not_enabled");
    return { ...row, coverage_start: null };
  }
  return row;
}

function report(url: URL, transform?: (rows: UsageRow[]) => void) {
  const feature = url.searchParams.get("feature") ?? "all";
  const rows = (feature === "all" ? Object.keys(LABELS) : [feature]).map(
    sampleRow,
  );
  transform?.(rows);
  return {
    feature,
    start_date: url.searchParams.get("start_date"),
    end_date: url.searchParams.get("end_date"),
    timezone: "UTC",
    as_of: new Date().toISOString(),
    rows,
  };
}

type Step = {
  status?: number;
  code?: string;
  abort?: boolean;
  hold?: boolean;
  malformed?: boolean;
  json?: unknown;
  transform?: (rows: UsageRow[]) => void;
};

async function setup(page: Page, first?: Step, user = ADMIN) {
  const auth = await mockAuthApi(page, { user });
  const requests: URL[] = [];
  const steps: Step[] = first ? [first] : [];
  const releases: (() => void)[] = [];
  const completed: URL[] = [];
  await page.route("**/api/health", (route) =>
    route.fulfill({ json: { status: "ok" } }),
  );
  // All unrelated API calls stay isolated from any developer backend.
  await page.route("**/api/admin/**", (route) =>
    route.fulfill({ json: { accounts: [], courses: [] } }),
  );
  await page.route(
    (url) => url.pathname === API,
    async (route: Route) => {
      const url = new URL(route.request().url());
      requests.push(url);
      const step = steps.shift() ?? {};
      if (step.hold)
        await new Promise<void>((resolve) => releases.push(resolve));
      if (step.abort) {
        await route.abort("connectionrefused").catch(() => undefined);
        return;
      }
      if (step.malformed) {
        await route
          .fulfill({ contentType: "application/json", body: "not-json" })
          .catch(() => undefined);
        return;
      }
      await route
        .fulfill({
          status: step.status ?? 200,
          json:
            step.json ??
            (step.status
              ? {
                  detail: {
                    code: step.code,
                    message: "ignored private server error",
                  },
                }
              : report(url, step.transform)),
          headers: { "cache-control": "private, no-store", vary: "Cookie" },
        })
        .catch(() => undefined);
      completed.push(url);
    },
  );
  return {
    auth,
    requests,
    completed,
    steps,
    release: () => releases.splice(0).forEach((resolve) => resolve()),
  };
}

const table = (page: Page) =>
  page.getByRole("table", { name: "AI usage by feature", exact: true });
const feature = (page: Page) =>
  page.getByRole("combobox", { name: "Feature", exact: true });
const apply = (page: Page) =>
  page.getByRole("button", { name: "Apply filters", exact: true });
const retry = (page: Page) =>
  page.getByRole("button", { name: "Retry", exact: true });
const alert = (page: Page, text: string) =>
  page.getByRole("alert").filter({ hasText: text });

async function choose(page: Page, label: string) {
  const control = feature(page);
  if ((await control.evaluate((el) => el.tagName)) === "SELECT") {
    await control.selectOption({ label });
  } else {
    await control.click();
    await page.getByRole("option", { name: label, exact: true }).click();
  }
}

async function ready(page: Page, first?: Step) {
  const ctx = await setup(page, first);
  await page.goto(PATH);
  await expect(table(page)).toBeVisible();
  return ctx;
}

test("adm06 AC2/3/7/13 named controls, metadata, exact columns and recorded values", async ({
  page,
}) => {
  const ctx = await ready(page);
  await expect(
    page.getByRole("heading", { level: 1, name: "AI usage", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("Demo · Sample data", { exact: true }),
  ).toHaveCount(0);
  await expect(
    page.getByRole("link", { name: "AI usage", exact: true }),
  ).toHaveAttribute("href", PATH);
  await expect(feature(page)).toBeVisible();
  for (const label of ["Start date (UTC)", "End date (UTC)"])
    await expect(page.getByLabel(label, { exact: true })).toBeVisible();
  for (const name of [
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
      table(page).getByRole("columnheader", { name, exact: true }),
    ).toBeVisible();
  await expect(table(page)).toContainText(
    "Service-call attempts, including retries. Dates are UTC. Local quota rejections are excluded.",
  );
  const row = table(page)
    .getByRole("row")
    .filter({ hasText: LABELS["STU-03"] });
  await expect(row).toContainText("731");
  await expect(row).toContainText("99");
  await expect(
    page.getByText("Collection started: 2020-01-01T00:00:00Z", { exact: true }),
  ).toHaveCount(2);
  expect(await table(page).innerText()).not.toContain("%");
  expect(ctx.requests).toHaveLength(1);
  const query = ctx.requests[0].searchParams;
  const now = new Date();
  const start = new Date(now);
  start.setUTCDate(start.getUTCDate() - 6);
  expect(query.get("feature")).toBe("all");
  expect(query.get("end_date")).toBe(now.toISOString().slice(0, 10));
  expect(query.get("start_date")).toBe(start.toISOString().slice(0, 10));
  await expect(
    page.getByText(
      `Period: ${query.get("start_date")} to ${query.get("end_date")} (UTC)`,
      { exact: true },
    ),
  ).toBeVisible();
});

test("adm06 AC13 loading makes one StrictMode request and prevents duplicate action", async ({
  page,
}) => {
  const ctx = await setup(page, { hold: true });
  await page.goto(PATH);
  await expect(
    page.getByRole("status").filter({ hasText: "Loading AI usage…" }),
  ).toBeVisible();
  await expect(apply(page)).toBeDisabled();
  await expect(table(page)).toHaveCount(0);
  await page.getByLabel("Start date (UTC)", { exact: true }).fill("2026-01-01");
  expect(ctx.requests).toHaveLength(1);
  ctx.release();
  await expect(table(page)).toBeVisible();
  expect(ctx.requests).toHaveLength(1);
});

test("adm06 AC4 complete zero is separate from unavailable tokens", async ({
  page,
}) => {
  const ctx = await ready(page);
  ctx.steps.push({
    transform(rows) {
      for (const row of rows) {
        for (const key of METRICS.slice(0, 4)) row[key] = metric(0);
        for (const key of METRICS.slice(4))
          row[key] = metric(null, "no_measurements");
      }
    },
  });
  await choose(page, LABELS["STU-03"]);
  await apply(page).click();
  await expect(
    page
      .getByRole("status")
      .filter({ hasText: "No AI service calls in this period." }),
  ).toBeVisible();
  await expect(table(page).getByText("0", { exact: true })).toHaveCount(4);
  await expect(
    table(page).getByText("Unavailable", { exact: true }),
  ).toHaveCount(3);
  await expect(table(page)).toContainText(
    "No recorded token measurements in this period.",
  );
});

test("adm06 AC4 unavailable selected feature prevents a global no-activity claim", async ({
  page,
}) => {
  await ready(page, {
    transform(rows) {
      for (const row of rows.filter((r) => r.feature !== "ADM-03")) {
        for (const key of METRICS.slice(0, 4)) row[key] = metric(0);
        for (const key of METRICS.slice(4))
          row[key] = metric(null, "no_measurements");
      }
    },
  });
  await expect(
    page.getByText("No AI service calls in this period.", { exact: true }),
  ).toHaveCount(0);
  await expect(table(page)).toContainText(
    "Collection is not enabled for this feature.",
  );
});

for (const [reason, message] of [
  ["not_enabled", "Collection is not enabled for this feature."],
  ["incomplete_coverage", "Coverage does not include the whole period."],
  ["pending_attempts", "Some service calls have not finished recording."],
  [
    "missing_measurement",
    "The provider did not supply this measurement for every call.",
  ],
]) {
  test(`adm06 AC4/8 unavailable ${reason} has visible reason and no false zero`, async ({
    page,
  }) => {
    await ready(page, {
      transform(rows) {
        for (const r of rows)
          for (const key of METRICS) r[key] = metric(null, reason);
      },
    });
    await expect(table(page)).toContainText(message);
    await expect(
      table(page).getByText("Unavailable", { exact: true }),
    ).toHaveCount(21);
    await expect(
      page.getByText("No AI service calls in this period.", { exact: true }),
    ).toHaveCount(0);
  });
}

test("adm06 AC2/13 apply sends one selected-feature request and keeps URL", async ({
  page,
}) => {
  const ctx = await ready(page);
  const before = page.url();
  await choose(page, LABELS["TEA-02"]);
  await page.getByLabel("Start date (UTC)", { exact: true }).fill("2026-01-01");
  await page.getByLabel("End date (UTC)", { exact: true }).fill("2026-01-31");
  await apply(page).click();
  await expect(table(page).getByRole("row")).toHaveCount(2);
  expect(ctx.requests).toHaveLength(2);
  expect(ctx.requests[1].searchParams.get("feature")).toBe("TEA-02");
  expect(ctx.requests[1].searchParams.get("start_date")).toBe("2026-01-01");
  expect(page.url()).toBe(before);
});

for (const [start, end] of [
  ["2026-01-16", "2026-01-15"],
  ["2026-01-01", "2026-02-01"],
  ["2099-01-01", "2099-01-02"],
  ["", "2026-01-15"],
]) {
  test(`adm06 AC11 local validation ${start}/${end} keeps fields, clears report, sends no GET`, async ({
    page,
  }) => {
    const ctx = await ready(page);
    await page.getByLabel("Start date (UTC)", { exact: true }).fill(start);
    await page.getByLabel("End date (UTC)", { exact: true }).fill(end);
    await apply(page).click();
    await expect(alert(page, MSG.invalid)).toBeVisible();
    await expect(table(page)).toHaveCount(0);
    await expect(
      page.getByLabel("Start date (UTC)", { exact: true }),
    ).toHaveValue(start);
    expect(ctx.requests).toHaveLength(1);
  });
}

for (const [status, code, message] of [
  [403, "forbidden", MSG.forbidden],
  [422, "invalid_ai_usage_filters", MSG.invalid],
  [429, "ai_usage_report_rate_limited", MSG.limited],
  [503, "ai_usage_unavailable", MSG.unavailable],
  [404, "not_found", MSG.malformed],
  [409, "conflict", MSG.malformed],
  [500, "internal", MSG.malformed],
] as const) {
  test(`adm06 AC13 exact HTTP ${status} error never mislabeled network`, async ({
    page,
  }) => {
    const ctx = await setup(page, { status, code });
    await page.goto(PATH);
    await expect(alert(page, message)).toBeVisible();
    await expect(table(page)).toHaveCount(0);
    expect(ctx.requests).toHaveLength(1);
    if (status === 403) await expect(retry(page)).toHaveCount(0);
    else {
      // The approved 422 recovery is valid resubmission via Apply filters.
      if (status === 422) await apply(page).click();
      else await retry(page).click();
      await expect(table(page)).toBeVisible();
      expect(ctx.requests).toHaveLength(2);
    }
  });
}

test("adm06 AC13 retry uses applied filters rather than unsent edits", async ({
  page,
}) => {
  const ctx = await ready(page);
  await choose(page, LABELS["TEA-02"]);
  ctx.steps.push({ status: 503, code: "ai_usage_unavailable" });
  await apply(page).click();
  await expect(alert(page, MSG.unavailable)).toBeVisible();
  await choose(page, LABELS["STU-03"]);
  await retry(page).click();
  await expect(table(page)).toBeVisible();
  expect(ctx.requests).toHaveLength(3);
  expect(ctx.requests[2].searchParams.get("feature")).toBe("TEA-02");
});

for (const bad of ["network", "json", "shape"] as const) {
  test(`adm06 AC13 ${bad} has distinct recoverable failure`, async ({
    page,
  }) => {
    const ctx = await setup(
      page,
      bad === "network"
        ? { abort: true }
        : bad === "json"
          ? { malformed: true }
          : { json: { rows: [] } },
    );
    await page.goto(PATH);
    await expect(
      alert(page, bad === "network" ? MSG.network : MSG.malformed),
    ).toBeVisible();
    expect(ctx.requests).toHaveLength(1);
    await retry(page).click();
    await expect(table(page)).toBeVisible();
    expect(ctx.requests).toHaveLength(2);
  });
}

test("adm06 AC13 timeout is bounded to 15 seconds with no automatic retry", async ({
  page,
}) => {
  // Let lazy routing/Suspense finish before freezing timers. Only the measured
  // held Apply request runs under the paused clock; the initial read has finished.
  const ctx = await ready(page);
  const now = new Date();
  await page.clock.install({ time: now });
  await page.clock.pauseAt(new Date(now.getTime() + 1000));
  ctx.steps.push({ hold: true });
  await apply(page).click();
  await expect.poll(() => ctx.requests.length).toBe(2);
  await expect(apply(page)).toBeDisabled();
  await page.clock.fastForward(14999);
  await expect(alert(page, MSG.timeout)).toHaveCount(0);
  await page.clock.fastForward(2);
  await expect(alert(page, MSG.timeout)).toBeVisible();
  expect(ctx.requests).toHaveLength(2);
  ctx.release();
});

for (const user of [STUDENT, TEACHER]) {
  test(`adm06 AC10 wrong role ${user.role} redirects without report request`, async ({
    page,
  }) => {
    const ctx = await setup(page, undefined, user);
    await page.goto(PATH);
    await expect(page).toHaveURL(new RegExp(`/${user.role}/overview$`));
    expect(ctx.requests).toHaveLength(0);
    await expect(table(page)).toHaveCount(0);
  });
}

test("adm06 AC13 refresh and Back/Forward each reload default filters exactly once", async ({
  page,
}) => {
  const ctx = await ready(page);
  await choose(page, LABELS["TEA-02"]);
  await apply(page).click();
  await expect(table(page).getByRole("row")).toHaveCount(2);
  await page.reload();
  await expect(table(page).getByRole("row")).toHaveCount(4);
  expect(ctx.requests).toHaveLength(3);
  await page.locator('a[href="/admin/overview"]').first().click();
  await expect(table(page)).toHaveCount(0);
  await page.goBack();
  await expect(table(page)).toBeVisible();
  expect(ctx.requests).toHaveLength(4);
  await page.goForward();
  await expect(table(page)).toHaveCount(0);
  await page.goBack();
  await expect(table(page)).toBeVisible();
  expect(ctx.requests).toHaveLength(5);
  expect(ctx.requests.at(-1)!.searchParams.get("feature")).toBe("all");
});

test("adm06 AC10 expired session clears report and uses shared sign-in flow", async ({
  page,
}) => {
  const ctx = await ready(page);
  ctx.auth.expire();
  ctx.steps.push({ status: 401, code: "unauthenticated" });
  await apply(page).click();
  await expect(page).toHaveURL(/\/login/);
  await expect(
    page.getByText("Your session has expired. Sign in again.", { exact: true }),
  ).toBeVisible();
  await expect(table(page)).toHaveCount(0);
  await page.goBack();
  await expect(table(page)).toHaveCount(0);
});

test("adm06 AC13 failed logout preserves session and report, success and Back clear private results", async ({
  page,
}) => {
  const ctx = await ready(page);
  ctx.auth.script("logout", {
    status: 503,
    json: { detail: { code: "service_unavailable" } },
  });
  await logOutWithConfirmation(page);
  await expect(
    page.getByRole("dialog", { name: "Confirm logout", exact: true }),
  ).toBeVisible();
  // The modal correctly removes its background from the accessibility tree.
  await expect(
    page.getByRole("table", {
      name: "AI usage by feature",
      exact: true,
      includeHidden: true,
    }),
  ).toBeVisible();
  await logOutWithConfirmation(page);
  await expect(page).toHaveURL(/\/login/);
  await page.goBack();
  await expect(table(page)).toHaveCount(0);
});

test("adm06 AC13 old pending result cannot flash after account switch", async ({
  page,
}) => {
  const ctx = await setup(page, {
    hold: true,
    transform(rows) {
      for (const row of rows) row.requests = metric(9127);
    },
  });
  await page.goto(PATH);
  await expect(apply(page)).toBeDisabled();
  await logOutWithConfirmation(page);
  const other = {
    ...ADMIN,
    id: "another-admin",
    email: "other-admin@example.com",
  };
  ctx.auth.accounts.set(other.email!, {
    user: other,
    password: "correct horse battery staple 42",
  });
  await signInThroughForm(page, other.email!);
  await page.goto(PATH);
  await expect(table(page)).toBeVisible();
  ctx.release();
  await expect.poll(() => ctx.completed.length).toBe(2);
  await expect(table(page)).toBeVisible();
  await expect(table(page)).not.toContainText("9127");
  await expectNoSecretsInBrowser(page, [
    "731",
    "2020-01-01T00:00:00Z",
    "another-admin",
  ]);
  expect(ctx.requests).toHaveLength(2);
});

for (const badValue of [-1, 9007199254740992, true, "731", null]) {
  test(`adm06 AC8/13 malformed counter ${String(badValue)} is rejected`, async ({
    page,
  }) => {
    const ctx = await ready(page);
    ctx.steps.push({
      transform(rows) {
        rows[0].requests = { value: badValue, reason: null } as Metric;
      },
    });
    await apply(page).click();
    await expect(alert(page, MSG.malformed)).toBeVisible();
    await expect(table(page)).toHaveCount(0);
  });
}

test("adm06 AC13 navigating away drops late result and return gets fresh report", async ({
  page,
}) => {
  const ctx = await setup(page, { hold: true });
  await page.goto(PATH);
  await expect(apply(page)).toBeDisabled();
  await page.locator('a[href="/admin/overview"]').first().click();
  ctx.release();
  await expect(table(page)).toHaveCount(0);
  await page.getByRole("link", { name: "AI usage", exact: true }).click();
  await expect(table(page)).toBeVisible();
  expect(ctx.requests).toHaveLength(2);
});

test("adm06 AC5 browser stores no report and malformed content is not rendered", async ({
  page,
}) => {
  const ctx = await ready(page);
  await expectNoSecretsInBrowser(page, ["731", "2020-01-01T00:00:00Z"]);
  ctx.steps.push({
    json: {
      rows: [
        { feature: "<img src=x onerror=alert(1)>", requests: { value: 3 } },
      ],
    },
  });
  await apply(page).click();
  await expect(alert(page, MSG.malformed)).toBeVisible();
  await expect(page.locator("img[src=x]")).toHaveCount(0);
});

for (const width of [390, 1100]) {
  test(`adm06 AC13 ${width}px controls visible, labelled and keyboard accessible`, async ({
    page,
  }) => {
    await page.setViewportSize({ width, height: 700 });
    await ready(page);
    await expect(
      page.getByRole("region", { name: "AI usage results", exact: true }),
    ).toBeVisible();
    for (const control of [
      feature(page),
      page.getByLabel("Start date (UTC)", { exact: true }),
      page.getByLabel("End date (UTC)", { exact: true }),
      apply(page),
    ]) {
      await expect(control).toBeVisible();
      const rect = await control.boundingBox();
      expect(rect!.x).toBeGreaterThanOrEqual(0);
      expect(rect!.x + rect!.width).toBeLessThanOrEqual(width + 1);
      await control.focus();
      await expect(control).toBeFocused();
    }
    expect(
      await page.evaluate(() => document.documentElement.scrollWidth),
    ).toBeLessThanOrEqual(width);
    const spacing = await page.locator(".ai-usage-panel").evaluate((panel) => {
      const period = panel.querySelector("p")!;
      return (
        period.getBoundingClientRect().left - panel.getBoundingClientRect().left
      );
    });
    expect(spacing).toBeGreaterThanOrEqual(16);
    const reason = table(page).locator(".ai-usage-reason").last();
    expect(
      await reason.evaluate((el) => parseFloat(getComputedStyle(el).fontSize)),
    ).toBeGreaterThanOrEqual(14);
    expect(
      await reason.evaluate((el) => el.scrollWidth <= el.clientWidth),
    ).toBe(true);
    const caption = table(page).locator("caption");
    expect(
      await caption.evaluate((el) => parseFloat(getComputedStyle(el).fontSize)),
    ).toBeGreaterThanOrEqual(16);
    const region = page.getByRole("region", {
      name: "AI usage results",
      exact: true,
    });
    const captionText = await caption.evaluate((el) => {
      const range = document.createRange();
      range.selectNodeContents(el);
      return range.getBoundingClientRect().width;
    });
    expect(captionText).toBeLessThanOrEqual(
      (await region.boundingBox())!.width + 1,
    );
  });
}

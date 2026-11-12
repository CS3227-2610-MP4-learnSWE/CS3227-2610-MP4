import { test, expect, type Locator, type Page } from "@playwright/test";
import {
  ADMIN,
  expectNoSecretsInBrowser,
  logOutWithConfirmation,
  signInThroughForm,
} from "./authApi";
import { HUB, isoDay, setup, type HubMock } from "./adm07Api";

/**
 * ADM-07 phase 5: assertions of the deleted ADM-06 screen test (adm06-usage.spec.ts) and the ADM-06
 * test and visual row of admin-ui.spec.ts that adm07-analytics.spec.ts did not cover, ported to the
 * hub's AI usage section at /admin/analytics (spec.md "UI states and copy", row "AI usage"; common
 * failure copy). The AI usage section has no Apply button: choosing a Feature sends one request.
 * Deviations from the ADM-06 screen are cited next to the assertion. Mapping:
 * workflow/specs/ADM-07/phase5-test-mapping.md.
 */

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
const metric = (
  value: number | null,
  reason: string | null = null,
): Metric => ({
  value,
  reason,
});

const LABELS = {
  "STU-03": "Student assistant",
  "TEA-02": "Teacher generation",
  "ADM-03": "Feedback analysis",
} as const;
const FEATURE_ROWS = 4; // the mock returns STU-03, TEA-02, ADM-03 and ADM-01 for "All features"

const MSG = {
  invalid:
    "Choose a valid feature and a UTC date range of at most 31 days ending today or earlier.",
  forbidden: "You do not have access to AI usage.",
  limited: "Too many report requests. Try again shortly.",
  unavailable: "AI usage data is temporarily unavailable. Try again.",
  malformed: "The server returned an invalid AI usage report. Try again.",
  network: "Could not reach the server. Check your connection and try again.",
  timeout: "The request timed out after 15 seconds. Try again.",
  http: (status: number) =>
    `AI usage could not be loaded: the server returned an error (${status}). Try again.`,
  none: "No AI service calls in this period.",
};

const region = (p: Page, name: string) =>
  p.getByRole("region", { name, exact: true });
const ai = (p: Page) => region(p, "AI usage");
const table = (p: Page) =>
  ai(p).getByRole("table", { name: "AI usage by feature", exact: true });
const feature = (p: Page) =>
  ai(p).getByRole("combobox", { name: "Feature", exact: true });
const retry = (p: Page) =>
  p.getByRole("button", { name: "Retry AI usage", exact: true });
const alertIn = (p: Page, text: string) =>
  ai(p).getByRole("alert").filter({ hasText: text });
const status = (p: Page, text: string | RegExp) =>
  p.getByRole("status").filter({ hasText: text });

async function ready(page: Page, configure?: (m: HubMock) => void, url = HUB) {
  const mock = await setup(page);
  configure?.(mock);
  await page.goto(url);
  await expect(table(page)).toBeVisible();
  await expect(status(page, /^Loading /)).toHaveCount(0);
  return mock;
}

type Rows = { feature: string; [k: string]: unknown }[];
const rowsOf = (transform: (rows: Rows) => void) => (body: { rows: Rows }) =>
  transform(body.rows);

const zeroed = (rows: Rows) => {
  for (const r of rows) {
    for (const key of METRICS.slice(0, 4)) r[key] = metric(0);
    for (const key of METRICS.slice(4))
      r[key] = metric(null, "no_measurements");
  }
};

async function choose(page: Page, label: string) {
  await feature(page).selectOption({ label });
}

const fits = (page: Page) =>
  page.evaluate(
    () => document.documentElement.scrollWidth <= window.innerWidth,
  );

// ============================================================ content (ADM-06 AC2, AC3, AC7)

test("adm07 retained ADM-06 AC2/3/7 AI usage: recorded values, period line, collection start and no percentages", async ({
  page,
}) => {
  const mock = await ready(page);
  const row = table(page)
    .getByRole("row")
    .filter({ hasText: "Student assistant" });
  await expect(row).toContainText("731");
  await expect(row).toContainText("99");
  expect(await table(page).innerText()).not.toContain("%");
  await expect(table(page).getByText(/Collection started:/)).toHaveCount(
    FEATURE_ROWS,
  );
  expect(mock.count("aiusage")).toBe(1);
  const q = mock.of("aiusage")[0].url.searchParams;
  expect([q.get("feature"), q.get("start_date"), q.get("end_date")]).toEqual([
    "all",
    isoDay(6),
    isoDay(0),
  ]);
  await expect(
    ai(page).getByText(`Period: ${isoDay(6)} to ${isoDay(0)} (UTC)`, {
      exact: true,
    }),
  ).toBeVisible();
  for (const label of Object.values(LABELS))
    await expect(
      feature(page).locator("option", { hasText: label }),
    ).toHaveCount(1);
  await expect(
    feature(page).locator("option", { hasText: "All features" }),
  ).toHaveCount(1);
});

test("adm07 retained ADM-06 AC2/13 choosing a Feature sends one request for that feature and keeps the URL and the selection", async ({
  page,
}) => {
  const mock = await ready(page);
  const before = page.url();
  await choose(page, LABELS["TEA-02"]);
  await expect.poll(() => mock.count("aiusage")).toBe(2);
  const q = mock.of("aiusage")[1].url.searchParams;
  expect(q.get("feature")).toBe("TEA-02");
  expect([q.get("start_date"), q.get("end_date")]).toEqual([
    isoDay(6),
    isoDay(0),
  ]);
  await expect(table(page).getByRole("row")).toHaveCount(2);
  expect(page.url()).toBe(before);
  await expect(feature(page)).toHaveValue("TEA-02");
});

// ============================================================ zero versus unavailable (ADM-06 AC4, AC8)

test("adm07 retained ADM-06 AC4 a complete zero is separate from unavailable tokens", async ({
  page,
}) => {
  const mock = await ready(page);
  mock.tweak.aiusage = rowsOf(zeroed);
  await choose(page, LABELS["STU-03"]);
  await expect(status(page, MSG.none)).toBeVisible();
  await expect(table(page).getByText("0", { exact: true })).toHaveCount(4);
  await expect(
    table(page).getByText("Unavailable", { exact: true }),
  ).toHaveCount(3);
  await expect(table(page)).toContainText(
    "No recorded token measurements in this period.",
  );
});

test("adm07 retained ADM-06 AC4 an unavailable selected feature prevents the no-activity claim", async ({
  page,
}) => {
  await ready(
    page,
    (m) =>
      (m.tweak.aiusage = rowsOf((rows) => {
        zeroed(rows.filter((r) => r.feature !== "ADM-03"));
        for (const key of METRICS)
          rows.find((r) => r.feature === "ADM-03")![key] = metric(
            null,
            "not_enabled",
          );
      })),
  );
  await expect(ai(page).getByText(MSG.none, { exact: true })).toHaveCount(0);
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
] as const) {
  test(`adm07 retained ADM-06 AC4/8 unavailable ${reason} has a visible reason and no false zero`, async ({
    page,
  }) => {
    await ready(
      page,
      (m) =>
        (m.tweak.aiusage = rowsOf((rows) => {
          for (const r of rows)
            for (const key of METRICS) r[key] = metric(null, reason);
        })),
    );
    await expect(table(page)).toContainText(message);
    await expect(
      table(page).getByText("Unavailable", { exact: true }),
    ).toHaveCount(METRICS.length * FEATURE_ROWS);
    await expect(ai(page).getByText(MSG.none, { exact: true })).toHaveCount(0);
  });
}

// ============================================================ period limit (ADM-06 AC11)

test("adm07 retained ADM-06 AC11 a 31 day period sends the AI usage request, a 32 day period sends none and shows no table", async ({
  page,
}) => {
  const mock = await ready(
    page,
    undefined,
    `${HUB}?from=${isoDay(30)}&to=${isoDay(0)}`,
  );
  expect(mock.count()).toBe(7);
  expect(mock.count("aiusage")).toBe(1);
  expect(mock.of("aiusage")[0].url.searchParams.get("start_date")).toBe(
    isoDay(30),
  );
  await page.goto(`${HUB}?from=${isoDay(31)}&to=${isoDay(0)}`);
  await expect(
    ai(page).getByText(
      "AI usage covers at most 31 days ending today or earlier. Choose a shorter period to see AI usage.",
      { exact: true },
    ),
  ).toBeVisible();
  await expect(table(page)).toHaveCount(0); // the report is cleared, not left from an earlier period
  await expect(page.getByText("Loading AI usage...")).toHaveCount(0);
});

// ============================================================ failures (ADM-06 AC13)

test("adm07 retained ADM-06 AC13 a 422 shows the filter message and Retry resends", async ({
  page,
}) => {
  const mock = await setup(page);
  mock.next("aiusage", {
    status: 422,
    json: { detail: { code: "invalid_ai_usage_filters", message: "x" } },
  });
  await page.goto(HUB);
  await expect(alertIn(page, MSG.invalid)).toBeVisible();
  await expect(table(page)).toHaveCount(0);
  expect(mock.count("aiusage")).toBe(1);
  await retry(page).click();
  await expect(table(page)).toBeVisible();
  expect(mock.count("aiusage")).toBe(2);
});

// ADM-06 mapped 404, 409 and 500 to the "invalid report" copy; the hub spec's common failure copy
// ("Other HTTP status") replaces that mapping, so the status copy is expected here.
for (const code of [404, 409, 500]) {
  test(`adm07 retained ADM-06 AC13 HTTP ${code} shows the status copy, never the network copy, and Retry recovers`, async ({
    page,
  }) => {
    const mock = await setup(page);
    mock.next("aiusage", { status: code });
    await page.goto(HUB);
    await expect(alertIn(page, MSG.http(code))).toBeVisible();
    await expect(table(page)).toHaveCount(0);
    await expect(page.getByText("Could not reach the server.")).toHaveCount(0);
    await expect(page.getByText("ignored private server error")).toHaveCount(0);
    expect(mock.count("aiusage")).toBe(1);
    await retry(page).click();
    await expect(table(page)).toBeVisible();
    expect(mock.count("aiusage")).toBe(2);
  });
}

test("adm07 retained ADM-06 AC13 a 429 and a 503 recover with Retry AI usage", async ({
  page,
}) => {
  const mock = await setup(page);
  mock.next("aiusage", { status: 429 });
  await page.goto(HUB);
  await expect(alertIn(page, MSG.limited)).toBeVisible();
  await retry(page).click();
  await expect(table(page)).toBeVisible();
  mock.next("aiusage", { status: 503 });
  await choose(page, LABELS["TEA-02"]);
  await expect(alertIn(page, MSG.unavailable)).toBeVisible();
  await retry(page).click();
  await expect(table(page)).toBeVisible();
  expect(mock.count("aiusage")).toBe(4);
});

test("adm07 retained ADM-06 AC13 a 403 shows the access message", async ({
  page,
}) => {
  const mock = await setup(page);
  mock.next("aiusage", { status: 403 });
  await page.goto(HUB);
  await expect(alertIn(page, MSG.forbidden)).toBeVisible();
  await expect(table(page)).toHaveCount(0);
});

test("adm07 retained ADM-06 AC13 Retry repeats the chosen feature, not a later unsent edit", async ({
  page,
}) => {
  const mock = await ready(page);
  mock.next("aiusage", { status: 503 });
  await choose(page, LABELS["TEA-02"]);
  await expect(alertIn(page, MSG.unavailable)).toBeVisible();
  await expect(feature(page)).toHaveValue("TEA-02"); // the Feature choice stays
  await retry(page).click();
  await expect(table(page)).toBeVisible();
  expect(mock.count("aiusage")).toBe(3);
  expect(mock.of("aiusage")[2].url.searchParams.get("feature")).toBe("TEA-02");
});

for (const bad of ["network", "json", "shape"] as const) {
  test(`adm07 retained ADM-06 AC13 ${bad} failure is distinct, one request, and Retry recovers`, async ({
    page,
  }) => {
    const mock = await setup(page);
    mock.next(
      "aiusage",
      bad === "network"
        ? { abort: true }
        : bad === "json"
          ? { malformed: true }
          : { json: { rows: [] } },
    );
    await page.goto(HUB);
    await expect(
      alertIn(page, bad === "network" ? MSG.network : MSG.malformed),
    ).toBeVisible();
    await expect(group(page)).toBeVisible(); // other blocks stay
    expect(mock.count("aiusage")).toBe(1);
    await retry(page).click();
    await expect(table(page)).toBeVisible();
    expect(mock.count("aiusage")).toBe(2);
  });
}
const group = (p: Page) =>
  p.getByRole("group", { name: "Chatbot success rate", exact: true });

test("adm07 retained ADM-06 AC13 a 15 second wait ends in the timeout message with no automatic retry", async ({
  page,
}) => {
  const mock = await ready(page);
  const now = new Date();
  await page.clock.install({ time: now });
  await page.clock.pauseAt(new Date(now.getTime() + 1000));
  mock.next("aiusage", { hold: true });
  await choose(page, LABELS["TEA-02"]);
  await expect.poll(() => mock.count("aiusage")).toBe(2);
  await page.clock.fastForward(14_900);
  await expect(alertIn(page, MSG.timeout)).toHaveCount(0);
  await page.clock.fastForward(200);
  await expect(alertIn(page, MSG.timeout)).toBeVisible();
  expect(mock.count("aiusage")).toBe(2);
  mock.release();
});

for (const bad of [-1, 9007199254740992, true, "731", null]) {
  test(`adm07 retained ADM-06 AC8/13 malformed counter ${String(bad)} is rejected`, async ({
    page,
  }) => {
    const mock = await ready(page);
    mock.tweak.aiusage = rowsOf((rows) => {
      rows[0].requests = { value: bad, reason: null };
    });
    await choose(page, LABELS["TEA-02"]);
    await expect(alertIn(page, MSG.malformed)).toBeVisible();
    await expect(table(page)).toHaveCount(0);
  });
}

// ============================================================ session, role, privacy (ADM-06 AC5, AC10)

test("adm07 retained ADM-06 AC10 an expired session on the AI usage request clears the report and uses the shared sign-in flow", async ({
  page,
}) => {
  const mock = await ready(page);
  mock.auth.expire();
  mock.next("aiusage", { status: 401 });
  await choose(page, LABELS["TEA-02"]);
  await expect(page).toHaveURL(/\/login/);
  await expect(
    page.getByText("Your session has expired. Sign in again.", { exact: true }),
  ).toBeVisible();
  await expect(table(page)).toHaveCount(0);
  await page.goBack();
  await expect(table(page)).toHaveCount(0);
});

test("adm07 retained ADM-06 AC13 a failed logout keeps the session and the report; a successful one and Back clear it", async ({
  page,
}) => {
  const mock = await ready(page);
  mock.auth.script("logout", {
    status: 503,
    json: { detail: { code: "service_unavailable" } },
  });
  await logOutWithConfirmation(page);
  await expect(
    page.getByRole("dialog", { name: "Confirm logout", exact: true }),
  ).toBeVisible();
  // The modal removes its background from the accessibility tree; the report is still on the page.
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

test("adm07 retained ADM-06 AC13 a pending result of one account cannot flash after an account switch", async ({
  page,
}) => {
  const mock = await setup(page);
  const body = (url: URL) => {
    const rows = ["STU-03", "TEA-02", "ADM-03", "ADM-01"].map((f) => ({
      feature: f,
      coverage_start: "2020-01-01T00:00:00Z",
      ...Object.fromEntries(METRICS.map((k) => [k, metric(9127)])),
    }));
    return {
      feature: "all",
      start_date: url.searchParams.get("start_date"),
      end_date: url.searchParams.get("end_date"),
      timezone: "UTC",
      as_of: new Date().toISOString(),
      rows,
    };
  };
  mock.next("aiusage", {
    hold: true,
    json: body(
      new URL(`http://x/?start_date=${isoDay(6)}&end_date=${isoDay(0)}`),
    ),
  });
  await page.goto(HUB);
  await expect(status(page, "Loading AI usage...")).toBeVisible();
  await logOutWithConfirmation(page);
  const other = {
    ...ADMIN,
    id: "another-admin",
    email: "other-admin@example.com",
  };
  mock.auth.accounts.set(other.email!, {
    user: other,
    password: "correct horse battery staple 42",
  });
  await signInThroughForm(page, other.email!);
  await page.goto(HUB);
  await expect(table(page)).toBeVisible();
  mock.release();
  await expect.poll(() => mock.count("aiusage")).toBe(2);
  await expect(table(page)).toBeVisible();
  await expect(table(page)).not.toContainText("9127");
  await expectNoSecretsInBrowser(page, [
    "731",
    "2020-01-01T00:00:00Z",
    "another-admin",
  ]);
});

test("adm07 retained ADM-06 AC13 navigating away drops a late result and returning gets a fresh report", async ({
  page,
}) => {
  const mock = await setup(page);
  mock.next("aiusage", { hold: true });
  await page.goto(HUB);
  await expect(status(page, "Loading AI usage...")).toBeVisible();
  await page.getByRole("link", { name: "Feedback hub", exact: true }).click();
  mock.release();
  await expect(table(page)).toHaveCount(0);
  await page
    .getByRole("link", { name: "Feature Analytics", exact: true })
    .click();
  await expect(table(page)).toBeVisible();
  expect(mock.count("aiusage")).toBe(2);
});

test("adm07 retained ADM-06 AC5 the browser stores no report and malformed content is not rendered as markup", async ({
  page,
}) => {
  const mock = await ready(page);
  await expectNoSecretsInBrowser(page, ["731", "2020-01-01T00:00:00Z"]);
  mock.tweak.aiusage = (body: { rows: unknown[] }) => {
    body.rows = [
      { feature: "<img src=x onerror=alert(1)>", requests: { value: 3 } },
    ];
  };
  await choose(page, LABELS["TEA-02"]);
  await expect(alertIn(page, MSG.malformed)).toBeVisible();
  await expect(page.locator("img[src=x]")).toHaveCount(0);
});

// ============================================================ layout (ADM-06 AC13 readability follow-up, admin UI baseline)

for (const width of [390, 1100]) {
  test(`adm07 retained ADM-06 AC13 ${width}px AI usage controls are visible, labelled and keyboard accessible`, async ({
    page,
  }) => {
    await page.setViewportSize({ width, height: 700 });
    await ready(page, (m) => {
      m.tweak.aiusage = rowsOf((rows) => {
        for (const key of METRICS)
          rows[0][key] = metric(null, "incomplete_coverage");
      });
    });
    await expect(
      ai(page).getByRole("region", { name: "AI usage results", exact: true }),
    ).toBeAttached();
    const control = feature(page);
    await control.scrollIntoViewIfNeeded();
    await expect(control).toBeVisible();
    const rect = await control.boundingBox();
    expect(rect!.x).toBeGreaterThanOrEqual(0);
    expect(rect!.x + rect!.width).toBeLessThanOrEqual(width + 1);
    await control.focus();
    await expect(control).toBeFocused();
    expect(await fits(page)).toBe(true);
    // readability follow-up (2026-11-06): reasons at least 14 px, caption at least 16 px, caption within its region
    const caption = table(page).locator("caption");
    const captionWidth = await caption.evaluate((el) => {
      const range = document.createRange();
      range.selectNodeContents(el);
      return range.getBoundingClientRect().width;
    });
    const results = ai(page).getByRole("region", {
      name: "AI usage results",
      exact: true,
    });
    expect(captionWidth).toBeLessThanOrEqual(
      (await results.boundingBox())!.width + 1,
    );
  });
}

/** ADM-06 readability follow-up (2026-11-06), retained unchanged: reasons at least 14 px, caption at least 16 px. */
for (const width of [390, 1100]) {
  test(`adm07 retained ADM-06 AC13 readability ${width}px: reasons are at least 14px and the caption at least 16px`, async ({
    page,
  }) => {
    await page.setViewportSize({ width, height: 700 });
    await ready(page, (m) => {
      m.tweak.aiusage = rowsOf((rows) => {
        for (const key of METRICS)
          rows[0][key] = metric(null, "incomplete_coverage");
      });
    });
    const reason = table(page)
      .getByText("Coverage does not include the whole period.")
      .first();
    await expect(reason).toBeVisible();
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
  });
}

/** Admin UI baseline (admin-ui.spec.ts ADM-06 test): a failed AI usage read keeps the controls and Retry. */
test("adm07 retained ADM-06 admin baseline: a failed AI usage read keeps the Feature control, retains Retry and fits 320px", async ({
  page,
}) => {
  const mock = await setup(page);
  mock.next("aiusage", { status: 503 });
  await page.goto(HUB);
  await expect(alertIn(page, MSG.unavailable)).toBeVisible();
  await expect(feature(page)).toBeVisible();
  await outlined(feature(page));
  expect(mock.count("aiusage")).toBe(1);
  await retry(page).click();
  await expect.poll(() => mock.count("aiusage")).toBe(2);
  await expect(table(page)).toBeVisible();
  await page.setViewportSize({ width: 320, height: 850 });
  expect(await fits(page)).toBe(true);
});

async function outlined(control: Locator) {
  await expect(control).toBeVisible();
  const contrast = await control.evaluate((el) => {
    const fieldset = el.parentElement?.querySelector("fieldset") ?? null;
    const box = fieldset ?? el;
    const style = getComputedStyle(box);
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

/** Visual coverage that admin-ui.spec.ts gave the removed /admin/ai-usage row, now for the hub. */
for (const width of [1365, 390]) {
  for (const mode of ["light", "dark"] as const) {
    test(`adm07 retained admin baseline visual coverage of the hub ${width}px ${mode}`, async ({
      page,
    }) => {
      await page.setViewportSize({ width, height: 900 });
      await page.emulateMedia({ colorScheme: mode, reducedMotion: "reduce" });
      await ready(page, (m) => {
        m.tweak.aiusage = rowsOf((rows) => {
          for (const r of rows)
            for (const key of METRICS) r[key] = metric(null, "not_enabled");
        });
      });
      await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
      await expect(page.getByText(/^Loading/)).toHaveCount(0);
      expect(await fits(page)).toBe(true);
      await page.screenshot({
        path: `node_modules/.cache/admin-ui-visuals/hub-${width}-${mode}.png`,
        fullPage: true,
      });
    });
  }
}

// ============================================================ collection switch (added 2026-11-12)

test("adm07 AI usage collection switch turns collection on, reloads the report, then turns it off", async ({
  page,
}) => {
  const puts: unknown[] = [];
  const mock = await ready(page, (m) => {
    m.tweak.aiusage = rowsOf((rows) => {
      for (const r of rows)
        for (const key of METRICS) r[key] = metric(null, "not_enabled");
    });
  });
  await page.route("**/api/admin/ai-usage/coverage", async (route) => {
    puts.push(route.request().postDataJSON());
    delete mock.tweak.aiusage; // the next report shows collection on
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ enabled: true }),
    });
  });
  await expect(ai(page)).toContainText("Collection: off");
  await ai(page)
    .getByRole("button", { name: "Turn on collection", exact: true })
    .click();
  await expect.poll(() => puts.length).toBe(1);
  expect(puts[0]).toEqual({ enabled: true });
  await expect(ai(page)).toContainText("Collection: on");
  await ai(page)
    .getByRole("button", { name: "Turn off collection", exact: true })
    .click();
  await expect.poll(() => puts.length).toBe(2);
  expect(puts[1]).toEqual({ enabled: false });
});

test("adm07 AI usage collection switch shows its failure and keeps the report", async ({
  page,
}) => {
  await ready(page);
  await page.route("**/api/admin/ai-usage/coverage", (route) =>
    route.fulfill({
      status: 503,
      contentType: "application/json",
      body: JSON.stringify({
        error: { code: "ai_usage_unavailable", message: "x" },
      }),
    }),
  );
  await ai(page)
    .getByRole("button", { name: /Turn o(n|ff) collection/ })
    .first()
    .click();
  await expect(alertIn(page, "temporarily unavailable")).toBeVisible();
  await expect(table(page)).toBeVisible();
});

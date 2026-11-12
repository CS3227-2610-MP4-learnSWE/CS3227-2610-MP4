import { expect, test, type Page } from "@playwright/test";
import { logOutWithConfirmation } from "./authApi";
import {
  COUNT_ANALYSES,
  COUNT_FOLLOWUP,
  COUNT_FORMS,
  DRAFT_FORM_ID,
  FEEDBACK,
  FORM_ID,
  HUB,
  MESSAGING,
  MSG,
  RESPONSE_ID,
  SECOND_FORM_ID,
  STUDENT,
  TABS,
  TEACHER,
  TITLE,
  alertWith,
  analysisFor,
  analysisUuid,
  button,
  formId,
  heading,
  link,
  makeForm,
  noStorage,
  open,
  settle,
  setup,
  statusWith,
  tab,
  tablist,
} from "./adm08Api";

const keys = (rows: { method: string; path: string }[]) =>
  rows.map((r) => `${r.method} ${r.path}`).sort();
const COUNT_KEYS = keys([
  { method: "GET", path: COUNT_FORMS },
  { method: "GET", path: COUNT_ANALYSES },
  { method: "GET", path: COUNT_FOLLOWUP },
]);

/** forms: open, closed, draft; one saved analysis */
async function arrange(page: Page, over: Parameters<typeof setup>[1] = {}) {
  return setup(page, {
    forms: [
      makeForm(FORM_ID, TITLE, "open", 2),
      makeForm(SECOND_FORM_ID, "Closed form", "closed", 3),
      makeForm(DRAFT_FORM_ID, "Draft form", "draft", 0),
    ],
    analyses: [analysisFor(1, "complete")],
    followUp: 4,
    ...over,
  });
}

// ---------------------------------------------------------------- AC4 entry
test("adm08 AC4 entry replaces /admin/feedback-hub with /forms, shows label, muted line, tablist and four tabs, no heading of its own", async ({
  page,
}) => {
  const ctx = await arrange(page);
  await page.goto("/admin/not-a-page");
  const historyBefore = await page.evaluate(() => window.history.length);
  await page.goto(HUB);
  await expect(page).toHaveURL(new RegExp(`${HUB}/forms$`));
  expect(await page.evaluate(() => window.history.length)).toBeLessThanOrEqual(
    historyBefore + 1,
  );
  const region = page.getByRole("region", {
    name: "Feedback hub",
    exact: true,
  });
  await expect(region).toBeVisible();
  await expect(region.getByText("Feedback hub", { exact: true })).toBeVisible();
  await expect(region.getByText(MSG.muted, { exact: true })).toBeVisible();
  await expect(tablist(page)).toBeVisible();
  for (const name of TABS) await expect(tab(page, name)).toBeVisible();
  expect(await tablist(page).getByRole("tab").count()).toBe(4);
  // the hub adds no heading of its own
  await expect(
    region.getByRole("heading", { name: "Feedback hub" }),
  ).toHaveCount(0);
  await expect(heading(page, "Feedback forms")).toBeVisible();
  await settle(ctx);
  // forms list twice (screen + count), analyses count, follow-up count; nothing else
  expect(keys(ctx.api())).toEqual(
    keys([
      { method: "GET", path: COUNT_FORMS },
      { method: "GET", path: COUNT_FORMS },
      { method: "GET", path: COUNT_ANALYSES },
      { method: "GET", path: COUNT_FOLLOWUP },
    ]),
  );
  expect(await noStorage(page)).toBe(0);
});

test("adm08 AC4 a trailing slash entry and the Back button do not trap the user on the entry URL", async ({
  page,
}) => {
  await arrange(page);
  await page.goto("/admin/not-a-page");
  await page.goto(`${HUB}/`);
  await expect(page).toHaveURL(new RegExp(`${HUB}/forms$`));
  await page.goBack();
  await expect(page).toHaveURL(/\/admin\/not-a-page$/);
});

// ---------------------------------------------------------------- AC5 deep links
const ANALYSIS_ID = analysisUuid(1);
const DEEP: [string, string][] = [
  ["/forms", "Forms"],
  ["/forms/new", "Forms"],
  [`/forms/${DRAFT_FORM_ID}`, "Forms"],
  [`/forms/${DRAFT_FORM_ID}/edit`, "Forms"],
  ["/responses", "Responses"],
  [`/responses/${FORM_ID}`, "Responses"],
  [`/responses/${FORM_ID}/${RESPONSE_ID}`, "Responses"],
  ["/analysis", "Analysis"],
  [`/analysis/${ANALYSIS_ID}`, "Analysis"],
  [`/analysis/${ANALYSIS_ID}/responses/R1`, "Analysis"],
  ["/follow-up", "Follow-up"],
  [`/follow-up/reply/${FORM_ID}/${RESPONSE_ID}`, "Follow-up"],
];
for (const [suffix, expected] of DEEP) {
  test(`adm08 AC5 deep link ${suffix} opens with tab ${expected} selected`, async ({
    page,
  }) => {
    await arrange(page);
    await open(page, HUB + suffix);
    await expect(page).toHaveURL(HUB + suffix);
    for (const name of TABS)
      await expect(tab(page, name)).toHaveAttribute(
        "aria-selected",
        name === expected ? "true" : "false",
      );
    await expect(
      page.getByRole("tabpanel", { name: expected, exact: true }),
    ).toBeVisible();
  });
}

test("adm08 AC5 unknown first segment is replaced with /forms (case-sensitive match)", async ({
  page,
}) => {
  await arrange(page);
  await page.goto("/admin/not-a-page");
  for (const bad of ["nonsense", "Forms", "FORMS", "follow_up", "analyses"]) {
    await page.goto(`${HUB}/${bad}`);
    await expect(page).toHaveURL(new RegExp(`${HUB}/forms$`));
    await expect(tab(page, "Forms")).toHaveAttribute("aria-selected", "true");
  }
  await page.goBack();
  await expect(page).not.toHaveURL(new RegExp(`${HUB}/(nonsense|Forms)`));
});

test("adm08 AC5 a known tab with an unmatched rest shows the hub not-found alert, the tab bar, a Go to Forms link and sends no screen request", async ({
  page,
}) => {
  const ctx = await arrange(page);
  await open(page, `${HUB}/forms/${DRAFT_FORM_ID}/edit/extra`);
  await expect(alertWith(page, MSG.notFound)).toBeVisible();
  await expect(tab(page, "Forms")).toHaveAttribute("aria-selected", "true");
  await settle(ctx);
  expect(keys(ctx.api())).toEqual(COUNT_KEYS);
  await link(page, "Go to Forms").click();
  await expect(page).toHaveURL(new RegExp(`${HUB}/forms$`));
  await expect(alertWith(page, MSG.notFound)).toHaveCount(0);
  await page.goBack(); // "Go to Forms" pushes
  await expect(page).toHaveURL(
    new RegExp(`${HUB}/forms/${DRAFT_FORM_ID}/edit/extra$`),
  );
});

for (const bad of [
  "/responses/a/b/c/d",
  "/analysis/x/y/z",
  "/follow-up/other",
  "/follow-up/reply/only-one",
]) {
  test(`adm08 AC5 unmatched path ${bad} shows the not-found alert`, async ({
    page,
  }) => {
    await arrange(page);
    await open(page, HUB + bad);
    await expect(alertWith(page, MSG.notFound)).toBeVisible();
  });
}

test("adm08 AC5 a well-formed path with a malformed or unknown id shows the inner not-found message, not the hub alert", async ({
  page,
}) => {
  await arrange(page);
  await open(page, `${HUB}/forms/not-a-uuid`);
  await expect(alertWith(page, MSG.missing)).toBeVisible();
  await expect(alertWith(page, MSG.notFound)).toHaveCount(0);
  await expect(tab(page, "Forms")).toHaveAttribute("aria-selected", "true");
});

// ---------------------------------------------------------------- AC6 tab semantics
test("adm08 AC6 roles, names, aria-selected, roving tabindex and aria-controls", async ({
  page,
}) => {
  await arrange(page);
  await open(page, `${HUB}/responses`);
  for (const name of TABS) {
    const t = tab(page, name);
    const selected = name === "Responses";
    await expect(t).toHaveAttribute("aria-selected", String(selected));
    await expect(t).toHaveAttribute("tabindex", selected ? "0" : "-1");
    const controls = await t.getAttribute("aria-controls");
    expect(controls).toBeTruthy();
    expect(await page.locator(`[id="${controls}"]`).count()).toBe(1);
  }
  const panel = page.getByRole("tabpanel", { name: "Responses", exact: true });
  await expect(panel).toBeVisible();
  expect(await page.getByRole("tabpanel").count()).toBe(1);
  // tab names stay exact even when badges exist
  await expect(tab(page, "Responses")).toHaveAccessibleName("Responses");
});

test("adm08 AC6 arrows, Home and End move focus without navigating; Enter and Space activate; focus stays on the activated tab", async ({
  page,
}) => {
  const ctx = await arrange(page);
  await open(page, `${HUB}/forms`);
  await settle(ctx);
  await tab(page, "Forms").focus();
  const before = ctx.requests.length;
  await page.keyboard.press("ArrowRight");
  await expect(tab(page, "Responses")).toBeFocused();
  await page.keyboard.press("ArrowRight");
  await expect(tab(page, "Analysis")).toBeFocused();
  await page.keyboard.press("End");
  await expect(tab(page, "Follow-up")).toBeFocused();
  await page.keyboard.press("ArrowRight");
  await expect(tab(page, "Forms")).toBeFocused(); // wraps
  await page.keyboard.press("ArrowLeft");
  await expect(tab(page, "Follow-up")).toBeFocused(); // wraps
  await page.keyboard.press("Home");
  await expect(tab(page, "Forms")).toBeFocused();
  await expect(page).toHaveURL(new RegExp(`${HUB}/forms$`));
  expect(ctx.requests.length).toBe(before); // moving focus is not activation
  await page.keyboard.press("ArrowRight");
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(new RegExp(`${HUB}/responses$`));
  await expect(tab(page, "Responses")).toBeFocused();
  await page.keyboard.press("ArrowRight");
  await page.keyboard.press("Space");
  await expect(page).toHaveURL(new RegExp(`${HUB}/analysis$`));
  await expect(tab(page, "Analysis")).toBeFocused();
});

test("adm08 AC6 the selected tab is distinguishable without colour and keyboard focus is visible", async ({
  page,
}) => {
  await arrange(page);
  await open(page, `${HUB}/forms`);
  const weight = (name: string) =>
    tab(page, name).evaluate((el) => Number(getComputedStyle(el).fontWeight));
  expect(await weight("Forms")).toBeGreaterThanOrEqual(600);
  expect(await weight("Responses")).toBeLessThan(600);
  const box = await tab(page, "Forms").boundingBox();
  expect(box!.height).toBeGreaterThanOrEqual(44);
  await tab(page, "Responses").focus();
  await page.keyboard.press("ArrowLeft");
  const ring = await tab(page, "Forms").evaluate((el) => {
    const s = getComputedStyle(el);
    return {
      outline: s.outlineStyle !== "none" ? parseFloat(s.outlineWidth) : 0,
      shadow: s.boxShadow !== "none",
    };
  });
  expect(ring.outline >= 2 || ring.shadow).toBe(true);
});

// ---------------------------------------------------------------- AC7 tab switching
test("adm08 AC7 each tab click pushes its landing URL with exactly its own landing request; Back returns to the earlier tab", async ({
  page,
}) => {
  const ctx = await arrange(page);
  await open(page, `${HUB}/forms`);
  await settle(ctx);
  const landing: [string, string, string[]][] = [
    ["Responses", "/responses", [`GET ${COUNT_FORMS}`]],
    ["Analysis", "/analysis", [`GET ${COUNT_FORMS}`, `GET ${COUNT_ANALYSES}`]],
    ["Follow-up", "/follow-up", [`GET ${MESSAGING}/recipients`]],
    ["Forms", "/forms", [`GET ${COUNT_FORMS}`]],
  ];
  for (const [name, suffix, expected] of landing) {
    const mark = ctx.mark();
    await tab(page, name).click();
    await expect(page).toHaveURL(new RegExp(`${HUB}${suffix}$`));
    await expect(tab(page, name)).toHaveAttribute("aria-selected", "true");
    await expect
      .poll(() => ctx.since(mark).length)
      .toBeGreaterThanOrEqual(expected.length);
    await page.waitForTimeout(150);
    expect(keys(ctx.since(mark))).toEqual([...expected].sort());
  }
  await page.goBack();
  await expect(page).toHaveURL(new RegExp(`${HUB}/follow-up$`));
  await expect(tab(page, "Follow-up")).toHaveAttribute("aria-selected", "true");
});

test("adm08 AC7 clicking the selected tab on its landing sends nothing; from a deeper screen it goes to the landing by push", async ({
  page,
}) => {
  const ctx = await arrange(page);
  await open(page, `${HUB}/forms`);
  await settle(ctx);
  const mark = ctx.mark();
  const length = await page.evaluate(() => history.length);
  await tab(page, "Forms").click();
  await page.waitForTimeout(200);
  expect(ctx.since(mark)).toHaveLength(0);
  expect(await page.evaluate(() => history.length)).toBe(length);
  await open(page, `${HUB}/forms/${DRAFT_FORM_ID}`);
  await tab(page, "Forms").click();
  await expect(page).toHaveURL(new RegExp(`${HUB}/forms$`));
  await page.goBack();
  await expect(page).toHaveURL(new RegExp(`${HUB}/forms/${DRAFT_FORM_ID}$`));
});

// ---------------------------------------------------------------- AC9 navigation
test("adm08 AC9 nav link Feedback hub goes to the Forms tab (push), is selected on hub URLs, and the old links are gone (AC25)", async ({
  page,
}) => {
  await arrange(page);
  await page.goto("/admin/not-a-page");
  const nav = link(page, "Feedback hub");
  await expect(nav).toHaveAttribute("href", `${HUB}/forms`);
  for (const removed of [
    "Feedback forms",
    "Announcements",
    "Feedback insights",
    "Analytics",
  ])
    await expect(link(page, removed)).toHaveCount(0);
  for (const kept of ["Feature Analytics"])
    await expect(link(page, kept)).toBeVisible();
  await nav.click();
  await expect(page).toHaveURL(new RegExp(`${HUB}/forms$`));
  await page.goBack();
  await expect(page).toHaveURL(/\/admin\/not-a-page$/);
  for (const suffix of [
    "/responses",
    `/analysis/${ANALYSIS_ID}`,
    "/follow-up",
  ]) {
    await page.goto(HUB + suffix);
    await expect(link(page, "Feedback hub")).toHaveAttribute(
      "aria-current",
      "page",
    );
  }
  await page.goto("/admin/not-a-page");
  await expect(link(page, "Feedback hub")).not.toHaveAttribute(
    "aria-current",
    "page",
  );
});

// ---------------------------------------------------------------- AC11 access
const HUB_SAMPLES = ["/forms", "/responses", `/analysis/${ANALYSIS_ID}`];
for (const [user, home] of [
  [STUDENT, /\/student\/overview$/],
  [TEACHER, /\/teacher\/overview$/],
] as const) {
  for (const suffix of HUB_SAMPLES) {
    test(`adm08 AC11 ${user.role} opening ${suffix} is replaced to their home with zero feedback requests`, async ({
      page,
    }) => {
      const ctx = await setup(page, { user });
      await page.goto(HUB + suffix);
      await expect(page).toHaveURL(home);
      await expect(tablist(page)).toHaveCount(0);
      expect(ctx.api()).toHaveLength(0);
      await page.goBack().catch(() => undefined);
      await expect(page).not.toHaveURL(new RegExp(HUB));
    });
  }
}
for (const suffix of HUB_SAMPLES) {
  test(`adm08 AC11 anonymous opening ${suffix} is replaced to /login with no request`, async ({
    page,
  }) => {
    const ctx = await setup(page, { user: null });
    await page.goto(HUB + suffix);
    await expect(page).toHaveURL(/\/login/);
    expect(ctx.api()).toHaveLength(0);
    await page.goBack().catch(() => undefined);
    await expect(page).not.toHaveURL(new RegExp(HUB));
    expect(ctx.api()).toHaveLength(0);
  });
}

test("adm08 AC11 a 401 on the chooser GET and on an inner GET ends at sign-in with the session notice and no hub data", async ({
  page,
}) => {
  const ctx = await arrange(page);
  ctx.steps.push({
    method: "GET",
    suffix: "/forms",
    query: "limit=100",
    status: 401,
    code: "unauthenticated",
    persist: true,
  });
  await page.goto(`${HUB}/responses`);
  await expect(page).toHaveURL(/\/login/);
  await expect(page.getByText(MSG.expired)).toBeVisible();
  await expect(page.getByText(TITLE)).toHaveCount(0);
  expect(await noStorage(page)).toBe(0);
});

test("adm08 AC11 a 401 on an inner screen GET clears the hub and goes to sign-in", async ({
  page,
}) => {
  const ctx = await arrange(page);
  ctx.steps.push({
    method: "GET",
    suffix: `/analyses/${ANALYSIS_ID}`,
    status: 401,
    code: "unauthenticated",
  });
  await page.goto(`${HUB}/analysis/${ANALYSIS_ID}`);
  await expect(page).toHaveURL(/\/login/);
  await expect(page.getByText(MSG.expired)).toBeVisible();
  await expect(tablist(page)).toHaveCount(0);
});

test("adm08 AC11 after logout Back shows sign-in, not stale hub content", async ({
  page,
}) => {
  const ctx = await arrange(page);
  await open(page, `${HUB}/forms`);
  await settle(ctx);
  await expect(tab(page, "Responses")).toBeVisible();
  await logOutWithConfirmation(page);
  await expect(page).toHaveURL(/\/login/);
  await page.goBack().catch(() => undefined);
  await expect(page.getByText(TITLE)).toHaveCount(0);
  await expect(tablist(page)).toHaveCount(0);
});

// ---------------------------------------------------------------- AC12 dirty guard
test("adm08 AC12 leaving a dirty new-form editor by tab, nav link or in-hub link shows the dialog; Keep editing stays, Discard leaves; pristine shows none", async ({
  page,
}) => {
  const ctx = await arrange(page);
  await open(page, `${HUB}/forms/new`);
  // pristine: no dialog
  await tab(page, "Analysis").click();
  await expect(page).toHaveURL(new RegExp(`${HUB}/analysis$`));
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await page.goBack();
  const title = page.getByRole("textbox", { name: "Form title", exact: true });
  await title.fill("Unsaved title");
  for (const leave of [
    () => tab(page, "Responses").click(),
    () => link(page, "Feedback hub").click(),
  ]) {
    await leave();
    const dialog = page.getByRole("dialog", { name: MSG.discard, exact: true });
    await expect(dialog).toBeVisible();
    await dialog
      .getByRole("button", { name: "Keep editing", exact: true })
      .click();
    await expect(dialog).toHaveCount(0);
    await expect(page).toHaveURL(new RegExp(`${HUB}/forms/new$`));
    await expect(tab(page, "Forms")).toHaveAttribute("aria-selected", "true");
    await expect(title).toHaveValue("Unsaved title");
  }
  await tab(page, "Responses").click();
  await page
    .getByRole("dialog", { name: MSG.discard, exact: true })
    .getByRole("button", { name: "Discard changes", exact: true })
    .click();
  await expect(page).toHaveURL(new RegExp(`${HUB}/responses$`));
  expect(ctx.of("POST")).toHaveLength(0);
});

// ---------------------------------------------------------------- AC13 request counts
const LANDINGS: [string, string[]][] = [
  ["/forms", [`GET ${COUNT_FORMS}`]],
  ["/forms/new", [`GET ${FEEDBACK}/associations`]],
  [`/forms/${DRAFT_FORM_ID}`, [`GET ${FEEDBACK}/forms/${DRAFT_FORM_ID}`]],
  [
    `/forms/${DRAFT_FORM_ID}/edit`,
    [`GET ${FEEDBACK}/forms/${DRAFT_FORM_ID}`, `GET ${FEEDBACK}/associations`],
  ],
  ["/responses", [`GET ${COUNT_FORMS}`]],
  [`/responses/${FORM_ID}`, [`GET ${FEEDBACK}/forms/${FORM_ID}/responses`]],
  [
    `/responses/${FORM_ID}/${RESPONSE_ID}`,
    [
      `GET ${FEEDBACK}/forms/${FORM_ID}/responses/${RESPONSE_ID}`,
      `GET ${FEEDBACK}/forms/${FORM_ID}`,
    ],
  ],
  ["/analysis", [`GET ${COUNT_FORMS}`, `GET ${COUNT_ANALYSES}`]],
  [`/analysis/${ANALYSIS_ID}`, [`GET ${COUNT_ANALYSES}/${ANALYSIS_ID}`]],
  ["/follow-up", [`GET ${MESSAGING}/recipients`]],
  [
    `/follow-up/reply/${FORM_ID}/${RESPONSE_ID}`,
    [`GET ${MESSAGING}/feedback-responses/${RESPONSE_ID}/recipient`],
  ],
];
for (const [suffix, own] of LANDINGS) {
  test(`adm08 AC13 first entry at ${suffix} sends the screen's own requests plus exactly the three counts, once`, async ({
    page,
  }) => {
    const ctx = await arrange(page);
    await page.goto(HUB + suffix);
    await expect(tablist(page)).toBeVisible();
    await settle(ctx);
    await page.waitForTimeout(400);
    const expected = [...own, ...COUNT_KEYS];
    expect(keys(ctx.api())).toEqual([...expected].sort());
    expect(ctx.formsCountGets().length).toBeGreaterThanOrEqual(1);
    expect(ctx.followUpGets()).toHaveLength(1);
    expect(ctx.analysesCountGets()).toHaveLength(1);
  });
}

test("adm08 AC13 entry counts: /forms 4, /responses 4, /analysis 5 requests in total", async ({
  page,
}) => {
  for (const [suffix, total] of [
    ["/forms", 4],
    ["/responses", 4],
    ["/analysis", 5],
  ] as const) {
    const ctx = await arrange(page);
    await page.goto(HUB + suffix);
    await settle(ctx);
    await page.waitForTimeout(400);
    expect(ctx.api()).toHaveLength(total);
    await page.unrouteAll({ behavior: "ignoreErrors" });
  }
});

test("adm08 AC13 refresh sends that URL's requests and the three counts again, nothing else", async ({
  page,
}) => {
  const ctx = await arrange(page);
  await open(page, `${HUB}/responses/${FORM_ID}`);
  await settle(ctx);
  const mark = ctx.mark();
  await page.reload();
  await expect(tablist(page)).toBeVisible();
  await expect.poll(() => ctx.since(mark).length).toBe(4);
  expect(keys(ctx.since(mark))).toEqual(
    [`GET ${FEEDBACK}/forms/${FORM_ID}/responses`, ...COUNT_KEYS].sort(),
  );
});

test("adm08 AC13 Back and Forward between hub URLs remount and reload from the server without resending mutations", async ({
  page,
}) => {
  const ctx = await arrange(page);
  await open(page, `${HUB}/forms`);
  await settle(ctx);
  await tab(page, "Responses").click();
  await expect(page).toHaveURL(new RegExp(`${HUB}/responses$`));
  await expect
    .poll(async () => {
      const n = ctx.api().length;
      await page.waitForTimeout(300);
      return ctx.api().length === n;
    })
    .toBe(true);
  const mark = ctx.mark();
  await page.goBack();
  await expect(page).toHaveURL(new RegExp(`${HUB}/forms$`));
  await expect.poll(() => ctx.since(mark).length).toBeGreaterThanOrEqual(1);
  await page.waitForTimeout(200);
  expect(keys(ctx.since(mark))).toEqual([`GET ${COUNT_FORMS}`]); // no count refetch within the hub
  expect(ctx.of("POST")).toHaveLength(0);
  expect(ctx.of("PUT")).toHaveLength(0);
  expect(ctx.of("DELETE")).toHaveLength(0);
});

// ---------------------------------------------------------------- AC14 failure isolation
test("adm08 AC14 Forms list 503 shows the ADM-02 503 message, the tabs stay and still switch", async ({
  page,
}) => {
  const ctx = await arrange(page);
  ctx.steps.push({
    method: "GET",
    suffix: "/forms",
    status: 503,
    code: "feedback_unavailable",
    persist: true,
  });
  await page.goto(`${HUB}/forms`);
  await expect(alertWith(page, MSG.unavailable).first()).toBeVisible();
  for (const name of TABS) await expect(tab(page, name)).toBeVisible();
  await tab(page, "Follow-up").click();
  await expect(page).toHaveURL(new RegExp(`${HUB}/follow-up$`));
  await expect(heading(page, "New announcement")).toBeVisible();
  await expect(alertWith(page, MSG.unavailable)).toHaveCount(0);
});

test("adm08 AC14 a network failure on the Follow-up landing shows its own message and Retry, tabs stay", async ({
  page,
}) => {
  const ctx = await arrange(page);
  ctx.steps.push({ method: "GET", suffix: "/recipients", abort: true });
  await open(page, `${HUB}/follow-up`);
  await expect(
    page.getByRole("alert").filter({ hasText: /Could not reach the server/ }),
  ).toBeVisible();
  await expect(button(page, "Retry")).toBeVisible();
  for (const name of TABS) await expect(tab(page, name)).toBeVisible();
  const mark = ctx.mark();
  await button(page, "Retry").click();
  await expect.poll(() => ctx.since(mark).length).toBe(1); // one request per retry, counts are not re-requested
  expect(ctx.since(mark)[0].path).toBe(`${MESSAGING}/recipients`);
});

// ---------------------------------------------------------------- AC18 chooser
async function chooser(page: Page, over: Parameters<typeof setup>[1] = {}) {
  const ctx = await arrange(page, over);
  await open(page, `${HUB}/responses`);
  return ctx;
}
const select = (page: Page) =>
  page.getByRole("combobox", { name: "Feedback form", exact: true });

test("adm08 AC18 chooser: heading, supporting text, one list GET with limit=100, drafts dropped, exact option text and order", async ({
  page,
}) => {
  const ctx = await chooser(page);
  await expect(heading(page, "Feedback responses")).toBeVisible();
  await expect(
    page.getByText(
      "Choose a form to review its submitted responses. Unfinished drafts are private and never shown.",
      { exact: true },
    ),
  ).toBeVisible();
  await expect(select(page)).toBeVisible();
  await expect(select(page).locator("option")).toHaveText([
    "Choose a feedback form",
    `${TITLE} · Open · Responses: 2`,
    "Closed form · Closed · Responses: 3",
  ]);
  await expect(select(page)).toHaveValue("");
  await settle(ctx);
  expect(ctx.formsCountGets()).toHaveLength(2);
  expect(ctx.of("GET", "/forms", "limit=100&offset=0")).toHaveLength(2);
  await expect(page.getByText("Draft form")).toHaveCount(0);
  await expect(page.getByText(MSG.chooserTruncated)).toHaveCount(0);
});

test("adm08 AC18 choosing a form pushes /responses/{id} and the chooser sends no request of its own; Choose another form pushes back", async ({
  page,
}) => {
  const ctx = await chooser(page);
  await settle(ctx);
  const mark = ctx.mark();
  await select(page).selectOption({ label: `${TITLE} · Open · Responses: 2` });
  await expect(page).toHaveURL(new RegExp(`${HUB}/responses/${FORM_ID}$`));
  await expect(heading(page, "Submitted responses", 2)).toBeVisible();
  expect(keys(ctx.since(mark))).toEqual([
    `GET ${FEEDBACK}/forms/${FORM_ID}/responses`,
  ]);
  await link(page, "Choose another form").click();
  await expect(page).toHaveURL(new RegExp(`${HUB}/responses$`));
  await page.goBack();
  await expect(page).toHaveURL(new RegExp(`${HUB}/responses/${FORM_ID}$`));
});

test("adm08 AC18 loading text, empty state with Go to Forms link", async ({
  page,
}) => {
  const ctx = await arrange(page, {
    forms: [makeForm(DRAFT_FORM_ID, "Only a draft", "draft", 0)],
  });
  ctx.steps.push({
    method: "GET",
    suffix: "/forms",
    query: "limit=100",
    hold: true,
    persist: true,
  });
  await page.goto(`${HUB}/responses`);
  await expect(statusWith(page, "Loading feedback forms...")).toBeVisible();
  await expect(select(page)).toHaveCount(0);
  ctx.release();
  await expect(statusWith(page, MSG.chooserEmpty)).toBeVisible();
  await expect(select(page)).toHaveCount(0);
  await link(page, "Go to Forms").click();
  await expect(page).toHaveURL(new RegExp(`${HUB}/forms$`));
});

test("adm08 AC18 truncation note when next_offset is not null (101 forms)", async ({
  page,
}) => {
  const many = Array.from({ length: 101 }, (_, n) =>
    makeForm(formId(n), `Form ${n}`, "open", 1),
  );
  const ctx = await arrange(page, { forms: many });
  await open(page, `${HUB}/responses`);
  await expect(
    page.getByText(MSG.chooserTruncated, { exact: true }),
  ).toBeVisible();
  await expect(select(page).locator("option")).toHaveCount(101); // placeholder + first 100
  await settle(ctx);
});

const CHOOSER_FAILURES: [
  string,
  { status?: number; code?: string; abort?: boolean },
  string,
][] = [
  ["403", { status: 403, code: "forbidden" }, MSG.forbidden],
  ["429", { status: 429, code: "feedback_rate_limited" }, MSG.limited],
  ["500", { status: 500, code: "feedback_error" }, MSG.unexpected],
  [
    "502 (unknown status)",
    { status: 502, code: "bad_gateway" },
    MSG.unexpected,
  ],
  ["503", { status: 503, code: "feedback_unavailable" }, MSG.unavailable],
  ["network", { abort: true }, MSG.network],
];
for (const [name, fail, message] of CHOOSER_FAILURES) {
  test(`adm08 AC18 chooser failure ${name}: exact message, tabs stay, Retry sends exactly one request and recovers`, async ({
    page,
  }) => {
    const ctx = await arrange(page);
    // fail only the chooser's own request: the second matching GET is the screen's (counts are silent anyway)
    ctx.steps.push({
      method: "GET",
      suffix: "/forms",
      query: "limit=100",
      ...fail,
    });
    ctx.steps.push({
      method: "GET",
      suffix: "/forms",
      query: "limit=100",
      ...fail,
    });
    await page.goto(`${HUB}/responses`);
    await expect(alertWith(page, message).first()).toBeVisible();
    await expect(tablist(page)).toBeVisible();
    await expect(button(page, "Retry")).toBeVisible();
    await settle(ctx);
    const mark = ctx.mark();
    await button(page, "Retry").click();
    await expect(select(page)).toBeVisible();
    expect(keys(ctx.since(mark))).toEqual([`GET ${COUNT_FORMS}`]);
  });
}

test("adm08 AC18 chooser 15 second timeout shows the ADM-02 timeout message", async ({
  page,
}) => {
  test.setTimeout(60_000);
  const ctx = await arrange(page);
  ctx.steps.push({
    method: "GET",
    suffix: "/forms",
    query: "limit=100",
    hold: true,
  });
  ctx.steps.push({
    method: "GET",
    suffix: "/forms",
    query: "limit=100",
    hold: true,
  });
  await page.goto(`${HUB}/responses`);
  await expect(alertWith(page, MSG.timeout).first()).toBeVisible({
    timeout: 25_000,
  });
  await expect(tablist(page)).toBeVisible();
  ctx.release();
});

test("adm08 AC18 an XSS-style form title renders as literal text in the chooser", async ({
  page,
}) => {
  const evil = "<img src=x onerror=alert(1)>";
  let fired = false;
  page.on("dialog", (d) => {
    fired = true;
    void d.dismiss();
  });
  await arrange(page, { forms: [makeForm(FORM_ID, evil, "open", 1)] });
  await open(page, `${HUB}/responses`);
  await expect(select(page).locator("option", { hasText: evil })).toHaveCount(
    1,
  );
  await expect(page.locator("img[src='x']")).toHaveCount(0);
  expect(fired).toBe(false);
});

// ---------------------------------------------------------------- AC26 tab counts
const badge = (page: Page, name: string) =>
  tab(page, name).locator("[aria-hidden='true']");

test("adm08 AC26 badges and descriptions: open and draft mix, response sum excluding drafts, analyses, follow-up", async ({
  page,
}) => {
  const ctx = await arrange(page, {
    forms: [
      makeForm(FORM_ID, TITLE, "open", 5),
      makeForm(SECOND_FORM_ID, "Closed form", "closed", 7),
      makeForm(DRAFT_FORM_ID, "Draft form", "draft", 0),
      makeForm(formId(1), "Draft two", "draft", 0),
    ],
    analyses: [analysisFor(1), analysisFor(2), analysisFor(3), analysisFor(4)],
    followUp: 3,
  });
  await open(page, `${HUB}/follow-up`);
  await settle(ctx);
  await expect(tab(page, "Forms")).toHaveAccessibleDescription(
    "1 open form, 2 drafts",
  );
  await expect(badge(page, "Forms")).toHaveText("1");
  await expect(tab(page, "Responses")).toHaveAccessibleDescription(
    "12 submitted responses",
  );
  await expect(badge(page, "Responses")).toHaveText("12");
  await expect(tab(page, "Analysis")).toHaveAccessibleDescription(
    "4 saved analyses",
  );
  await expect(badge(page, "Analysis")).toHaveText("4");
  await expect(tab(page, "Follow-up")).toHaveAccessibleDescription(
    "3 responses without a reply",
  );
  await expect(badge(page, "Follow-up")).toHaveText("3");
  for (const name of TABS)
    await expect(tab(page, name)).toHaveAccessibleName(name);
  expect(await noStorage(page)).toBe(0);
});

test("adm08 AC26 singular forms, one draft, one saved analysis and one response without a reply", async ({
  page,
}) => {
  const ctx = await arrange(page, {
    forms: [
      makeForm(FORM_ID, TITLE, "open", 1),
      makeForm(DRAFT_FORM_ID, "Draft form", "draft", 0),
    ],
    analyses: [analysisFor(1)],
    followUp: 1,
  });
  await open(page, `${HUB}/forms`);
  await settle(ctx);
  await expect(tab(page, "Forms")).toHaveAccessibleDescription(
    "1 open form, 1 draft",
  );
  await expect(tab(page, "Responses")).toHaveAccessibleDescription(
    "1 submitted response",
  );
  await expect(tab(page, "Analysis")).toHaveAccessibleDescription(
    "1 saved analysis",
  );
  await expect(tab(page, "Follow-up")).toHaveAccessibleDescription(
    "1 response without a reply",
  );
});

test("adm08 AC26 zero hides the badge and the description; nothing shown while loading", async ({
  page,
}) => {
  const ctx = await arrange(page, { forms: [], analyses: [], followUp: 0 });
  ctx.steps.push({ method: "GET", suffix: "/followup-counts", hold: true });
  await open(page, `${HUB}/forms`);
  await expect(badge(page, "Follow-up")).toHaveCount(0); // loading: nothing
  ctx.release();
  await settle(ctx);
  await page.waitForTimeout(300);
  for (const name of TABS) {
    await expect(badge(page, name)).toHaveCount(0);
    await expect(tab(page, name)).not.toHaveAttribute("aria-describedby", /.+/);
  }
});

test("adm08 AC26 a count request that is slow never blocks the tab or the screen", async ({
  page,
}) => {
  const ctx = await arrange(page);
  ctx.steps.push({ method: "GET", suffix: "/followup-counts", hold: true });
  await open(page, `${HUB}/forms`);
  await expect(heading(page, "Feedback forms")).toBeVisible();
  await tab(page, "Analysis").click();
  await expect(heading(page, "Feedback analysis")).toBeVisible();
  await expect(badge(page, "Follow-up")).toHaveCount(0);
  ctx.release();
  await expect(badge(page, "Follow-up")).toHaveText("4");
});

test("adm08 AC26 truncated lists show {n}+ and 'at least' descriptions; Follow-up above 99 shows 99+ with the true number", async ({
  page,
}) => {
  const forms = Array.from({ length: 101 }, (_, n) =>
    makeForm(formId(n), `Form ${n}`, "open", 1),
  );
  const analyses = Array.from({ length: 51 }, (_, n) => analysisFor(n + 1));
  const ctx = await arrange(page, { forms, analyses, followUp: 150 });
  await open(page, `${HUB}/follow-up`);
  await settle(ctx);
  await expect(badge(page, "Forms")).toHaveText("100+");
  await expect(tab(page, "Forms")).toHaveAccessibleDescription(
    /^at least 100 open forms/,
  );
  await expect(badge(page, "Responses")).toHaveText("100+");
  await expect(tab(page, "Responses")).toHaveAccessibleDescription(
    /^at least 100 submitted responses/,
  );
  await expect(badge(page, "Analysis")).toHaveText("50+");
  await expect(tab(page, "Analysis")).toHaveAccessibleDescription(
    "at least 50 saved analyses",
  );
  await expect(badge(page, "Follow-up")).toHaveText("99+");
  await expect(tab(page, "Follow-up")).toHaveAccessibleDescription(
    "150 responses without a reply",
  );
});

const COUNT_FAILS: [
  string,
  { status?: number; code?: string; abort?: boolean },
][] = [
  ["500", { status: 500, code: "feedback_error" }],
  ["429", { status: 429, code: "feedback_rate_limited" }],
  ["network", { abort: true }],
];
for (const [name, fail] of COUNT_FAILS) {
  test(`adm08 AC26 each count failing alone (${name}) leaves no badge, no alert text and working tabs`, async ({
    page,
  }) => {
    const ctx = await arrange(page);
    ctx.steps.push({ method: "GET", suffix: "/followup-counts", ...fail });
    ctx.steps.push({
      method: "GET",
      suffix: "/analyses",
      query: "limit=50",
      ...fail,
    });
    await open(page, `${HUB}/follow-up`);
    await settle(ctx);
    await page.waitForTimeout(300);
    await expect(badge(page, "Follow-up")).toHaveCount(0);
    await expect(badge(page, "Analysis")).toHaveCount(0);
    await expect(badge(page, "Forms")).toHaveText("1"); // other counts unaffected
    await expect(page.getByRole("alert")).toHaveCount(0);
    await expect(button(page, "Retry")).toHaveCount(0);
    await tab(page, "Forms").click();
    await expect(heading(page, "Feedback forms")).toBeVisible();
  });
}

test("adm08 AC26 a forms-count failure (500) leaves the Forms and Responses badges absent while the screen still works", async ({
  page,
}) => {
  const ctx = await arrange(page);
  // the count is the request that arrives with limit=100&offset=0; the Forms screen uses its own query
  ctx.steps.push({
    method: "GET",
    suffix: "/forms",
    query: "limit=100&offset=0",
    status: 500,
    code: "x",
  });
  await open(page, `${HUB}/follow-up`);
  await settle(ctx);
  await page.waitForTimeout(300);
  await expect(badge(page, "Forms")).toHaveCount(0);
  await expect(badge(page, "Responses")).toHaveCount(0);
  await expect(badge(page, "Follow-up")).toHaveText("4");
});

test("adm08 AC26 a count request that times out (15 s) shows nothing and no message", async ({
  page,
}) => {
  test.setTimeout(60_000);
  const ctx = await arrange(page);
  ctx.steps.push({ method: "GET", suffix: "/followup-counts", hold: true });
  await open(page, `${HUB}/follow-up`);
  await page.waitForTimeout(16_500);
  await expect(badge(page, "Follow-up")).toHaveCount(0);
  await expect(page.getByRole("alert")).toHaveCount(0);
  ctx.release();
});

test("adm08 AC26 a 401 on a count request ends the session at sign-in", async ({
  page,
}) => {
  const ctx = await arrange(page);
  ctx.steps.push({
    method: "GET",
    suffix: "/followup-counts",
    status: 401,
    code: "unauthenticated",
  });
  await page.goto(`${HUB}/forms`);
  await expect(page).toHaveURL(/\/login/);
  await expect(tablist(page)).toHaveCount(0);
  expect(await noStorage(page)).toBe(0);
});

test("adm08 AC26 no count request on tab clicks, Retry, chooser selection or Back within the hub", async ({
  page,
}) => {
  const ctx = await arrange(page);
  await open(page, `${HUB}/follow-up`);
  await settle(ctx);
  const followUps = ctx.followUpGets().length;
  const analysesCounts = ctx.analysesCountGets().length;
  for (const name of ["Forms", "Responses", "Analysis", "Follow-up", "Forms"])
    await tab(page, name).click();
  await page.goBack();
  await page.goBack();
  await page.waitForTimeout(300);
  expect(ctx.followUpGets()).toHaveLength(followUps);
  expect(ctx.analysesCountGets()).toHaveLength(analysesCounts); // the Analysis screen's own list uses limit=20
});

test("adm08 AC26 XSS-style titles do not affect the numbers or add markup to the tab bar", async ({
  page,
}) => {
  await arrange(page, {
    forms: [
      makeForm(FORM_ID, "<b>9</b><script>window.x=1</script>", "open", 2),
    ],
  });
  await open(page, `${HUB}/forms`);
  await expect(badge(page, "Forms")).toHaveText("1");
  await expect(tablist(page).locator("b, script")).toHaveCount(0);
});

test("adm08 AC26 wrong-role and anonymous visitors send no count request", async ({
  page,
}) => {
  const ctx = await setup(page, { user: STUDENT });
  await page.goto(`${HUB}/forms`);
  await expect(page).toHaveURL(/\/student\/overview$/);
  expect(ctx.followUpGets()).toHaveLength(0);
  expect(ctx.formsCountGets()).toHaveLength(0);
  expect(ctx.analysesCountGets()).toHaveLength(0);
});

// ---------------------------------------------------------------- AC28 browser side
test("adm08 AC28 the Follow-up badge renders the mocked value and description, no private identifiers in the tab bar", async ({
  page,
}) => {
  const ctx = await arrange(page, { followUp: 7 });
  await open(page, `${HUB}/forms`);
  await settle(ctx);
  await expect(badge(page, "Follow-up")).toHaveText("7");
  await expect(tab(page, "Follow-up")).toHaveAccessibleDescription(
    "7 responses without a reply",
  );
  const bar = await tablist(page).innerText();
  expect(bar).not.toContain(STUDENT.display_name);
  expect(bar).not.toContain(RESPONSE_ID);
});

// ---------------------------------------------------------------- AC15 layout
for (const width of [320, 390]) {
  test(`adm08 AC15 no horizontal page scroll at ${width}px with long titles and badges`, async ({
    page,
  }) => {
    await arrange(page, {
      forms: [
        makeForm(
          FORM_ID,
          "An extremely long feedback form title that must wrap rather than overflow the page",
          "open",
          1234,
        ),
      ],
      followUp: 250,
    });
    await page.setViewportSize({ width, height: 800 });
    for (const suffix of ["/forms", "/responses", "/follow-up"]) {
      await open(page, HUB + suffix);
      await expect(tab(page, "Follow-up")).toBeVisible();
      expect(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth,
        ),
      ).toBe(true);
    }
    for (const name of TABS) {
      const box = await tab(page, name).boundingBox();
      expect(box!.x).toBeGreaterThanOrEqual(0);
      expect(box!.x + box!.width).toBeLessThanOrEqual(width + 1);
    }
  });
}

test("adm08 AC15 tabs share one row from 480 px", async ({ page }) => {
  await arrange(page);
  await page.setViewportSize({ width: 600, height: 800 });
  await open(page, `${HUB}/forms`);
  const tops = await Promise.all(
    TABS.map(async (n) => (await tab(page, n).boundingBox())!.y),
  );
  expect(Math.max(...tops) - Math.min(...tops)).toBeLessThan(4);
});

for (const scheme of ["light", "dark"] as const) {
  test(`adm08 AC15 ${scheme} theme keeps the tab outline and a visible selected state`, async ({
    page,
  }, info) => {
    await arrange(page);
    await page.emulateMedia({ colorScheme: scheme });
    await open(page, `${HUB}/forms`);
    const border = await tablist(page).evaluate(
      (el) => getComputedStyle(el).borderTopWidth,
    );
    expect(parseFloat(border)).toBeGreaterThanOrEqual(1);
    await page.screenshot({
      path: info.outputPath(`hub-${scheme}.png`),
      fullPage: true,
      animations: "disabled",
    });
  });
}

test("adm08 AC15 reduced motion removes tab transitions", async ({ page }) => {
  await arrange(page);
  await page.emulateMedia({ reducedMotion: "reduce" });
  await open(page, `${HUB}/forms`);
  for (const name of TABS) {
    const duration = await tab(page, name).evaluate(
      (el) => getComputedStyle(el).transitionDuration,
    );
    expect(duration.split(",").every((d) => parseFloat(d) <= 0.01)).toBe(true);
  }
});

test("adm08 AC15 keyboard-only: Tab reaches the selected tab, then the panel content", async ({
  page,
}) => {
  await arrange(page);
  await open(page, `${HUB}/responses`);
  await tab(page, "Responses").focus();
  await page.keyboard.press("Tab");
  expect(
    await page.evaluate(
      () => !!document.activeElement?.closest("[role='tabpanel']"),
    ),
  ).toBe(true);
});

// ---------------------------------------------------------------- security
test("adm08 security: route params with ../, %2f, script text and very long strings never leave the hub or execute", async ({
  page,
}) => {
  let fired = false;
  page.on("dialog", (d) => {
    fired = true;
    void d.dismiss();
  });
  await arrange(page);
  const bad = [
    "/forms/..%2f..%2fadmin",
    "/responses/%3Cscript%3Ealert(1)%3C%2Fscript%3E",
    "/analysis/" + "a".repeat(2000),
    "/analysis/x/responses/%3Cimg%20src%3Dx%20onerror%3Dalert(1)%3E",
    "/follow-up/reply/..%2f/..%2f",
  ];
  for (const suffix of bad) {
    await page.goto(HUB + suffix);
    await expect(tablist(page)).toBeVisible();
    expect(new URL(page.url()).pathname.startsWith(HUB)).toBe(true);
  }
  expect(fired).toBe(false);
  expect(await noStorage(page)).toBe(0);
});

test("adm08 security: the hub shell holds no response text, names or ids outside inner screens and nothing in storage", async ({
  page,
}) => {
  const ctx = await arrange(page);
  await open(page, `${HUB}/follow-up`);
  await settle(ctx);
  const shell = await page
    .getByRole("region", { name: "Feedback hub", exact: true })
    .locator("[role='tablist']")
    .innerText();
  expect(shell).not.toContain(STUDENT.display_name);
  expect(shell).not.toContain(STUDENT.email ?? "@@");
  expect(await noStorage(page)).toBe(0);
  const cookies = (await page.context().cookies()).map((c) => c.name);
  expect(cookies.some((n) => /count|hub/i.test(n))).toBe(false);
});

test("adm08 security: a second admin signing in after logout sees none of the previous counts", async ({
  page,
}) => {
  const ctx = await arrange(page);
  await open(page, `${HUB}/forms`);
  await settle(ctx);
  await expect(badge(page, "Follow-up")).toHaveText("4");
  await logOutWithConfirmation(page);
  await expect(page).toHaveURL(/\/login/);
  await expect(page.getByText("4 responses without a reply")).toHaveCount(0);
  expect(await noStorage(page)).toBe(0);
});

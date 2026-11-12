// ADM-08 AC21 (phase 5): every old admin feedback and announcement URL redirects to its hub URL by
// history replace, keeping query and hash. Do not weaken.
import { expect, test, type Page } from "@playwright/test";
import {
  FORM_ID,
  HUB,
  MSG,
  RESPONSE_ID,
  REVIEW_ID,
  STUDENT,
  TEACHER,
  alertWith,
  analysisFor,
  analysisUuid,
  makeForm,
  setup,
  tablist,
} from "./adm08Api";

const ANALYSIS_ID = analysisUuid(1);
const LABEL = "R1";

const MAP: [string, string][] = [
  ["/admin/feedback", `${HUB}/forms`],
  ["/admin/feedback/new", `${HUB}/forms/new`],
  [`/admin/feedback/${FORM_ID}`, `${HUB}/forms/${FORM_ID}`],
  [`/admin/feedback/${FORM_ID}/edit`, `${HUB}/forms/${FORM_ID}/edit`],
  [`/admin/feedback/${FORM_ID}/responses`, `${HUB}/responses/${FORM_ID}`],
  [
    `/admin/feedback/${FORM_ID}/responses/${RESPONSE_ID}`,
    `${HUB}/responses/${FORM_ID}/${RESPONSE_ID}`,
  ],
  [
    `/admin/feedback/${FORM_ID}/responses/${RESPONSE_ID}/reply`,
    `${HUB}/follow-up/reply/${FORM_ID}/${RESPONSE_ID}`,
  ],
  ["/admin/feedback/analysis", `${HUB}/analysis`],
  [`/admin/feedback/analysis/${ANALYSIS_ID}`, `${HUB}/analysis/${ANALYSIS_ID}`],
  [
    `/admin/feedback/analysis/${ANALYSIS_ID}/responses/${LABEL}`,
    `${HUB}/analysis/${ANALYSIS_ID}/responses/${LABEL}`,
  ],
  ["/admin/announcements", `${HUB}/follow-up`],
  ["/admin/announcements/new", `${HUB}/follow-up`],
];

const arrange = (page: Page, user?: Parameters<typeof setup>[1]) =>
  setup(page, {
    forms: [makeForm(FORM_ID, "Redirect form", "open", 2)],
    analyses: [analysisFor(1, "complete")],
    followUp: 1,
    ...user,
  });

const here = (page: Page) => {
  const u = new URL(page.url());
  return u.pathname + u.search + u.hash;
};

/** Push the old URL as an in-app navigation, so that replace versus push is observable. */
async function pushOld(page: Page, old: string) {
  await page.evaluate((url) => {
    window.history.pushState({}, "", url);
    window.dispatchEvent(new PopStateEvent("popstate"));
  }, old);
}

for (const [old, hub] of MAP) {
  for (const suffix of ["", "?x=1", "?x=1#part"]) {
    test(`adm08 AC21 ${old}${suffix} ends at ${hub}${suffix} on a fresh load`, async ({
      page,
    }) => {
      await arrange(page);
      await page.goto(old + suffix);
      await expect.poll(() => here(page)).toBe(hub + suffix);
      await expect(tablist(page)).toBeVisible();
      await expect(alertWith(page, MSG.notFound)).toHaveCount(0);
    });
  }

  test(`adm08 AC21 ${old} is replaced, not pushed: Back skips the old URL`, async ({
    page,
  }) => {
    await arrange(page);
    await page.goto("/admin/not-a-page");
    const before = await page.evaluate(() => history.length);
    await pushOld(page, old);
    await expect.poll(() => here(page)).toBe(hub);
    expect(await page.evaluate(() => history.length)).toBe(before + 1);
    await page.goBack();
    await expect(page).toHaveURL(/\/admin\/not-a-page$/);
  });
}

for (const old of [
  `/admin/feedback/${FORM_ID}/responses/${RESPONSE_ID}/reply`,
  "/admin/announcements/new",
]) {
  test(`adm08 AC21 ${old}?review= keeps the review query on the follow-up URL`, async ({
    page,
  }) => {
    await arrange(page);
    await page.goto(`${old}?review=${REVIEW_ID}`);
    const base = old.endsWith("/reply")
      ? `${HUB}/follow-up/reply/${FORM_ID}/${RESPONSE_ID}`
      : `${HUB}/follow-up`;
    await expect.poll(() => here(page)).toBe(`${base}?review=${REVIEW_ID}`);
    await expect(tablist(page)).toBeVisible();
  });
}

test("adm08 AC21 /admin/feedback/analysis is not treated as a form id", async ({
  page,
}) => {
  const ctx = await arrange(page);
  await page.goto("/admin/feedback/analysis");
  await expect.poll(() => here(page)).toBe(`${HUB}/analysis`);
  await expect(tablist(page)).toBeVisible();
  await expect(page).not.toHaveURL(/forms\/analysis/);
  expect(
    ctx.requests.filter((r) => /\/forms\/analysis(\/|$)/.test(r.path)),
  ).toEqual([]);
  expect(
    ctx.requests.filter((r) => /\/feedback\/analysis$/.test(r.path)),
  ).toEqual([]);
  await expect(alertWith(page, MSG.notFound)).toHaveCount(0);
});

test("adm08 AC21 no old URL shows an error page or the old page chrome", async ({
  page,
}) => {
  await arrange(page);
  for (const [old, hub] of MAP) {
    await page.goto(old);
    await expect.poll(() => here(page)).toBe(hub);
    await expect(alertWith(page, MSG.notFound)).toHaveCount(0);
    await expect(page.getByText(/page not found|404/i)).toHaveCount(0);
  }
});

const SAMPLE_OLD = MAP.map(([old]) => old);
for (const [user, home] of [
  [STUDENT, /\/student\/overview$/],
  [TEACHER, /\/teacher\/overview$/],
] as const) {
  for (const old of SAMPLE_OLD) {
    test(`adm08 AC21 ${user.role} opening ${old} is replaced to their home with zero feedback requests`, async ({
      page,
    }) => {
      const ctx = await setup(page, { user });
      await page.goto(old);
      await expect(page).toHaveURL(home);
      await expect(tablist(page)).toHaveCount(0);
      expect(ctx.api()).toHaveLength(0);
      await page.goBack().catch(() => undefined);
      await expect(page).not.toHaveURL(/\/admin\//);
    });
  }
}

for (const old of SAMPLE_OLD) {
  test(`adm08 AC21 anonymous opening ${old} is replaced to /login with no request`, async ({
    page,
  }) => {
    const ctx = await setup(page, { user: null });
    await page.goto(old);
    await expect(page).toHaveURL(/\/login/);
    expect(ctx.api()).toHaveLength(0);
    await page.goBack().catch(() => undefined);
    await expect(page).not.toHaveURL(/\/admin\//);
    expect(ctx.api()).toHaveLength(0);
  });
}

// Gate F decision D1 (phase 5): the deleted demo "Feedback insights" route redirects to the Forms tab
// by replace. Decision D2 (anonymous /admin/announcements ends on /login) is covered by the
// anonymous loop above, which runs over the whole redirect map including both announcements URLs.
for (const suffix of ["", "?x=1", "?x=1#part"]) {
  test(`adm08 AC21 D1 /admin/responses${suffix} ends at ${HUB}/forms${suffix} on a fresh load`, async ({
    page,
  }) => {
    await arrange(page);
    await page.goto(`/admin/responses${suffix}`);
    await expect.poll(() => here(page)).toBe(`${HUB}/forms${suffix}`);
    await expect(tablist(page)).toBeVisible();
  });
}

test("adm08 AC21 D1 /admin/responses is replaced, not pushed: Back skips the old URL", async ({
  page,
}) => {
  await arrange(page);
  await page.goto("/admin/not-a-page");
  const before = await page.evaluate(() => history.length);
  await pushOld(page, "/admin/responses");
  await expect.poll(() => here(page)).toBe(`${HUB}/forms`);
  expect(await page.evaluate(() => history.length)).toBe(before + 1);
  await page.goBack();
  await expect(page).toHaveURL(/\/admin\/not-a-page$/);
});

for (const [user, home] of [
  [STUDENT, /\/student\/overview$/],
  [TEACHER, /\/teacher\/overview$/],
] as const) {
  test(`adm08 AC21 D1 ${user.role} opening /admin/responses is replaced to their home with zero feedback requests`, async ({
    page,
  }) => {
    const ctx = await setup(page, { user });
    await page.goto("/admin/responses");
    await expect(page).toHaveURL(home);
    expect(ctx.api()).toHaveLength(0);
  });
}

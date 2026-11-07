import { test, expect, type Page } from "@playwright/test";
import {
  emptyProgress,
  sampleProgress,
  signedInProgress,
  type ProgressBody,
} from "./progressApi";

/**
 * STU-04 presentation amendment 2026-11-08: the Progress sections have inner padding, readable
 * type sizes and a visible progress bar. Measured from computed styles at 1280px and 390px.
 */

test.beforeEach(async ({ page }) => {
  await page.route("**/api/health", (route) =>
    route.fulfill({ json: { status: "ok" } }),
  );
});

async function open(page: Page, body: ProgressBody, width: number) {
  await page.setViewportSize({ width, height: 900 });
  await signedInProgress(page, { body });
  await page.goto("/student/progress");
  await expect(
    page.getByRole("heading", { level: 1, name: "Your progress" }),
  ).toBeVisible();
  await expect(page.locator(".progress-sections")).toBeVisible();
}

const px = (page: Page, selector: string, prop: string) =>
  page
    .locator(selector)
    .first()
    .evaluate((el, p) => parseFloat(getComputedStyle(el)[p as never]), prop);

for (const [label, width, minPad, maxPad] of [
  ["desktop", 1280, 24, 28],
  ["390px", 390, 16, 20],
] as const) {
  for (const [state, body] of [
    ["with data", sampleProgress()],
    ["empty", emptyProgress()],
  ] as const) {
    test(`stu04 layout ${label} ${state}: every section card has inner padding and the cards are spaced`, async ({
      page,
    }) => {
      await open(page, body, width);
      const cards = page.locator(".progress-sections > .panel");
      expect(await cards.count()).toBe(3);
      for (let i = 0; i < 3; i++) {
        const style = await cards.nth(i).evaluate((el) => {
          const s = getComputedStyle(el);
          return {
            l: parseFloat(s.paddingLeft),
            r: parseFloat(s.paddingRight),
            t: parseFloat(s.paddingTop),
            b: parseFloat(s.paddingBottom),
          };
        });
        for (const v of [style.l, style.r, style.t, style.b]) {
          expect(v).toBeGreaterThanOrEqual(minPad);
          expect(v).toBeLessThanOrEqual(maxPad);
        }
      }
      const boxes = await cards.evaluateAll((els) =>
        els.map((el) => {
          const r = el.getBoundingClientRect();
          return { top: r.top, bottom: r.bottom };
        }),
      );
      expect(boxes[1].top - boxes[0].bottom).toBeGreaterThanOrEqual(16);
      expect(boxes[2].top - boxes[1].bottom).toBeGreaterThanOrEqual(16);
    });
  }
}

test("stu04 layout: section headings are 20px and body text is at least 14px", async ({
  page,
}) => {
  await open(page, sampleProgress(), 1280);
  for (const name of [
    "Lesson progress",
    "Practice scores",
    "Topics to revise",
  ]) {
    const size = await page
      .getByRole("heading", { level: 2, name, exact: true })
      .evaluate((el) => parseFloat(getComputedStyle(el).fontSize));
    expect(size).toBe(20);
  }
  expect(
    await px(page, ".progress-sections section > p", "fontSize"),
  ).toBeGreaterThanOrEqual(14);
  expect(
    await px(page, ".progress-list li", "fontSize"),
  ).toBeGreaterThanOrEqual(14);
  expect(
    await px(page, ".progress-sections td", "fontSize"),
  ).toBeGreaterThanOrEqual(14);
  expect(
    await px(page, ".progress-sections th", "fontSize"),
  ).toBeGreaterThanOrEqual(12);
});

test("stu04 layout: empty states use text of at least 14px", async ({
  page,
}) => {
  await open(page, emptyProgress(), 1280);
  expect(
    await px(page, ".progress-sections .empty-state p", "fontSize"),
  ).toBeGreaterThanOrEqual(14);
});

test("stu04 layout: the lesson progress bar is at least 8px high and not grey", async ({
  page,
}) => {
  await open(page, sampleProgress(), 1280);
  expect(await px(page, ".progress-bar", "height")).toBeGreaterThanOrEqual(8);
  const fill = await page
    .locator(".progress-bar > div")
    .first()
    .evaluate((el) => getComputedStyle(el).backgroundColor);
  const [r, g, b] = (fill.match(/[\d.]+/g) ?? []).map(Number);
  expect(b).toBeGreaterThan(r + 40);
  expect(b).toBeGreaterThan(g);
});

test("stu04 layout: links in the sections are blue", async ({ page }) => {
  await open(page, emptyProgress(), 1280);
  const color = await page
    .getByRole("link", { name: "Go to practice" })
    .evaluate((el) => getComputedStyle(el).color);
  const [r, g, b] = (color.match(/[\d.]+/g) ?? []).map(Number);
  expect(b).toBeGreaterThan(r + 30);
  expect(b).toBeGreaterThanOrEqual(g);
});

test("stu04 layout: no horizontal overflow at 390px", async ({ page }) => {
  await open(page, sampleProgress(), 390);
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth > window.innerWidth + 1,
  );
  expect(overflow).toBe(false);
});

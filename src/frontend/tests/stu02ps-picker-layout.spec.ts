import { test, expect, type Page } from "@playwright/test";
import { STUDENT, mockAuthApi } from "./authApi";
import { catalogCourse, catalogSet, mockPracticeApi } from "./practiceApi";

/**
 * STU-02-published-sets presentation amendment 2026-11-08: the practice set cards have inner
 * padding, readable type sizes and spacing. Measured from computed styles at 1280px and 390px.
 */

test.beforeEach(async ({ page }) => {
  await page.route("**/api/health", (route) =>
    route.fulfill({ json: { status: "ok" } }),
  );
});

async function open(page: Page, width: number) {
  await page.setViewportSize({ width, height: 900 });
  const auth = await mockAuthApi(page, { user: STUDENT });
  await mockPracticeApi(page, {
    auth,
    catalog: {
      courses: [
        catalogCourse("Software Engineering", [
          catalogSet({
            title: "Testing basics",
            best: { correct: 3, total: 3 },
          }),
          catalogSet({
            id: "a0000000-0000-4000-8000-000000000002",
            title: "Never tried",
            best: null,
          }),
        ]),
      ],
    },
  });
  await page.goto("/student/practice");
  await expect(
    page.getByRole("link", { name: "Testing basics" }),
  ).toBeVisible();
}

const rows = (page: Page) => page.locator(".practice-set-row");

for (const [label, width, minPad, maxPad] of [
  ["desktop", 1280, 20, 28],
  ["390px", 390, 16, 20],
] as const) {
  test(`stu02ps layout ${label}: set cards have inner padding and are spaced`, async ({
    page,
  }) => {
    await open(page, width);
    expect(await rows(page).count()).toBe(2);
    for (let i = 0; i < 2; i++) {
      const pad = await rows(page)
        .nth(i)
        .evaluate((el) => {
          const s = getComputedStyle(el);
          return [
            s.paddingTop,
            s.paddingRight,
            s.paddingBottom,
            s.paddingLeft,
          ].map(parseFloat);
        });
      for (const v of pad) {
        expect(v).toBeGreaterThanOrEqual(minPad);
        expect(v).toBeLessThanOrEqual(maxPad);
      }
    }
    const boxes = await rows(page).evaluateAll((els) =>
      els.map((el) => {
        const r = el.getBoundingClientRect();
        return { top: r.top, bottom: r.bottom };
      }),
    );
    expect(boxes[1].top - boxes[0].bottom).toBeGreaterThanOrEqual(12);
  });
}

test("stu02ps layout: the set title link is at least 16px and blue, other lines at least 14px", async ({
  page,
}) => {
  await open(page, 1280);
  const link = page.getByRole("link", { name: "Testing basics" });
  const style = await link.evaluate((el) => {
    const s = getComputedStyle(el);
    return { size: parseFloat(s.fontSize), color: s.color };
  });
  expect(style.size).toBeGreaterThanOrEqual(16);
  const [r, g, b] = (style.color.match(/[\d.]+/g) ?? []).map(Number);
  expect(b).toBeGreaterThan(r + 30);
  expect(b).toBeGreaterThanOrEqual(g);
  const sizes = await rows(page)
    .first()
    .locator("p")
    .evaluateAll((els) =>
      els.map((el) => parseFloat(getComputedStyle(el).fontSize)),
    );
  expect(sizes.length).toBe(2);
  for (const s of sizes) expect(s).toBeGreaterThanOrEqual(14);
});

test("stu02ps layout: no horizontal overflow at 390px", async ({ page }) => {
  await open(page, 390);
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth > window.innerWidth + 1,
  );
  expect(overflow).toBe(false);
});

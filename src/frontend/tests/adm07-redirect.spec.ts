import { test, expect } from "@playwright/test";
import { HUB, setup } from "./adm07Api";

/**
 * ADM-07 phase 5, Gate F decision recorded 2026-11-11 (workflow/specs/ADM-07/phase5-deletion-list.md):
 * after the old AI usage page is deleted, /admin/ai-usage redirects to /admin/usage and the admin
 * navigation has no "AI usage" link. These tests are expected to FAIL until the deletion step is done.
 */

const title = {
  level: 1 as const,
  name: "Feature Analytics",
  exact: true,
};

test("adm07 phase5 /admin/ai-usage redirects with replace to the hub, which loads once", async ({
  page,
}) => {
  const mock = await setup(page);
  await page.goto("/admin/usage");
  const entries = await page.evaluate(() => history.length);
  await page.goto("/admin/ai-usage");
  await expect(page).toHaveURL(new RegExp(`${HUB}$`));
  await expect(page.getByRole("heading", title)).toBeVisible();
  expect(await page.evaluate(() => history.length)).toBe(entries + 1); // replaced, not pushed
  await expect(
    page.getByRole("region", { name: "AI usage", exact: true }),
  ).toBeVisible();
  await expect.poll(() => mock.count()).toBe(7);
});

test("adm07 phase5 the admin navigation has no AI usage link and no legacy analytics route", async ({
  page,
}) => {
  await setup(page);
  await page.goto(HUB);
  await expect(page.getByRole("heading", title)).toBeVisible();
  await expect(
    page.getByRole("link", { name: "AI usage", exact: true }),
  ).toHaveCount(0);
  await page.goto("/admin/feature-analytics-legacy");
  await expect(
    page.getByRole("heading", { ...title, name: "Feature analytics" }),
  ).toHaveCount(0);
});

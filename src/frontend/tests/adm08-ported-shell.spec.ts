// ADM-08 phase 5 port of the first test of shell-confirmation.spec.ts: the only change is the link
// clicked ("Feedback insights" is removed with the demo page, AC25; "Feature Analytics" stays).
import { expect, test } from "@playwright/test";
import { ADMIN, mockAuthApi } from "./authApi";

test("shr01 shell tip dismisses, stays dismissed on navigation and returns after refresh", async ({
  page,
}, testInfo) => {
  await mockAuthApi(page, { user: ADMIN });
  await page.setViewportSize({ width: 1280, height: 1000 });
  await page.goto("/admin/overview");
  await expect(
    page.getByText("Listen. Learn. Improve.", { exact: true }),
  ).toBeVisible();
  await page.screenshot({ path: testInfo.outputPath("dismissible-tip.png") });
  await page
    .getByRole("button", { name: "Dismiss sidebar tip", exact: true })
    .click();
  await expect(
    page.getByText("Listen. Learn. Improve.", { exact: true }),
  ).toHaveCount(0);
  await page
    .getByRole("link", { name: "Feature Analytics", exact: true })
    .click();
  await expect(
    page.getByText("Listen. Learn. Improve.", { exact: true }),
  ).toHaveCount(0);
  await page.reload();
  await expect(
    page.getByText("Listen. Learn. Improve.", { exact: true }),
  ).toBeVisible();
});

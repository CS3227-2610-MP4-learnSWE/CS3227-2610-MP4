import { expect, test } from "@playwright/test";
import { ADMIN, STUDENT, TEACHER, mockAuthApi } from "./authApi";

for (const user of [STUDENT, TEACHER, ADMIN]) {
  test(`shr01 ${user.role} logout cancel and Escape preserve session without a POST`, async ({
    page,
  }, testInfo) => {
    const auth = await mockAuthApi(page, { user });
    await page.goto(`/${user.role}/overview`);
    await page.getByRole("button", { name: "Log out", exact: true }).click();
    const dialog = page.getByRole("dialog", {
      name: "Confirm logout",
      exact: true,
    });
    await expect(dialog).toBeVisible();
    if (user.role === "admin") {
      await expect(page.locator(".MuiDialog-container").last()).toHaveCSS(
        "opacity",
        "1",
      );
      await page.screenshot({
        path: testInfo.outputPath("logout-confirmation.png"),
      });
    }
    expect(auth.count("logout")).toBe(0);
    await dialog.getByRole("button", { name: "Cancel", exact: true }).click();
    await expect(dialog).toHaveCount(0);
    await expect(page).toHaveURL(new RegExp(`/${user.role}/overview$`));
    await page.getByRole("button", { name: "Log out", exact: true }).click();
    await page.keyboard.press("Escape");
    await expect(dialog).toHaveCount(0);
    expect(auth.count("logout")).toBe(0);
    expect(auth.user?.id).toBe(user.id);
  });
}

test("shr01 logout confirmation submits once and cannot dismiss during pending logout", async ({
  page,
}) => {
  const auth = await mockAuthApi(page, { user: ADMIN });
  auth.script("logout", { hold: true });
  await page.goto("/admin/overview");
  await page.getByRole("button", { name: "Log out", exact: true }).click();
  const dialog = page.getByRole("dialog", {
    name: "Confirm logout",
    exact: true,
  });
  await dialog.getByRole("button", { name: "Log out", exact: true }).click();
  await expect(
    dialog.getByRole("button", { name: "Log out", exact: true }),
  ).toBeDisabled();
  await expect(
    dialog.getByRole("button", { name: "Cancel", exact: true }),
  ).toBeDisabled();
  await expect(dialog.getByRole("status")).toHaveText("Logging out...");
  await page.keyboard.press("Escape");
  await expect(dialog).toBeVisible();
  expect(auth.count("logout")).toBe(1);
  auth.release();
  await expect(page).toHaveURL(/\/login$/);
  expect(auth.count("logout")).toBe(1);
});

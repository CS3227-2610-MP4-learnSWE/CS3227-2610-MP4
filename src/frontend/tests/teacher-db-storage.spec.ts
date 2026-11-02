import { test, expect } from "@playwright/test";
import { mockTeacherMaterialsApi, COURSE_A } from "./teacherMaterialsApi";

for (const theme of ["light", "dark"] as const) {
  for (const width of [390, 1440]) {
    test(`tea01 db storage quota recovery ${theme} ${width}`, async ({
      page,
    }) => {
      await page.setViewportSize({ width, height: 900 });
      await page.emulateMedia({ colorScheme: theme, reducedMotion: "reduce" });
      await page.route("**/api/health", (route) =>
        route.fulfill({ json: { status: "ok" } }),
      );
      const api = await mockTeacherMaterialsApi(page);
      let posts = 0;
      await page.route(
        `**/api/teacher/courses/${COURSE_A}/materials`,
        async (route) => {
          if (route.request().method() !== "POST") return api.handle(route);
          posts++;
          if (posts === 1)
            return route.fulfill({
              status: 413,
              json: {
                detail: {
                  code: "storage_quota_exceeded",
                  message:
                    "Upload would exceed the 100 MiB total storage limit.",
                },
              },
            });
          return api.handle(route);
        },
      );
      await page.goto("/teacher/materials");
      await expect(
        page.getByRole("button", { name: "Upload material" }),
      ).toBeEnabled();
      await page.getByRole("button", { name: "Upload material" }).click();
      const dialog = page.getByRole("dialog");
      await expect(
        dialog.getByText(
          "PDF or UTF-8 text · Up to 10 MiB per file · 100 MiB total upload storage.",
        ),
      ).toBeVisible();
      await dialog.getByLabel("Title").fill("Quota recovery source");
      await dialog
        .locator('input[type="file"]')
        .setInputFiles({
          name: "source.txt",
          mimeType: "text/plain",
          buffer: Buffer.from("One responsibility per function."),
        });
      await dialog.getByRole("button", { name: "Upload", exact: true }).click();
      await expect(dialog.getByRole("alert")).toContainText(
        "Upload would exceed the 100 MiB total storage limit.",
      );
      await expect(dialog.getByLabel("Title")).toHaveValue(
        "Quota recovery source",
      );
      expect(
        await dialog
          .locator('input[type="file"]')
          .evaluate((input) => (input as HTMLInputElement).files?.[0].name),
      ).toBe("source.txt");
      await expect(
        dialog.getByRole("button", { name: "Upload", exact: true }),
      ).toBeEnabled();
      await dialog.getByLabel("Title").focus();
      await expect(dialog.getByLabel("Title")).toBeFocused();
      expect(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth,
        ),
      ).toBe(true);
      expect(posts).toBe(1);
      await page.screenshot({
        path: test.info().outputPath(`db-storage-${theme}-${width}.png`),
        fullPage: true,
      });
      await dialog.getByRole("button", { name: "Upload", exact: true }).click();
      await expect(dialog).not.toBeVisible();
      await expect(
        page.getByText("Quota recovery source", { exact: true }),
      ).toBeVisible();
      expect(posts).toBe(2);
    });
  }
}

import { expect, test, type Page } from "@playwright/test";
import { ADMIN, mockAuthApi, STUDENT } from "./authApi";
import { setup, FORM_ID } from "./adm02Api";
import { mkdir } from "node:fs/promises";

async function outlined(page: Page, label: string) {
  const field = page.getByLabel(label, { exact: true });
  const outline = field.locator("..").locator("fieldset");
  await expect(field).toBeVisible();
  await expect(outline).toHaveCSS("border-top-style", "solid");
  expect(
    await outline.evaluate((el) =>
      parseFloat(getComputedStyle(el).borderTopWidth),
    ),
  ).toBeGreaterThan(0);
  const contrast = await outline.evaluate((el) => {
    const luminance = (color: string) => {
      const channels = color
        .match(/[\d.]+/g)!
        .slice(0, 3)
        .map(Number)
        .map((value) => {
          const channel = value / 255;
          return channel <= 0.04045
            ? channel / 12.92
            : ((channel + 0.055) / 1.055) ** 2.4;
        });
      return channels[0] * 0.2126 + channels[1] * 0.7152 + channels[2] * 0.0722;
    };
    const border = luminance(getComputedStyle(el).borderTopColor);
    const surface = luminance(
      getComputedStyle(el.parentElement!).backgroundColor,
    );
    return (
      (Math.max(border, surface) + 0.05) / (Math.min(border, surface) + 0.05)
    );
  });
  expect(contrast).toBeGreaterThanOrEqual(3);
  await field.focus();
  await expect(field).toBeFocused();
  await expect(outline).toHaveCSS("border-top-width", "2px");
}

async function noOverflow(page: Page) {
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
}

for (const mode of ["light", "dark"] as const) {
  test(`ADM-05 admin baseline separates account discovery and creation ${mode}`, async ({
    page,
  }) => {
    await page.emulateMedia({ colorScheme: mode });
    await setup(page, ADMIN);
    await page.route("**/api/admin/accounts?**", (route) =>
      route.fulfill({
        json: { accounts: [], page: 1, page_size: 20, total: 0 },
      }),
    );
    await page.route("**/api/admin/courses", (route) =>
      route.fulfill({ json: { courses: [] } }),
    );
    await page.goto("/admin/users");
    await expect(
      page.getByRole("heading", { name: "Find accounts", exact: true }),
    ).toBeVisible();
    await outlined(page, "Search accounts");
    await outlined(page, "Display name");
    const panels = page.locator(".admin-workspace > .panel");
    await expect(panels).toHaveCount(2);
    const [list, create] = await Promise.all([
      panels.nth(0).boundingBox(),
      panels.nth(1).boundingBox(),
    ]);
    expect(create!.x).toBeGreaterThan(list!.x);
    await page.setViewportSize({ width: 320, height: 850 });
    await noOverflow(page);
    await page.goto("/admin/courses");
    await expect(
      page.getByRole("heading", { name: "Available courses", exact: true }),
    ).toBeVisible();
    await outlined(page, "Course title");
    await noOverflow(page);
  });
}

for (const path of ["overview", "forms", "usage"]) {
  test(`admin preview ${path} retains sample scope at 320px`, async ({
    page,
  }) => {
    await page.route("**/api/**", (route) =>
      route.fulfill({ status: 503, json: {} }),
    );
    await mockAuthApi(page, { user: ADMIN });
    await page.setViewportSize({ width: 320, height: 850 });
    await page.goto(`/admin/${path}`);
    await expect(page.locator(".admin-preview")).toBeVisible();
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    await noOverflow(page);
  });
}

for (const width of [1365, 390]) {
  for (const mode of ["light", "dark"] as const) {
    test(`admin baseline visual coverage ${width}px ${mode}`, async ({
      page,
    }) => {
      await page.setViewportSize({ width, height: 900 });
      await page.emulateMedia({ colorScheme: mode, reducedMotion: "reduce" });
      const ctx = await setup(page, ADMIN);
      ctx.form.title = "Feedback on learning and practice";
      ctx.form.state = "draft";
      ctx.submitted = true;
      const course = {
        id: FORM_ID,
        title:
          "Software engineering fundamentals and collaborative development",
      };
      await page.route("**/api/admin/courses", (route) =>
        route.fulfill({ json: { courses: [course] } }),
      );
      await page.route("**/api/admin/accounts?**", (route) =>
        route.fulfill({
          json: {
            accounts: [
              {
                ...STUDENT,
                display_name: "Learner with a long name for responsive review",
                status: "enabled",
              },
            ],
            page: 1,
            page_size: 20,
            total: 1,
          },
        }),
      );
      const folder = "node_modules/.cache/admin-ui-visuals";
      await mkdir(folder, { recursive: true });
      for (const [name, path] of [
        ["users", "/admin/users"],
        ["courses", "/admin/courses"],
        ["analytics", "/admin/overview"],
      ]) {
        await page.goto(path);
        await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
        await expect(page.getByText(/^Loading/)).toHaveCount(0);
        await noOverflow(page);
        await page.screenshot({
          path: `${folder}/${width}-${mode}-${name}.png`,
          fullPage: true,
        });
      }
    });
  }
}

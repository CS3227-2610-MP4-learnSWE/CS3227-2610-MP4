// ADM-08 phase 5 port of the admin-route tests of admin-ui.spec.ts onto hub paths; assertions unchanged. ADM-05 users/courses tests and the demo preview tests stay in admin-ui.spec.ts or are superseded (see phase5-test-mapping.md).
import { expect, test, type Page } from "@playwright/test";
import { ADMIN, STUDENT } from "./authApi";
import { setup, FORM_ID, RESPONSE_ID, TIME } from "./adm08-ported-adm02Api";
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
  test(`ADM-02 admin baseline editor outlines and question groups at 320px ${mode}`, async ({
    page,
  }) => {
    await page.emulateMedia({ colorScheme: mode, reducedMotion: "reduce" });
    await page.setViewportSize({ width: 320, height: 850 });
    await setup(page, ADMIN);
    await page.goto("/admin/feedback-hub/forms/new");
    await expect(
      page.getByRole("heading", { name: "Form details", exact: true }),
    ).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Association", exact: true }),
    ).toBeVisible();
    await outlined(page, "Form title");
    await page
      .getByRole("button", { name: "Add question", exact: true })
      .click();
    await outlined(page, "Question 1 prompt");
    await noOverflow(page);
  });
}

test("ADM-02 admin baseline preserves selection across recipient search and separates review", async ({
  page,
}) => {
  const ctx = await setup(page, ADMIN);
  ctx.form.state = "draft";
  await page.goto(`/admin/feedback-hub/forms/${FORM_ID}`);
  await page
    .getByRole("button", { name: "Review audience", exact: true })
    .click();
  const dialog = page.getByRole("dialog", {
    name: "Review audience",
    exact: true,
  });
  await expect(
    dialog.getByRole("heading", { name: "Find recipients", exact: true }),
  ).toBeVisible();
  await dialog
    .getByRole("checkbox", {
      name: `${STUDENT.display_name} (${STUDENT.id})`,
      exact: true,
    })
    .check();
  await expect(dialog.getByText("1 selected", { exact: true })).toBeVisible();
  await dialog.getByLabel("Search recipients", { exact: true }).fill("Sam");
  await dialog.getByRole("button", { name: "Search", exact: true }).click();
  await expect.poll(() => ctx.of("GET", "/audience").length).toBe(2);
  await expect(dialog.getByText("1 selected", { exact: true })).toBeVisible();
  await dialog
    .getByRole("button", { name: "Review selected recipients", exact: true })
    .click();
  await expect(dialog.getByRole("textbox")).toHaveCount(0);
  await expect(dialog.getByText("1 recipients", { exact: true })).toBeVisible();
  expect(ctx.of("POST")).toHaveLength(0);
});

test("ADM-02 admin baseline response dates remain semantic and names lead long IDs", async ({
  page,
}) => {
  const ctx = await setup(page, ADMIN);
  ctx.submitted = true;
  await page.goto(`/admin/feedback-hub/responses/${FORM_ID}`);
  await expect(
    page.getByRole("heading", { name: "Submitted responses", exact: true }),
  ).toBeVisible();
  await expect(page.locator("time")).toHaveAttribute("datetime", TIME);
  await expect(page.locator(".feedback-list-entry-title")).toHaveText(
    STUDENT.display_name,
  );
  await page
    .getByRole("link", {
      name: `Response ${RESPONSE_ID} · ${STUDENT.display_name} · ${TIME}`,
      exact: true,
    })
    .click();
  await expect(page.locator("time")).toHaveAttribute("datetime", TIME);
  await expect(
    page.getByRole("heading", { name: "Feedback response", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText(`Response ${RESPONSE_ID}`, { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Respond to feedback", exact: true }),
  ).toBeVisible();
});

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
        ["forms", "/admin/feedback-hub/forms"],
        ["editor", "/admin/feedback-hub/forms/new"],
        ["form", `/admin/feedback-hub/forms/${FORM_ID}`],
        ["responses", `/admin/feedback-hub/responses/${FORM_ID}`],
        ["response", `/admin/feedback-hub/responses/${FORM_ID}/${RESPONSE_ID}`],
      ]) {
        await page.goto(path);
        await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
        await expect(page.getByText(/^Loading/)).toHaveCount(0);
        await noOverflow(page);
        await page.screenshot({
          path: `${folder}/${width}-${mode}-${name}.png`,
          fullPage: true,
        });
        if (name === "form") {
          await page
            .getByRole("button", { name: "Review audience", exact: true })
            .click();
          await expect(page.getByRole("checkbox")).toBeVisible();
          await noOverflow(page);
          await page.screenshot({
            path: `${folder}/${width}-${mode}-audience.png`,
            fullPage: true,
          });
          await page.keyboard.press("Escape");
        }
      }
    });
  }
}

// ADM-08 phase 5 port of adm04-redesign.spec.ts onto hub paths; assertions unchanged (see workflow/specs/ADM-08/phase5-test-mapping.md).
import { expect, test } from "@playwright/test";
import {
  setup,
  STUDENT,
  NEW,
  sampleMessage,
  FORM_ID,
  TIME,
  uuid,
} from "./adm08-ported-adm04Api";

test("adm04 redesign separates recipient search and outlined message inputs", async ({
  page,
}) => {
  await setup(page);
  await page.goto(NEW);
  const search = page.getByRole("textbox", {
    name: "Search recipients",
    exact: true,
  });
  const subject = page.getByRole("textbox", { name: "Subject", exact: true });
  await expect(
    page.getByRole("heading", { name: "Message details", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Recipients", exact: true }),
  ).toBeVisible();
  expect(await search.evaluate((el) => el.closest("form") === null)).toBe(true);
  const outline = subject.locator("..").locator("fieldset");
  await expect(outline).toHaveCSS("border-top-style", "solid");
  expect(
    parseFloat(
      await outline.evaluate((el) => getComputedStyle(el).borderTopWidth),
    ),
  ).toBeGreaterThan(0);
  await search.fill("Student 00");
  await expect(
    page.getByText("All active students selected", { exact: true }),
  ).toBeVisible();
  await expect(page.getByText("1 selected", { exact: true })).toHaveCount(0);
});

for (const [theme, width] of [
  ["light", 1365],
  ["dark", 1365],
  ["dark", 390],
] as const) {
  test(`adm04 redesign ${theme} ${width} responsive composer and inbox`, async ({
    page,
  }) => {
    await page.setViewportSize({ width, height: 950 });
    await page.emulateMedia({ colorScheme: theme });
    await setup(page);
    await page.goto(NEW);
    await page
      .getByRole("textbox", { name: "Subject", exact: true })
      .fill("Your feedback made a difference");
    await page
      .getByRole("textbox", { name: "Message", exact: true })
      .fill(
        "We have improved practice explanations.\nThank you for helping us make learnSWE better.",
      );
    await expect(
      page.getByRole("heading", { name: "Recipients", exact: true }),
    ).toBeVisible();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    ).toBe(true);
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.screenshot({
      path: `node_modules/.cache/adm04-ui-${theme}-${width}-compose.png`,
      fullPage: true,
    });
    const ctx = await setup(page, STUDENT);
    ctx.messages = [
      {
        ...sampleMessage(),
        subject: "Your feedback made a difference",
        body: "We have improved practice explanations.\nThank you for helping us make learnSWE better.",
      },
    ];
    await page.route("**/api/feedback/inbox?**", (route) =>
      route.fulfill({
        json: {
          items: [
            {
              id: uuid(300),
              form_id: FORM_ID,
              title: "Feedback on learnSWE",
              created_at: TIME,
              read_at: TIME,
              state: "open",
              submitted: true,
              response_status: "completed",
            },
          ],
          next_offset: null,
          unread_count: 0,
        },
      }),
    );
    await page.goto("/student/inbox");
    await expect(
      page.getByRole("heading", { name: "Inbox", exact: true }),
    ).toBeVisible();
    await expect(
      page.getByRole("article", {
        name: "Your feedback made a difference",
        exact: true,
      }),
    ).toBeVisible();
    await expect(page.locator("time[datetime]")).toHaveAttribute(
      "datetime",
      TIME,
    );
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    ).toBe(true);
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.screenshot({
      path: `node_modules/.cache/adm04-ui-${theme}-${width}-inbox.png`,
      fullPage: true,
    });
    if (width < 600) {
      await page
        .getByRole("button", { name: "Open navigation", exact: true })
        .click();
      await expect(
        page.getByRole("status", { name: "1 unread inbox items", exact: true }),
      ).toBeVisible();
    }
  });
}

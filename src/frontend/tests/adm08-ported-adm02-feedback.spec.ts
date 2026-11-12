// ADM-08 phase 5 port of adm02-feedback.spec.ts (admin tests) onto hub paths; assertions unchanged (see workflow/specs/ADM-08/phase5-test-mapping.md).
import { expect, test } from "@playwright/test";
import { ADMIN, STUDENT } from "./authApi";
import {
  FORM_ID,
  RESPONSE_ID,
  TITLE,
  MSG,
  TIME,
  setup,
  questions,
  choose,
  alert,
  status,
} from "./adm08-ported-adm02Api";

// Only the STUDENT row of the original wrong-role table visits an admin route; the other rows stay in adm02-feedback.spec.ts.
for (const [user, url, destination] of [
  [STUDENT, "/admin/feedback-hub/forms", "/student/overview"],
] as const) {
  test(`ADM-02 wrong role ${user.role} ${url} replaces and sends zero feature reads`, async ({
    page,
  }) => {
    const ctx = await setup(page, user);
    await page.goto(url);
    await expect(page).toHaveURL(new RegExp(`${destination}$`));
    expect(ctx.requests).toHaveLength(0);
  });
}

test("ADM-02 AC01-06 admin creates draft with accessible controls and correct save payload", async ({
  page,
}) => {
  const ctx = await setup(page, ADMIN);
  await page.goto("/admin/feedback-hub/forms/new");
  await expect(
    page.getByRole("heading", { name: "New feedback form", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("Add a question to get started.", { exact: true }),
  ).toBeVisible();
  await page
    .getByRole("textbox", { name: "Form title", exact: true })
    .fill("Focused survey");
  await page
    .getByRole("textbox", { name: "Description", exact: true })
    .fill("A focused survey.");
  await page.getByRole("button", { name: "Add question", exact: true }).click();
  await page
    .getByRole("textbox", { name: "Question 1 prompt", exact: true })
    .fill("What helped?");
  await page
    .getByRole("checkbox", { name: "Question 1 required", exact: true })
    .check();
  await page.getByRole("button", { name: "Save draft", exact: true }).click();
  await expect(status(page, "Draft saved.")).toBeVisible();
  expect(ctx.of("POST")[0].body.questions[0]).toMatchObject({
    prompt: "What helped?",
    type: "short_answer",
    required: true,
  });
  expect(ctx.of("GET", "/associations")).toHaveLength(1);
  expect(ctx.of("GET", "/forms")).toHaveLength(1); // ADM-08 AC29: create adds exactly one forms-count refetch (was 0)
  await expect(page).toHaveURL(
    new RegExp(`/admin/feedback-hub/forms/${FORM_ID}$`),
  );
});

for (const [kind, label] of [
  ["multiple_choice", "Multiple choice"],
  ["dropdown", "Dropdown"],
  ["checkbox", "Checkboxes"],
  ["linear_scale", "Linear scale"],
  ["paragraph", "Paragraph"],
]) {
  test(`ADM-02 AC01-03 authoring ${kind} configuration persists`, async ({
    page,
  }) => {
    const ctx = await setup(page, ADMIN);
    await page.goto("/admin/feedback-hub/forms/new");
    await page
      .getByRole("textbox", { name: "Form title", exact: true })
      .fill("Type survey");
    await page
      .getByRole("button", { name: "Add question", exact: true })
      .click();
    await choose(page, "Question 1 type", label);
    await page
      .getByRole("textbox", { name: "Question 1 prompt", exact: true })
      .fill("A prompt");
    if (["multiple_choice", "dropdown", "checkbox"].includes(kind)) {
      // The contract does not mandate pre-created options; add until the two named controls exist.
      for (let i = 1; i <= 2; i++) {
        const option = page.getByRole("textbox", {
          name: `Question 1 option ${i}`,
          exact: true,
        });
        if (!(await option.count()))
          await page
            .getByRole("button", {
              name: "Add option to question 1",
              exact: true,
            })
            .click();
        await option.fill(i === 1 ? "Alpha" : "Beta");
      }
    }
    if (kind === "linear_scale") {
      await page
        .getByRole("spinbutton", { name: "Question 1 minimum", exact: true })
        .fill("0");
      await page
        .getByRole("spinbutton", { name: "Question 1 maximum", exact: true })
        .fill("7");
      await page
        .getByRole("textbox", { name: "Question 1 minimum label", exact: true })
        .fill("Low");
      await page
        .getByRole("textbox", { name: "Question 1 maximum label", exact: true })
        .fill("High");
    }
    await page.getByRole("button", { name: "Save draft", exact: true }).click();
    await expect(status(page, "Draft saved.")).toBeVisible();
    expect(ctx.of("POST")[0].body.questions[0].type).toBe(kind);
    await page.getByRole("link", { name: "Edit draft", exact: true }).click();
    await expect(
      page.getByRole("textbox", { name: "Question 1 prompt", exact: true }),
    ).toHaveValue("A prompt");
    if (kind === "linear_scale")
      await expect(
        page.getByRole("spinbutton", {
          name: "Question 1 maximum",
          exact: true,
        }),
      ).toHaveValue("7");
  });
}

test("ADM-02 AC09 audience review precedes publication and dialog restores focus", async ({
  page,
}) => {
  const ctx = await setup(page, ADMIN);
  ctx.form.state = "draft";
  ctx.form.version = 1;
  await page.goto(`/admin/feedback-hub/forms/${FORM_ID}`);
  const opener = page.getByRole("button", {
    name: "Review audience",
    exact: true,
  });
  await opener.click();
  const dialog = page.getByRole("dialog", {
    name: "Review audience",
    exact: true,
  });
  await expect(dialog).toBeVisible();
  await dialog
    .getByRole("checkbox", {
      name: `${STUDENT.display_name} (${STUDENT.id})`,
      exact: true,
    })
    .check();
  await dialog
    .getByRole("button", { name: "Review selected recipients", exact: true })
    .click();
  await expect(
    dialog.getByRole("heading", { name: "Selected students", exact: true }),
  ).toBeVisible();
  expect(ctx.of("POST", "/publish")).toHaveLength(0);
  await dialog
    .getByRole("button", { name: "Publish form", exact: true })
    .click();
  await expect(
    status(page, "Form published. Inbox requests sent."),
  ).toBeVisible();
  expect(ctx.of("POST", "/publish")[0].body).toEqual({
    version: 1,
    audience_role: "student",
    recipient_ids: [STUDENT.id],
  });
  expect(ctx.of("GET", "/audience")).toHaveLength(1);
});

test("ADM-02 AC14 close requires confirmation and preserves response review", async ({
  page,
}) => {
  const ctx = await setup(page, ADMIN);
  await page.goto(`/admin/feedback-hub/forms/${FORM_ID}`);
  await page
    .getByRole("button", { name: "Close collection", exact: true })
    .click();
  const dialog = page.getByRole("dialog", {
    name: "Close collection",
    exact: true,
  });
  await expect(dialog).toContainText(
    "Closing collection prevents new responses and keeps existing responses.",
  );
  await dialog.getByRole("button", { name: "Cancel", exact: true }).click();
  expect(ctx.of("POST")).toHaveLength(0);
  await page
    .getByRole("button", { name: "Close collection", exact: true })
    .click();
  await dialog
    .getByRole("button", { name: "Confirm close", exact: true })
    .click();
  await expect(status(page, "Collection closed.")).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Review responses", exact: true }),
  ).toBeVisible();
  expect(ctx.of("POST", "/close")).toHaveLength(1);
});

test("ADM-02 AC18-20 response snapshot renders harmless text and exact original question association", async ({
  page,
}) => {
  const ctx = await setup(page, ADMIN);
  ctx.submitted = true;
  ctx.responseAnswers = [
    {
      question_id: questions()[0].id,
      value: "<img src=x onerror=window.ADM02_XSS=1>",
    },
  ];
  await page.goto(`/admin/feedback-hub/responses/${FORM_ID}/${RESPONSE_ID}`);
  await expect(
    page.getByRole("heading", { name: "Feedback response", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText(`Respondent: ${STUDENT.display_name}`, { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("<img src=x onerror=window.ADM02_XSS=1>", { exact: true }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => (window as Window & { ADM02_XSS?: number }).ADM02_XSS,
    ),
  ).toBeUndefined();
  await expect(
    page.getByText("One sentence", { exact: false }).first(),
  ).toBeVisible();
  expect(ctx.of("GET", RESPONSE_ID)).toHaveLength(1);
});

test("ADM-02 admin form and response rows are one-line, full-row links with hover feedback", async ({
  page,
}) => {
  const ctx = await setup(page, ADMIN);
  ctx.form.response_count = 1;
  ctx.submitted = true;

  await page.goto("/admin/feedback-hub/forms");
  const formLink = page.getByRole("link", {
    name: `${TITLE} · Open · Responses: 1`,
    exact: true,
  });
  await expect(formLink).toBeVisible();
  await expect(formLink).toHaveCSS("display", "flex");
  await expect(formLink).toHaveCSS("min-height", "80px");
  const formTextRows = await formLink
    .locator("span")
    .evaluateAll((nodes) =>
      nodes.map((node) => node.getBoundingClientRect().top),
    );
  expect(Math.abs(formTextRows[0] - formTextRows[1])).toBeLessThan(2);
  const formColor = await formLink.evaluate(
    (node) => getComputedStyle(node).backgroundColor,
  );
  await formLink.hover();
  await expect
    .poll(() =>
      formLink.evaluate((node) => getComputedStyle(node).backgroundColor),
    )
    .not.toBe(formColor);
  await formLink.getByText("Open · Responses: 1", { exact: true }).click();
  await expect(page).toHaveURL(
    new RegExp(`/admin/feedback-hub/forms/${FORM_ID}$`),
  );

  await page
    .getByRole("link", { name: "Review responses", exact: true })
    .click();
  const responseLink = page.getByRole("link", {
    name: `Response ${RESPONSE_ID} · ${STUDENT.display_name} · ${TIME}`,
    exact: true,
  });
  await expect(responseLink).toBeVisible();
  await expect(responseLink).toHaveCSS("display", "flex");
  await expect(responseLink).toHaveCSS("min-height", "80px");
  const responseTextRows = await responseLink
    .locator("span")
    .evaluateAll((nodes) =>
      nodes.map((node) => node.getBoundingClientRect().top),
    );
  expect(Math.abs(responseTextRows[0] - responseTextRows[1])).toBeLessThan(2);
  const responseColor = await responseLink.evaluate(
    (node) => getComputedStyle(node).backgroundColor,
  );
  await responseLink.hover();
  await expect
    .poll(() =>
      responseLink.evaluate((node) => getComputedStyle(node).backgroundColor),
    )
    .not.toBe(responseColor);
  await responseLink.locator(`time[datetime="${TIME}"]`).click();
  await expect(page).toHaveURL(
    `/admin/feedback-hub/responses/${FORM_ID}/${RESPONSE_ID}`,
  );
});

test("ADM-02 admin empty response review distinguishes no submitted responses", async ({
  page,
}) => {
  await setup(page, ADMIN);
  await page.goto(`/admin/feedback-hub/responses/${FORM_ID}`);
  await expect(
    page.getByText("No responses yet.", { exact: true }),
  ).toBeVisible();
});

for (const width of [1365, 390]) {
  test(`ADM-02 responsive admin editor audience and response snapshots at ${width}px`, async ({
    page,
  }, info) => {
    await page.setViewportSize({ width, height: 900 });
    const ctx = await setup(page, ADMIN);
    ctx.form.state = "draft";
    ctx.form.version = 1;
    await page.goto(`/admin/feedback-hub/forms/${FORM_ID}/edit`);
    await expect(
      page.getByRole("textbox", { name: "Form title", exact: true }),
    ).toHaveValue(TITLE);
    await page.screenshot({
      path: info.outputPath(`admin-editor-${width}.png`),
      fullPage: true,
      animations: "disabled",
    });
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    await page.goto(`/admin/feedback-hub/forms/${FORM_ID}`);
    const opener = page.getByRole("button", {
      name: "Review audience",
      exact: true,
    });
    await opener.click();
    const dialog = page.getByRole("dialog", {
      name: "Review audience",
      exact: true,
    });
    await expect(dialog).toBeVisible();
    await page.screenshot({
      path: info.outputPath(`admin-audience-${width}.png`),
      fullPage: true,
      animations: "disabled",
    });
    await page.keyboard.press("Escape");
    await expect(dialog).toHaveCount(0);
    await expect(opener).toBeFocused();
    ctx.form.state = "closed";
    ctx.submitted = true;
    ctx.responseAnswers = [
      { question_id: questions()[0].id, value: "Long response ".repeat(40) },
    ];
    await page.goto(`/admin/feedback-hub/responses/${FORM_ID}/${RESPONSE_ID}`);
    await expect(
      page.getByRole("heading", {
        name: "Feedback response",
        exact: true,
      }),
    ).toBeVisible();
    await page.screenshot({
      path: info.outputPath(`admin-response-${width}.png`),
      fullPage: true,
      animations: "disabled",
    });
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
  });
}

test("ADM-02 admin failed draft save preserves editor fields and retries explicit action", async ({
  page,
}) => {
  const ctx = await setup(page, ADMIN);
  ctx.form.state = "draft";
  await page.goto(`/admin/feedback-hub/forms/${FORM_ID}/edit`);
  await page
    .getByRole("textbox", { name: "Form title", exact: true })
    .fill("Keep edited title");
  ctx.steps.push({ method: "PUT", status: 503, code: "feedback_unavailable" });
  await page.getByRole("button", { name: "Save draft", exact: true }).click();
  await expect(alert(page, MSG.unavailable)).toBeVisible();
  await expect(
    page.getByRole("textbox", { name: "Form title", exact: true }),
  ).toHaveValue("Keep edited title");
  expect(ctx.of("PUT")).toHaveLength(1);
  await page.getByRole("button", { name: "Save draft", exact: true }).click();
  await expect(status(page, "Draft saved.")).toBeVisible();
  expect(ctx.of("PUT")).toHaveLength(2);
});

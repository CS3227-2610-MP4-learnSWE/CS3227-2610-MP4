import { expect, test } from "@playwright/test";
import {
  ADMIN,
  STUDENT,
  TEACHER,
  expectNoSecretsInBrowser,
  logOutWithConfirmation,
} from "./authApi";
import {
  FORM_ID,
  RESPONSE_ID,
  TITLE,
  MSG,
  TIME,
  setup,
  recipientReady,
  firstAnswer,
  questions,
  choose,
  alert,
  status,
} from "./adm02Api";

const path = `/student/feedback/${FORM_ID}`;

test("ADM-02 AC01-03 six question controls and accessible required/optional labels", async ({
  page,
}) => {
  const ctx = await recipientReady(page);
  await expect(
    page.getByRole("heading", { level: 1, name: TITLE, exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("textbox", { name: "2. Your experience", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("group", { name: /3\. Choose one/ }),
  ).toBeVisible();
  await expect(
    page.getByRole("radio", { name: "First option", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("combobox", { name: "4. Pick a topic", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("checkbox", { name: "First option", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("radiogroup", { name: "6. Rate usefulness", exact: true }),
  ).toBeVisible();
  for (const n of ["0", "5"])
    await expect(
      page.getByRole("radio", { name: n, exact: true }),
    ).toBeVisible();
  const scaleQuestion = page.getByRole("group", {
    name: "6. Rate usefulness",
    exact: true,
  });
  await expect(scaleQuestion).toContainText("Low");
  await expect(scaleQuestion).toContainText("High");
  await expect(status(page, MSG.initial)).toBeVisible();
  expect(ctx.of("GET", FORM_ID)).toHaveLength(1);
  expect(ctx.of("PUT")).toHaveLength(0);
});

for (const role of ["student", "teacher"] as const) {
  test(`ADM-02 AC22 ${role} acknowledged autosave restores after refresh and return`, async ({
    page,
  }) => {
    const ctx = await recipientReady(page, role);
    await firstAnswer(page).fill("  Keep my progress  ");
    await expect(status(page, MSG.saved)).toBeVisible();
    expect(ctx.of("PUT", "/draft")).toHaveLength(1);
    expect(ctx.of("PUT", "/draft")[0].body.version).toBe(0);
    expect(ctx.of("PUT", "/draft")[0].body.answers).toContainEqual({
      question_id: questions()[0].id,
      value: "  Keep my progress  ",
    });
    await page.reload();
    await expect(firstAnswer(page)).toHaveValue("  Keep my progress  ");
    expect(ctx.of("PUT", "/draft")).toHaveLength(1);
    await page
      .getByRole("link", { name: "Back to inbox", exact: true })
      .click();
    await expect(
      page
        .getByRole("article")
        .filter({ has: page.getByRole("link", { name: TITLE, exact: true }) }),
    ).toContainText(/\bDraft\b/);
    await page.getByRole("link", { name: TITLE, exact: true }).click();
    await expect(firstAnswer(page)).toHaveValue("  Keep my progress  ");
    await expectNoSecretsInBrowser(page, ["Keep my progress"]);
  });
}

test("ADM-02 AC22 loads own existing six-type draft without save-on-hydration", async ({
  page,
}) => {
  const ctx = await setup(page);
  const qs = questions();
  ctx.draft = {
    version: 4,
    updated_at: TIME,
    answers: [
      { question_id: qs[0].id, value: "Saved short answer" },
      { question_id: qs[1].id, value: "Saved\nparagraph" },
      { question_id: qs[2].id, value: qs[2].options[1].id },
      { question_id: qs[3].id, value: qs[3].options[1].id },
      { question_id: qs[4].id, value: [qs[4].options[0].id] },
      { question_id: qs[5].id, value: 0 },
    ],
  };
  await page.goto(path);
  await expect(firstAnswer(page)).toHaveValue("Saved short answer");
  await expect(
    page.getByRole("textbox", { name: "2. Your experience", exact: true }),
  ).toHaveValue("Saved\nparagraph");
  await expect(
    page.getByRole("radio", { name: "Second option", exact: true }),
  ).toBeChecked();
  await expect(
    page.getByRole("checkbox", { name: "First option", exact: true }),
  ).toBeChecked();
  await expect(
    page.getByRole("radio", { name: "0", exact: true }),
  ).toBeChecked();
  await page.waitForTimeout(1200);
  expect(ctx.of("PUT")).toHaveLength(0);
});

test("ADM-02 AC22 debounces latest edits and serialises in-flight saves without losing edits", async ({
  page,
}) => {
  const ctx = await recipientReady(page);
  ctx.steps.push({ method: "PUT", path: "/draft", hold: true });
  await firstAnswer(page).fill("First draft");
  await expect.poll(() => ctx.of("PUT").length).toBe(1);
  await expect(status(page, MSG.saving)).toBeVisible();
  await firstAnswer(page).fill("Newest draft");
  await page.waitForTimeout(1200);
  expect(ctx.of("PUT")).toHaveLength(1);
  ctx.release();
  await expect.poll(() => ctx.of("PUT").length).toBe(2);
  await expect(status(page, MSG.saved)).toBeVisible();
  expect(ctx.of("PUT")[1].body.version).toBe(1);
  expect(ctx.of("PUT")[1].body.answers).toContainEqual({
    question_id: questions()[0].id,
    value: "Newest draft",
  });
  await expect(firstAnswer(page)).toHaveValue("Newest draft");
});

for (const failure of [
  { status: 503, code: "feedback_unavailable", text: MSG.unavailable },
  { status: 429, code: "feedback_rate_limited", text: MSG.limited },
  { abort: true, text: MSG.network },
]) {
  test(`ADM-02 AC25 draft save failure ${failure.code ?? "network"} preserves answers and retries once`, async ({
    page,
  }) => {
    const ctx = await recipientReady(page);
    ctx.steps.push({ method: "PUT", path: "/draft", ...failure });
    await firstAnswer(page).fill("Unsaved private answer");
    await expect(alert(page, failure.text)).toBeVisible();
    await expect(page.getByText(MSG.unsaved, { exact: true })).toBeVisible();
    await expect(firstAnswer(page)).toHaveValue("Unsaved private answer");
    await page.waitForTimeout(1300);
    expect(ctx.of("PUT")).toHaveLength(1);
    await page
      .getByRole("button", { name: "Retry saving draft", exact: true })
      .click();
    await expect(status(page, MSG.saved)).toBeVisible();
    expect(ctx.of("PUT")).toHaveLength(2);
  });
}

test("ADM-02 AC25 stale two-tab draft never silently overwrites and explicit reload restores saved version", async ({
  page,
}) => {
  const ctx = await recipientReady(page);
  ctx.steps.push({
    method: "PUT",
    path: "/draft",
    status: 409,
    code: "feedback_draft_version_conflict",
  });
  await firstAnswer(page).fill("Local tab answer");
  await expect(alert(page, MSG.conflict)).toBeVisible();
  ctx.draft = {
    version: 8,
    answers: [{ question_id: questions()[0].id, value: "Other tab answer" }],
    updated_at: TIME,
  };
  await page
    .getByRole("button", { name: "Reload saved draft", exact: true })
    .click();
  const dialog = page.getByRole("dialog", {
    name: "Reload saved draft?",
    exact: true,
  });
  await expect(dialog).toBeVisible();
  await dialog
    .getByRole("button", { name: "Keep editing", exact: true })
    .click();
  await expect(firstAnswer(page)).toHaveValue("Local tab answer");
  await page
    .getByRole("button", { name: "Reload saved draft", exact: true })
    .click();
  await dialog
    .getByRole("button", { name: "Reload draft", exact: true })
    .click();
  await expect(firstAnswer(page)).toHaveValue("Other tab answer");
  expect(ctx.of("GET", FORM_ID)).toHaveLength(2);
  expect(ctx.of("PUT")).toHaveLength(1);
});

test("ADM-02 AC25 in-app leaving flushes an answer before navigation then Back resumes it", async ({
  page,
}) => {
  const ctx = await recipientReady(page);
  await firstAnswer(page).fill("Leave immediately");
  await page.getByRole("link", { name: "Back to inbox", exact: true }).click();
  await expect(page).toHaveURL(/\/student\/inbox$/);
  expect(ctx.of("PUT")).toHaveLength(1);
  await expect(
    page.getByRole("heading", { name: "Feedback requests", exact: true }),
  ).toBeVisible();
  await page.goBack();
  await expect(firstAnswer(page)).toHaveValue("Leave immediately");
  expect(ctx.of("GET", FORM_ID)).toHaveLength(2);
});

test("ADM-02 AC25 failed navigation flush stays on form with original answers", async ({
  page,
}) => {
  const ctx = await recipientReady(page);
  ctx.steps.push({ method: "PUT", status: 503, code: "feedback_unavailable" });
  await firstAnswer(page).fill("Do not lose these words");
  await page.getByRole("link", { name: "Back to inbox", exact: true }).click();
  await expect(alert(page, MSG.unavailable)).toBeVisible();
  await expect(page).toHaveURL(new RegExp(`/student/feedback/${FORM_ID}$`));
  await expect(firstAnswer(page)).toHaveValue("Do not lose these words");
  expect(ctx.of("GET", "/inbox")).toHaveLength(0);
});

test("ADM-02 AC04_24 required validation does not complete form or erase draft", async ({
  page,
}) => {
  const ctx = await recipientReady(page);
  await page
    .getByRole("textbox", { name: "2. Your experience", exact: true })
    .fill("Preserve this optional draft answer");
  await expect(status(page, MSG.saved)).toBeVisible();
  ctx.steps.push({
    method: "POST",
    path: "/responses",
    status: 422,
    code: "invalid_feedback_answers",
  });
  await page
    .getByRole("button", { name: "Submit feedback", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Submit feedback", exact: true }),
  ).toBeVisible();
  expect(ctx.submitted).toBe(false);
  await expect(firstAnswer(page)).toBeVisible();
  await expect(
    alert(
      page,
      "Answer every required question and check that all answers match their question type.",
    ),
  ).toBeVisible();
  await expect(firstAnswer(page)).toBeFocused();
  await expect(
    page.getByRole("textbox", { name: "2. Your experience", exact: true }),
  ).toHaveValue("Preserve this optional draft answer");
  expect(ctx.draft.answers).toContainEqual({
    question_id: questions()[1].id,
    value: "Preserve this optional draft answer",
  });
  expect(ctx.of("POST")).toHaveLength(1);
});

test("ADM-02 AC24 explicit submit uses final local answers and Completed has no editable controls", async ({
  page,
}) => {
  const ctx = await recipientReady(page);
  await firstAnswer(page).fill("Final answer");
  await page
    .getByRole("button", { name: "Submit feedback", exact: true })
    .click();
  await expect(status(page, "Feedback submitted. Thank you.")).toBeVisible();
  expect(ctx.of("POST", "/responses")).toHaveLength(1);
  expect(ctx.of("GET", FORM_ID)).toHaveLength(1);
  expect(ctx.of("POST", "/responses")[0].body.answers).toContainEqual({
    question_id: questions()[0].id,
    value: "Final answer",
  });
  expect(ctx.of("POST", "/responses")[0].body.draft_version).toBe(
    ctx.of("PUT").length,
  );
  await expect(firstAnswer(page)).toHaveCount(0);
  await page.reload();
  await expect(
    page.getByText("Completed", { exact: true }).first(),
  ).toBeVisible();
  await expect(status(page, MSG.completed)).toBeVisible();
  expect(ctx.of("POST", "/responses")).toHaveLength(1);
  await expectNoSecretsInBrowser(page, ["Final answer"]);
});

test("ADM-02 AC24 submit waits for in-flight autosave and sends its latest version once", async ({
  page,
}) => {
  const ctx = await recipientReady(page);
  ctx.steps.push({ method: "PUT", hold: true });
  await firstAnswer(page).fill("Autosaving");
  await expect.poll(() => ctx.of("PUT").length).toBe(1);
  await firstAnswer(page).fill("Latest at submit");
  await page
    .getByRole("button", { name: "Submit feedback", exact: true })
    .click();
  expect(ctx.of("POST")).toHaveLength(0);
  ctx.release();
  await expect(status(page, "Feedback submitted. Thank you.")).toBeVisible();
  expect(ctx.of("POST")).toHaveLength(1);
  expect(ctx.of("POST")[0].body.draft_version).toBe(1);
  expect(ctx.of("POST")[0].body.answers).toContainEqual({
    question_id: questions()[0].id,
    value: "Latest at submit",
  });
});

test("ADM-02 AC24 uncertain submission checks server completion without replay", async ({
  page,
}) => {
  const ctx = await recipientReady(page);
  ctx.steps.push({ method: "POST", path: "/responses", abort: true });
  await firstAnswer(page).fill("Uncertain answer");
  await page
    .getByRole("button", { name: "Submit feedback", exact: true })
    .click();
  await expect(alert(page, MSG.network)).toBeVisible();
  ctx.submitted = true;
  await page
    .getByRole("button", { name: "Check submission status", exact: true })
    .click();
  await expect(status(page, MSG.completed)).toBeVisible();
  expect(ctx.of("POST")).toHaveLength(1);
  expect(ctx.of("GET", FORM_ID)).toHaveLength(2);
});

test("ADM-02 AC15 draft-save closure stops autosave and clears editable answers", async ({
  page,
}) => {
  const ctx = await recipientReady(page);
  ctx.steps.push({ method: "PUT", status: 409, code: "feedback_closed" });
  await firstAnswer(page).fill("Draft before closure");
  await expect(
    page.getByText(MSG.closed, { exact: true }).first(),
  ).toBeVisible();
  await expect(firstAnswer(page)).toHaveCount(0);
  await page.waitForTimeout(1200);
  expect(ctx.of("PUT")).toHaveLength(1);
});

for (const terminal of ["closed", "completed"] as const) {
  test(`ADM-02 terminal ${terminal} direct open never renders private answers`, async ({
    page,
  }) => {
    const ctx = await setup(page);
    if (terminal === "closed") ctx.form.state = "closed";
    else ctx.submitted = true;
    ctx.draft = {
      version: 2,
      answers: [{ question_id: questions()[0].id, value: "PRIVATE" }],
      updated_at: TIME,
    };
    await page.goto(path);
    await expect(
      status(page, terminal === "closed" ? MSG.closed : MSG.completed),
    ).toBeVisible();
    await expect(firstAnswer(page)).toHaveCount(0);
    await expect(page.getByText("PRIVATE", { exact: true })).toHaveCount(0);
    expect(ctx.of("PUT")).toHaveLength(0);
  });
}

for (const failure of [
  { status: 403, code: "forbidden", text: MSG.forbidden },
  { status: 404, code: "feedback_not_found", text: MSG.missing },
  { status: 429, code: "feedback_rate_limited", text: MSG.limited },
  { status: 503, code: "feedback_unavailable", text: MSG.unavailable },
  { status: 500, code: "feedback_error", text: MSG.unexpected },
  { abort: true, text: MSG.network },
]) {
  test(`ADM-02 exact form load ${failure.code ?? "network"} error and one explicit retry`, async ({
    page,
  }) => {
    const ctx = await setup(page);
    ctx.steps.push({ method: "GET", path: FORM_ID, ...failure });
    await page.goto(path);
    await expect(alert(page, failure.text)).toBeVisible();
    expect(ctx.of("GET", FORM_ID)).toHaveLength(1);
    await page.getByRole("button", { name: "Retry", exact: true }).click();
    await expect(firstAnswer(page)).toBeVisible();
    expect(ctx.of("GET", FORM_ID)).toHaveLength(2);
  });
}

test("ADM-02 15-second timeout distinguishes transport from timeout without automatic retry", async ({
  page,
}) => {
  const ctx = await setup(page);
  ctx.steps.push({ method: "GET", path: FORM_ID, hold: true });
  await page.goto(path);
  await expect(status(page, "Loading feedback form...")).toBeVisible();
  await expect(alert(page, MSG.timeout)).toBeVisible({ timeout: 18000 });
  expect(ctx.of("GET", FORM_ID)).toHaveLength(1);
  ctx.release();
});

test("ADM-02 logout clears draft UI, cancels autosave and late responses cannot restore it", async ({
  page,
}) => {
  const ctx = await recipientReady(page);
  ctx.steps.push({ method: "PUT", hold: true });
  await firstAnswer(page).fill("PRIVATE AFTER LOGOUT");
  await expect.poll(() => ctx.of("PUT").length).toBe(1);
  await logOutWithConfirmation(page);
  await expect(page).toHaveURL(/\/login/);
  ctx.release();
  await expect(
    page.getByText("PRIVATE AFTER LOGOUT", { exact: true }),
  ).toHaveCount(0);
  await expectNoSecretsInBrowser(page, ["PRIVATE AFTER LOGOUT"]);
});

for (const [user, url, destination] of [
  [STUDENT, "/admin/feedback", "/student/overview"],
  [ADMIN, path, "/admin/overview"],
  [TEACHER, path, "/teacher/overview"],
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

test("ADM-02 AC09-10 inbox links to targeted form, read status changes and no sample rows", async ({
  page,
}) => {
  const ctx = await setup(page);
  await page.goto("/student/inbox");
  await expect(
    page.getByRole("heading", { name: "Feedback requests", exact: true }),
  ).toBeVisible();
  await expect(status(page, "Unread requests: 1")).toBeVisible();
  await page.getByRole("link", { name: TITLE, exact: true }).click();
  await expect(firstAnswer(page)).toBeVisible();
  await page.getByRole("link", { name: "Back to inbox", exact: true }).click();
  await expect(status(page, "Unread requests: 0")).toBeVisible();
  expect(ctx.of("GET", "/inbox")).toHaveLength(2);
  await expect(
    page.getByText("Sample inbox message", { exact: false }),
  ).toHaveCount(0);
});

test("ADM-02 inbox empty state uses live contextual copy", async ({ page }) => {
  const ctx = await setup(page);
  ctx.steps.push({
    method: "GET",
    path: "/inbox",
    json: { items: [], next_offset: null, unread_count: 0 },
  });
  await page.goto("/student/inbox");
  await expect(
    page.getByText("No feedback requests yet.", { exact: true }),
  ).toBeVisible();
});

test("ADM-02 AC01-06 admin creates draft with accessible controls and correct save payload", async ({
  page,
}) => {
  const ctx = await setup(page, ADMIN);
  await page.goto("/admin/feedback/new");
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
  expect(ctx.of("GET", "/forms")).toHaveLength(0);
  await expect(page).toHaveURL(new RegExp(`/admin/feedback/${FORM_ID}$`));
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
    await page.goto("/admin/feedback/new");
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
  await page.goto(`/admin/feedback/${FORM_ID}`);
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
  await page.goto(`/admin/feedback/${FORM_ID}`);
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
  await page.goto(`/admin/feedback/${FORM_ID}/responses/${RESPONSE_ID}`);
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

  await page.goto("/admin/feedback");
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
  await expect(page).toHaveURL(new RegExp(`/admin/feedback/${FORM_ID}$`));

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
    `/admin/feedback/${FORM_ID}/responses/${RESPONSE_ID}`,
  );
});

test("ADM-02 admin empty response review distinguishes no submitted responses", async ({
  page,
}) => {
  await setup(page, ADMIN);
  await page.goto(`/admin/feedback/${FORM_ID}/responses`);
  await expect(
    page.getByText("No responses yet.", { exact: true }),
  ).toBeVisible();
});

for (const width of [1365, 390]) {
  test(`ADM-02 responsive resumed draft and completed UI at ${width}px`, async ({
    page,
  }, info) => {
    await page.setViewportSize({ width, height: 900 });
    const ctx = await recipientReady(page);
    await firstAnswer(page).fill("A resumable draft on every screen.");
    await expect(status(page, MSG.saved)).toBeVisible();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    await page.screenshot({
      path: info.outputPath(`draft-${width}.png`),
      fullPage: true,
      animations: "disabled",
    });
    await page
      .getByRole("button", { name: "Submit feedback", exact: true })
      .click();
    await expect(status(page, "Feedback submitted. Thank you.")).toBeVisible();
    await page.screenshot({
      path: info.outputPath(`completed-${width}.png`),
      fullPage: true,
      animations: "disabled",
    });
    expect(ctx.of("POST")).toHaveLength(1);
  });
  test(`ADM-02 responsive admin editor audience and response snapshots at ${width}px`, async ({
    page,
  }, info) => {
    await page.setViewportSize({ width, height: 900 });
    const ctx = await setup(page, ADMIN);
    ctx.form.state = "draft";
    ctx.form.version = 1;
    await page.goto(`/admin/feedback/${FORM_ID}/edit`);
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
    await page.goto(`/admin/feedback/${FORM_ID}`);
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
    await page.goto(`/admin/feedback/${FORM_ID}/responses/${RESPONSE_ID}`);
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
  await page.goto(`/admin/feedback/${FORM_ID}/edit`);
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

// STU-05-06 AC15 supersedes the floating label this test used to pin: the prompt is now one
// visible element above the control. Intent kept: no overlap between prompt and selected text.
test("ADM-02 mobile empty dropdown keeps its label above the selected placeholder", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 900 });
  await recipientReady(page);
  const dropdown = page.getByRole("combobox", {
    name: "4. Pick a topic",
    exact: true,
  });
  const prompt = page.getByText("4. Pick a topic", { exact: true });
  await expect(prompt).toHaveCount(1);
  await expect(dropdown.locator("option").first()).toHaveText(
    "Choose an option",
  );
  await expect(dropdown).toHaveValue("");
  const geometry = await dropdown.evaluate((element, promptText) => {
    const select = element as HTMLSelectElement;
    const promptEl = Array.from(document.querySelectorAll("*")).find(
      (el) => el.children.length === 0 && el.textContent === promptText,
    );
    if (!promptEl) return null;
    const promptRect = promptEl.getBoundingClientRect();
    const selectRect = select.getBoundingClientRect();
    return {
      promptBottom: promptRect.bottom,
      promptRight: promptRect.right,
      viewport: window.innerWidth,
      textTop:
        selectRect.top + Number.parseFloat(getComputedStyle(select).paddingTop),
    };
  }, "4. Pick a topic");
  expect(geometry).not.toBeNull();
  expect(geometry!.promptBottom).toBeLessThanOrEqual(geometry!.textTop + 1);
  expect(geometry!.promptRight).toBeLessThanOrEqual(geometry!.viewport);
});

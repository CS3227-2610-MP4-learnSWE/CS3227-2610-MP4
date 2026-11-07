import { expect, test } from "@playwright/test";
import { logOutWithConfirmation, signInThroughForm } from "./authApi";
import {
  STUDENT,
  TEACHER,
  NEW,
  REPLY,
  FORM_ID,
  RESPONSE_ID,
  SUBJECT,
  BODY,
  MSG,
  setup,
  heading,
  alert,
  fill,
  review,
  uuid,
  samplePreview,
  person,
} from "./adm04Api";

const confirm = (page: import("@playwright/test").Page) =>
  page.getByRole("button", { name: "Confirm send", exact: true });

test("adm04 AC01-05 feedback entry derives recipient, reviews exact text, sends once without private responses", async ({
  page,
}) => {
  const ctx = await setup(page);
  await page.goto(`/admin/feedback/${FORM_ID}/responses/${RESPONSE_ID}`);
  await page
    .getByRole("link", { name: "Respond to feedback", exact: true })
    .click();
  await expect(page).toHaveURL(new RegExp(REPLY + "$"));
  await expect(heading(page, "Respond to feedback")).toBeVisible();
  await expect(
    page.getByText(`Recipient: ${STUDENT.display_name} (student)`, {
      exact: true,
    }),
  ).toBeVisible();
  expect(ctx.of("GET", "/recipient")).toHaveLength(1);
  expect(ctx.of("GET", "/recipients")).toHaveLength(0);
  await review(page);
  expect(ctx.of("POST", "/previews")).toHaveLength(1);
  expect(ctx.of("POST", "/previews")[0].body).toEqual({
    kind: "feedback_response",
    response_id: RESPONSE_ID,
    subject: SUBJECT,
    body: BODY,
  });
  await expect(
    page.getByRole("list", { name: "Recipients", exact: true }),
  ).toContainText(STUDENT.display_name);
  expect(ctx.of("POST", "/send")).toHaveLength(0);
  await confirm(page).click();
  await expect(heading(page, "Message sent")).toBeVisible();
  expect(ctx.of("POST", "/send")).toHaveLength(1);
  await page
    .getByRole("link", { name: "Back to feedback", exact: true })
    .click();
  await expect(page).toHaveURL(new RegExp(`/responses/${RESPONSE_ID}$`));
});

test("adm04 AC06-08 announcement navigation default audience one load review receipt and explicit new message", async ({
  page,
}) => {
  const ctx = await setup(page);
  await page.goto("/admin/overview");
  await page.getByRole("link", { name: "Announcements", exact: true }).click();
  await expect(page).toHaveURL(new RegExp(NEW + "$"));
  await expect(heading(page, "New announcement")).toBeVisible();
  await expect(
    page.getByRole("radio", { name: "Students", exact: true }),
  ).toBeChecked();
  await expect(
    page.getByRole("radio", { name: "All active users", exact: true }),
  ).toBeChecked();
  expect(ctx.of("GET", "/recipients")).toHaveLength(1);
  await review(page);
  await expect(page).toHaveURL(new RegExp("review=" + uuid(1)));
  await expect(page.getByText("Recipients: 1", { exact: true })).toBeVisible();
  await expect(heading(page, "Review message")).toBeFocused();
  expect(ctx.of("GET", uuid(1))).toHaveLength(0);
  await confirm(page).click();
  await expect(heading(page, "Message sent")).toBeFocused();
  await expect(
    page.getByRole("status").filter({ hasText: "Sent to 1 recipient(s)." }),
  ).toBeVisible();
  expect(ctx.of("POST", "/send")[0].body).toEqual({});
  expect(ctx.of("POST", "/send")[0].headers["x-csrf-token"]).toBe(
    ctx.auth.csrf,
  );
  await page
    .getByRole("button", { name: "New announcement", exact: true })
    .click();
  await expect(
    page.getByRole("textbox", { name: "Subject", exact: true }),
  ).toHaveValue("");
  await expect(page).toHaveURL(new RegExp(NEW + "$"));
  expect(ctx.of("POST", "/send")).toHaveLength(1);
});

test("adm04 AC06 selected IDs persist across paging search and review then clear on role change", async ({
  page,
}) => {
  const ctx = await setup(page);
  ctx.recipients = Array.from({ length: 51 }, (_, n) => ({
    id: `opaque-${n}`,
    display_name: `Student ${String(n).padStart(2, "0")}`,
    role: "student",
  }));
  ctx.recipients.push(person(TEACHER));
  await page.goto(NEW);
  await page
    .getByRole("radio", { name: "Selected users", exact: true })
    .check();
  const first = ctx.recipients[0],
    last = ctx.recipients[50];
  await page
    .getByRole("checkbox", {
      name: `${first.display_name} (${first.id})`,
      exact: true,
    })
    .check();
  await page.getByRole("button", { name: "Next page", exact: true }).click();
  await page
    .getByRole("checkbox", {
      name: `${last.display_name} (${last.id})`,
      exact: true,
    })
    .check();
  await page
    .getByRole("textbox", { name: "Search recipients", exact: true })
    .fill("Student 00");
  const firstBox = page.getByRole("checkbox", {
    name: `${first.display_name} (${first.id})`,
    exact: true,
  });
  await expect(firstBox).toBeChecked();
  await review(page);
  const posted = ctx.of("POST", "/previews")[0].body;
  expect((posted.recipient_ids as string[]).sort()).toEqual(
    [first.id, last.id].sort(),
  );
  expect(posted.audience_mode).toBe("selected");
  const list = page.getByRole("list", { name: "Recipients", exact: true });
  await expect(list).toContainText(first.display_name);
  await expect(list).toContainText(last.display_name);
  await page.getByRole("button", { name: "Edit message", exact: true }).click();
  await expect(
    page.getByRole("textbox", { name: "Subject", exact: true }),
  ).toHaveValue(SUBJECT);
  await page.getByRole("radio", { name: "Teachers", exact: true }).check();
  await expect(page.getByText("0 selected", { exact: true })).toBeVisible();
  await expect(
    page.getByRole("checkbox", {
      name: `${TEACHER.display_name} (${TEACHER.id})`,
      exact: true,
    }),
  ).not.toBeChecked();
});

test("adm04 AC13 debounced search makes one request and stale response cannot replace latest role", async ({
  page,
}) => {
  const ctx = await setup(page);
  await page.goto(NEW);
  await expect(heading(page, "New announcement")).toBeVisible();
  expect(ctx.of("GET", "/recipients")).toHaveLength(1);
  await page.clock.install();
  await page
    .getByRole("textbox", { name: "Search recipients", exact: true })
    .fill("Sam");
  await page.clock.fastForward(299);
  expect(ctx.of("GET", "/recipients")).toHaveLength(1);
  ctx.steps.push({ method: "GET", suffix: "/recipients", hold: true });
  await page.clock.fastForward(2);
  await expect.poll(() => ctx.of("GET", "/recipients").length).toBe(2);
  await page.getByRole("radio", { name: "Teachers", exact: true }).check();
  await expect.poll(() => ctx.of("GET", "/recipients").length).toBe(3);
  ctx.release();
  await expect(
    page.getByRole("radio", { name: "Teachers", exact: true }),
  ).toBeChecked();
  expect(ctx.of("GET", "/recipients").at(-1)!.query.get("role")).toBe(
    "teacher",
  );
  expect(ctx.of("POST")).toHaveLength(0);
});

test("adm04 AC12 edit restores fields and replaces query with one new eligibility load", async ({
  page,
}) => {
  const ctx = await setup(page);
  const value = samplePreview();
  value.audience_mode = "selected";
  ctx.previews.set(value.id, value);
  await page.goto(NEW + "?review=" + value.id);
  await expect(heading(page, "Review message")).toBeVisible();
  expect(ctx.of("GET", value.id)).toHaveLength(1);
  expect(ctx.of("GET", "/recipients")).toHaveLength(0);
  await page.getByRole("button", { name: "Edit message", exact: true }).click();
  await expect(page).toHaveURL(new RegExp(NEW + "$"));
  await expect(
    page.getByRole("textbox", { name: "Subject", exact: true }),
  ).toHaveValue(SUBJECT);
  await expect(
    page.getByRole("textbox", { name: "Message", exact: true }),
  ).toHaveValue(BODY);
  await expect(
    page.getByRole("radio", { name: "Selected users", exact: true }),
  ).toBeChecked();
  await expect(
    page.getByRole("checkbox", {
      name: `${STUDENT.display_name} (${STUDENT.id})`,
      exact: true,
    }),
  ).toBeChecked();
  expect(ctx.of("GET", "/recipients")).toHaveLength(1);
  expect(ctx.of("POST")).toHaveLength(0);
});

test("adm04 AC12 reload after lost successful send recovers durable receipt without resending", async ({
  page,
}) => {
  const ctx = await setup(page);
  await page.goto(NEW);
  await review(page);
  ctx.steps.push({ method: "POST", suffix: "/send", commitThenAbort: true });
  await confirm(page).click();
  await expect(alert(page, MSG.network)).toBeVisible();
  expect(ctx.of("POST", "/send")).toHaveLength(1);
  await page.reload();
  await expect(heading(page, "Message sent")).toBeVisible();
  expect(ctx.of("GET", uuid(1))).toHaveLength(1);
  expect(ctx.of("POST", "/send")).toHaveLength(1);
  await page.reload();
  await expect(heading(page, "Message sent")).toBeVisible();
  expect(ctx.of("POST", "/send")).toHaveLength(1);
});

test("adm04 AC12 uncertain send retries exact preview and blocks concurrent clicks", async ({
  page,
}) => {
  const ctx = await setup(page);
  await page.goto(NEW);
  await review(page);
  ctx.steps.push({ method: "POST", suffix: "/send", abort: true });
  await confirm(page).click();
  await expect(alert(page, MSG.network)).toBeVisible();
  ctx.steps.push({ method: "POST", suffix: "/send", hold: true });
  await confirm(page).click();
  await expect(confirm(page)).toBeDisabled();
  await expect(
    page.getByRole("status").filter({ hasText: "Sending message…" }),
  ).toBeVisible();
  expect(ctx.of("POST", "/send")).toHaveLength(2);
  expect(new Set(ctx.of("POST", "/send").map((r) => r.path)).size).toBe(1);
  ctx.release();
  await expect(heading(page, "Message sent")).toBeVisible();
  expect(ctx.of("POST", "/previews")).toHaveLength(1);
});

test("adm04 AC12 browser Back Forward and refresh recover review with no duplicate send or preview", async ({
  page,
}) => {
  const ctx = await setup(page);
  await page.goto("/admin/overview");
  await page.getByRole("link", { name: "Announcements", exact: true }).click();
  await review(page);
  await page.goBack();
  await expect(page).toHaveURL(/\/admin\/overview$/);
  await page.goForward();
  await expect(heading(page, "Review message")).toBeVisible();
  expect(ctx.of("GET", uuid(1))).toHaveLength(1);
  expect(ctx.of("GET", "/recipients")).toHaveLength(1);
  await page.reload();
  await expect(heading(page, "Review message")).toBeVisible();
  expect(ctx.of("GET", uuid(1))).toHaveLength(2);
  expect(ctx.of("POST", "/previews")).toHaveLength(1);
  expect(ctx.of("POST", "/send")).toHaveLength(0);
});

for (const fault of [
  { status: 403, code: "csrf_failed", copy: MSG.csrf },
  { status: 413, code: "REQUEST_TOO_LARGE", copy: MSG.large },
  { status: 422, code: "INVALID_BODY", copy: MSG.body },
  { status: 429, code: "MESSAGING_RATE_LIMITED", copy: MSG.limited },
  { status: 500, code: "MESSAGING_ERROR", copy: MSG.error },
  { status: 503, code: "MESSAGING_UNAVAILABLE", copy: MSG.unavailable },
]) {
  test(`adm04 AC13 preview ${fault.code} keeps text and retries only the failed preview`, async ({
    page,
  }) => {
    const ctx = await setup(page);
    await page.goto(NEW);
    await fill(page);
    ctx.steps.push({ method: "POST", suffix: "/previews", ...fault });
    await page
      .getByRole("button", { name: "Review message", exact: true })
      .click();
    await expect(alert(page, fault.copy)).toBeVisible();
    await expect(
      page.getByRole("textbox", { name: "Subject", exact: true }),
    ).toHaveValue(SUBJECT);
    await expect(
      page.getByRole("textbox", { name: "Message", exact: true }),
    ).toHaveValue(BODY);
    expect(ctx.of("POST", "/previews")).toHaveLength(1);
    expect(ctx.of("GET", "/recipients")).toHaveLength(1);
    await page
      .getByRole("button", { name: "Review message", exact: true })
      .click();
    await expect(heading(page, "Review message")).toBeVisible();
    expect(ctx.of("POST", "/previews")).toHaveLength(2);
  });
}
for (const fault of [
  { status: 403, code: "csrf_failed", copy: MSG.csrf },
  { status: 429, code: "MESSAGING_RATE_LIMITED", copy: MSG.limited },
  { status: 500, code: "MESSAGING_ERROR", copy: MSG.error },
  { status: 503, code: "MESSAGING_UNAVAILABLE", copy: MSG.unavailable },
]) {
  test(`adm04 AC12 send ${fault.code} retains immutable review for safe retry`, async ({
    page,
  }) => {
    const ctx = await setup(page);
    await page.goto(NEW);
    await review(page);
    ctx.steps.push({ method: "POST", suffix: "/send", ...fault });
    await confirm(page).click();
    await expect(alert(page, fault.copy)).toBeVisible();
    await expect(heading(page, "Review message")).toBeVisible();
    expect(ctx.of("POST", "/send")).toHaveLength(1);
    await confirm(page).click();
    await expect(heading(page, "Message sent")).toBeVisible();
    expect(ctx.of("POST", "/send")).toHaveLength(2);
    expect(ctx.of("POST", "/previews")).toHaveLength(1);
  });
}
for (const fault of [
  { status: 409, code: "AUDIENCE_CHANGED", copy: MSG.changed },
  { status: 409, code: "PREVIEW_EXPIRED", copy: MSG.expired },
  { status: 404, code: "PREVIEW_UNAVAILABLE", copy: MSG.preview },
]) {
  test(`adm04 AC12 in-memory ${fault.code} invalidates review and retains populated composer`, async ({
    page,
  }) => {
    const ctx = await setup(page);
    await page.goto(NEW);
    await review(page);
    ctx.steps.push({ method: "POST", suffix: "/send", ...fault });
    await confirm(page).click();
    await expect(alert(page, fault.copy)).toBeVisible();
    await expect(
      page.getByRole("textbox", { name: "Subject", exact: true }),
    ).toHaveValue(SUBJECT);
    await expect(
      page.getByRole("textbox", { name: "Message", exact: true }),
    ).toHaveValue(BODY);
    await expect(page).toHaveURL(new RegExp(NEW + "$"));
    await expect(confirm(page)).toHaveCount(0);
    expect(ctx.of("GET", "/recipients")).toHaveLength(2);
  });
}
for (const fault of [
  { status: 409, code: "PREVIEW_EXPIRED", copy: MSG.expired },
  { status: 404, code: "PREVIEW_UNAVAILABLE", copy: MSG.preview },
]) {
  test(`adm04 AC12 recovered ${fault.code} offers explicit fresh composer without sending`, async ({
    page,
  }) => {
    const ctx = await setup(page);
    ctx.steps.push({ method: "GET", suffix: uuid(1), ...fault });
    await page.goto(NEW + "?review=" + uuid(1));
    await expect(alert(page, fault.copy)).toBeVisible();
    expect(ctx.of("GET", "/recipients")).toHaveLength(0);
    await page
      .getByRole("button", { name: "Start a new message", exact: true })
      .click();
    await expect(
      page.getByRole("textbox", { name: "Subject", exact: true }),
    ).toHaveValue("");
    expect(ctx.of("GET", "/recipients")).toHaveLength(1);
    expect(ctx.of("POST")).toHaveLength(0);
  });
}
for (const field of ["Subject", "Message"]) {
  test(`adm04 AC13 empty ${field} is exact local validation with focus and no POST`, async ({
    page,
  }) => {
    const ctx = await setup(page);
    await page.goto(NEW);
    await fill(
      page,
      field === "Subject" ? "" : SUBJECT,
      field === "Message" ? "" : BODY,
    );
    await page
      .getByRole("button", { name: "Review message", exact: true })
      .click();
    await expect(
      alert(page, field === "Subject" ? MSG.subject : MSG.body),
    ).toBeVisible();
    await expect(
      page.getByRole("textbox", { name: field, exact: true }),
    ).toBeFocused();
    expect(ctx.of("POST")).toHaveLength(0);
  });
}

test("adm04 AC13 zero selected recipients prevented and empty eligible state specific", async ({
  page,
}) => {
  const ctx = await setup(page);
  ctx.recipients = [];
  await page.goto(NEW);
  await expect(
    page.getByText("No eligible recipients.", { exact: true }),
  ).toBeVisible();
  await page
    .getByRole("radio", { name: "Selected users", exact: true })
    .check();
  await fill(page);
  await page
    .getByRole("button", { name: "Review message", exact: true })
    .click();
  await expect(alert(page, MSG.recipients)).toBeVisible();
  expect(ctx.of("POST")).toHaveLength(0);
});

test("adm04 AC13 network recipient failure has exact loading copy and one explicit retry", async ({
  page,
}) => {
  const ctx = await setup(page);
  ctx.steps.push({
    method: "GET",
    suffix: "/recipients",
    hold: true,
    abort: true,
  });
  await page.goto(NEW);
  await expect(
    page.getByRole("status").filter({ hasText: "Loading recipients…" }),
  ).toBeVisible();
  ctx.release();
  await expect(alert(page, MSG.network)).toBeVisible();
  expect(ctx.of("GET", "/recipients")).toHaveLength(1);
  await page.getByRole("button", { name: "Retry", exact: true }).click();
  await expect(heading(page, "New announcement")).toBeVisible();
  await expect.poll(() => ctx.of("GET", "/recipients").length).toBe(2);
});

test("adm04 AC13 fifteen-second send timeout preserves exact same preview and no automatic retry", async ({
  page,
}) => {
  const ctx = await setup(page);
  await page.goto(NEW);
  await review(page);
  const now = new Date();
  await page.clock.install({ time: now });
  await page.clock.pauseAt(new Date(now.getTime() + 1000));
  ctx.steps.push({ method: "POST", suffix: "/send", hold: true });
  await confirm(page).click();
  await expect(confirm(page)).toBeDisabled();
  await page.clock.fastForward(14999);
  await expect(alert(page, MSG.timeout)).toHaveCount(0);
  await page.clock.fastForward(2);
  await expect(alert(page, MSG.timeout)).toBeVisible();
  expect(ctx.of("POST", "/send")).toHaveLength(1);
  await expect(heading(page, "Review message")).toBeVisible();
  ctx.release();
});
for (const who of [STUDENT, TEACHER, null]) {
  test(`adm04 AC11 wrong role ${who?.role ?? "anonymous"} has no messaging requests`, async ({
    page,
  }) => {
    const ctx = await setup(page, who);
    await page.goto(NEW);
    await expect(page).toHaveURL(
      who ? new RegExp("/" + who.role + "/") : /\/login/,
    );
    expect(ctx.requests).toHaveLength(0);
    await expect(
      page.getByRole("textbox", { name: "Message", exact: true }),
    ).toHaveCount(0);
  });
}

test("adm04 AC11 expiry from send clears private text and stale review before login", async ({
  page,
}) => {
  const ctx = await setup(page);
  await page.goto(NEW);
  await review(page);
  ctx.auth.expire();
  ctx.steps.push({
    method: "POST",
    suffix: "/send",
    status: 401,
    code: "unauthenticated",
  });
  await confirm(page).click();
  await expect(page).toHaveURL(/\/login/);
  await expect(page.getByText(BODY, { exact: true })).toHaveCount(0);
  expect(ctx.of("POST", "/send")).toHaveLength(1);
});

test("adm04 AC11 logout and another account never restore previous admin draft", async ({
  page,
}) => {
  const ctx = await setup(page);
  await page.goto(NEW);
  await fill(page, "PRIVATE ACCOUNT DRAFT", "PRIVATE UNSENT BODY");
  await logOutWithConfirmation(page);
  await expect(page).toHaveURL(/\/login/);
  await signInThroughForm(page, TEACHER.email!);
  await expect(page).toHaveURL(/\/teacher\//);
  await expect(
    page.getByText("PRIVATE UNSENT BODY", { exact: true }),
  ).toHaveCount(0);
  expect(ctx.of("POST")).toHaveLength(0);
});

test("adm04 AC13 mobile long text and malicious HTML remain literal and controls stay usable", async ({
  page,
}) => {
  await page.setViewportSize({ width: 320, height: 740 });
  await page.emulateMedia({ reducedMotion: "reduce" });
  await setup(page);
  await page.goto(NEW);
  const subject = "A".repeat(120),
    body =
      '<img src=x onerror="window.ADM04_XSS=1">\n' + "unbroken".repeat(500);
  await fill(page, subject, body);
  await page
    .getByRole("button", { name: "Review message", exact: true })
    .click();
  await expect(heading(page, "Review message")).toBeVisible();
  await expect(page.getByText(body, { exact: true })).toBeVisible();
  expect(
    await page.evaluate(() =>
      Object.prototype.hasOwnProperty.call(window, "ADM04_XSS"),
    ),
  ).toBe(false);
  expect(
    await page
      .locator("main")
      .evaluate((el) => el.scrollWidth <= el.clientWidth + 1),
  ).toBe(true);
  await confirm(page).scrollIntoViewIfNeeded();
  await expect(confirm(page)).toBeInViewport();
  await confirm(page).click();
  await expect(heading(page, "Message sent")).toBeVisible();
});

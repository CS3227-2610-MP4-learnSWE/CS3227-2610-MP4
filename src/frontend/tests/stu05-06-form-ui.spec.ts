import { expect, test, type Locator, type Page } from "@playwright/test";
import {
  FORM_ID,
  TITLE,
  alert,
  choose,
  form,
  setup,
  status,
  type Question,
} from "./adm02Api";

/**
 * STU-05-06 AC15-AC18: student feedback form presentation. Browser tests only; the ADM-02
 * mock supplies the form, the draft and the 422 `invalid_feedback_answers` submit failure.
 * Names and shapes come from workflow/specs/STU-05-06/plan.md ("Student form presentation
 * contract"). Not covered: pixel-level colour contrast (only red-dominant borders are
 * asserted) and the screenshots the plan lists as verifier evidence.
 */
const path = `/student/feedback/${FORM_ID}`;
const REQUIRED = "This question is required.";
const V10 =
  "Answer every required question and check that all answers match their question type.";
const PRIVACY =
  "Once submitted, your name and feedback are visible to administrators. Your unfinished draft is private.";

const oid = (n: number) =>
  `c2000000-0000-4000-8000-${String(n).padStart(12, "0")}`;
function q(
  n: number,
  type: string,
  prompt: string,
  required: boolean,
  scale: Question["scale"] = null,
): Question {
  const hasOptions = ["multiple_choice", "dropdown", "checkbox"].includes(type);
  return {
    id: `d2000000-0000-4000-8000-${String(n).padStart(12, "0")}`,
    type,
    prompt,
    required,
    options: hasOptions
      ? [
          { id: oid(n * 10), label: "First option" },
          { id: oid(n * 10 + 1), label: "Second option" },
        ]
      : [],
    scale,
  };
}
const SCALE = { min: 1, max: 5, min_label: "Low", max_label: "High" };

/** Seven required-or-optional questions in a fixed order, used by the AC17 tests. */
const markerQuestions = () => [
  q(1, "short_answer", "Nickname", false),
  q(2, "short_answer", "Main point", true),
  q(3, "paragraph", "Details", true),
  q(4, "multiple_choice", "Pick one", true),
  q(5, "dropdown", "Pick topic", true),
  q(6, "checkbox", "Tools", true),
  q(7, "linear_scale", "Rate", true, SCALE),
  q(8, "short_answer", "Extra", false),
];

async function open(page: Page, qs?: Question[]) {
  const ctx = await setup(page);
  if (qs) ctx.form = { ...ctx.form, questions: qs };
  await page.goto(path);
  await expect(
    page.getByRole("button", { name: "Submit feedback", exact: true }),
  ).toBeVisible();
  return ctx;
}
const submit = (page: Page) =>
  page.getByRole("button", { name: "Submit feedback", exact: true }).click();
const box = async (l: Locator) => {
  const b = await l.first().boundingBox();
  if (!b) throw new Error("element has no bounding box");
  return b;
};
const noOverflow = (page: Page) =>
  page.evaluate(
    () =>
      document.documentElement.scrollWidth <= window.innerWidth &&
      document.body.scrollWidth <= window.innerWidth,
  );
const failSubmit = (ctx: Awaited<ReturnType<typeof open>>) =>
  ctx.steps.push({
    method: "POST",
    path: "/responses",
    status: 422,
    code: "invalid_feedback_answers",
  });
/** Controls of the AC17 question set, by accessible role and name. */
const c = (page: Page) => ({
  main: page.getByRole("textbox", { name: "2. Main point", exact: true }),
  details: page.getByRole("textbox", { name: "3. Details", exact: true }),
  pick: page.getByRole("radiogroup", { name: "4. Pick one", exact: true }),
  topic: page.getByRole("combobox", { name: "5. Pick topic", exact: true }),
  tools: page.getByRole("group", { name: /^6\. Tools/ }),
  rate: page.getByRole("radiogroup", { name: "7. Rate", exact: true }),
});
/** Marked = aria-invalid="true" and aria-describedby resolving to the inline text; red = a 2px red-dominant border near it. */
const marking = (l: Locator) =>
  l.evaluateAll((els, text) => {
    for (const el of els) {
      if (el.getAttribute("aria-invalid") !== "true") continue;
      const ids = (el.getAttribute("aria-describedby") ?? "")
        .split(/\s+/)
        .filter(Boolean);
      const msg = ids
        .map((i) => document.getElementById(i))
        .find((e) => e && e.textContent?.trim() === text);
      if (!msg) continue;
      let scope: Element | null = msg.parentElement;
      while (scope && !scope.contains(el)) scope = scope.parentElement;
      const nodes = scope
        ? [scope, ...Array.from(scope.querySelectorAll("*"))]
        : [];
      const red = nodes.some((n) => {
        const s = getComputedStyle(n);
        if (!(parseFloat(s.borderTopWidth) >= 2)) return false;
        const [r, g, b] = (s.borderTopColor.match(/[\d.]+/g) ?? []).map(Number);
        return r >= 150 && r - Math.max(g, b) >= 50;
      });
      return { marked: true, red };
    }
    return { marked: false, red: false };
  }, REQUIRED);
const isMarked = async (l: Locator) => (await marking(l)).marked;

// ---------------------------------------------------------------- AC15

test("stu05 AC15 stu05_form_prompt_shown_once: every prompt appears once and keeps its accessible name", async ({
  page,
}) => {
  const ctx = await open(page);
  const prompts = [
    "1. One sentence",
    "2. Your experience",
    "3. Choose one",
    "4. Pick a topic",
    "5. Useful tools",
    "6. Rate usefulness",
  ];
  for (const p of prompts) {
    await expect(page.getByText(p, { exact: true }), p).toHaveCount(1);
    await expect(
      page.locator("label", { hasText: p }),
      `label ${p}`,
    ).toHaveCount(0);
  }
  const placeholders = await page.evaluate(() =>
    Array.from(document.querySelectorAll("[placeholder]")).map((e) =>
      e.getAttribute("placeholder"),
    ),
  );
  for (const p of prompts) expect(placeholders).not.toContain(p);
  // Required and Optional are plain tags: one Required, five Optional here.
  await expect(page.getByText("Required", { exact: true })).toHaveCount(1);
  await expect(page.getByText("Optional", { exact: true })).toHaveCount(5);
  // Accessible names unchanged.
  await expect(
    page.getByRole("textbox", { name: prompts[0], exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("textbox", { name: prompts[1], exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("group", { name: /3\. Choose one/ }).first(),
  ).toBeVisible();
  await expect(
    page.getByRole("radiogroup", { name: prompts[2], exact: true }),
  ).toBeVisible();
  const dropdown = page.getByRole("combobox", {
    name: prompts[3],
    exact: true,
  });
  await expect(dropdown).toBeVisible();
  await expect(dropdown.locator("option").first()).toHaveText(
    "Choose an option",
  );
  await expect(
    page.getByRole("group", { name: /5\. Useful tools/ }).first(),
  ).toBeVisible();
  await expect(
    page.getByRole("radiogroup", { name: prompts[5], exact: true }),
  ).toBeVisible();
  // Page outline is unchanged: the form title is the only heading.
  await expect(
    page.getByRole("heading", { level: 1, name: TITLE }),
  ).toBeVisible();
  await expect(page.getByRole("heading", { level: 2 })).toHaveCount(0);
  await expect(page.getByRole("heading", { level: 3 })).toHaveCount(0);
  // Presentation only: no extra request.
  expect(ctx.of("GET", FORM_ID)).toHaveLength(1);
  expect(ctx.of("PUT")).toHaveLength(0);
});

for (const theme of ["light", "dark"] as const) {
  test(`stu05 AC15 prompt is prominent (ink colour, 16-18px, bold) in the ${theme} theme`, async ({
    page,
  }) => {
    await page.emulateMedia({ colorScheme: theme });
    await open(page);
    const style = await page
      .getByText("1. One sentence", { exact: true })
      .first()
      .evaluate((el) => {
        const probe = document.createElement("span");
        probe.style.color = "var(--ink)";
        document.body.append(probe);
        const ink = getComputedStyle(probe).color;
        probe.remove();
        const s = getComputedStyle(el);
        return {
          ink,
          color: s.color,
          size: parseFloat(s.fontSize),
          weight: Number(s.fontWeight),
        };
      });
    expect(style.color).toBe(style.ink);
    expect(style.size).toBeGreaterThanOrEqual(16);
    expect(style.size).toBeLessThanOrEqual(18);
    expect(style.weight).toBeGreaterThanOrEqual(600);
  });
}

test("stu05 AC15 inputs keep a visible outlined edge and a changed focus treatment", async ({
  page,
}) => {
  await open(page);
  const input = page.getByRole("textbox", {
    name: "1. One sentence",
    exact: true,
  });
  const edge = () =>
    input.evaluate((el) => {
      const root = el.closest(".MuiOutlinedInput-root");
      const outline = root?.querySelector(".MuiOutlinedInput-notchedOutline");
      if (!outline) return null;
      const s = getComputedStyle(outline);
      return `${s.borderTopWidth} ${s.borderTopStyle} ${s.borderTopColor}`;
    });
  const rest = await edge();
  expect(rest, "outlined input edge element").not.toBeNull();
  expect(parseFloat(rest as string)).toBeGreaterThan(0);
  await input.focus();
  await expect.poll(edge).not.toBe(rest);
});

test("stu05 AC15 tag sits right of the prompt on desktop", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 900 });
  await open(page);
  const prompt = await box(page.getByText("1. One sentence", { exact: true }));
  const tag = await box(page.getByText("Required", { exact: true }));
  const control = await box(
    page.getByRole("textbox", { name: "1. One sentence", exact: true }),
  );
  expect(tag.x).toBeGreaterThanOrEqual(prompt.x + prompt.width);
  expect(
    Math.abs(tag.y + tag.height / 2 - (prompt.y + prompt.height / 2)),
  ).toBeLessThan(20);
  expect(tag.x + tag.width).toBeGreaterThan(control.x + control.width - 48);
  expect(tag.y + tag.height).toBeLessThanOrEqual(control.y + 2);
});

test("stu05 AC15 tag stacks under the prompt at 390px", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await open(page);
  const prompt = await box(page.getByText("1. One sentence", { exact: true }));
  const tag = await box(page.getByText("Required", { exact: true }));
  expect(tag.y).toBeGreaterThanOrEqual(prompt.y + prompt.height - 2);
  expect(await noOverflow(page)).toBe(true);
});

test("stu05 AC15 a 300-character unbroken prompt wraps at 390px and still appears once", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  const long = "x".repeat(300);
  await open(page, [q(1, "short_answer", long, true)]);
  await expect(page.getByText(`1. ${long}`, { exact: true })).toHaveCount(1);
  expect(await noOverflow(page)).toBe(true);
});

// ---------------------------------------------------------------- AC16

const scaleQs = (min: string, max: string) => [
  q(1, "linear_scale", "Rate usefulness", false, {
    min: 1,
    max: 5,
    min_label: min,
    max_label: max,
  }),
];
const group = (page: Page) =>
  page.getByRole("radiogroup", { name: "1. Rate usefulness", exact: true });

test("stu05 AC16 stu05_linear_scale_endpoints: minimum label left, maximum label right of the numbers", async ({
  page,
}) => {
  await page.setViewportSize({ width: 1280, height: 900 });
  await open(page, scaleQs("Low", "High"));
  const radios = group(page).getByRole("radio");
  await expect(radios).toHaveCount(5);
  for (const n of ["1", "2", "3", "4", "5"])
    await expect(
      group(page).getByRole("radio", { name: n, exact: true }),
    ).toHaveCount(1);
  // Labels are outside the radio group, so radio names stay the decimal values.
  await expect(group(page).getByText("Low")).toHaveCount(0);
  const low = await box(page.getByText("Low", { exact: true }));
  const high = await box(page.getByText("High", { exact: true }));
  const first = await box(radios.first());
  const last = await box(radios.last());
  expect(low.x + low.width).toBeLessThanOrEqual(first.x + 2);
  expect(high.x).toBeGreaterThanOrEqual(last.x + last.width - 2);
  const mid = (b: { y: number; height: number }) => b.y + b.height / 2;
  expect(Math.abs(mid(low) - mid(first))).toBeLessThan(30);
  expect(Math.abs(mid(high) - mid(last))).toBeLessThan(30);
});

for (const [name, min, max, absent] of [
  ["missing minimum label", "", "High", "Low"],
  ["missing maximum label", "Low", "", "High"],
] as const) {
  test(`stu05 AC16 ${name} leaves that end empty without a dash or placeholder`, async ({
    page,
  }) => {
    await page.setViewportSize({ width: 1280, height: 900 });
    await open(page, scaleQs(min, max));
    const card = page.getByRole("group", {
      name: "1. Rate usefulness",
      exact: true,
    });
    const shown = min || max;
    await expect(page.getByText(shown, { exact: true })).toHaveCount(1);
    await expect(page.getByText(absent, { exact: true })).toHaveCount(0);
    const text = (await card.first().innerText()).replace(/\s+/g, " ");
    for (const junk of ["-", "–", "—", "N/A", "undefined", "null"])
      expect(text, `junk ${junk}`).not.toContain(junk);
    const radios = group(page).getByRole("radio");
    const label = await box(page.getByText(shown, { exact: true }));
    const first = await box(radios.first());
    const last = await box(radios.last());
    if (min) expect(label.x + label.width).toBeLessThanOrEqual(first.x + 2);
    else expect(label.x).toBeGreaterThanOrEqual(last.x + last.width - 2);
  });
}

test("stu05 AC16 at 390px the labels keep minimum left and maximum right", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await open(page, scaleQs("Low", "High"));
  const radios = group(page).getByRole("radio");
  const g = await box(group(page));
  const low = await box(page.getByText("Low", { exact: true }));
  const high = await box(page.getByText("High", { exact: true }));
  const first = await box(radios.first());
  const mid = g.x + g.width / 2;
  expect(low.x + low.width / 2).toBeLessThan(mid);
  expect(high.x + high.width / 2).toBeGreaterThan(mid);
  // Labels sit on the row or below it, never above it.
  expect(low.y + low.height).toBeGreaterThan(first.y);
  expect(high.y + high.height).toBeGreaterThan(first.y);
  expect(await noOverflow(page)).toBe(true);
});

// ---------------------------------------------------------------- AC17

test("stu05 AC17 stu05_required_markers_after_failed_submit: blank required questions are marked, then clear and return with the answers", async ({
  page,
}) => {
  const ctx = await open(page, markerQuestions());
  const k = c(page);
  const message = page.getByText(REQUIRED, { exact: true });
  // Nothing is marked before the first failed submit or while typing.
  await expect(message).toHaveCount(0);
  await k.main.fill("   ");
  await page
    .getByRole("textbox", { name: "1. Nickname", exact: true })
    .fill("Sam");
  await expect(
    status(page, "Draft saved. You can return to finish later."),
  ).toBeVisible();
  await expect(message).toHaveCount(0);
  await expect(page.locator('[aria-invalid="true"]')).toHaveCount(0);
  // One failed submit: whitespace-only text, empty paragraph, radio, select, checkbox and scale.
  failSubmit(ctx);
  await submit(page);
  await expect(alert(page, V10)).toBeVisible();
  await expect(message).toHaveCount(6);
  for (const [name, control] of Object.entries(k)) {
    const m = await marking(control);
    expect(m.marked, `${name} marked`).toBe(true);
    expect(m.red, `${name} red border`).toBe(true);
  }
  // Optional questions (blank or answered) are not marked.
  await expect(
    page.getByRole("textbox", { name: "1. Nickname", exact: true }),
  ).not.toHaveAttribute("aria-invalid", "true");
  await expect(
    page.getByRole("textbox", { name: "8. Extra", exact: true }),
  ).not.toHaveAttribute("aria-invalid", "true");
  // The failed submit is the one POST and nothing else was requested.
  expect(ctx.of("POST", "/responses")).toHaveLength(1);
  expect(ctx.of("GET", FORM_ID)).toHaveLength(1);
  // Answering clears only that marker.
  await k.main.fill("A point");
  await expect(message).toHaveCount(5);
  expect(await isMarked(k.main)).toBe(false);
  expect(await isMarked(k.details)).toBe(true);
  await k.details.fill("More");
  await expect(message).toHaveCount(4);
  await k.pick
    .getByRole("radio", { name: "First option", exact: true })
    .check();
  await expect(message).toHaveCount(3);
  await choose(page, "5. Pick topic", "First option");
  await expect(message).toHaveCount(2);
  await k.tools
    .getByRole("checkbox", { name: "First option", exact: true })
    .first()
    .check();
  await expect(message).toHaveCount(1);
  await k.rate.getByRole("radio", { name: "3", exact: true }).check();
  await expect(message).toHaveCount(0);
  await expect(page.locator('[aria-invalid="true"]')).toHaveCount(0);
  // The alert's lifetime after an autosave is existing ADM-02 behaviour (the draft save clears
  // the page error), so it is asserted right after the failed submit only, not here.
  // Emptying an answer again brings its marker back.
  await k.main.fill("");
  await expect(message).toHaveCount(1);
  expect(await isMarked(k.main)).toBe(true);
  await k.main.fill("   ");
  await expect(message).toHaveCount(1);
  await k.main.fill("Again");
  await expect(message).toHaveCount(0);
  await k.tools
    .getByRole("checkbox", { name: "First option", exact: true })
    .first()
    .uncheck();
  await expect(message).toHaveCount(1);
  expect(await isMarked(k.tools)).toBe(true);
  await k.tools
    .getByRole("checkbox", { name: "Second option", exact: true })
    .first()
    .check();
  await expect(message).toHaveCount(0);
  // A successful submit leaves no marker and sends exactly one more POST.
  await submit(page);
  await expect(status(page, "Feedback submitted. Thank you.")).toBeVisible();
  await expect(message).toHaveCount(0);
  expect(ctx.of("POST", "/responses")).toHaveLength(2);
  expect(ctx.of("GET", FORM_ID)).toHaveLength(1);
});

test("stu05 AC17 focus goes to the first marked control", async ({ page }) => {
  const ctx = await open(page, markerQuestions());
  failSubmit(ctx);
  await submit(page);
  await expect(page.getByText(REQUIRED, { exact: true })).toHaveCount(6);
  // Optional "Nickname" is the earlier text question and is skipped.
  await expect(c(page).main).toBeFocused();
});

test("stu05 AC17 focus lands on the first blank required control even when earlier text questions exist", async ({
  page,
}) => {
  const ctx = await open(page, [
    q(1, "short_answer", "Nickname", false),
    q(2, "paragraph", "Notes", false),
    q(3, "multiple_choice", "Pick one", true),
    q(4, "dropdown", "Pick topic", true),
  ]);
  await page
    .getByRole("textbox", { name: "1. Nickname", exact: true })
    .fill("Sam");
  await page
    .getByRole("textbox", { name: "2. Notes", exact: true })
    .fill("Hello");
  failSubmit(ctx);
  await submit(page);
  await expect(page.getByText(REQUIRED, { exact: true })).toHaveCount(2);
  await expect(
    page
      .getByRole("radiogroup", { name: "3. Pick one", exact: true })
      .getByRole("radio")
      .first(),
  ).toBeFocused();
});

test("stu05 AC17 a type-mismatch rejection with no blank required question shows only the page alert", async ({
  page,
}) => {
  const ctx = await open(page, markerQuestions());
  const k = c(page);
  await k.main.fill("A point");
  await k.details.fill("More");
  await k.pick
    .getByRole("radio", { name: "First option", exact: true })
    .check();
  await choose(page, "5. Pick topic", "First option");
  await k.tools
    .getByRole("checkbox", { name: "First option", exact: true })
    .first()
    .check();
  await k.rate.getByRole("radio", { name: "3", exact: true }).check();
  failSubmit(ctx);
  await submit(page);
  await expect(alert(page, V10)).toBeVisible();
  await expect(page.getByText(REQUIRED, { exact: true })).toHaveCount(0);
  await expect(page.locator('[aria-invalid="true"]')).toHaveCount(0);
  expect(ctx.of("POST", "/responses")).toHaveLength(1);
});

test("stu05 AC17 a different submit failure (service unavailable) marks nothing", async ({
  page,
}) => {
  const ctx = await open(page, markerQuestions());
  ctx.steps.push({
    method: "POST",
    path: "/responses",
    status: 503,
    code: "feedback_unavailable",
  });
  await submit(page);
  await expect(page.getByRole("alert").first()).toBeVisible();
  expect(ctx.of("POST", "/responses")).toHaveLength(1);
  await expect(page.getByText(REQUIRED, { exact: true })).toHaveCount(0);
  await expect(page.locator('[aria-invalid="true"]')).toHaveCount(0);
});

for (const theme of ["light", "dark"] as const) {
  test(`stu05 AC17 marked controls have a red 2px border in the ${theme} theme`, async ({
    page,
  }) => {
    await page.emulateMedia({ colorScheme: theme });
    const ctx = await open(page, markerQuestions());
    failSubmit(ctx);
    await submit(page);
    await expect(page.getByText(REQUIRED, { exact: true })).toHaveCount(6);
    for (const control of Object.values(c(page)))
      expect((await marking(control)).red).toBe(true);
  });
}

// ---------------------------------------------------------------- AC18

type PanelState = "closed" | "already completed" | "just submitted";
const COMPLETED_COPY: Record<PanelState, string> = {
  closed: "This form is closed.",
  "already completed": "You have already submitted feedback.",
  "just submitted": "Feedback submitted. Thank you.",
};
async function openPanel(page: Page, state: PanelState) {
  if (state === "just submitted") {
    await open(page);
    await page
      .getByRole("textbox", { name: "1. One sentence", exact: true })
      .fill("Final answer");
    await submit(page);
  } else {
    const ctx = await setup(page);
    if (state === "closed") ctx.form = form("closed");
    else ctx.submitted = true;
    await page.goto(path);
  }
  const text = COMPLETED_COPY[state];
  await expect(status(page, text).first()).toBeVisible();
  if (state !== "closed")
    await expect(status(page, "Completed").first()).toBeVisible();
  return text;
}

for (const state of ["closed", "already completed", "just submitted"] as const)
  for (const theme of ["light", "dark"] as const)
    for (const [width, lo, hi] of [
      [1280, 24, 28],
      [390, 16, 20],
    ] as const)
      test(`stu06 AC18 stu06_completed_closed_layout ${state} panel is padded and left-aligned (${theme}, ${width}px)`, async ({
        page,
      }) => {
        await page.setViewportSize({ width, height: 900 });
        await page.emulateMedia({ colorScheme: theme });
        const text = await openPanel(page, state);
        const back = page.getByRole("link", {
          name: "Back to inbox",
          exact: true,
        });
        await expect(back).toBeVisible();
        await expect(
          page.getByRole("button", { name: "Submit feedback", exact: true }),
        ).toHaveCount(0);
        // Roles unchanged: status text and a link.
        await expect(status(page, text)).toBeVisible();
        // Standard panel padding.
        const panel = page.locator(".feedback-form").filter({ has: back });
        await expect(
          panel,
          "a .feedback-form panel holds the link",
        ).toHaveCount(1);
        const pad = await panel.evaluate((el) => {
          const s = getComputedStyle(el);
          return [
            s.paddingTop,
            s.paddingRight,
            s.paddingBottom,
            s.paddingLeft,
          ].map(parseFloat);
        });
        for (const p of pad) {
          expect(p).toBeGreaterThanOrEqual(lo);
          expect(p).toBeLessThanOrEqual(hi);
        }
        // Back to inbox is left-aligned with the text above it.
        const left = (await box(back)).x;
        const statusText = status(page, text);
        expect(Math.abs((await box(statusText)).x - left)).toBeLessThanOrEqual(
          2,
        );
        const privacy = page.getByText(PRIVACY, { exact: true });
        if (state !== "closed") await expect(privacy).toHaveCount(1);
        if (await privacy.count())
          expect(Math.abs((await box(privacy)).x - left)).toBeLessThanOrEqual(
            2,
          );
        // Even vertical spacing between privacy sentence, status block and link.
        const parts = [
          privacy,
          page.getByRole("status").filter({ hasText: text }),
          back,
        ];
        const boxes: { y: number; height: number }[] = [];
        for (const part of parts)
          if (await part.count()) boxes.push(await box(part));
        boxes.sort((a, b) => a.y - b.y);
        const gaps = boxes
          .slice(1)
          .map((b, i) => b.y - (boxes[i].y + boxes[i].height));
        for (const gap of gaps) {
          expect(gap).toBeGreaterThanOrEqual(8);
          expect(gap).toBeLessThanOrEqual(32);
        }
        if (gaps.length > 1)
          expect(Math.abs(gaps[0] - gaps[1])).toBeLessThanOrEqual(10);
        expect(await noOverflow(page)).toBe(true);
      });

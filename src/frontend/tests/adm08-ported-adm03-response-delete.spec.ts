// ADM-08 phase 5 port of adm03-response-delete.spec.ts onto hub paths; assertions unchanged (see workflow/specs/ADM-08/phase5-test-mapping.md).
import { expect, test, type Page } from "@playwright/test";
import { ADMIN } from "./authApi";
import { FORM_ID, RESPONSE_ID, ROOT, TITLE, setup } from "./adm08-ported-adm02Api";

// AC48: the Delete response button and dialog on the ADM-02 response detail view.
const DETAIL = `/admin/feedback-hub/responses/${FORM_ID}/${RESPONSE_ID}`;
const NOT_FOUND =
  "This response was not found. It may already have been deleted, or it does not belong to this form.";
const DONE =
  "Response deleted. The form, the respondent's account and stored analyses were not changed. The respondent can submit again only if the form is open.";
const NETWORK =
  "Could not reach the server while deleting the response. It was not confirmed as deleted. Press Delete permanently to try again.";
const FORBIDDEN =
  "You do not have permission to delete feedback responses. Only admin accounts can.";
const INTERNAL =
  "An unexpected server error occurred while deleting the response. Nothing was confirmed as deleted. Reference abc123 identifies it in the server logs.";

type Step = {
  status?: number;
  code?: string;
  message?: string;
  abort?: boolean;
  hold?: boolean;
};

async function open(page: Page, steps: Step[] = []) {
  const ctx = await setup(page, ADMIN);
  ctx.submitted = true;
  const deletes: string[] = [];
  const waiting: (() => void)[] = [];
  await page.route(
    (url) =>
      url.pathname === `${ROOT}/forms/${FORM_ID}/responses/${RESPONSE_ID}`,
    async (route) => {
      if (route.request().method() !== "DELETE") return route.fallback();
      deletes.push(route.request().url());
      const step = steps.shift();
      if (step?.hold) await new Promise<void>((r) => waiting.push(r));
      if (step?.abort) return route.abort("connectionrefused");
      if (step?.status)
        return route.fulfill({
          status: step.status,
          json: { detail: { code: step.code, message: step.message ?? "x" } },
        });
      ctx.submitted = false;
      return route.fulfill({ status: 204 });
    },
  );
  await page.goto(DETAIL);
  await expect(
    page.getByRole("heading", { name: "Feedback response", exact: true }),
  ).toBeVisible();
  return { ctx, deletes, release: () => waiting.splice(0).forEach((r) => r()) };
}
const trigger = (page: Page) =>
  page.getByRole("button", { name: "Delete response", exact: true });
const dialog = (page: Page) =>
  page.getByRole("alertdialog", { name: "Delete this response permanently?" });
const confirm = (page: Page) =>
  page.getByRole("button", { name: "Delete permanently", exact: true });
const cancel = (page: Page) =>
  page.getByRole("button", { name: "Cancel", exact: true });

test("adm03 AC48 dialog texts, initial focus on Cancel, focus trap, Escape and Cancel return focus and send nothing", async ({
  page,
}) => {
  const { ctx, deletes } = await open(page);
  const before = ctx.requests.length;
  await trigger(page).click();
  await expect(dialog(page)).toBeVisible();
  await expect(dialog(page)).toContainText(`Form: ${TITLE}. Respondent: `);
  await expect(dialog(page)).toContainText("This cannot be undone.");
  await expect(dialog(page)).toContainText(
    "Not deleted: the form, the respondent's account, and stored analyses with their statistics and AI summaries.",
  );
  await expect(dialog(page)).toContainText(
    "Links in stored analyses that cite this response will stop working and will show that the response is no longer available.",
  );
  await expect(dialog(page)).toContainText(
    /The form is open, so .+ will be able to submit it again\./,
  );
  await expect(cancel(page)).toBeFocused();
  for (let i = 0; i < 6; i++) {
    await page.keyboard.press("Tab");
    expect(
      await page.evaluate(
        () => !!document.activeElement?.closest('[role="alertdialog"]'),
      ),
    ).toBe(true);
  }
  await page.keyboard.press("Escape");
  await expect(dialog(page)).toHaveCount(0);
  await expect(trigger(page)).toBeFocused();
  await trigger(page).click();
  await cancel(page).click();
  await expect(dialog(page)).toHaveCount(0);
  await expect(trigger(page)).toBeFocused();
  expect(deletes).toHaveLength(0);
  expect(ctx.requests.length).toBe(before);
});

test("adm03 AC48 a closed form says the respondent will not be able to submit again", async ({
  page,
}) => {
  const { ctx } = await open(page);
  ctx.form.state = "closed";
  await page.reload();
  await trigger(page).click();
  await expect(dialog(page)).toContainText(
    /The form is closed, so .+ will not be able to submit it again\./,
  );
});

test("adm03 AC48 confirm sends one DELETE on double click, shows Deleting..., then replaces to the list with the status and focus", async ({
  page,
}) => {
  const { deletes, release } = await open(page, [{ hold: true }]);
  await trigger(page).click();
  await confirm(page).dblclick();
  await expect(
    page.getByRole("button", { name: "Deleting...", exact: true }),
  ).toBeDisabled();
  await expect(cancel(page)).toBeDisabled();
  await page.keyboard.press("Escape");
  await expect(dialog(page)).toBeVisible();
  expect(deletes).toHaveLength(1);
  release();
  await expect(page).toHaveURL(
    new RegExp(`/admin/feedback-hub/responses/${FORM_ID}$`),
  );
  await expect(
    page.getByRole("status").filter({ hasText: DONE }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Submitted responses" }),
  ).toBeFocused();
  expect(deletes).toHaveLength(1);
  await page.goBack(); // replace: Back does not return to the deleted detail
  await expect(page).not.toHaveURL(new RegExp(`${RESPONSE_ID}$`));
});

for (const [name, step, message] of [
  ["network", { abort: true }, NETWORK],
  [
    "500 internal_error",
    { status: 500, code: "internal_error", message: INTERNAL },
    INTERNAL,
  ],
  ["403", { status: 403, code: "forbidden", message: FORBIDDEN }, FORBIDDEN],
] as const) {
  test(`adm03 AC49 delete failure ${name}: exact message as an alert in the dialog, detail kept, buttons enabled`, async ({
    page,
  }) => {
    await open(page, [step]);
    await trigger(page).click();
    await confirm(page).click();
    await expect(
      dialog(page).getByRole("alert").filter({ hasText: message }),
    ).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Feedback response", exact: true }),
    ).toBeVisible();
    await expect(confirm(page)).toBeEnabled();
    await expect(cancel(page)).toBeEnabled();
    await expect(
      page.getByText(/something went wrong|an error occurred/i),
    ).toHaveCount(0);
  });
}

test("adm03 AC49 a retry after a network failure sends one more DELETE", async ({
  page,
}) => {
  const { deletes } = await open(page, [{ abort: true }]);
  await trigger(page).click();
  await confirm(page).click();
  await expect(dialog(page).getByRole("alert")).toBeVisible();
  await confirm(page).click();
  await expect(page).toHaveURL(new RegExp(`/responses/${FORM_ID}$`));
  expect(deletes).toHaveLength(2);
});

test("adm03 AC49 delete 404 closes the dialog and replaces to the list with the not-found status", async ({
  page,
}) => {
  await open(page, [
    { status: 404, code: "feedback_response_not_found", message: NOT_FOUND },
  ]);
  await trigger(page).click();
  await confirm(page).click();
  await expect(dialog(page)).toHaveCount(0);
  await expect(page).toHaveURL(
    new RegExp(`/admin/feedback-hub/responses/${FORM_ID}$`),
  );
  await expect(
    page.getByRole("status").filter({ hasText: NOT_FOUND }),
  ).toBeVisible();
});

test("adm03 AC49 delete 401 goes to sign in", async ({ page }) => {
  await open(page, [{ status: 401, code: "unauthenticated", message: "x" }]);
  await trigger(page).click();
  await confirm(page).click();
  await expect(
    page.getByText("Your session has expired. Sign in again."),
  ).toBeVisible();
});

import { expect, test } from "@playwright/test";

// Runs against the real FastAPI backend (no mocks): a contract change on either side fails here.
// Start the backend first, then: REAL_BACKEND=1 npx playwright test --project=real-backend
test("student answers, submits and sees the server's score", async ({
  page,
}) => {
  // SHR-01: sign in first as the seeded demo-student. Credentials come from the environment
  // used to run `python -m auth.seed` (never committed): E2E_STUDENT_EMAIL / E2E_STUDENT_PASSWORD.
  const email = process.env.E2E_STUDENT_EMAIL;
  const password = process.env.E2E_STUDENT_PASSWORD;
  test.skip(
    !email || !password,
    "E2E_STUDENT_EMAIL / E2E_STUDENT_PASSWORD not set",
  );
  await page.goto("/login");
  await page.getByLabel(/^e-?mail( address)?\s*\*?$/i).fill(email!);
  await page.getByLabel(/^password\s*\*?$/i).fill(password!);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page).toHaveURL(/\/student\/overview$/);
  await page.goto("/student/practice");
  await expect(page.getByText("Software engineering basics")).toBeVisible();
  await expect(page.getByText("Correct answer:")).toHaveCount(0);
  await page
    .getByRole("radio", { name: "A single, focused responsibility" })
    .check();
  await page
    .getByRole("radio", { name: "To catch regressions when code changes" })
    .check();
  await page.getByRole("radio", { name: "3", exact: true }).check();
  await expect(page.getByText("3 of 3 answered")).toBeVisible();
  await page.getByRole("button", { name: "Submit practice set" }).click();
  await expect(
    page.getByRole("heading", { name: "3 / 3 — Nicely done!" }),
  ).toBeVisible();
  await expect(page.getByText("Correct answer:")).toHaveCount(3);
  await expect(
    page.getByText("len returns the number of items."),
  ).toBeVisible();
});

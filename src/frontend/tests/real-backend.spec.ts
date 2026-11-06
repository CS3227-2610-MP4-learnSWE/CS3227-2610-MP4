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
  // STU-02-published-sets: the seeded published set (python -m teacher_publications.seed) is picked
  // from the picker; the page reads the set id from the URL.
  await page.goto("/student/practice");
  await expect(
    page.getByRole("heading", { level: 1, name: "Choose a practice set" }),
  ).toBeVisible();
  await page
    .getByRole("link", { name: "Software engineering practice", exact: true })
    .click();
  await expect(page).toHaveURL(/\/student\/practice\/[0-9a-f-]{36}$/);
  await expect(
    page.getByRole("heading", {
      level: 2,
      name: "Software engineering practice",
    }),
  ).toBeVisible();
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

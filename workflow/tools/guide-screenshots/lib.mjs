// Helpers for capturing the User Guide screenshots. See README.md in this folder.
import { chromium } from "../../../src/frontend/node_modules/@playwright/test/index.mjs";
import { fileURLToPath } from "node:url";
import path from "node:path";

const here = path.dirname(fileURLToPath(import.meta.url));
export const ROOT = path.resolve(here, "../../..");
export const BASE = process.env.GUIDE_BASE || "http://127.0.0.1:5173";
export const OUT = process.env.GUIDE_OUT || path.join(ROOT, "docs/images/guide");
export const SAMPLE_FILE = path.join(ROOT, "docs/sample-files/testing-basics.txt");
// The example accounts of src/backend/.env.example; override if you changed them.
export const ACCOUNTS = {
  student: [process.env.GUIDE_STUDENT_EMAIL || "student@example.com", process.env.GUIDE_STUDENT_PASSWORD || "Student-Demo-4821"],
  teacher: [process.env.GUIDE_TEACHER_EMAIL || "teacher@example.com", process.env.GUIDE_TEACHER_PASSWORD || "Teacher-Demo-4821"],
  admin: [process.env.GUIDE_ADMIN_EMAIL || "admin@example.com", process.env.GUIDE_ADMIN_PASSWORD || "Admin-Demo-4821"],
};

export const open = () => chromium.launch();

export async function session(browser, role, size = { width: 1280, height: 800 }) {
  const context = await browser.newContext({ viewport: size, colorScheme: "light" });
  const page = await context.newPage();
  const [email, password] = ACCOUNTS[role];
  await page.goto(BASE + "/login");
  await page.getByLabel(/^email/i).fill(email);
  await page.getByLabel(/^password/i).fill(password);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await page.waitForURL((u) => !u.pathname.startsWith("/login"));
  await page.waitForTimeout(800);
  return page;
}

export const shot = async (page, name, opts = {}) => {
  await page.evaluate(() => {
    window.scrollTo(0, 0);
    document.querySelector("main")?.scrollTo?.(0, 0);
  });
  await page.waitForTimeout(700);
  await page.screenshot({ path: path.join(OUT, `${name}.png`), ...opts });
  console.log("shot", name);
};

import { expect, test, type Page } from "@playwright/test";

// ponytail: self-contained mock copy (not shared with demo-flow.spec.ts) so this
// one-off screenshot generator can't break the real e2e test. Run with:
//   npm run build && npx playwright test e2e/screenshots.spec.ts
// Output lands in ../docs/assets and is committed for the README.

const apiBaseUrl = "https://api.lepomas.xyz";
const owner = {
  id: 1,
  login: "demo-owner",
  email: "demo-owner@example.com",
  created_at: "2026-06-04T00:00:00Z",
  updated_at: "2026-06-04T00:00:00Z",
};
const project = {
  id: 10,
  name: "Acme Rollout",
  description: "Q3 launch documents and access control",
  owner_id: owner.id,
  total_size_bytes: 2048,
  documents_count: 1,
  created_at: "2026-06-04T00:00:00Z",
  updated_at: "2026-06-04T00:00:00Z",
};
const projectSummary = { ...project, documents: ["statement-of-work.pdf"] };
const member = {
  id: 1,
  project_id: project.id,
  user_id: owner.id,
  login: owner.login,
  role: "owner",
  created_at: "2026-06-04T00:00:00Z",
};
const participant = {
  id: 2,
  project_id: project.id,
  user_id: 2,
  login: "demo-participant",
  role: "participant",
  created_at: "2026-06-04T00:00:00Z",
};
const documentItem = {
  id: 50,
  project_id: project.id,
  uploaded_by_id: owner.id,
  filename: "statement-of-work.pdf",
  content_type: "application/pdf",
  size_bytes: 2048,
  storage_key: "documents/statement-of-work.pdf",
  status: "uploaded",
  created_at: "2026-06-04T00:00:00Z",
  updated_at: "2026-06-04T00:00:00Z",
};

async function mockApi(page: Page) {
  await page.route(`${apiBaseUrl}/auth/register`, (r) => r.fulfill({ json: owner }));
  await page.route(`${apiBaseUrl}/auth/login`, (r) =>
    r.fulfill({ json: { access_token: "jwt-token", token_type: "bearer", expires_in: 900 } }),
  );
  await page.route(`${apiBaseUrl}/auth/me`, (r) => r.fulfill({ json: owner }));
  await page.route(`${apiBaseUrl}/projects`, (r) => r.fulfill({ json: [projectSummary] }));
  await page.route(`${apiBaseUrl}/project/${project.id}/info`, (r) => r.fulfill({ json: project }));
  await page.route(`${apiBaseUrl}/project/${project.id}/members`, (r) =>
    r.fulfill({ json: [member, participant] }),
  );
  await page.route(`${apiBaseUrl}/project/${project.id}/documents`, (r) =>
    r.fulfill({ json: [documentItem] }),
  );
}

test("capture portfolio screenshots", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 860 });
  await mockApi(page);

  await page.goto("/");
  await page.getByRole("button", { name: "Register" }).click();
  await expect(page.getByText("Live test path")).toBeVisible();
  await page.screenshot({ path: "../docs/assets/01-auth.png" });

  await page.getByLabel("Login").fill(owner.login);
  await page.getByLabel("Email").fill(owner.email);
  await page.getByLabel("Password", { exact: true }).fill("super-secret-123");
  await page.getByLabel("Repeat password").fill("super-secret-123");
  await page.getByRole("button", { name: "Register and login" }).click();

  await page.getByRole("button", { name: /Acme Rollout/ }).click();
  await expect(page.getByRole("heading", { name: "statement-of-work.pdf" })).toBeVisible();
  await expect(page.getByText("demo-participant")).toBeVisible();
  await page.screenshot({ path: "../docs/assets/02-dashboard.png", fullPage: true });
});

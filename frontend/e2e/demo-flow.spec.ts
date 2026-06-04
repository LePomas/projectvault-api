import { expect, test, type Page } from "@playwright/test";

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
  name: "Demo project",
  description: "Controlled demo",
  owner_id: owner.id,
  total_size_bytes: 2048,
  documents_count: 1,
  created_at: "2026-06-04T00:00:00Z",
  updated_at: "2026-06-04T00:00:00Z",
};
const projectSummary = { ...project, documents: ["brief.pdf"] };
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
  filename: "brief.pdf",
  content_type: "application/pdf",
  size_bytes: 2048,
  storage_key: "documents/brief.pdf",
  status: "uploaded",
  created_at: "2026-06-04T00:00:00Z",
  updated_at: "2026-06-04T00:00:00Z",
};

async function mockApi(page: Page) {
  await page.route(`${apiBaseUrl}/auth/register`, async (route) => {
    await route.fulfill({ json: owner });
  });
  await page.route(`${apiBaseUrl}/auth/login`, async (route) => {
    await route.fulfill({
      json: {
        access_token: "jwt-token",
        token_type: "bearer",
        expires_in: 900,
      },
    });
  });
  await page.route(`${apiBaseUrl}/auth/me`, async (route) => {
    await route.fulfill({ json: owner });
  });
  await page.route(`${apiBaseUrl}/projects`, async (route) => {
    await route.fulfill({ json: [projectSummary] });
  });
  await page.route(`${apiBaseUrl}/project`, async (route) => {
    await route.fulfill({ status: 201, json: project });
  });
  await page.route(`${apiBaseUrl}/project/${project.id}/info`, async (route) => {
    await route.fulfill({ json: project });
  });
  await page.route(`${apiBaseUrl}/project/${project.id}/members`, async (route) => {
    await route.fulfill({ json: [member, participant] });
  });
  await page.route(
    `${apiBaseUrl}/project/${project.id}/invite?user=demo-participant`,
    async (route) => {
      await route.fulfill({ status: 201, json: participant });
    },
  );
  await page.route(`${apiBaseUrl}/project/${project.id}/documents`, async (route) => {
    if (route.request().method() === "POST") {
      await route.fulfill({ status: 201, json: documentItem });
      return;
    }
    await route.fulfill({ json: [documentItem] });
  });
  await page.route(
    `${apiBaseUrl}/document/${documentItem.id}/download-url`,
    async (route) => {
      await route.fulfill({
        json: {
          download_url: "https://signed.example.com/brief.pdf",
          expires_in: 900,
        },
      });
    },
  );
}

test("controlled demo auth, project, member, and document flow", async ({ page }) => {
  await mockApi(page);
  const openedUrls: string[] = [];
  await page.addInitScript(() => {
    window.open = (url?: string | URL) => {
      window.dispatchEvent(
        new CustomEvent("projectvault:window-open", {
          detail: url?.toString() ?? "",
        }),
      );
      return null;
    };
  });
  await page.exposeFunction("recordOpenedUrl", (url: string) => {
    openedUrls.push(url);
  });

  await page.goto("/");
  await page.evaluate(() => {
    window.addEventListener("projectvault:window-open", (event) => {
      const openedEvent = event as CustomEvent<string>;
      void window.recordOpenedUrl(openedEvent.detail);
    });
  });

  await page.getByRole("button", { name: "Register" }).click();
  await page.getByLabel("Login").fill(owner.login);
  await page.getByLabel("Email").fill(owner.email);
  await page.getByLabel("Password", { exact: true }).fill("super-secret-123");
  await page.getByLabel("Repeat password").fill("super-secret-123");
  await page.getByRole("button", { name: "Register and login" }).click();

  await expect(page.getByText(owner.email)).toBeVisible();
  await expect(page.getByRole("button", { name: /Demo project/ })).toBeVisible();

  await page.getByLabel("Name").fill(project.name);
  await page.getByLabel("Description").fill(project.description);
  await page.getByRole("button", { name: "Create project" }).click();
  await expect(page.getByRole("heading", { name: project.name })).toBeVisible();

  await page.getByLabel("Add participant by login").fill(participant.login);
  await page.getByRole("button", { name: "Grant access" }).click();
  await expect(page.getByText(participant.login)).toBeVisible();

  await page.getByLabel("Upload PDF or DOCX").setInputFiles({
    name: "brief.pdf",
    mimeType: "application/pdf",
    buffer: Buffer.from("%PDF-1.4"),
  });
  await page.getByRole("button", { name: "Upload", exact: true }).click();
  await expect(page.getByRole("heading", { name: "brief.pdf" })).toBeVisible();
  await expect(page.getByText("application/pdf")).toBeVisible();

  await page.getByRole("button", { name: "Download" }).click();
  await expect.poll(() => openedUrls).toContain("https://signed.example.com/brief.pdf");
});

declare global {
  interface Window {
    recordOpenedUrl: (url: string) => Promise<void>;
  }
}

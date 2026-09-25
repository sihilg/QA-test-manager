import { expect, test } from "@playwright/test";

const password = "DemoPassword123!";

async function login(page: import("@playwright/test").Page, email: string) {
  await page.goto("/");
  await page.getByLabel("Email", { exact: true }).fill(email);
  await page.getByLabel("Palavra-passe", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Entrar" }).click();
  await expect(page.getByRole("heading", { name: "Projetos", exact: true })).toBeVisible();
}

test("Admin sees project and user administration", async ({ page }) => {
  await login(page, "admin.demo@example.com");
  await expect(page.getByRole("button", { name: "Utilizadores" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Novo projeto" })).toBeVisible();
  await expect(page.getByText("Portal de demonstração")).toBeVisible();
});

test("Tester can create cases only in an assigned project", async ({ page }) => {
  await login(page, "tester.demo@example.com");
  await expect(page.getByRole("button", { name: "Utilizadores" })).toHaveCount(0);
  await page.getByRole("button", { name: "Abrir casos" }).click();
  await expect(page.getByRole("button", { name: "Novo caso" })).toBeVisible();
  await expect(page.getByText("CT001")).toBeVisible();
});

test("Dev has read-only access to assigned cases", async ({ page }) => {
  await login(page, "dev.demo@example.com");
  await expect(page.getByRole("heading", { name: "Novo projeto" })).toHaveCount(0);
  await page.getByRole("button", { name: "Abrir casos" }).click();
  await expect(page.getByRole("button", { name: "Novo caso" })).toHaveCount(0);
  await expect(page.getByText("CT001")).toBeVisible();
});

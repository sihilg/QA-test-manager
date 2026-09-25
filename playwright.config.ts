import { defineConfig, devices } from "@playwright/test";

const demoPassword = "DemoPassword123!";
const python = process.platform === "win32" ? '"..\\..\\.venv\\Scripts\\python.exe"' : "python";

export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: false,
  workers: 1,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? "github" : "list",
  use: {
    baseURL: "http://127.0.0.1:5174",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: [
    {
      command: `${python} -m alembic upgrade head && ${python} -m qa_test_manager.seed_demo && ${python} -m uvicorn qa_test_manager.main:app --app-dir src --host 127.0.0.1 --port 8001`,
      cwd: "apps/api",
      env: {
        ...process.env,
        QA_TEST_MANAGER_DATABASE_URL: "sqlite:///./e2e-release1-demo.db",
        QA_TEST_MANAGER_ALLOW_DEMO_SEED: "1",
        QA_TEST_MANAGER_DEMO_PASSWORD: demoPassword,
      },
      port: 8001,
      reuseExistingServer: false,
      timeout: 120_000,
    },
    {
      command: "pnpm --dir apps/web dev --host 127.0.0.1 --port 5174",
      env: { ...process.env, VITE_API_TARGET: "http://127.0.0.1:8001" },
      port: 5174,
      reuseExistingServer: false,
      timeout: 120_000,
    },
  ],
});

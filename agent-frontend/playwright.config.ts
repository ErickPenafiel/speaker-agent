import { defineConfig, devices } from "@playwright/test"

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: "list",
  timeout: 30000,
  use: {
    baseURL: "http://localhost:5173",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: {
        ...devices["Desktop Chrome"],
        // Use system chromium if playwright's internal browser isn't downloaded for this exact version
        launchOptions: {
          executablePath: process.env.CHROME_BIN || "/usr/bin/chromium",
          args: ["--no-sandbox", "--disable-setuid-sandbox"],
        },
      },
    },
  ],
})

// @ts-check
const { defineConfig, devices } = require('@playwright/test');

/**
 * Playwright configuration for Restaurant Sentiment Analysis E2E tests.
 * @see https://playwright.dev/docs/test-configuration
 */
module.exports = defineConfig({
  testDir: './tests',
  testMatch: '**/test_dashboard_e2e.py',
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: 'html',
  timeout: 60000,

  use: {
    baseURL: 'http://localhost:8505',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    headless: true,
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],

  webServer: {
    command: 'python -m streamlit run dashboard/app.py --server.port 8505 --server.headless true --browser.gatherUsageStats false',
    url: 'http://localhost:8505',
    reuseExistingServer: !process.env.CI,
    timeout: 60000,
  },
});

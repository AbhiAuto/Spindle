import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  retries: process.env.CI ? 2 : 0,
  use: { baseURL: process.env.BASE_URL, trace: 'on-first-retry' },
  reporter: [['html'], ['junit', { outputFile: 'results/junit.xml' }]],
  projects: [
    // signs in once and saves the session; every other test starts signed in
    { name: 'setup', testMatch: /.*\.setup\.ts/ },
    {
      name: 'e2e',
      use: { storageState: 'playwright/.auth/user.json' },
      dependencies: ['setup'],
    },
  ],
});

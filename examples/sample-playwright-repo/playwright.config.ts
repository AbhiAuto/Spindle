import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  retries: process.env.CI ? 2 : 0,
  use: { baseURL: process.env.BASE_URL, trace: 'on-first-retry' },
  reporter: [['html'], ['junit', { outputFile: 'results/junit.xml' }]],
});

import { test as setup, expect } from '@playwright/test';
import { loginWithOtp } from '../fixtures/auth';

const authFile = 'playwright/.auth/user.json';

/** Signs in once as the standard claims handler, OTP included, and saves the session for every other test. */
setup('sign in as claims handler', async ({ page }) => {
  await loginWithOtp(page, process.env.TEST_USER!, process.env.TEST_PASS!);
  await expect(page).toHaveURL(/dashboard/);
  await page.context().storageState({ path: authFile });
});

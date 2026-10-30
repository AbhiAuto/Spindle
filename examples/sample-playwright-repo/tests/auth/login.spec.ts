import { test, expect } from '@playwright/test';
import { LoginPage } from '../../pages/LoginPage';

// this test checks the login screen itself, so it starts signed out
test.use({ storageState: { cookies: [], origins: [] } });

test('valid user can sign in @smoke', async ({ page }) => {
  await new LoginPage(page).login(process.env.TEST_USER!, process.env.TEST_PASS!);
  await expect(page).toHaveURL(/dashboard/);
});

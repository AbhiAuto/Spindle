import { test, expect } from '@playwright/test';
import { LoginPage } from '../../pages/LoginPage';

test('valid user can sign in @smoke', async ({ page }) => {
  await new LoginPage(page).login(process.env.TEST_USER!, process.env.TEST_PASS!);
  await expect(page).toHaveURL(/dashboard/);
});

import { test as base, Page } from '@playwright/test';
import { LoginPage } from '../pages/LoginPage';
import { getLatestOtp } from '../utils/mailStub';

/** Full sign-in including the OTP step, for users with two-step login switched on. */
export async function loginWithOtp(page: Page, user: string, password: string) {
  await new LoginPage(page).login(user, password);
  const code = await getLatestOtp(page.request, user);
  await page.getByTestId('otp-code').fill(code);
  await page.getByRole('button', { name: 'Verify' }).click();
}

export const test = base.extend<{ loggedIn: Page }>({
  /** A page already signed in as the standard claims handler, OTP included. */
  loggedIn: async ({ page }, use) => {
    await loginWithOtp(page, process.env.TEST_USER!, process.env.TEST_PASS!);
    await use(page);
  },
});

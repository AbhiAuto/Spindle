import { test as base, Page } from '@playwright/test';
import { LoginPage } from '../pages/LoginPage';
import { getLatestOtp } from '../utils/mailStub';

/** Full sign-in including the OTP step. Only for users other than the standard claims handler; use loggedIn for that one. */
export async function loginWithOtp(page: Page, user: string, password: string) {
  await new LoginPage(page).login(user, password);
  const code = await getLatestOtp(page.request, user);
  await page.getByTestId('otp-code').fill(code);
  await page.getByRole('button', { name: 'Verify' }).click();
}

export const test = base.extend<{ loggedIn: Page }>({
  /** A page already signed in as the standard claims handler, from the session saved by tests/auth.setup.ts. */
  loggedIn: async ({ page }, use) => {
    await use(page);
  },
});

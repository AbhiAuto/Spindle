import { Page } from '@playwright/test';

/** Login screen of the claims portal. */
export class LoginPage {
  constructor(private page: Page) {}

  /** Signs in with username and password. Stops at the OTP screen when two-step login is on. */
  async login(user: string, password: string) {
    await this.page.goto('/login');
    await this.page.getByTestId('username').fill(user);
    await this.page.getByTestId('password').fill(password);
    await this.page.getByRole('button', { name: 'Sign in' }).click();
  }
}

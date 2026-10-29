import { Page, expect } from '@playwright/test';

/** Claims list and new claim form. */
export class ClaimsPage {
  constructor(private page: Page) {}

  /** Opens the claims list. */
  async open() { await this.page.goto('/claims'); }

  /** Starts a new claim against a policy number and stops on the incident details step. */
  async startNewClaim(policyNo: string) {
    await this.page.getByRole('button', { name: 'New claim' }).click();
    await this.page.getByTestId('policy-number').fill(policyNo);
  }

  /** Uploads an evidence file and waits for the virus scan to finish, not a fixed timeout. */
  async uploadEvidence(filePath: string) {
    await this.page.getByTestId('evidence-upload').setInputFiles(filePath);
    await expect(this.page.getByTestId('scan-status')).toHaveText('Scan complete', { timeout: 60000 });
  }

  /** Asserts the claim status badge, for example Draft or Submitted. */
  async expectStatus(status: string) {
    await expect(this.page.getByTestId('claim-status')).toHaveText(status);
  }
}

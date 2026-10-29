import { APIRequestContext } from '@playwright/test';

/**
 * Reads the latest one-time passcode sent to a test inbox from the mail stub API.
 * Retries for up to 30 seconds because the stub can lag behind the login request.
 */
export async function getLatestOtp(request: APIRequestContext, inbox: string): Promise<string> {
  for (let i = 0; i < 15; i++) {
    const res = await request.get(`/mail-stub/inbox/${inbox}/latest`);
    const code = (await res.json()).body?.match(/\b\d{6}\b/)?.[0];
    if (code) return code;
    await new Promise(r => setTimeout(r, 2000));
  }
  throw new Error(`No OTP arrived for ${inbox}`);
}

---
id: otp-login
type: pattern
name: OTP login
aliases: []
tags: []
status: active
links: []
use_when: [otp, mfa, 2fa, two-step, one-time code, passcode, verification code, signed in, signed-in, logged in, logged-in, login, session, storageState]
---
- 2026-08-20 [pattern superseded] Two-step login: use loginWithOtp() in fixtures/auth.ts, which reads the code from the mail stub. Never bypass OTP with a flag
- 2026-10-30 [pattern] Signed-in tests: ask for the loggedIn fixture in fixtures/auth.ts. tests/auth.setup.ts signs in once with OTP and saves the session, so loggedIn costs nothing. Call loginWithOtp() only for a different user. Never bypass OTP with a flag

---
id: otp-login
type: pattern
name: OTP login
aliases: []
tags: []
status: active
links: []
use_when: [otp, mfa, 2fa, two-step, one-time code, passcode, verification code]
---
- 2026-08-20 [pattern] Two-step login: use loginWithOtp() in fixtures/auth.ts, which reads the code from the mail stub. Never bypass OTP with a flag

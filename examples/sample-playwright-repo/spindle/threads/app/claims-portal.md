---
id: claims-portal
type: app
name: Claims portal
aliases: [Claims, claims app]
tags: []
status: active
links: [sample-playwright-repo, claims-regression-q3, otp-login, file-upload]
---
- 2026-07-01 [env] SIT and UAT; SIT refreshed every Sunday night, tests fail 22:00-02:00 Sunday
- 2026-07-01 [data] Policies come from test-data/policies.json; claims created through api/claimsClient.ts, not the UI, for speed
- 2026-07-03 [convention] Use getByTestId first, getByRole second; no CSS or XPath locators
- 2026-08-12 [gotcha] Evidence upload times out in SIT. Cause: virus scan delay. Fix: ClaimsPage.uploadEvidence waits for scan-complete, never a fixed timeout src:PR 214
- 2026-09-02 [gotcha by:ravi] Evidence upload stalls in SIT. Fix: ClaimsPage.uploadEvidence waits for the scan status, never a fixed wait error:"locator.setInputFiles: Timeout 30000ms exceeded"
- 2026-09-03 [gotcha by:sam avoid] Upload flaky on Fridays. Fix: added waitForTimeout(8000) before submit
- 2026-09-05 [gotcha by:ravi] Proper fix for the Friday upload flake: wait for the scan-complete text; the waitForTimeout was removed

---
id: sample-playwright-repo
type: framework
name: Claims portal e2e
aliases: [claims e2e]
tags: []
status: active
links: [claims-portal]
---
- 2026-10-28 [convention] Stack: Playwright. Main language: TypeScript src:harvest
- 2026-10-28 [convention] Config files: package.json, playwright.config.ts src:harvest
- 2026-10-28 [convention] 2 test files. Main folders: tests/auth (1), tests/claims (1). Naming: *.spec.ts src:harvest
- 2026-10-28 [asset] Page objects (2): pages/ClaimsPage.ts, pages/LoginPage.ts src:harvest
- 2026-10-28 [asset] Helpers (2): utils/dataBuilder.ts, utils/mailStub.ts src:harvest
- 2026-10-28 [asset] Fixtures (1): fixtures/auth.ts src:harvest
- 2026-10-28 [asset] API clients (1): api/claimsClient.ts src:harvest
- 2026-10-28 [data] Test data folders: test-data src:harvest
- 2026-10-28 [convention] Tags in use: @regression (2), @smoke (1) src:harvest
- 2026-10-28 [decision] Retries configured in playwright.config.ts: 2 src:harvest
- 2026-10-28 [gotcha] 1 skipped, fixme or disabled test(s), check why: tests/claims/new-claim.spec.ts:12 src:harvest
- 2026-10-28 [env] CI: .github/workflows/e2e.yml src:harvest

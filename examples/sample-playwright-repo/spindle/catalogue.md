# Capability catalogue

Generated 2026-10-30 from the code by harvest. 12 capabilities in 6 files.
Don't edit by hand: add doc comments in the code and re-run harvest. Search it with `spindle.py match`.

## api/claimsClient.ts

- api/claimsClient.ts :: createClaimViaApi(request, body) :: Creates a claim through the API. Use it for test data setup instead of the UI, it is much faster.

## fixtures/auth.ts

- fixtures/auth.ts :: loginWithOtp(page, user, password) :: Full sign-in including the OTP step. Only for users other than the standard claims handler; use loggedIn for that one.
- fixtures/auth.ts :: fixture loggedIn :: A page already signed in as the standard claims handler, from the session saved by tests/auth.setup.ts.

## pages/ClaimsPage.ts

- pages/ClaimsPage.ts :: ClaimsPage :: Claims list and new claim form.
- pages/ClaimsPage.ts :: ClaimsPage.open() :: Opens the claims list.
- pages/ClaimsPage.ts :: ClaimsPage.startNewClaim(policyNo) :: Starts a new claim against a policy number and stops on the incident details step.
- pages/ClaimsPage.ts :: ClaimsPage.uploadEvidence(filePath) :: Uploads an evidence file and waits for the virus scan to finish, not a fixed timeout.
- pages/ClaimsPage.ts :: ClaimsPage.expectStatus(status) :: Asserts the claim status badge, for example Draft or Submitted.

## pages/LoginPage.ts

- pages/LoginPage.ts :: LoginPage :: Login screen of the claims portal.
- pages/LoginPage.ts :: LoginPage.login(user, password) :: Signs in with username and password. Stops at the OTP screen when two-step login is on.

## utils/dataBuilder.ts

- utils/dataBuilder.ts :: buildClaim(overrides = {}) :: Builds a valid claim payload with a random policy number and a recent incident date.

## utils/mailStub.ts

- utils/mailStub.ts :: getLatestOtp(request, inbox) :: Reads the latest one-time passcode sent to a test inbox from the mail stub API.

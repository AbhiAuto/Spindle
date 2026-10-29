import { test } from '../../fixtures/auth';
import { ClaimsPage } from '../../pages/ClaimsPage';
import { buildClaim } from '../../utils/dataBuilder';

test('create a new claim @regression', async ({ loggedIn }) => {
  const claims = new ClaimsPage(loggedIn);
  await claims.open();
  await claims.startNewClaim(buildClaim().policyNo);
  await claims.expectStatus('Draft');
});

test.fixme('upload evidence document @regression', async () => {
  // upload widget times out in the test environment
});

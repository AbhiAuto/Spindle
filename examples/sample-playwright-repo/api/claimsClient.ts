import { APIRequestContext } from '@playwright/test';

/** Creates a claim through the API. Use it for test data setup instead of the UI, it is much faster. */
export const createClaimViaApi = (request: APIRequestContext, body: object) =>
  request.post('/api/claims', { data: body });

import { faker } from '@faker-js/faker';

/** Builds a valid claim payload with a random policy number and a recent incident date. */
export const buildClaim = (overrides = {}) => ({
  policyNo: `POL-${faker.string.numeric(6)}`,
  incidentDate: faker.date.recent().toISOString().slice(0, 10),
  ...overrides,
});

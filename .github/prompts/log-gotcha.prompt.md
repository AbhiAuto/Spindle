---
description: 'Spider: log a flaky test or problem and its fix'
agent: 'agent'
argument-hint: 'Symptom, root cause, fix'
---
Use the spider skill. First search memory for this problem in case we've seen it before, and tell me if we have.

Then log it as a `gotcha` strand on the right app or framework thread:
${input:gotcha} (for example: Upload widget times out in SIT. Cause: virus scan delay. Fix: wait for the scan-complete event, not a fixed timeout)

Include the test or file path if we know it. Confirm the wording with me once before writing.

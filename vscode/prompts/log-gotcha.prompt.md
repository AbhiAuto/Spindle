---
description: 'Spindle: log a flaky test or problem and its fix'
agent: 'agent'
argument-hint: 'Symptom, root cause, fix'
---
Use the spindle skill. First search memory for this problem in case we've seen it before, and tell me if we have.

Then log it as a `gotcha` strand on the right app or framework thread:
${input:gotcha} (for example: Upload widget times out in SIT. Cause: virus scan delay. Fix: wait for the scan-complete event, not a fixed timeout)

Error text (paste the message the test failed with, if there was one): ${input:error}

Store the error text with the gotcha (`error` in spindle_add, or `--error`) so pasting it later finds this fix. Include the test or file path if we know it. If the fix was a shortcut (sleep, force, raised timeout, removed assertion), say so: Spindle will store it as `avoid`, and ask me for the proper fix. Confirm the wording with me once before writing.

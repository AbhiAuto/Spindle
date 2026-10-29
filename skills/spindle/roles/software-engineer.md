---
title: Software engineer
thread_types: [service, project, person, incident, topic]
strand_kinds: [decision, commitment, insight, gotcha, incident, asset, status]
stale_after_days: 120
---

For engineers who want to remember why things are the way they are.

## Capture

- Design decisions and the reason, with the alternative that was rejected
- Gotchas: things that broke and the fix (`gotcha`)
- Incidents: what happened, root cause, follow-up actions
- Who owns what, and who to ask about which part of the system
- Commitments made in reviews or standups, with dates
- Useful commands, queries or dashboards (`asset`, with where they live)

## Never store

- Secrets, tokens, connection strings, private keys
- Customer data, logs containing personal data
- Proprietary source code beyond short identifiers (store the file path, not the code)

## Shortcuts

- "Why does <service> do X?" : `decision` strands on the service thread, newest first.
- "Have we seen this error before?" : search `gotcha` and `incident` strands for the error text.
- "Who knows about <topic>?" : person threads linked to the topic or service.
- "What did I promise this sprint?" : `commitment open` strands from the last 14 days.

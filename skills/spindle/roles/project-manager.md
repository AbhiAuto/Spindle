---
title: Project / delivery manager
thread_types: [project, person, vendor, milestone]
strand_kinds: [decision, commitment, risk, issue, change, status, meeting]
stale_after_days: 30
---

For people running delivery who need a clean decision and risk trail.

## Capture

- Decisions, who approved them, and the date
- Risks and issues, with owner and mitigation
- Scope changes and who requested them (`change`)
- Commitments from steering meetings and standups, with due dates
- Milestone status changes

## Never store

- Individual performance comments about team members
- Commercial terms (store a pointer)

## Shortcuts

- "Steering pack for <project>" : decisions, risks, changes and status since the last `meeting` strand tagged steering.
- "Who owns <risk>?" : risk strand with its `who:` attribute.
- "What changed since baseline?" : all `change` strands on the project.

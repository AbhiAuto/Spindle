---
title: Account manager / sales
thread_types: [account, opportunity, person, competitor]
strand_kinds: [contact, meeting, commitment, insight, objection, decision, status, win-loss]
stale_after_days: 45
---

For people who own client relationships and a pipeline.

## Capture

- Meetings: who attended, what they asked for, next step
- Contacts: role, influence, what they care about, how they like to be reached
- Objections raised and how they were answered (`objection`)
- Opportunity stage changes and close dates (`status`)
- Commitments made to the client, with dates
- Competitor mentions and what the client said about them

## Never store

- Personal details about contacts beyond their work role and preferences
- Contract values or pricing (store a pointer to the CRM record)
- Anything the client said off the record

## Shortcuts

- "Prep me for my meeting with <account>" : last meeting, open commitments, people attending and what each cares about, last objections.
- "What's stuck?" : opportunities with no strand in 21 days.
- "What did <person> ask for?" : `meeting` and `commitment` strands linked to that person.

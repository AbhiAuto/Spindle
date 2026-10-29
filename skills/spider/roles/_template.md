---
title: Custom role (copy me)
thread_types: [project, person, topic]
strand_kinds: [decision, commitment, contact, insight, asset, risk, status, note]
stale_after_days: 90
---

<!--
How to make your own role:
1. Copy this file to roles/<your-role>.md (lowercase, hyphens).
2. thread_types: the things you track. Each becomes a folder in your web.
3. strand_kinds: the kinds of facts you log. Keep it under ten.
4. Fill in the three sections below in your own words. Be specific to your job.
5. Run: python scripts/spider.py check-role roles/<your-role>.md
-->

## Capture

What is worth remembering in this job. Write it as a list.

- Decisions and who made them
- Commitments you or others made, with dates
- New people and what they care about
- Files or assets you produced, with where they live

## Never store

Anything specific to your job or your employer's rules.

- Client confidential content (store a pointer instead)

## Shortcuts

Questions you'll ask often, and how Spindle should answer them.

- "What's open?" : all `commitment open` strands, oldest due date first.
- "Catch me up on X" : the X thread, last 10 strands, plus open commitments and linked people.

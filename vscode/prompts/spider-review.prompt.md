---
description: 'Spindle: review memory health, pattern evidence and what to prune'
agent: 'agent'
---
Use the spider skill to review the health of this project's memory. Change nothing; show me what needs a decision.

1. Run `spider_scan` and report any secrets or personal details found, with file and line.
2. Run `spider_candidates`. For each candidate pattern, say whether it has enough evidence to approve.
3. Run `spider_efficacy` and summarise which patterns are effective, which are disputed (with the reasons people gave) and which are unused.
4. Run `spider.py prune spider` and list its proposals.
5. Finish with the exact commands I'd run to act on this, for example `spider.py approve spider <pattern> --by "<my name>"` or `spider.py retire spider <pattern> --by "<my name>" --why "<reason>"`. Approving and retiring are my decisions: never run them yourself.

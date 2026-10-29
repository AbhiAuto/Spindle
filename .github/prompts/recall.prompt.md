---
description: 'Spider: ask the team memory'
agent: 'agent'
argument-hint: 'Your question, e.g. how do we handle OTP login?'
---
Use the spider skill to answer from memory: ${input:question} (for example: What can I reuse for the claims module?)

Search memory first: spider_match for "what applies to this", spider_find for anything else, or read the index. Answer with dates and the thread each fact came from, and open the files that asset strands point to if that helps. If memory has nothing, say so plainly.

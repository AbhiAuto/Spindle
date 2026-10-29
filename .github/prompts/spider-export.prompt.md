---
description: 'Spider: export reusable memory as a kit for another project'
agent: 'agent'
argument-hint: 'Kit name, and any client names to hide'
---
Use the spider skill to export this project's reusable memory as a kit another project can import.

Kit name: ${input:name} (for example: playwright-framework-kit)
Client names, product names or codenames to hide: ${input:redact} (for example: none)

1. Run a dry run first (spider_export with dry_run true, or `python3 .github/skills/spider/scripts/spider.py export spider kits/<name>.zip --name <name> --redact "<names>" --dry-run`). By default it takes framework and pattern threads, and conventions, patterns, gotchas, decisions, assets and insights. It leaves out app, pack and people threads, open commitments, source references, URLs, emails and IP addresses, and replaces client names with [client].
2. Show me the thread list and the preview. Read the strands yourself and point out anything that still looks client-specific (names, codenames, internal system names, ticket numbers). Suggest extra words for --redact.
3. When I confirm, write the kit to `kits/<name>.zip` (dry_run false).
4. Remind me to open the kit and review every file before sharing it, and never to share a kit between clients without that review.

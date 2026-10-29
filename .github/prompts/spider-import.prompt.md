---
description: 'Spider: import a memory kit from another project'
agent: 'agent'
argument-hint: 'Path to the kit (.zip or folder)'
---
Use the spider skill to import a memory kit into this project's memory.

Kit: ${input:kit} (for example: kits/playwright-framework-kit.zip)

1. Run a dry run first (spider_import with dry_run true, or `python3 .github/skills/spider/scripts/spider.py import spider <kit> --dry-run`) and show me which threads are new and which will be merged.
2. When I confirm, import it. Every imported line is marked with src:kit-<name>.
3. Then run /spider-harvest so the catalogue reflects this repo's own code.
4. Check the asset strands that came from the kit: tell me which paths exist in this repo and which don't. For the ones that don't, ask whether that code is coming across or the strand should be marked superseded.

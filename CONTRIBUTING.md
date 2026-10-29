# Contributing to Spindle

The best thing you can add is a role file for a job Spindle doesn't cover yet: recruiter, product manager, lawyer, teacher, researcher, support lead.

1. Copy `skills/spider/roles/_template.md` to `skills/spider/roles/<role-name>.md`.
2. Fill it in from real experience of the job. Shortcuts should be questions people in that role actually ask.
3. Keep `thread_types` to around five and `strand_kinds` under ten.
4. Run `python3 skills/spider/scripts/spider.py check-role skills/spider/roles/<role-name>.md` and `python3 -m unittest discover tests`.
5. Open a pull request with one line on who the role is for.

Bug fixes and CLI improvements are welcome too. Keep the CLI to the Python standard library so it runs anywhere.

Please don't include real client, company or personal data in examples.

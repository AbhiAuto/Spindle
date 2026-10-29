# Security

Spindle stores team memory as plain files in your repository. It removes secrets and personal details on every write, import and export, but that removal is pattern-based and can miss things.

- Never paste real credentials, tokens or customer data into memory, even for test environments.
- Run `spindle.py scan spindle` (or `spindle.py ci spindle` in CI) to check a memory before sharing it.
- Review every memory kit before moving it between projects or clients.

To report a security problem in Spindle itself, please open a private security advisory on GitHub (Security tab, "Report a vulnerability") rather than a public issue.

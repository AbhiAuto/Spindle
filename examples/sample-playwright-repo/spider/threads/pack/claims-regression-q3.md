---
id: claims-regression-q3
type: pack
name: Claims regression Q3
aliases: []
tags: []
status: active
links: [claims-portal]
---
- 2026-09-05 [coverage] Regression pack for [[claims-portal]]: new claim, edit claim, withdraw claim. 24 tests: 4 smoke, 20 regression. Excluded: payments (owned by finance team)
- 2026-09-05 [asset] Reused LoginPage, ClaimsPage, buildClaim; added ClaimHistoryPage in pages/
- 2026-09-09 [defect] Found duplicate claim reference on double-click submit (DEF-1182)
- 2026-09-10 [insight] Data setup through API cut run time from 18 to 7 minutes

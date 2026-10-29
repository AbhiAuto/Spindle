---
description: 'Spider: create a test automation pack from team memory'
agent: 'agent'
argument-hint: 'App or module, pack type (smoke, regression, API, E2E), scope'
---
Use the spider-pack-builder skill.

Application or module: ${input:app} (for example: Claims portal, new claim journey)
Pack type: ${input:type} (for example: regression)
Scope and notes: ${input:scope} (for example: happy path plus validation errors)

Load memory first, show me the plan with what you'll reuse and the watch-outs, then generate after I confirm. Finish by proposing what to remember.

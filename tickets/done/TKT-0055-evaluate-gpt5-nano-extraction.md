---
id: TKT-0055
title: Evaluate GPT-5 Nano for structured extraction
status: done
priority: P1
milestone: planning-workspace
depends_on: [TKT-0054]
created: 2026-08-09
updated: 2026-08-10
---

# TKT-0055: Evaluate GPT-5 Nano for Structured Extraction

## Outcome

GPT-5 Nano was evaluated and rejected for this extraction workload. Repeated live Ruhrogue runs failed through malformed or truncated JSON, unsupported settings, ungrounded evidence, and inconsistent coverage bookkeeping, including failure after bounded retry. Campaign Core rejected every invalid derived result; no canonical mutation occurred.

## Evidence

Live failures: `019fea51-e76`, `019feef3-396`, `019fef08-0df`, `019fef14-1a1`, `019fef21-094`, and `019fef2c-f80`. The final run failed cross-field coverage validation after two attempts: `coverage s4 requires a claim index`.

## Follow-up

TKT-0056 activates controlled model selection with `deepseek/deepseek-chat` as the default.

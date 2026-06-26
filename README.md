# spec-case

> The shared source-of-truth for **spec/case assets bound to code**. Consumed white-box by [case-code-review (`ccr`)](https://github.com/qiankunli/case-code-review) and black-box by test/eval/perf harnesses. ｜ 中文: [README.zh-CN.md](./README.zh-CN.md)

## What it is

A **spec** states the intent/contract of a code symbol (a function). A **case** is one reusable stimulus + per-face judgment criteria hanging off that spec. spec-case's distinct contribution is a stable **code↔spec/case binding** — the **unit-id** — so the same asset can be:

- **run** black-box by a harness (`case → verdict`), and
- **attached** white-box by `ccr` to the changed review **unit** (spec/case as a per-function checklist).

A review **unit** is the review-side twin of a `case`: same "requirement/contract" asset, two consumers.

## Layout (modeled on OpenSpec)

- `docs/` — `concepts.md`, `glossary.md`
- `specs/` — normative specs in OpenSpec's `Requirement / Scenario` style; `specs/unit-id/` is the core contract
- `languages/` — per-language expression (`go.md` markers, `python.md` decorators) + examples
- `schemas/` — `case.schema.json`, `spec-json.schema.json` (the generated artifact `ccr` ingests)

## Status

Early WIP. The case model and vocabulary are standard test/eval terms; the **unit-id binding** is the new piece this project owns.

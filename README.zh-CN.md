# spec-case

> 一套**代码内的 AI-native 标注体系 + 多语言工具链**：`@spec`/`@rule`/`@link` 这类标记就近长在代码上，由各语言工具抽成机器可读的资产供 AI 消费。它是**绑定到代码的 spec/case 资产**的共享真源，白盒侧被 [case-code-review (`ccr`)](https://github.com/qiankunli/case-code-review) 消费、黑盒侧被 test/eval/perf harness 消费。｜ English: [README.md](./README.md)

## 这是什么

**spec** 描述一个代码符号（函数）的意图/契约；**case** 是挂在该 spec 上的一条可复用激励 + 各判定面的判据。spec-case 独有的贡献是稳定的 **代码↔spec/case 绑定**——**symbol-id**——让同一份资产能：

- 被黑盒 harness **跑**（`case → verdict`），以及
- 被 `ccr` **白盒挂**到改动的评审 **unit** 上（spec/case 作为函数级 checklist）。

评审 **unit** 是 `case` 的**评审侧孪生**：同一份"需求/契约"资产，两个消费者。

## 布局（参考 OpenSpec）

- `docs/` — `concepts.md`（理念）、`glossary.md`（术语）
- `specs/` — OpenSpec 的 `Requirement / Scenario` 规范风格；`specs/symbol-id/` 是核心契约
- `languages/` — 各语言表达（`go.md` marker、`python.md` decorator）+ 示例
- `schemas/` — `case.schema.json`、`spec-json.schema.json`（`ccr` 吃的生成态产物）

## 状态

早期 WIP。case 模型与术语沿用通用 test/eval 词汇；**symbol-id 绑定**是本项目独有、要确立的那块。

# spec-case — 项目地图

## 项目定位与边界

spec-case 是**绑定到代码的 spec/case 资产的共享真源**，被两类消费方使用：

- **黑盒 harness**（test/eval/perf）：把 case 跑成 verdict（`case → verdict`，打真实被测系统）。
- **case-code-review / [`ccr`](https://github.com/qiankunli/case-code-review)**（白盒）：把 spec/case 挂到改动的评审 **unit**（函数）上，作为 review 的 checklist。

**边界**：spec-case 只定义**资产的形状、表达与绑定契约**（concept / schema / marker grammar / unit-id），**不实现** harness 引擎，也**不实现** `specgen`（抽取器）——抽取器是语言相关工具，按本仓契约去各被测仓里实现。

**它独有的那块**：`unit-id`——把"一条 spec/一组 case 断言的是哪个代码符号"形式化为一等绑定，让绑定可被消费方 key（普通 case 模型只有跨运行对齐用的 `case_id`，没有代码符号绑定）。

## 代码地图与核心模块

- `docs/concepts.md` — 理念：spec/case/unit 三词、case 模型、双消费、三种编写前端、生成态 `spec.json`。
- `docs/glossary.md` — 术语表。
- `specs/unit-id/spec.md` — ★ **unit-id 契约**（`specgen` 与 `ccr` 共用的 join key），OpenSpec `Requirement/Scenario` 风格。
- `languages/go.md` · `languages/python.md` — 各语言 spec/case 表达（Go `+spec`/`+case` marker、Python `@spec`/`@case` decorator）+ 示例。
- `schemas/case.schema.json` — case 定义（含 `binding` 绑定字段）。
- `schemas/spec-json.schema.json` — 生成态 `spec.json`（`ccr` 的 `SpecBuilder` 入口）。

## 关键约定

- **两个 key 不混**：`case_id`（`^[a-z][a-z0-9_]*$`，CaseSet 内对齐一条 case）；`unit-id`（`<relpath>::<symbol>`，把 spec/一组 case 绑到一个代码符号）。
- **spec 挂 symbol，case 挂 spec**：一个符号 0..1 个 spec、0..N 个 case。
- **绑定基于符号、不基于行号**：函数体内编辑、行号漂移都不改 unit-id；重命名函数/文件 = 新 id（= 漂移，`specgen --check` 报警）。
- **词汇统一**：spec / case / case_id / input / judge / face / facet / verdict / run / scope / check / source，全仓一致，不另造同义词。

## References

- 消费方引擎（白盒）：[`case-code-review`](https://github.com/qiankunli/case-code-review)（`ccr`）— `UnitSplitter` / `ContextBuilder` / `SpecBuilder`。

# spec-case — 项目地图

## 项目定位与边界

spec-case 是**绑定到代码的 spec/case 资产的共享真源**，被两类消费方使用：

- **黑盒 harness**（test/eval/perf）：把 case 跑成 verdict（`case → verdict`，打真实被测系统）。
- **case-code-review / [`ccr`](https://github.com/qiankunli/case-code-review)**（白盒）：把 spec/case 挂到改动的评审 **unit**（函数）上，作为 review 的 checklist。

**边界**：spec-case 定义**资产的形状、表达与绑定契约**（concept / schema / marker grammar / symbol-id），并提供**参考实现**——Python 的 marker 装饰器（项目 import）+ `specgen` 抽取器（`python/`，把 marker 编译成 `spec.json`）。**不实现** harness 引擎（黑盒跑 case 那套）。被测仓直接用本仓的 specgen，无需自己实现。

**它独有的那块**：`symbol-id`——把"一条 spec/一组 case 断言的是哪个代码符号"形式化为一等绑定，让绑定可被消费方 key（普通 case 模型只有跨运行对齐用的 `case_id`，没有代码符号绑定）。

## 代码地图与核心模块

- `docs/concepts.md` — 理念：spec/case/unit 三词、case 模型、双消费、三种编写前端、生成态 `spec.json`。
- `docs/glossary.md` — 术语表。
- `specs/symbol-id/spec.md` — ★ **symbol-id 契约**（`specgen` 与 `ccr` 共用的 join key），OpenSpec `Requirement/Scenario` 风格。
- `languages/go.md` · `languages/python.md` — 各语言 spec/case/link/rule 表达（Go `+spec`/`+case`/`+link`/`+rule` marker、Python `@spec`/`@case`/`@link`/`@rule` decorator）+ 示例。
- `schemas/case.schema.json` — case 定义（含 `binding` 绑定字段）。
- `schemas/spec-json.schema.json` — 生成态 `spec.json`（`ccr` 的 `SpecBuilder` 入口）。
- `python/` — ★ **Python 参考实现**：`spec_case`（marker 装饰器，项目 `from spec_case import spec, case, link, rule`）+ `spec_case.specgen`（`ast` 静态抽取 → `spec.json`，`python -m spec_case.specgen <dir>`）。
- `go/` — ★ **Go 参考实现**：`specgen`（`go/ast` 扫 doc 注释里的 `+spec`/`+case`/`+link`/`+rule` marker → `spec.json`，`go build -o specgen . && ./specgen <dir>`）。
- 两个 specgen 都带 `--check`：比对 committed `spec.json` vs 当前 marker，漂移（重命名/删除/marker 改动）则报差异 + 非零退出——CI 漂移门。

## 关键约定

- **两个 key 不混**：`case_id`（`^[a-z][a-z0-9_]*$`，CaseSet 内对齐一条 case）；`symbol-id`（`<relpath>::<symbol>`，把 spec/一组 case 绑到一个代码符号）。
- **spec / case / link / rule 都挂 symbol**（ccr 评审一个改动函数收的**四类上下文**）：一个符号 0..1 spec、0..N case、0..N link、0..N rule。link = 作者策展的 "see also"（md 路径或另一 symbol-id）；rule = 函数级审查准则（rule.json 的共置细化）。见 `docs/concepts.md`。
- **绑定基于符号、不基于行号**：函数体内编辑、行号漂移都不改 symbol-id；重命名函数/文件 = 新 id（= 漂移，`specgen --check` 报警）。
- **消费方依赖方式（Go/Python 不对称）**：Go marker 是 doc 注释，业务代码零依赖；Python marker 是真装饰器、import 时执行，业务仓须把 `spec_case` 作为 **runtime 依赖**（`spec-case` 发 PyPI，`uv add spec-case`），同一包附带的 `specgen` 供 CI 跑 `--check`。细节见 `languages/python.md` / `python/README.md`。
- **词汇统一**：spec / case / case_id / input / judge / face / facet / verdict / run / scope / check / source，全仓一致，不另造同义词。

## References

- 消费方引擎（白盒）：[`case-code-review`](https://github.com/qiankunli/case-code-review)（`ccr`）— `UnitSplitter` / `ContextBuilder` / `SpecBuilder`。

# 术语表

| 术语 | 定义 |
|------|------|
| **spec** | 一个代码符号（函数）的意图/契约，自然语言。一个符号 0..1 个 spec。 |
| **case** | 一条可积累、可复用的激励 + 各判定面判据（`id` / `input` / `judge.<face>`）。挂在某 spec 上，一个 spec 0..N 个 case。 |
| **case_id** | case 在所属 CaseSet 内唯一、不可变的主键，格式 `^[a-z][a-z0-9_]*$`。跨运行/跨判定面对齐用。 |
| **CaseSet** | 一个 case 文件：`caseset` 标识 + `sources` + `facet_schema` + `cases`。可共享的 git 资产。 |
| **unit** | 评审的最小作用域（一个函数的改动切片）。case 的评审侧孪生。 |
| **symbol-id** | 把 spec/一组 case 绑到一个代码符号的稳定标识，格式 `<relpath>::<symbol>`。`specgen` 与 `ccr` 共用的 join key。详见 `specs/symbol-id`。 |
| **binding** | case/spec 上的代码绑定字段（`symbol-id` + spec 文本）。本仓相对通用 case 模型独有的扩展。 |
| **input** | 协议无关的激励描述（schemaless dict），只承载激励，不含环境/参数。 |
| **judge** | 各判定面判据 dict（`judge.e2e` / `judge.eval` / `judge.perf` / `judge.trace`），各自可选；缺某面 = 只观测不判。 |
| **face（判定面）** | 判定视角：`e2e`（对错）、`eval`（效果）、`perf`（容量）、`trace`（链路归因）。 |
| **facet（分类轴）** | 分类维度（difficulty / type / lang…），词表在 CaseSet 声明。与 face 正交。 |
| **source（素材）** | case 声明依赖的材料（`uri` xor `content`）。声明随 case 走（git），provision 由运行时负责。 |
| **verdict** | 对一条 case（或 check）的判定结论：status + reason + metrics。黑盒 harness 的输出。 |
| **run** | 一次执行，产物落 `runs/<scope>/<run-id>/`。 |
| **scope** | harness 无关的运行单元名（run 目录首段）。 |
| **check** | run 级断言门（对聚合/切片指标的 pass/fail），与 per-case 判定是不同的判定单元。 |
| **case_hash** | 对 case 身份字段（id/input/facets/requires/judge）的稳定 hash；含义变才漂。用于检测过期产物。 |
| **spec.json** | `specgen` 的生成态产物，按 symbol-id 索引 `{spec, cases[]}`。`ccr` 的 `SpecBuilder` 入口。 |
| **specgen** | 语言相关的静态抽取器：扫代码标记（AST）→ 编译成 case + `spec.json`。按本仓契约实现，不在本仓内。 |

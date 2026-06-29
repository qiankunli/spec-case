# 理念

本文讲 spec-case 的核心概念与它们怎么咬合。术语见 [glossary.md](./glossary.md)。

spec-case 是**绑定到代码的 spec/case 资产的真源**——它自己定义 spec/case 的形状、表达与代码绑定契约，再被两类消费方使用。

## 三个词：spec / case / unit

- **spec**：一个代码符号（函数）的意图/契约，自然语言。
- **case**：挂在某个 spec 上的一条可复用激励 + 各判定面判据（`id` / `input` / `judge.<face>`）。
- **unit**：评审的最小作用域（一个函数的改动切片）。它是 **case 的评审侧孪生**——case 是"喂给被测系统的激励"，unit 是"被评审的那段代码"，二者通过同一个符号（**symbol-id**）对上。

关系：**一个符号 0..1 个 spec、0..N 个 case**。

## case 模型

case 是可积累、可共享的 git 资产。一个 case 文件是一个 **CaseSet**（`caseset` 标识 + `sources` 素材 + `facet_schema` 分类轴词表 + `cases`）。单条 case 字段：

| 字段 | 含义 | 备注 |
|------|------|------|
| `id` | 同一 CaseSet 内唯一、不可变的主键 | 格式 `^[a-z][a-z0-9_]*$`；跨运行/跨判定面对齐用 |
| `input` | 协议无关的激励描述（schemaless dict） | 只承载激励，不含环境/参数 |
| `desc` | 一行人读描述 | 装饰性，不进 `case_hash` |
| `facets` | 分类轴（difficulty/type…），词表在 CaseSet 声明 | 报表分组/透视用 |
| `requires` | 依赖的 source（素材）名 | 素材另行声明，运行时按需 provision |
| `judge.<face>` | 各判定面判据 | `face ∈ {e2e, eval, perf, trace}`，各自可选；缺某面 = 只观测不判 |
| **`binding`** | **代码符号绑定：`symbol-id` + spec 文本** | **★ spec-case 独有**——把这条 case 钉在它断言的函数上 |

判定面（**face**，判定视角）：`e2e`（对错）、`eval`（效果）、`perf`（容量）、`trace`（链路归因）。与分类轴（facet）正交。

`binding` 是关键新增：把"这条 case 断言的是哪个代码符号"升为一等字段，于是绑定可被消费方 key（见 [specs/symbol-id/spec.md](../specs/symbol-id/spec.md)）。

## link

第三个挂在符号上的维度（和 spec/case 正交，借笔记软件的双链）：一个函数声明**改它时该顺带看的东西**——一篇设计 md，或另一个函数。

- **spec** 答"这个 func 的契约"，**case** 答"具体场景 checklist"，**link** 答"改它时还该看哪"。
- link 是**作者策展的高信号上下文**，区别于自动发现（如 caller 上溯）——把"动 `create_notebook` 时记得 `update_notebook` 要保持一致"这种部落知识编码进代码，正中"改完不敢保证没坏"。
- 一个引用 `<ref>` = 仓库相对 **md 路径** 或 **symbol-id**（另一函数），靠有没有 `::` 区分。
- 消费方（ccr）注入的是**指针**，内容**按需取**（fetch 那篇 md / 查那个 func 的 spec）——link 只标"该看什么"，不预塞内容。
- **双链**：正向（函数自己的 see-also）先做；反向 backlink（谁 link 到我）后续从全量 `links` 建反向索引。

## rule

第四个挂在符号上的维度：函数级**审查准则**——评审这个函数时**该盯什么**。

- 它是 `rule.json`（路径级、glob、dir 级粗准则）的**共置细化版**：写在函数上，只管这个函数。
- 和 spec 别混：**spec = 代码保证什么（契约/事实）**；**rule = 评审时盯什么（reviewer 指令，不一定是代码已满足的事实）**。例：spec=`不跨 tenant`；rule=`这个 handler 在热路径，盯新增的同步 DB 调用`。
- 消费方（ccr）的 `RuleBuilder` 同时吃两路：函数级 `rule`（走 spec.json）+ 路径级 `rule.json`（走现有 resolver）。

四个维度合起来，就是 ccr 为一个改动函数收集的**四类上下文**——评审时"diff→func→收齐 spec/case/rule/link（能拿到多少逐步迭代）"：

关系：**一个符号 0..1 spec、0..N case、0..N link、0..N rule**。

## 双消费：黑盒 vs 白盒

同一份 spec/case 资产，两个方向消费：

```
                         ┌──────────────────────────────┐
   代码符号 ──绑定──▶ spec/case 资产 (spec-case)        │
   (symbol-id)             └───────┬───────────────┬──────┘
                                 │               │
                    黑盒(run)    │               │   白盒(attach)
                                 ▼               ▼
              黑盒 harness: case→verdict     ccr: unit→checklist
              (跑真实被测系统, e2e/eval/perf)  (评审改动函数时挂上其 spec/case)
```

- **黑盒（harness）**：把 case 跑成 **verdict**，答"接口/契约对不对、效果好不好、容量如何"。
- **白盒（[`ccr`](https://github.com/qiankunli/case-code-review)）**：评审某函数改动时，用 symbol-id 查到它的 spec + cases，作为**函数级 checklist** 注入 review（精干上下文，不展开 caller）。

## 三种编写前端（都收敛到同一 case 模型）

1. **数据优先 `case.yaml`**：直接写 `CaseSet`。外部/共享 case 走这条。
2. **代码优先注解**：贴着函数写标记（Python `@spec`/`@case`、Go `+spec`/`+case`，见 `languages/`）。co-location + 漂移检测——改函数就看见并更新它。
3. **build-time 抽取**：NL 标记 → `specgen` 静态扫描（AST）→ 编译成 case + `spec.json`。**`specgen` 是语言相关工具，按本仓契约实现，不在 spec-case 内。**

spec-case 把代码优先这条的**产物绑定**钉死：标记落在哪个符号上，就生成对应 symbol-id。

## 生成态产物：`spec.json`

`specgen` 的输出、`ccr` 的 `SpecBuilder` 入口。按 symbol-id 索引：

```jsonc
{
  "internal/notebook/handler.go::Service.CreateNotebook": {
    "spec": "tenant/user header 必填；(tenant,user,name) 唯一，重复→ConflictError",
    "cases": [
      { "id": "happy_minimal",  "desc": "只传 Name 应创建成功", "expect": "201; id 非空" },
      { "id": "duplicate_name", "desc": "重复 Name",          "expect": "409 ConflictError" }
    ]
  }
}
```

`ccr` 拿到改动函数的 symbol-id → 查 `spec.json` → 把 `spec` + 该函数的 `cases` 作为 checklist 注入。schema 见 [schemas/spec-json.schema.json](../schemas/spec-json.schema.json)。

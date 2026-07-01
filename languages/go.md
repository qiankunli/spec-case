# Go：spec/case 表达

Go 用**函数上方的 doc-comment 标记**写 spec/case，贴着它断言的函数（co-location + 漂移检测）。`specgen` 静态扫描（`go/ast`）抽取，编译成 case + `spec.json`。

## 标记语法

```go
// CreateNotebook ...（正常 doc 注释）
//
// +spec=`tenant/user header 必填；(tenant,user,name) 唯一，重复创建返回 ConflictError`
// +case:id=happy_minimal,desc=`只传 Name 应创建成功`,expect=`201; body.id 非空`
// +case:id=duplicate_name,desc=`重复 Name`,expect=`409`,forbid=`写入第二条记录`
// +link=docs/tenancy.md
// +link=internal/notebook/handler.go::Service.UpdateNotebook
// +rule=`这个 handler 在请求热路径，盯新增的同步 DB 调用`
func (s *Service) CreateNotebook(ctx context.Context, req *CreateReq) (*Notebook, error) {
```

- `+spec=\`...\`` — 0..1 条，该函数的契约前言（被它所有 case 共享）。
- `+case:...` — 0..N 条，字段 `id`（必填，`^[a-z][a-z0-9_]*$`）、`desc`（必填）、`input` / `expect` / `forbid`（自然语言，build-time 编译成结构化 `input` / `judge`）。
- `+link=<ref>` — 0..N 条，作者策展的"改它时该顺带看的东西"：`<ref>` = 仓库相对 **md 路径** 或 **symbol-id**（另一函数），靠有没有 `::` 区分。见 [概念](../docs/concepts.md#link)。
- `+rule=\`...\`` — 0..N 条，**审查准则**（评审它时盯什么），是 `rule.json` 路径级准则的共置细化；rule 是 reviewer 指令、不是代码已满足的契约（那是 spec）。见 [概念](../docs/concepts.md#rule)。
- 文本含逗号/换行时用反引号包裹。

**四个 marker（`+spec`/`+case`/`+link`/`+rule`）都可挂在类型（`type`）上**，描述该类型整体（契约/用例/see-also/用法约束）。其中 `+rule` 尤其常用——表达**类型级用法约束**："用到这个类型时盯什么"，供 review 在 diff *引用* 该类型时回溯注入。doc 注释挂在 `type` 声明上（单条 `type X` 挂在声明上，`type ( ... )` 组内挂在各 spec 上）：

```go
// +rule=`仅 per-request 使用——禁缓存/复用（events 无界累积）`
type PhaseEventMiddleware struct{ events []Event }
```

## 绑定（symbol-id）

标记所在符号决定 symbol-id（见 [`specs/symbol-id`](../specs/symbol-id/spec.md)）：

| 符号 | symbol-id |
|------|---------|
| 包级 `func Foo` @ `internal/x/y.go` | `internal/x/y.go::Foo` |
| 方法 `func (s *Service) CreateNotebook` @ `internal/notebook/handler.go` | `internal/notebook/handler.go::Service.CreateNotebook` |
| 类型 `type PhaseEventMiddleware` @ `common/middleware/trace.go` | `common/middleware/trace.go::PhaseEventMiddleware` |

每条 entry 另带可选 `fqn`——`importpath.Symbol`（如 `github.com/org/framework/common/middleware/trace.PhaseEventMiddleware`），import path 由 `go.mod` 的 module path + 目录推导，作跨仓引用的 location-independent 身份（供 ccr 从依赖模块解析 rule）。找不到 `go.mod` 则省略。

## 抽取产物

上面的例子经 `specgen` →

```jsonc
// spec.json 片段
{
  "internal/notebook/handler.go::Service.CreateNotebook": {
    "spec": "tenant/user header 必填；(tenant,user,name) 唯一，重复创建返回 ConflictError",
    "cases": [
      { "id": "happy_minimal",  "desc": "只传 Name 应创建成功", "expect": "201; body.id 非空" },
      { "id": "duplicate_name", "desc": "重复 Name", "expect": "409", "forbid": "写入第二条记录" }
    ],
    "links": ["docs/tenancy.md", "internal/notebook/handler.go::Service.UpdateNotebook"],
    "rules": ["这个 handler 在请求热路径，盯新增的同步 DB 调用"]
  }
}
```

`specgen` 的 Go 参考实现就在本仓 [`go/`](../go/)：`cd go && go build -o specgen .`，跑 `./specgen -root <repo-root> -o spec.json <src-dir>`（`go/ast` 静态扫描 doc 注释里的 marker，不编译 / 不运行被测代码）。

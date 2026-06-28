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
- `+link=<ref>` — 0..N 条，作者策展的"改它时该顺带看的东西"：`<ref>` = 仓库相对 **md 路径** 或 **unit-id**（另一函数），靠有没有 `::` 区分。见 [概念](../docs/concepts.md#link)。
- `+rule=\`...\`` — 0..N 条，函数级**审查准则**（评审它时盯什么），是 `rule.json` 路径级准则的共置细化；rule 是 reviewer 指令、不是代码已满足的契约（那是 spec）。见 [概念](../docs/concepts.md#rule)。
- 文本含逗号/换行时用反引号包裹。

## 绑定（unit-id）

标记所在函数决定 unit-id（见 [`specs/unit-id`](../specs/unit-id/spec.md)）：

| 符号 | unit-id |
|------|---------|
| 包级 `func Foo` @ `internal/x/y.go` | `internal/x/y.go::Foo` |
| 方法 `func (s *Service) CreateNotebook` @ `internal/notebook/handler.go` | `internal/notebook/handler.go::Service.CreateNotebook` |

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

# Go：spec/case 表达

Go 用**函数上方的 doc-comment 标记**写 spec/case，贴着它断言的函数（co-location + 漂移检测）。`specgen` 静态扫描（`go/ast`）抽取，编译成 case + `spec.json`。

## 标记语法

```go
// CreateNotebook ...（正常 doc 注释）
//
// +spec=`tenant/user header 必填；(tenant,user,name) 唯一，重复创建返回 ConflictError`
// +case:id=happy_minimal,desc=`只传 Name 应创建成功`,expect=`201; body.id 非空`
// +case:id=duplicate_name,desc=`重复 Name`,expect=`409`,forbid=`写入第二条记录`
func (s *Service) CreateNotebook(ctx context.Context, req *CreateReq) (*Notebook, error) {
```

- `+spec=\`...\`` — 0..1 条，该函数的契约前言（被它所有 case 共享）。
- `+case:...` — 0..N 条，字段 `id`（必填，`^[a-z][a-z0-9_]*$`）、`desc`（必填）、`input` / `expect` / `forbid`（自然语言，build-time 编译成结构化 `input` / `judge`）。
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
    ]
  }
}
```

`specgen` 是语言相关工具，按本仓契约在被测仓内实现（不在 spec-case 内）。

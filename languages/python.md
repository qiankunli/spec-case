# Python：spec/case 表达

Python 用**装饰器**写 spec/case，贴着它断言的函数（co-location + 漂移检测）。`specgen` 静态扫描（`ast`）抽取，编译成 case + `spec.json`。装饰器本身是 no-op（仅作标记），不改变运行时行为。

## 装饰器语法

```python
@spec("""
notebook 创建接口:
- tenant/user header 必填
- (tenant, user, name) 唯一，重复创建返回 ConflictError
""")
@case("happy_minimal", "只传 Name 应创建成功", expect="201; body.id 非空")
@case("duplicate_name", "重复 Name", expect="409", forbid="写入第二条记录")
@link("docs/tenancy.md")
@link("app/notebook/api.py::NotebookService.update_notebook")
@rule("这个 handler 在请求热路径，盯新增的同步 DB 调用")
async def create_notebook(req: CreateReq) -> Notebook:
    ...
```

- `@spec(text)` — 0..1 个，该函数的契约前言（被它所有 case 共享）。
- `@case(id, desc, *, input="", expect="", forbid="", group=...)` — 0..N 个，`id` 必填且 `^[a-z][a-z0-9_]*$`，`desc` 必填；`input` / `expect` / `forbid` 自然语言，build-time 编译成结构化 `input` / `judge`。
- `@link(ref)` — 0..N 个，作者策展的"改它时该顺带看的东西"：`ref` = 仓库相对 **md 路径** 或 **unit-id**（另一函数），靠有没有 `::` 区分。见 [概念](../docs/concepts.md#link)。
- `@rule(text)` — 0..N 个，函数级**审查准则**（评审它时盯什么），是 `rule.json` 路径级准则的共置细化；rule 是 reviewer 指令、不是代码已满足的契约（那是 spec）。见 [概念](../docs/concepts.md#rule)。

## 绑定（unit-id）

装饰器所在函数的 `__qualname__` 决定 unit-id（见 [`specs/unit-id`](../specs/unit-id/spec.md)）：

| 符号 | unit-id |
|------|---------|
| 模块级 `def create_notebook` @ `app/notebook/api.py` | `app/notebook/api.py::create_notebook` |
| 方法 `NotebookService.get` @ `app/notebook/api.py` | `app/notebook/api.py::NotebookService.get` |

## 抽取产物

上面的例子经 `specgen` →

```jsonc
// spec.json 片段
{
  "app/notebook/api.py::create_notebook": {
    "spec": "notebook 创建接口: tenant/user header 必填; (tenant,user,name) 唯一，重复创建返回 ConflictError",
    "cases": [
      { "id": "happy_minimal",  "desc": "只传 Name 应创建成功", "expect": "201; body.id 非空" },
      { "id": "duplicate_name", "desc": "重复 Name", "expect": "409", "forbid": "写入第二条记录" }
    ]
  }
}
```

`specgen` 的 Python 参考实现就在本仓 [`python/`](../python/)：装饰器从 `spec_case` import，抽取器跑 `python -m spec_case.specgen <src-dir> -o spec.json`（`ast` 静态扫描，不 import / 不运行被测代码）。

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
- `@link(ref)` — 0..N 个，作者策展的"改它时该顺带看的东西"：`ref` = 仓库相对 **md 路径** 或 **symbol-id**（另一函数），靠有没有 `::` 区分。见 [概念](../docs/concepts.md#link)。
- `@rule(text)` — 0..N 个，**审查准则**（评审它时盯什么），是 `rule.json` 路径级准则的共置细化；rule 是 reviewer 指令、不是代码已满足的契约（那是 spec）。见 [概念](../docs/concepts.md#rule)。

**四个 marker（`@spec`/`@case`/`@link`/`@rule`）都可挂在类上**，描述该类型整体（契约/用例/see-also/用法约束）。其中类级 `@rule` 尤其常用——表达**类型级用法约束**：不是"改这个类时盯什么"，而是"用到这个类型时盯什么"，供 review 在 diff *引用* 该类型时回溯注入。例：

```python
@rule("仅 per-request 使用——禁缓存/复用（events 无界累积）")
class PhaseEventMiddleware:
    ...
```

## 绑定（symbol-id）

装饰器所在符号的 `__qualname__` 决定 symbol-id（见 [`specs/symbol-id`](../specs/symbol-id/spec.md)）：

| 符号 | symbol-id |
|------|---------|
| 模块级 `def create_notebook` @ `app/notebook/api.py` | `app/notebook/api.py::create_notebook` |
| 方法 `NotebookService.get` @ `app/notebook/api.py` | `app/notebook/api.py::NotebookService.get` |
| 类 `class PhaseEventMiddleware` @ `common/middleware/trace.py` | `common/middleware/trace.py::PhaseEventMiddleware` |

每条 entry 另带可选 `fqn`——点号 import 路径（如 `common.middleware.trace.PhaseEventMiddleware`），由文件的 `__init__.py` 包链推导，作跨仓引用的 location-independent 身份（供 ccr 从依赖包解析 rule）。不在包内（无 `__init__.py`）则退化为模块 stem。

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

## specgen 怎么识别 marker（按名字 + 形状，不绑 import 来源）

specgen 纯静态扫 `ast`，按装饰器的**表面形态**识别，**不看它 import 自哪里**：

- **名字命中**：裸名 `@spec(...)` 或属性调用 `@m.spec(...)`，名字是 `spec`/`case`/`link`/`rule` 即算（裸 `@spec` 不带括号的不算——marker 都带参数）。
- **形状取值**：`case` 取位置参 0=`id`、位置参 1=`desc`，`input`/`expect`/`forbid` 取同名 kwarg；且**只读字符串字面量**（变量、f-string、拼接都取不到）。

推论：specgen 是这套 marker **grammar 的静态前端**，识别契约是"名字 + 参数形状"而非 import 来源。因此**任何遵循同一 grammar 的库**——哪怕装饰器 import 自别处、运行时行为不同（如做校验、挂属性供动态枚举）——只要名字与参数形状一致，specgen 都能原样抽成 `spec.json`。grammar 是契约，import 来源不是。

边界（duck-typing 的代价）：

- **别名会漏**：`from x import case as c` 后 `@c(...)` 不识别（表面名字变了）。
- **同名会被命中**：任何叫 `@case(...)`/`@spec(...)` 的装饰器都会进 `spec.json`，包括无关第三方库或业务自定义的同名装饰器——specgen 不校验来源。
- **非字面量取不到**：`@case(MY_ID, ...)` 这类首参非字符串字面量，`id` 取空 → 该 case 被跳过。

## 消费方如何依赖

与 Go 侧不对称：Go 的 marker 是 **doc 注释**（`+spec`），业务代码 import 任何东西都不需要；Python 的 marker 是**真装饰器**（`@spec`），在业务模块 **import 时就执行**，所以业务仓必须真的依赖 `spec_case`、且它要在**任何会 import 该模块的环境里都可导入**（含生产 runtime，不只是 CI）。好在 `spec_case` 零三方依赖、极轻，作为正式依赖成本可忽略。

发布在 PyPI，业务仓一行依赖同时解决两端：

```bash
uv add spec-case        # 或 pip install spec-case
```

```python
from spec_case import spec, case, link, rule
```

- **markers**：作为 runtime 依赖随之安装，装饰器在 import 时可用。
- **specgen**：同一个包带的 console script，CI 里直接 `uv run specgen <src-dir> -o spec.json --check`，**无需再加依赖**。`--check` 比对 committed `spec.json` 与当前 marker，漂移（重命名/删除符号、marker 改动）则非零退出——CI 漂移门。

> 不必为此把包拆成两个（markers 包 + specgen 包）：零依赖、specgen 在 runtime 从不被 import，多带一个 `.py` 成本为零。

详见包内 [`python/README.md`](../python/README.md)。

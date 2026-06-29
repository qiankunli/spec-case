# symbol-id Specification

## Purpose

定义把一条 spec / 一组 case 绑定到代码符号的稳定标识 **symbol-id**。它是 `specgen`（生产者）与 `ccr` 的 `UnitSplitter`（消费者）共用的 join key——两边必须用同一套规则计算，否则 spec/case 挂不上改动的 unit。

## Requirements

### Requirement: 标识格式

symbol-id 必须为 `<relpath>::<symbol>` 两段式。

#### Scenario: 通用结构

- **WHEN** 为任意语言的一个函数计算 symbol-id
- **THEN** `relpath` 是仓库根的相对路径，POSIX 正斜杠分隔
- **AND** 分隔符固定为 `::`
- **AND** `symbol` 是该语言下函数的规范名（见各语言 Requirement）
- **AND** 整串大小写敏感、不做归一化

### Requirement: Go 符号规范

Go 的 `symbol` 必须能无歧义定位到一个顶层函数或方法。

#### Scenario: 包级函数

- **WHEN** 符号是包级函数 `func Foo(...)`，文件 `internal/x/y.go`
- **THEN** symbol-id = `internal/x/y.go::Foo`

#### Scenario: 方法

- **WHEN** 符号是方法 `func (s *Service) CreateNotebook(...)`
- **THEN** `symbol` = `Service.CreateNotebook`（接收者去掉指针 `*`，无括号）
- **AND** symbol-id = `internal/notebook/handler.go::Service.CreateNotebook`

### Requirement: Python 符号规范

Python 的 `symbol` 必须是函数的 `__qualname__`（不含模块）。

#### Scenario: 模块级函数

- **WHEN** 符号是 `def create_notebook(...)`，文件 `app/notebook/api.py`
- **THEN** symbol-id = `app/notebook/api.py::create_notebook`

#### Scenario: 类方法

- **WHEN** 符号是 `NotebookService.get`
- **THEN** symbol-id = `app/notebook/api.py::NotebookService.get`

### Requirement: 基于符号、不基于行号

symbol-id 必须只由路径 + 符号决定，不含行号。

#### Scenario: 函数体内编辑

- **WHEN** 函数体被修改、或上方插入代码导致行号整体下移
- **THEN** symbol-id 不变（spec/case 仍挂得上）

#### Scenario: 重命名 = 新身份

- **WHEN** 函数或文件被重命名
- **THEN** 旧 symbol-id 不再解析到任何符号
- **AND** 这视为**漂移**：`specgen --check` 必须报错（spec 指向的符号已不存在），由人决定迁移或删除

### Requirement: 唯一性

在一个仓库快照内，symbol-id 必须唯一。

#### Scenario: 重载/同名

- **WHEN** 同一文件存在会产生相同 `<relpath>::<symbol>` 的两个符号（理论上的命名碰撞）
- **THEN** `specgen` 必须报错而非静默合并——契约要求 symbol 规范能区分二者；不能区分即视为该语言规范的缺陷，需在本 spec 补充

### Requirement: 消费契约

`spec.json`（见 `schemas/spec-json.schema.json`）必须以 symbol-id 为顶层 key。

#### Scenario: ccr 查表

- **WHEN** `ccr` 的 `UnitSplitter` 把一个改动函数解析出 symbol-id `U`
- **THEN** `SpecBuilder` 用 `U` 在 `spec.json` 查到 `{spec, cases[]}`
- **AND** 查不到 = 该函数无 spec/case（合法，跳过，不报错）

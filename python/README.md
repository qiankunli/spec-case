# spec-case (Python)

In-code **spec / case / link / rule** markers + **specgen**, the static extractor
that compiles them into `spec.json` — the artifact [`ccr`](https://github.com/qiankunli/case-code-review)
consumes. Part of [spec-case](https://github.com/qiankunli/spec-case); see the repo
for concepts, the unit-id contract, and the Go reference implementation.

## Install

```bash
uv add spec-case        # or: pip install spec-case
```

One dependency covers both ends: the markers are imported by your code at runtime,
and the same package ships the `specgen` console script for CI.

## Use the markers

The markers are **no-op decorators** — at runtime each returns the function
unchanged, so importing and annotating costs nothing and never changes behavior.
They only *mark* functions for specgen's static (`ast`) extraction.

```python
from spec_case import spec, case, link, rule

@spec("(tenant, name) unique; duplicate create -> ConflictError")
@case("happy_minimal", "only Name given should create", expect="201; body.id non-empty")
@case("duplicate_name", "duplicate Name", expect="409", forbid="a second row is written")
@link("docs/tenancy.md")
@rule("hot request path — watch new synchronous DB calls")
def create_notebook(req): ...
```

`spec_case` is zero-dependency (pure stdlib) and tiny, so taking it as a regular
runtime dependency is cheap. Because the decorators apply at **import time**, the
package must be importable anywhere the annotated module is imported (production
included) — it is a runtime dependency, not dev-only.

## Run specgen (CI)

Compile markers into `spec.json`, and gate drift in CI:

```bash
uv run specgen <src-dir> -o spec.json            # extract
uv run specgen <src-dir> -o spec.json --check    # CI gate: exit 1 if spec.json drifted
```

`--check` compares the committed `spec.json` against the current markers and fails
if a symbol was renamed/removed or a marker changed. specgen parses with `ast` and
never imports or runs your code.

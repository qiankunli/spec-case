"""spec-case (Python): the in-code spec/case/rule/link markers projects import,
plus `specgen` — the static extractor that compiles them into spec.json (the
artifact ccr's SpecBuilder consumes).

    from spec_case import spec, case, link, rule

    @spec("(tenant, name) unique; duplicate create -> ConflictError")
    @case("dup", "duplicate name", expect="409", forbid="a second row is written")
    def create_notebook(req): ...

Then: `python -m spec_case.specgen <src-dir> -o spec.json`.
"""
from .markers import case as case
from .markers import link as link
from .markers import rule as rule
from .markers import spec as spec


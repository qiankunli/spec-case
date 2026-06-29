import sys
from pathlib import Path

# importable when running tests straight from the repo (no install needed)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import spec_case  # noqa: E402
from spec_case import specgen  # noqa: E402

SAMPLE = '''
from spec_case import spec, case, link, rule

@spec("""
notebook create:
- tenant header required
- (tenant, name) unique -> ConflictError
""")
@case("happy", "name only succeeds", expect="201")
@case("dup", "duplicate name", expect="409", forbid="a second row is written")
@link("docs/tenancy.md")
@rule("hot path: watch new sync DB calls")
def create_notebook(req):
    ...

class Svc:
    @case("ok", "loads by id")
    def get(self, id):
        ...

def unmarked():
    ...
'''


def test_extract_markers():
    out = specgen.extract_file(SAMPLE, "app/api.py")

    e = out["app/api.py::create_notebook"]
    assert "tenant header required" in e["spec"]
    assert [c["id"] for c in e["cases"]] == ["happy", "dup"]
    assert e["cases"][0]["desc"] == "name only succeeds"
    assert e["cases"][1]["forbid"] == "a second row is written"
    assert e["links"] == ["docs/tenancy.md"]
    assert e["rules"] == ["hot path: watch new sync DB calls"]

    # a method binds to <relpath>::Class.method
    assert out["app/api.py::Svc.get"]["cases"][0]["id"] == "ok"

    # an unmarked function is absent
    assert "app/api.py::unmarked" not in out


def test_entry_always_has_cases():
    # a spec-only function still emits the (schema-required) cases array, empty
    out = specgen.extract_file('@spec("x")\ndef f(): ...\n', "f.py")
    assert out["f.py::f"] == {"cases": [], "spec": "x"}


def test_syntax_error_is_empty():
    assert specgen.extract_file("def (:", "bad.py") == {}


def test_markers_are_noops():
    def fn():
        return 1

    assert spec_case.spec("x")(fn) is fn
    assert spec_case.case("id", "d", expect="200")(fn) is fn
    assert spec_case.link("docs/x.md")(fn) is fn
    assert spec_case.rule("watch X")(fn) is fn


def _gen(tmp_path, body):
    src = tmp_path / "src"
    src.mkdir()
    (src / "a.py").write_text(body)
    out = tmp_path / "spec.json"
    specgen.main([str(src), "-o", str(out), "--root", str(src)])
    return src, out


def test_check_up_to_date(tmp_path):
    src, out = _gen(tmp_path, 'from spec_case import spec\n@spec("x")\ndef f(): ...\n')
    assert specgen.main([str(src), "-o", str(out), "--root", str(src), "--check"]) == 0


def test_check_reports_drift_on_rename(tmp_path):
    src, out = _gen(tmp_path, 'from spec_case import spec\n@spec("x")\ndef f(): ...\n')
    # rename the marked function -> its unit-id changes -> committed spec.json is stale
    (src / "a.py").write_text('from spec_case import spec\n@spec("x")\ndef g(): ...\n')
    assert specgen.main([str(src), "-o", str(out), "--root", str(src), "--check"]) == 1


def test_check_missing_file_is_drift(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "a.py").write_text('from spec_case import spec\n@spec("x")\ndef f(): ...\n')
    assert specgen.main([str(src), "-o", str(tmp_path / "nope.json"), "--root", str(src), "--check"]) == 1

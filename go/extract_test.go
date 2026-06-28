package main

import (
	"sort"
	"strings"
	"testing"
)

func TestExtractMarkers(t *testing.T) {
	src := "package p\n\n" +
		"// CreateNotebook creates a notebook.\n" +
		"//\n" +
		"// +spec=`(tenant,name) unique; dup -> ConflictError`\n" +
		"// +case:id=happy,desc=`name only`,expect=`201; id non-empty`\n" +
		"// +case:id=dup,desc=`duplicate name`,expect=`409`,forbid=`a second row is written`\n" +
		"// +link=docs/tenancy.md\n" +
		"// +rule=`hot path: watch new sync DB calls`\n" +
		"func (s *Service) CreateNotebook(req Req) error { return nil }\n\n" +
		"// Unmarked has no markers.\n" +
		"func Unmarked() {}\n"

	out := extractFile(src, "app/api.go")

	e, ok := out["app/api.go::Service.CreateNotebook"] // method binds to Recv.Method
	if !ok {
		t.Fatalf("missing CreateNotebook; got %v", sortedKeys(out))
	}
	if !strings.Contains(e.Spec, "ConflictError") {
		t.Errorf("spec: %q", e.Spec)
	}
	if len(e.Cases) != 2 || e.Cases[0].ID != "happy" || e.Cases[1].ID != "dup" {
		t.Fatalf("cases: %+v", e.Cases)
	}
	if e.Cases[0].Expect != "201; id non-empty" { // semicolon inside backticks survives
		t.Errorf("expect: %q", e.Cases[0].Expect)
	}
	if e.Cases[1].Forbid != "a second row is written" {
		t.Errorf("forbid: %q", e.Cases[1].Forbid)
	}
	if len(e.Links) != 1 || e.Links[0] != "docs/tenancy.md" {
		t.Errorf("links: %v", e.Links)
	}
	if len(e.Rules) != 1 {
		t.Errorf("rules: %v", e.Rules)
	}
	if _, ok := out["app/api.go::Unmarked"]; ok {
		t.Error("unmarked func should be absent")
	}
}

func TestParseMarkerArgs_QuotingAndCommas(t *testing.T) {
	args := parseMarkerArgs("id=x,desc=`a, b, c`,expect=plain,note=\"d, e\"")
	if args["desc"] != "a, b, c" { // commas inside backticks are literal
		t.Errorf("backtick desc: %q", args["desc"])
	}
	if args["note"] != "d, e" { // double-quote wrapping also supported
		t.Errorf("quoted note: %q", args["note"])
	}
	if args["expect"] != "plain" { // unquoted runs to the next comma
		t.Errorf("unquoted: %q", args["expect"])
	}
}

func TestMalformedCaseIDSkipped(t *testing.T) {
	out := extractFile("package p\n\n// +case:id=Bad-ID,desc=`x`\nfunc f() {}\n", "f.go")
	if _, ok := out["f.go::f"]; ok {
		t.Error("a function whose only case has a malformed id should be absent")
	}
}

func TestSpecOnlyHasEmptyCases(t *testing.T) {
	out := extractFile("package p\n\n// +spec=`x`\nfunc f() {}\n", "f.go")
	e := out["f.go::f"]
	if e.Spec != "x" || e.Cases == nil || len(e.Cases) != 0 {
		t.Errorf("spec-only entry must have empty non-nil cases: %+v", e)
	}
}

func TestUnparseableIsNil(t *testing.T) {
	if extractFile("func (:", "bad.go") != nil {
		t.Error("unparseable source should extract to nil")
	}
}

func sortedKeys(m map[string]Entry) []string {
	ks := make([]string, 0, len(m))
	for k := range m {
		ks = append(ks, k)
	}
	sort.Strings(ks)
	return ks
}

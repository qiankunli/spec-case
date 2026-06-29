package main

import (
	"os"
	"path/filepath"
	"testing"
)

func TestRunCheck(t *testing.T) {
	dir := t.TempDir()
	out := filepath.Join(dir, "spec.json")
	index := map[string]Entry{"a.go::F": {Spec: "x", Cases: []Case{}}}

	data, _ := canonical(index)
	if err := os.WriteFile(out, data, 0o644); err != nil {
		t.Fatal(err)
	}

	if rc := runCheck(out, index); rc != 0 {
		t.Errorf("identical index should be up to date, rc=%d want 0", rc)
	}
	renamed := map[string]Entry{"a.go::G": {Spec: "x", Cases: []Case{}}}
	if rc := runCheck(out, renamed); rc != 1 {
		t.Errorf("renamed symbol should drift, rc=%d want 1", rc)
	}
	changed := map[string]Entry{"a.go::F": {Spec: "y", Cases: []Case{}}}
	if rc := runCheck(out, changed); rc != 1 {
		t.Errorf("changed markers should drift, rc=%d want 1", rc)
	}
	if rc := runCheck(filepath.Join(dir, "nope.json"), index); rc != 1 {
		t.Errorf("missing spec.json should drift, rc=%d want 1", rc)
	}
	if rc := runCheck("-", index); rc != 2 {
		t.Errorf("stdout target is misuse, rc=%d want 2", rc)
	}
}

// TestRunCheck_RealRoundTrip guards the nil-vs-empty-cases trap: a fresh extract
// written then re-checked must report up-to-date, not spurious drift.
func TestRunCheck_RealRoundTrip(t *testing.T) {
	dir := t.TempDir()
	if err := os.WriteFile(filepath.Join(dir, "h.go"),
		[]byte("package p\n\n// +spec=`x`\nfunc F() {}\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	idx, err := extractTree(dir, dir)
	if err != nil {
		t.Fatal(err)
	}
	out := filepath.Join(dir, "spec.json")
	data, _ := canonical(idx)
	if err := os.WriteFile(out, data, 0o644); err != nil {
		t.Fatal(err)
	}
	idx2, _ := extractTree(dir, dir)
	if rc := runCheck(out, idx2); rc != 0 {
		t.Errorf("freshly-extracted spec.json should be up to date, rc=%d", rc)
	}
}

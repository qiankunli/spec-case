package main

import (
	"bytes"
	"encoding/json"
	"flag"
	"fmt"
	"os"
	"sort"
)

func main() {
	out := flag.String("o", "-", "output path (default: stdout)")
	root := flag.String("root", "", "repo root for relpath symbol-ids (default: src)")
	check := flag.Bool("check", false, "compare against -o instead of writing; exit 1 if spec.json is out of date (CI drift gate)")
	flag.Parse()
	if flag.NArg() != 1 {
		fmt.Fprintln(os.Stderr, "usage: specgen [-o spec.json] [-root <repo-root>] [-check] <src-dir>")
		os.Exit(2)
	}
	src := flag.Arg(0)
	r := *root
	if r == "" {
		r = src
	}

	index, err := extractTree(src, r)
	if err != nil {
		fmt.Fprintln(os.Stderr, "specgen:", err)
		os.Exit(1)
	}

	if *check {
		os.Exit(runCheck(*out, index))
	}

	data, err := canonical(index)
	if err != nil {
		fmt.Fprintln(os.Stderr, "specgen:", err)
		os.Exit(1)
	}
	if *out == "-" {
		fmt.Print(string(data))
		return
	}
	if err := os.WriteFile(*out, data, 0o644); err != nil {
		fmt.Fprintln(os.Stderr, "specgen:", err)
		os.Exit(1)
	}
	fmt.Fprintf(os.Stderr, "specgen: %d symbol(s) -> %s\n", len(index), *out)
}

// canonical renders v as deterministic JSON — sorted map keys (Go sorts them),
// -> / < / & kept literal, trailing newline — the exact form specgen writes, so
// --check can compare formatting- and nil/empty-slice-independently.
func canonical(v any) ([]byte, error) {
	var buf bytes.Buffer
	enc := json.NewEncoder(&buf)
	enc.SetEscapeHTML(false)
	enc.SetIndent("", "  ")
	if err := enc.Encode(v); err != nil {
		return nil, err
	}
	return buf.Bytes(), nil
}

// runCheck compares the freshly-extracted index against the committed spec.json
// at `out`. Drift means the markers no longer match what's committed — a symbol
// was renamed/moved (new symbol-id), removed, or its markers changed without
// regenerating. Returns 0 up-to-date, 1 on drift, 2 on misuse.
func runCheck(out string, fresh map[string]Entry) int {
	if out == "-" {
		fmt.Fprintln(os.Stderr, "specgen -check needs -o <spec.json>")
		return 2
	}
	data, err := os.ReadFile(out)
	if err != nil {
		fmt.Fprintf(os.Stderr, "specgen -check: %s does not exist — run specgen to create it\n", out)
		return 1
	}
	committed := map[string]Entry{}
	if len(bytes.TrimSpace(data)) > 0 {
		if err := json.Unmarshal(data, &committed); err != nil {
			fmt.Fprintf(os.Stderr, "specgen -check: %s is not valid JSON: %v\n", out, err)
			return 1
		}
	}

	freshJSON, _ := canonical(fresh)
	committedJSON, _ := canonical(committed)
	if bytes.Equal(freshJSON, committedJSON) {
		fmt.Fprintf(os.Stderr, "specgen -check: %s is up to date (%d symbol(s))\n", out, len(fresh))
		return 0
	}

	fmt.Fprintf(os.Stderr, "specgen -check: %s is out of date — run specgen to regenerate:\n", out)
	reportDrift(committed, fresh)
	return 1
}

func reportDrift(committed, fresh map[string]Entry) {
	for _, uid := range sortedIDs(fresh) {
		if _, ok := committed[uid]; !ok {
			fmt.Fprintf(os.Stderr, "  + %s  (marked in code, missing from spec.json)\n", uid)
		}
	}
	for _, uid := range sortedIDs(committed) {
		if _, ok := fresh[uid]; !ok {
			fmt.Fprintf(os.Stderr, "  - %s  (in spec.json, but no such marked symbol — renamed/removed)\n", uid)
		}
	}
	for _, uid := range sortedIDs(fresh) {
		c, ok := committed[uid]
		if !ok {
			continue
		}
		cj, _ := canonical(c)
		fj, _ := canonical(fresh[uid])
		if !bytes.Equal(cj, fj) {
			fmt.Fprintf(os.Stderr, "  ~ %s  (markers changed)\n", uid)
		}
	}
}

func sortedIDs(m map[string]Entry) []string {
	ids := make([]string, 0, len(m))
	for k := range m {
		ids = append(ids, k)
	}
	sort.Strings(ids)
	return ids
}

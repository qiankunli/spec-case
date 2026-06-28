package main

import (
	"bytes"
	"encoding/json"
	"flag"
	"fmt"
	"os"
)

func main() {
	out := flag.String("o", "-", "output path (default: stdout)")
	root := flag.String("root", "", "repo root for relpath unit-ids (default: src)")
	flag.Parse()
	if flag.NArg() != 1 {
		fmt.Fprintln(os.Stderr, "usage: specgen [-o spec.json] [-root <repo-root>] <src-dir>")
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
	// Encoder (not Marshal) so we can keep ->, <, & literal instead of > etc.
	// Go sorts map keys, so output is deterministic; Encode appends a newline.
	var buf bytes.Buffer
	enc := json.NewEncoder(&buf)
	enc.SetEscapeHTML(false)
	enc.SetIndent("", "  ")
	if err := enc.Encode(index); err != nil {
		fmt.Fprintln(os.Stderr, "specgen:", err)
		os.Exit(1)
	}
	if *out == "-" {
		fmt.Print(buf.String())
		return
	}
	if err := os.WriteFile(*out, buf.Bytes(), 0o644); err != nil {
		fmt.Fprintln(os.Stderr, "specgen:", err)
		os.Exit(1)
	}
	fmt.Fprintf(os.Stderr, "specgen: %d symbol(s) -> %s\n", len(index), *out)
}

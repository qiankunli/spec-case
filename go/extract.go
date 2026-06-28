// Command specgen statically extracts the +spec/+case/+link/+rule doc-comment
// markers from Go sources into spec.json — the artifact ccr's SpecBuilder
// consumes. Discovery is pure go/ast analysis: the scanned code is never
// imported or run, so the markers cost nothing at build time and work even when
// the code does not compile.
//
// The marker grammar follows kubebuilder's convention — a "+" prefix and a
// single-line "name:key=value" form, which sidesteps gofmt's reflow of
// multi-line doc comments — but is parsed directly here (no controller-tools
// dependency, which buys little for these all-string fields).
package main

import (
	"go/ast"
	"go/parser"
	"go/token"
	"io/fs"
	"os"
	"path/filepath"
	"regexp"
	"strings"
)

// caseIDPattern constrains a case id to a stable, file-name-safe slug — the
// schema's ^[a-z][a-z0-9_]*$. It doubles as a cross-run primary key, so it must
// be immutable and unique; a case with a malformed id is skipped.
var caseIDPattern = regexp.MustCompile(`^[a-z][a-z0-9_]*$`)

// Case mirrors one spec.json case entry.
type Case struct {
	ID     string `json:"id"`
	Desc   string `json:"desc,omitempty"`
	Input  string `json:"input,omitempty"`
	Expect string `json:"expect,omitempty"`
	Forbid string `json:"forbid,omitempty"`
}

// Entry is one symbol's spec.json entry (keyed by its unit-id).
type Entry struct {
	Spec  string   `json:"spec,omitempty"`
	Cases []Case   `json:"cases"` // required by the schema; may be empty
	Links []string `json:"links,omitempty"`
	Rules []string `json:"rules,omitempty"`
}

// parseMarkers scans a function's doc comment for the markers and builds its
// entry, or returns ok=false when it carries none. Each marker is one line.
func parseMarkers(doc *ast.CommentGroup) (Entry, bool) {
	e := Entry{Cases: []Case{}}
	found := false
	for _, c := range doc.List {
		line := strings.TrimSpace(strings.TrimPrefix(strings.TrimSpace(c.Text), "//"))
		switch {
		case strings.HasPrefix(line, "+spec="):
			e.Spec = unquote(strings.TrimPrefix(line, "+spec="))
			found = true
		case strings.HasPrefix(line, "+case:"):
			args := parseMarkerArgs(strings.TrimPrefix(line, "+case:"))
			if !caseIDPattern.MatchString(args["id"]) {
				continue // malformed id — skip this case
			}
			e.Cases = append(e.Cases, Case{
				ID: args["id"], Desc: args["desc"],
				Input: args["input"], Expect: args["expect"], Forbid: args["forbid"],
			})
			found = true
		case strings.HasPrefix(line, "+link="):
			if v := unquote(strings.TrimPrefix(line, "+link=")); v != "" {
				e.Links = append(e.Links, v)
				found = true
			}
		case strings.HasPrefix(line, "+rule="):
			if v := unquote(strings.TrimPrefix(line, "+rule=")); v != "" {
				e.Rules = append(e.Rules, v)
				found = true
			}
		}
	}
	return e, found
}

// parseMarkerArgs splits a "key=value,key=value" string. A value may be backtick-
// or double-quote-wrapped, in which case embedded commas/semicolons are literal;
// an unquoted value runs to the next comma.
func parseMarkerArgs(s string) map[string]string {
	args := map[string]string{}
	for i, n := 0, len(s); i < n; {
		for i < n && (s[i] == ',' || s[i] == ' ') {
			i++
		}
		keyStart := i
		for i < n && s[i] != '=' {
			i++
		}
		if i >= n {
			break // no '=' → malformed tail, stop
		}
		key := strings.TrimSpace(s[keyStart:i])
		i++ // skip '='
		var val string
		if i < n && (s[i] == '`' || s[i] == '"') {
			q := s[i]
			i++
			start := i
			for i < n && s[i] != q {
				i++
			}
			val = s[start:i]
			if i < n {
				i++ // skip closing quote
			}
		} else {
			start := i
			for i < n && s[i] != ',' {
				i++
			}
			val = strings.TrimSpace(s[start:i])
		}
		if key != "" {
			args[key] = val
		}
	}
	return args
}

// unquote strips a single layer of matching backtick or double quotes.
func unquote(s string) string {
	s = strings.TrimSpace(s)
	if len(s) >= 2 && (s[0] == '`' || s[0] == '"') && s[len(s)-1] == s[0] {
		return s[1 : len(s)-1]
	}
	return s
}

// symbolOf returns a function's symbol: "Name" for a free function, "Recv.Method"
// for a method (receiver normalized — pointer and generic params stripped), so
// the unit-id matches the contract and ccr's Go splitter.
func symbolOf(fd *ast.FuncDecl) string {
	if recv := recvTypeName(fd); recv != "" {
		return recv + "." + fd.Name.Name
	}
	return fd.Name.Name
}

func recvTypeName(fd *ast.FuncDecl) string {
	if fd.Recv == nil || len(fd.Recv.List) == 0 {
		return ""
	}
	expr := fd.Recv.List[0].Type
	if star, ok := expr.(*ast.StarExpr); ok { // *T
		expr = star.X
	}
	switch e := expr.(type) {
	case *ast.IndexExpr: // T[P]
		expr = e.X
	case *ast.IndexListExpr: // T[P, Q]
		expr = e.X
	}
	if id, ok := expr.(*ast.Ident); ok {
		return id.Name
	}
	return ""
}

// extractFile parses Go source and returns spec.json entries keyed by unit-id
// (<relpath>::<symbol>). Returns nil on a parse error — specgen never fails the
// build.
func extractFile(src, relpath string) map[string]Entry {
	fset := token.NewFileSet()
	f, err := parser.ParseFile(fset, relpath, src, parser.ParseComments|parser.SkipObjectResolution)
	if err != nil {
		return nil
	}
	out := map[string]Entry{}
	for _, decl := range f.Decls {
		fd, ok := decl.(*ast.FuncDecl)
		if !ok || fd.Doc == nil {
			continue
		}
		if e, ok := parseMarkers(fd.Doc); ok {
			out[relpath+"::"+symbolOf(fd)] = e
		}
	}
	return out
}

// extractTree extracts spec.json from every .go under srcDir; unit-id paths are
// relative to root (the repo root, so keys match ccr's review address space).
func extractTree(srcDir, root string) (map[string]Entry, error) {
	out := map[string]Entry{}
	err := filepath.WalkDir(srcDir, func(path string, d fs.DirEntry, err error) error {
		if err != nil || d.IsDir() || !strings.HasSuffix(path, ".go") {
			return err
		}
		src, readErr := os.ReadFile(path)
		if readErr != nil {
			return nil // skip unreadable
		}
		rel, relErr := filepath.Rel(root, path)
		if relErr != nil {
			return nil
		}
		for k, v := range extractFile(string(src), filepath.ToSlash(rel)) {
			out[k] = v
		}
		return nil
	})
	return out, err
}

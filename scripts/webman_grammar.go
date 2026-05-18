// webman_grammar: derive a formal grammar of the WEB source-file syntax.
//
// Two input modes, dispatched on the filename extension:
//
//   *.tex — Knuth's webman.tex user manual. The manual is prose, but the
//     control-code table in "\section Control codes." has the mechanical
//     shape `\@<code> [<contexts>] <prose>`, where contexts are a subset
//     of {L, T, P, M, C, S} with `\overline` (or \oP / \oT shortcuts)
//     meaning "terminates this part of the file". The extracted table is
//     paired with a hand-encoded top-level grammar transcribed from
//     "\section General rules." and "\section Macros."
//
//   *.web — weave.web or tangle.web. Both are literate Pascal programs
//     whose scanner IS the authoritative WEB syntax. We mine two
//     structures: (a) `@d NAME=@'OCTAL {comment}` constant definitions
//     and (b) the `case c of ... endcases` table inside
//     `function control_code`. Joining them gives user form → symbolic
//     category → opcode. webman mode is better for legality-per-context;
//     web mode is better for opcode/category ground truth.
//
// Usage: go run webman_grammar.go <path>
package main

import (
	"bufio"
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"strings"
)

// A codeEntry is one control-code description extracted from
// \section Control codes.
type codeEntry struct {
	raw       string   // exact \@... token from the .tex file
	code      string   // normalized two-char code, e.g. "@d", "@'", "@ "
	allow     []string // contexts where this code is legal: subset of {L,T,P,M,C,S}
	terminate []string // contexts this code ends (overlined in the manual)
	desc      string   // first sentence of prose, TeX-stripped
	sourceLn  int      // 1-based line number in webman.tex
}

// hand-encoded top-level grammar, transcribed from the prose in
// "\section General rules." (lines 154–397 of webman.tex) and
// "\section Macros." (lines 398–535). Kept separate from the extracted
// control-code table so that "mechanically derived" and "transcribed
// from prose" are visibly distinct.
const topLevelEBNF = `(* -------- Top-level structure (transcribed from §General rules) -------- *)

web_file        = limbo , module+ ;
limbo           = tex_text ;                  (* material before the first module;
                                                 only @@ is legal here *)

module          = module_start , tex_part , definition_part? , pascal_part? ;
module_start    = "@ " | "@*" ;               (* "@ " = at-sign + space;
                                                 "@*" starts a starred major group *)

tex_part        = tex_text ;                   (* may embed |pascal_text| and module_name *)
definition_part = ( macro_def | format_def )+ ;
pascal_part     = unnamed_pascal_part | named_pascal_part ;
unnamed_pascal_part = "@p" , pascal_text ;
named_pascal_part   = module_name , "=" , pascal_text ;

module_name     = "@<" , tex_text , "@>" ;     (* abbreviation: prefix "..." before @> *)

(* -------- Macro forms (transcribed from §Macros) -------- *)

macro_def          = numeric_macro | simple_macro | parametric_macro ;
numeric_macro      = "@d" , identifier , "=" , numeric_rhs ;
simple_macro       = "@d" , identifier , "==" , pascal_text ;
parametric_macro   = "@d" , identifier , "(#)" , "==" , pascal_text ;
numeric_rhs        = numeric_term , ( ("+" | "-") , numeric_term )* ;
numeric_term       = integer | numeric_macro_name | preprocessed_string | pascal_comment ;
preprocessed_string = '"' , { any_char_except_quote | '""' } , '"' ;

format_def         = "@f" , identifier , "==" , identifier , pascal_comment? ;

(* -------- Change-file grammar (transcribed from §Additional features 11) -------- *)

change_file     = interchange_line* , change* , interchange_line* ;
change          = "@x" , rest_of_line , web_line+ ,
                  "@y" , rest_of_line , web_line* ,
                  "@z" , rest_of_line ;
(* @x @y @z must be the first two characters of a line;
   the rest of that line is ignored. *)

`

// The context letters used inside brackets in the control-codes table.
var contextNames = map[string]string{
	"L": "limbo",
	"T": "TeX text",
	"P": "Pascal text",
	"M": "module name",
	"C": "comment",
	"S": "string",
}

const contextLegend = `(* Context legend:
     L = limbo (before first module)
     T = TeX text
     P = Pascal text
     M = module name
     C = comment (braces inside Pascal text)
     S = string
   "terminates" means the code ends the surrounding part; the manual
   renders this as an overline (\overline L, \oP, \oT). *)`

// Stop reading the Control codes section when we hit the next
// \section, or earlier if we hit the explicit closing paragraph.
var (
	sectionRe   = regexp.MustCompile(`^\s*\\section\s+(.+)\.$`)
	// Note: use \s* not \s+ — for the space-code entry the code
	// character IS a space (the line is `\@\ [...]` with no extra
	// separator before `[`). Every other entry has at least one space.
	codeStartRe = regexp.MustCompile(`^\\@(\\.|\S)\s*\[([^\]]+)\]\s*(.*)$`)
	// Bracket contents like "\overline L,\oP,\oT" or "P,T".
	contextTokenRe = regexp.MustCompile(`\\overline\s+([LTPMCS])|\\o([LTPMCS])|([LTPMCS])`)
)

// extractControlCodes scans webman.tex and pulls out every entry inside
// the "Control codes" section.
func extractControlCodes(r *bufio.Scanner) ([]codeEntry, error) {
	var (
		entries []codeEntry
		lineNo  int
		inSec   bool
		cur     *codeEntry
		prose   strings.Builder
	)

	flush := func() {
		if cur == nil {
			return
		}
		cur.desc = firstSentence(stripTeX(strings.TrimSpace(prose.String())))
		entries = append(entries, *cur)
		cur = nil
		prose.Reset()
	}

	for r.Scan() {
		lineNo++
		line := r.Text()

		if m := sectionRe.FindStringSubmatch(line); m != nil {
			if inSec {
				flush()
				return entries, nil // hit next section; done
			}
			if strings.EqualFold(strings.TrimSpace(m[1]), "Control codes") {
				inSec = true
			}
			continue
		}
		if !inSec {
			continue
		}

		if m := codeStartRe.FindStringSubmatch(line); m != nil {
			flush()
			cur = &codeEntry{
				raw:      fmt.Sprintf(`\@%s`, m[1]),
				code:     normalizeCode(m[1]),
				sourceLn: lineNo,
			}
			cur.allow, cur.terminate = parseContexts(m[2])
			prose.WriteString(m[3])
			prose.WriteByte(' ')
			continue
		}

		if cur != nil {
			// Continuation of the current entry's prose until blank
			// line or next \@... — the manual always separates entries
			// by a blank line.
			if strings.TrimSpace(line) == "" {
				// keep accumulating across blank lines; the entry ends
				// only at the next \@... or \section
				prose.WriteByte(' ')
				continue
			}
			prose.WriteString(line)
			prose.WriteByte(' ')
		}
	}
	flush()
	return entries, r.Err()
}

// normalizeCode turns a TeX-escaped control-code token into the
// two-character form a WEB user would actually type. The first
// character is always '@'; the second is recovered from the escape.
func normalizeCode(s string) string {
	switch s {
	case `\ `:
		return "@ "
	case `\\`:
		return `@\`
	case `\'`:
		return "@'"
	case `\"`:
		return `@"`
	case `\$`:
		return "@$"
	case `\{`:
		return "@{"
	case `\}`:
		return "@}"
	case `\&`:
		return "@&"
	case `\^`:
		return "@^"
	case `\#`:
		return "@#"
	}
	// unescaped single character (d, f, p, <, *, !, ?, ,, /, |, +, ;, ., :, t, =, @, ")
	return "@" + s
}

// parseContexts splits a bracket expression such as `P,\oT` into
// allow-letters and terminate-letters.
func parseContexts(s string) (allow, term []string) {
	allowed := map[string]bool{}
	termed := map[string]bool{}
	for _, m := range contextTokenRe.FindAllStringSubmatch(s, -1) {
		switch {
		case m[1] != "":
			termed[m[1]] = true // \overline X
		case m[2] != "":
			termed[m[2]] = true // \oX shortcut
		case m[3] != "":
			allowed[m[3]] = true
		}
	}
	allow = sortedKeys(allowed)
	term = sortedKeys(termed)
	return
}

func sortedKeys(m map[string]bool) []string {
	out := make([]string, 0, len(m))
	for k := range m {
		out = append(out, k)
	}
	sort.Strings(out)
	return out
}

// stripTeX removes the inline TeX control sequences that appear in the
// prose (\.{...}, \\{...}, \&{...}, \TeX, \PASCAL, etc.) so the
// extracted description is readable as plain text. It is a
// best-effort cleanup, not a TeX parser.
var (
	braceGroupRe = regexp.MustCompile(`\\(\.|\\|&|\|)\{([^{}]*)\}`)
	texWordRe    = regexp.MustCompile(`\\(TeX|PASCAL|WEB|TANGLE|WEAVE)\\?\s*`)
	inlinePbRe   = regexp.MustCompile(`\\pb\b`)
	dotRunRe     = regexp.MustCompile(`\\\.`)
	yskipRe      = regexp.MustCompile(`\\(yskip|hang|noindent|quad|qquad)\b\s*`)
	itemRe       = regexp.MustCompile(`\\itemitem?\{[^}]*\}\s*`)
	mathRe       = regexp.MustCompile(`\$[^$]*\$`)
	remainingRe  = regexp.MustCompile(`\\[A-Za-z]+\s?`)
)

func stripTeX(s string) string {
	s = braceGroupRe.ReplaceAllString(s, "$2")
	s = texWordRe.ReplaceAllStringFunc(s, func(m string) string {
		switch {
		case strings.HasPrefix(m, `\TeX`):
			return "TeX "
		case strings.HasPrefix(m, `\PASCAL`):
			return "Pascal "
		case strings.HasPrefix(m, `\WEB`):
			return "WEB "
		case strings.HasPrefix(m, `\TANGLE`):
			return "TANGLE "
		case strings.HasPrefix(m, `\WEAVE`):
			return "WEAVE "
		}
		return ""
	})
	s = inlinePbRe.ReplaceAllString(s, "|...|")
	s = dotRunRe.ReplaceAllString(s, "")
	s = yskipRe.ReplaceAllString(s, "")
	s = itemRe.ReplaceAllString(s, "")
	s = mathRe.ReplaceAllString(s, "")
	s = remainingRe.ReplaceAllString(s, "")
	s = strings.ReplaceAll(s, "{", "")
	s = strings.ReplaceAll(s, "}", "")
	s = strings.Join(strings.Fields(s), " ")
	return s
}

// firstSentence keeps at most the first sentence, so the table stays
// one-line-per-entry. The full prose for each code is in webman.tex.
func firstSentence(s string) string {
	for i := 0; i < len(s)-1; i++ {
		if s[i] == '.' && (s[i+1] == ' ' || s[i+1] == '\t') {
			return s[:i+1]
		}
	}
	return s
}

func render(entries []codeEntry, src string) string {
	var b strings.Builder

	fmt.Fprintf(&b, "(* WEB source-file grammar.\n")
	fmt.Fprintf(&b, "   Control-code table auto-extracted from %s.\n", src)
	fmt.Fprintf(&b, "   Top-level productions transcribed from the prose sections of the same file.\n")
	fmt.Fprintf(&b, "   Format: ISO-ish EBNF. *)\n\n")

	b.WriteString(contextLegend)
	b.WriteString("\n\n")
	b.WriteString(topLevelEBNF)

	b.WriteString("(* -------- Control codes (auto-extracted from §Control codes) -------- *)\n\n")
	b.WriteString("control_code =\n")

	// Alphabetize for determinism; print the first entry with a leading
	// "  " and subsequent entries with "| ".
	sort.Slice(entries, func(i, j int) bool {
		return entries[i].code < entries[j].code
	})
	for i, e := range entries {
		sep := "  "
		if i > 0 {
			sep = "| "
		}
		fmt.Fprintf(&b, "  %s%-6s", sep, quoteCode(e.code))
		fmt.Fprintf(&b, "  (* allow=%s", fmtSet(e.allow))
		if len(e.terminate) > 0 {
			fmt.Fprintf(&b, " terminates=%s", fmtSet(e.terminate))
		}
		fmt.Fprintf(&b, " — %s *)\n", e.desc)
	}
	b.WriteString("  ;\n")

	return b.String()
}

func quoteCode(c string) string {
	// EBNF-style literal. The only problematic characters are " and \.
	// Render " via single quotes; escape \ to \\ so the output reads as
	// an unambiguous two-character token (especially @\\ vs @" space).
	if strings.ContainsRune(c, '"') {
		return `'` + c + `'`
	}
	escaped := strings.ReplaceAll(c, `\`, `\\`)
	return `"` + escaped + `"`
}

func fmtSet(xs []string) string {
	if len(xs) == 0 {
		return "(none)"
	}
	return strings.Join(xs, ",")
}

func main() {
	if len(os.Args) != 2 {
		fmt.Fprintf(os.Stderr, "usage: %s <path-to-webman.tex|tangle.web|weave.web>\n", os.Args[0])
		os.Exit(2)
	}
	path := os.Args[1]
	ext := strings.ToLower(filepath.Ext(path))
	switch ext {
	case ".tex":
		runWebmanMode(path)
	case ".web":
		runWebMode(path)
	default:
		fmt.Fprintf(os.Stderr, "unknown file type %q: expected .tex or .web\n", ext)
		os.Exit(2)
	}
}

func runWebmanMode(path string) {
	f, err := os.Open(path)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	defer f.Close()

	entries, err := extractControlCodes(bufio.NewScanner(f))
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	if len(entries) == 0 {
		fmt.Fprintln(os.Stderr, "no control-code entries found — wrong file?")
		os.Exit(1)
	}
	fmt.Print(render(entries, path))
}

func runWebMode(path string) {
	data, err := os.ReadFile(path)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	lines := strings.Split(string(data), "\n")
	tokens := extractTokenConsts(lines)
	entries, ok := extractControlCodeCaseTable(lines)
	if !ok {
		fmt.Fprintln(os.Stderr, "could not locate `function control_code` case table — wrong file?")
		os.Exit(1)
	}
	fmt.Print(renderWebMode(path, tokens, entries))
}

// webToken is one `@d NAME=@'OCTAL {comment}` definition. In weave.web
// and tangle.web these constants spell out the token enum used by the
// scanner; the ones used as control_code case-table targets form the
// WEB token inventory.
type webToken struct {
	name    string
	octal   string // without leading @'
	comment string
	line    int
}

var tokenDefRe = regexp.MustCompile(`^@d\s+(\w+)\s*=\s*@'(\d+)\s*\{(.*)\}\s*$`)

func extractTokenConsts(lines []string) map[string]webToken {
	out := map[string]webToken{}
	for i, line := range lines {
		if m := tokenDefRe.FindStringSubmatch(line); m != nil {
			out[m[1]] = webToken{
				name:    m[1],
				octal:   m[2],
				comment: strings.TrimSpace(m[3]),
				line:    i + 1,
			}
		}
	}
	return out
}

// caseEntry is one row of the `case c of ... endcases` table inside
// `function control_code`. The keys are the user-typed characters (or
// identifiers like tab_mark) that dispatch to the destination token.
type caseEntry struct {
	userForms []string // normalized "@ ", "@<TAB>", "@*", "@D", etc.
	dst       string   // symbolic token name, or a literal char (for "@@")
	dstIsChar bool     // true iff RHS was a string literal (e.g. "@@")
}

// dstRe matches the statement that follows the case-label colon,
// capturing the destination (identifier or quoted literal). A trailing
// {...} Pascal comment is permitted and ignored.
var dstRe = regexp.MustCompile(`^control_code\s*:=\s*([^;]+?)\s*;`)

// findTopColon returns the index of the first `:` that is not inside a
// Pascal-style double-quoted string. Needed because case labels
// include `":"` (the colon character) as a valid label.
func findTopColon(s string) int {
	inStr := false
	for i := 0; i < len(s); i++ {
		c := s[i]
		if c == '"' {
			if inStr && i+1 < len(s) && s[i+1] == '"' {
				i++
				continue
			}
			inStr = !inStr
			continue
		}
		if c == ':' && !inStr {
			return i
		}
	}
	return -1
}

func extractControlCodeCaseTable(lines []string) ([]caseEntry, bool) {
	// Find the function header.
	start := -1
	for i, line := range lines {
		if strings.Contains(line, "function control_code(") {
			start = i
			break
		}
	}
	if start < 0 {
		return nil, false
	}
	// Find `case c of` after the header.
	caseStart := -1
	for i := start; i < len(lines); i++ {
		if strings.TrimSpace(lines[i]) == "case c of" || strings.HasSuffix(strings.TrimSpace(lines[i]), "case c of") {
			caseStart = i
			break
		}
	}
	if caseStart < 0 {
		return nil, false
	}
	// Walk until `endcases`. The tricky case is a compound branch like
	//     "*": begin print(...); control_code:=new_module; end;
	// where the LABEL and the ASSIGNMENT are on different lines. We
	// carry pending labels forward until we see the assignment.
	var entries []caseEntry
	var pending []string // user forms awaiting a control_code:=X; line
	finalize := func(forms []string, dstRaw string) {
		dstChar, dstIsLit := decodeDst(dstRaw)
		entries = append(entries, caseEntry{
			userForms: forms,
			dst:       dstChar,
			dstIsChar: dstIsLit,
		})
	}
	for i := caseStart + 1; i < len(lines); i++ {
		line := lines[i]
		trim := strings.TrimSpace(line)
		if strings.HasPrefix(trim, "endcases") || strings.HasPrefix(trim, "othercases") {
			break
		}
		// Case (A): we already have pending labels; look for the
		// assignment on this line (possibly inside a begin-end block).
		if pending != nil {
			if m := dstRe.FindStringSubmatch(trim); m != nil {
				finalize(pending, strings.TrimSpace(m[1]))
				pending = nil
				continue
			}
			// An `end;` closes a block without having written the
			// assignment — drop the pending labels; something
			// unusual (e.g. just `err_print` with no category).
			if strings.HasPrefix(trim, "end;") || trim == "end" {
				pending = nil
			}
			continue
		}
		// Case (B): a new case branch starts on this line.
		colon := findTopColon(line)
		if colon < 0 {
			continue
		}
		labelPart := line[:colon]
		rest := strings.TrimSpace(line[colon+1:])
		labels := splitCaseLabels(labelPart)
		if len(labels) == 0 {
			continue
		}
		var forms []string
		for _, lbl := range labels {
			ch, isIdent := decodeCaseLabel(lbl)
			if isIdent {
				forms = append(forms, userFormFromIdent(ch))
			} else {
				forms = append(forms, userFormFromChar(ch))
			}
		}
		// (B1) inline assignment
		if m := dstRe.FindStringSubmatch(rest); m != nil {
			finalize(forms, strings.TrimSpace(m[1]))
			continue
		}
		// (B2) compound block — defer until we find the assignment
		if strings.HasPrefix(rest, "begin") {
			pending = forms
			// Sometimes the same line already contains the
			// assignment after `begin`; try that too.
			if m := dstRe.FindStringSubmatch(strings.TrimPrefix(rest, "begin")); m != nil {
				finalize(pending, strings.TrimSpace(m[1]))
				pending = nil
			}
			continue
		}
	}
	return entries, true
}

// splitCaseLabels splits a Pascal case-label list on top-level commas,
// respecting "..." quoting (with "" as an escaped quote inside).
func splitCaseLabels(s string) []string {
	var out []string
	var cur strings.Builder
	inStr := false
	for i := 0; i < len(s); i++ {
		c := s[i]
		if c == '"' {
			cur.WriteByte(c)
			if inStr && i+1 < len(s) && s[i+1] == '"' {
				cur.WriteByte(s[i+1])
				i++
			} else {
				inStr = !inStr
			}
			continue
		}
		if c == ',' && !inStr {
			t := strings.TrimSpace(cur.String())
			if t != "" {
				out = append(out, t)
			}
			cur.Reset()
			continue
		}
		cur.WriteByte(c)
	}
	if t := strings.TrimSpace(cur.String()); t != "" {
		out = append(out, t)
	}
	return out
}

// decodeCaseLabel turns a raw case label into the character (or
// identifier) it stands for. "@@" denotes a single '@'; "" denotes a
// single '"' (two double-quotes inside the string).
func decodeCaseLabel(s string) (string, bool) {
	if len(s) >= 2 && s[0] == '"' && s[len(s)-1] == '"' {
		inner := s[1 : len(s)-1]
		inner = strings.ReplaceAll(inner, `""`, `"`)
		inner = strings.ReplaceAll(inner, `@@`, `@`)
		return inner, false
	}
	return s, true // identifier
}

func decodeDst(s string) (string, bool) {
	if len(s) >= 2 && s[0] == '"' && s[len(s)-1] == '"' {
		c, _ := decodeCaseLabel(s)
		return c, true
	}
	return s, false
}

// userFormFromChar maps the character following @ to the two-char WEB
// control code a programmer types.
func userFormFromChar(c string) string {
	switch c {
	case " ":
		return "@ "
	case "\t":
		return "@<TAB>"
	}
	return "@" + c
}

func userFormFromIdent(id string) string {
	switch id {
	case "tab_mark":
		return "@<TAB>"
	}
	return "@<" + id + ">"
}

// group collects every user form that dispatches to one destination
// token in the scanner's case table.
type group struct {
	dst       string
	dstIsChar bool
	forms     []string
}

// renderWebMode prints an EBNF-style grammar where each destination
// symbol becomes a production alternating over the user forms that map
// to it. The top-level `control_code` rule enumerates the destinations.
func renderWebMode(src string, tokens map[string]webToken, entries []caseEntry) string {
	var b strings.Builder

	fmt.Fprintf(&b, "(* WEB token inventory.\n")
	fmt.Fprintf(&b, "   Auto-extracted from %s (the `function control_code`\n", src)
	fmt.Fprintf(&b, "   case table and the `@d NAME=@'OCTAL` token-constant defs).\n")
	fmt.Fprintf(&b, "   Each production groups user forms that dispatch to one\n")
	fmt.Fprintf(&b, "   symbolic category; the opcode in the comment is Knuth's\n")
	fmt.Fprintf(&b, "   internal byte value, not part of the source syntax. *)\n\n")

	// Group entries by destination (preserving source order for stable
	// output; destinations appearing earlier in the case table first).
	seen := map[string]int{}
	var groups []*group

	for _, e := range entries {
		key := e.dst
		if e.dstIsChar {
			key = `char:` + key
		}
		idx, ok := seen[key]
		if !ok {
			idx = len(groups)
			seen[key] = idx
			groups = append(groups, &group{dst: e.dst, dstIsChar: e.dstIsChar})
		}
		groups[idx].forms = append(groups[idx].forms, e.userForms...)
	}

	// Per-category productions.
	maxName := 0
	for _, g := range groups {
		n := categoryName(g)
		if len(n) > maxName {
			maxName = len(n)
		}
	}
	for _, g := range groups {
		name := categoryName(g)
		pad := strings.Repeat(" ", maxName-len(name))
		fmt.Fprintf(&b, "%s%s = %s ;", name, pad, joinForms(g.forms))
		// Opcode + comment from the @d table, if available.
		if tok, ok := tokens[g.dst]; ok && !g.dstIsChar {
			fmt.Fprintf(&b, "  (* @'%s — %s *)", tok.octal, cleanTokenComment(tok.comment))
		} else if g.dstIsChar {
			fmt.Fprintf(&b, "  (* RHS is the literal char %q *)", g.dst)
		}
		b.WriteByte('\n')
	}

	// Top-level control_code production.
	b.WriteString("\ncontrol_code =\n")
	names := make([]string, len(groups))
	for i, g := range groups {
		names[i] = categoryName(g)
	}
	sort.Strings(names)
	for i, n := range names {
		sep := "    "
		if i > 0 {
			sep = "  | "
		}
		fmt.Fprintf(&b, "%s%s\n", sep, n)
	}
	b.WriteString("  ;\n")

	return b.String()
}

func categoryName(g *group) string {
	if g.dstIsChar {
		// Only case in practice is "@@" → '@', the quoted-at-sign.
		return "quoted_at"
	}
	return g.dst
}

func joinForms(forms []string) string {
	// Dedup while preserving order.
	seen := map[string]bool{}
	var uniq []string
	for _, f := range forms {
		if !seen[f] {
			seen[f] = true
			uniq = append(uniq, f)
		}
	}
	parts := make([]string, len(uniq))
	for i, f := range uniq {
		parts[i] = quoteCode(f)
	}
	return strings.Join(parts, " | ")
}

func cleanTokenComment(s string) string {
	// The "control code for `\.{@@X}'" style; strip the TeX wrapper so
	// the output reads as plain text. `\char'174` is webmac's encoding
	// of `|` (the pipe is normally active) and must be collapsed before
	// the apostrophe and backslash are stripped.
	s = strings.ReplaceAll(s, `\char'174`, "|")
	s = strings.ReplaceAll(s, `\.{`, "")
	s = strings.ReplaceAll(s, `\ `, " ")
	s = strings.ReplaceAll(s, "}", "")
	s = strings.ReplaceAll(s, "`", "")
	s = strings.ReplaceAll(s, "'", "")
	s = strings.ReplaceAll(s, `\`, "")
	s = strings.Join(strings.Fields(s), " ")
	return s
}

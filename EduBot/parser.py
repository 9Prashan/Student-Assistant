"""
parser.py
---------
Parses raw bot/content responses into clean, Streamlit-renderable parts.
 
Two responsibilities:
  1. parse_bot_response()   — splits the [SOLUTION_CHECKER / PROGRESS_TRACKER / MENTOR]
                              block into structured sections and cleans up the MENTOR text.
  2. parse_content()        — converts the raw DSL used in problems/solutions
                              (string(...), latex(...), evaluation_expression(...), etc.)
                              into plain text with proper LaTeX delimiters that
                              st.markdown / st.latex can render via KaTeX/MathJax.
"""
 
import re
 
 
# ---------------------------------------------------------------------------
# 1.  BOT RESPONSE PARSER
# ---------------------------------------------------------------------------
 
def parse_bot_response(raw: str) -> dict:
    """
    Parse a raw bot response into a dict with keys:
        solution_checker  : str | None
        progress_tracker  : str | None
        mentor            : str          (always present)
        is_conclude       : bool
        raw               : str          (original)
 
    The bot uses a format like:
        [
        SOLUTION_CHECKER: <none / some text>,
        PROGRESS_TRACKER: <none / some text>,
        MENTOR: <message>
        ]
    """
    result = {
        "solution_checker": None,
        "progress_tracker": None,
        "mentor": raw.strip(),
        "is_conclude": "@conclude" in raw,
        "raw": raw,
    }
 
    # Strip outer brackets if present
    cleaned = raw.strip()
    if cleaned.startswith("["):
        cleaned = cleaned[1:]
    if cleaned.endswith("]"):
        cleaned = cleaned[:-1]
 
    # Extract each section with a flexible regex
    sc_match = re.search(
        r"SOLUTION_CHECKER\s*:\s*(.*?)(?=PROGRESS_TRACKER|MENTOR|$)",
        cleaned, re.DOTALL | re.IGNORECASE
    )
    pt_match = re.search(
        r"PROGRESS_TRACKER\s*:\s*(.*?)(?=MENTOR|$)",
        cleaned, re.DOTALL | re.IGNORECASE
    )
    mentor_match = re.search(
        r"MENTOR\s*:\s*(.*)",
        cleaned, re.DOTALL | re.IGNORECASE
    )
 
    if sc_match:
        val = sc_match.group(1).strip().rstrip(",")
        result["solution_checker"] = None if val.lower() in ("none", "<none>", "") else val
 
    if pt_match:
        val = pt_match.group(1).strip().rstrip(",")
        result["progress_tracker"] = None if val.lower() in ("none", "<none>", "") else val
 
    if mentor_match:
        mentor_text = mentor_match.group(1).strip()
        # Clean trailing bracket that may appear
        mentor_text = mentor_text.rstrip("]").strip()
        result["mentor"] = mentor_text
 
    return result
 
 
# ---------------------------------------------------------------------------
# 2.  CONTENT / PROBLEM-SOLUTION DSL PARSER
# ---------------------------------------------------------------------------
 
def parse_content(raw: str) -> str:
    """
    Convert the raw DSL format used in problems & solutions into clean
    Markdown + LaTeX that Streamlit can render.
 
    Handles:
      - string(...)               → plain text line
      - latex(...)                → inline $...$
      - evaluation_expression(...)→ structured lhs = rhs block
      - objective_answer_types(...)→ MCQ options list
      - Bare LaTeX inside already-parsed text
      - Cleans up excess brackets, escaping artefacts
    """
 
    # If there is no DSL, just clean up LaTeX escaping and return
    if "string(" not in raw and "latex(" not in raw:
        return _clean_latex_escapes(raw)
 
    lines = []
 
    # ---- Step 1: extract all string(...) blocks in order ----
    # We iterate through the content pulling out top-level DSL tokens
    tokens = _tokenize(raw)
 
    for token_type, token_value in tokens:
        if token_type == "string":
            line = _process_inline_latex(token_value)
            if line.strip():
                lines.append(line.strip())
 
        elif token_type == "latex":
            # Standalone latex block (outside a string)
            lines.append(f"$${_clean_latex_escapes(token_value)}$$")
 
        elif token_type == "evaluation_expression":
            lines.append(_parse_evaluation_expression(token_value))
 
        elif token_type == "objective_answer_types":
            lines.append(_parse_objective_answer_types(token_value))
 
        elif token_type == "text":
            text = token_value.strip().strip(",[]")
            if text:
                lines.append(_process_inline_latex(text))
 
    result = "\n\n".join(l for l in lines if l.strip())
    return result if result else _clean_latex_escapes(raw)
 
 
# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
 
def _tokenize(text: str):
    """
    Walk through `text` and yield (type, content) tuples for each DSL token.
    Handles nested parentheses correctly.
    """
    i = 0
    buf = []
    known_tokens = [
        "string", "latex", "evaluation_expression",
        "objective_answer_types", "type", "continuous",
    ]
 
    while i < len(text):
        # Check if we're at the start of a known token
        matched_token = None
        for tok in known_tokens:
            if text[i:].startswith(tok + "("):
                matched_token = tok
                break
 
        if matched_token:
            # Flush buffer
            if buf:
                yield ("text", "".join(buf))
                buf = []
 
            # Find the matching closing paren
            start = i + len(matched_token) + 1  # skip "token("
            depth = 1
            j = start
            while j < len(text) and depth > 0:
                if text[j] == "(":
                    depth += 1
                elif text[j] == ")":
                    depth -= 1
                j += 1
            inner = text[start: j - 1]
 
            if matched_token in ("string", "continuous"):
                yield ("string", inner)
            elif matched_token == "latex":
                yield ("latex", inner)
            elif matched_token == "evaluation_expression":
                yield ("evaluation_expression", inner)
            elif matched_token == "objective_answer_types":
                yield ("objective_answer_types", inner)
            # skip "type(" wrapper — its content will be re-tokenized by caller
            i = j
        else:
            buf.append(text[i])
            i += 1
 
    if buf:
        yield ("text", "".join(buf))
 
 
def _process_inline_latex(text: str) -> str:
    """
    Replace latex(...) occurrences inside a string with $...$ inline math.
    """
    def replacer(m):
        inner = m.group(1)
        inner = _clean_latex_escapes(inner)
        return f"${inner}$"
 
    # Match latex(...) with nested parens support
    result = _replace_token(text, "latex", replacer)
    return result
 
 
def _replace_token(text: str, token: str, replacer) -> str:
    """Replace all occurrences of token(...) in text using replacer(match)."""
    out = []
    i = 0
    search = token + "("
    while i < len(text):
        idx = text.find(search, i)
        if idx == -1:
            out.append(text[i:])
            break
        out.append(text[i:idx])
        # Find matching paren
        start = idx + len(search)
        depth = 1
        j = start
        while j < len(text) and depth > 0:
            if text[j] == "(":
                depth += 1
            elif text[j] == ")":
                depth -= 1
            j += 1
        inner = text[start: j - 1]
 
        class _FakeMatch:
            def group(self, n):
                return inner
 
        out.append(replacer(_FakeMatch()))
        i = j
    return "".join(out)
 
 
def _clean_latex_escapes(text: str) -> str:
    """
    Normalise escape sequences that come from the raw DSL.
    \\\\times  →  \\times   (the DSL double-escapes backslashes)
    """
    # Replace quadruple backslash with single (common in the DSL)
    text = text.replace("\\\\\\\\", "\\")
    # Replace double backslash with single
    text = text.replace("\\\\", "\\")
    return text
 
 
def _parse_evaluation_expression(inner: str) -> str:
    """
    Convert evaluation_expression(lhs([...]), rhs([...])) into a
    display-math block:   lhs = rhs
    """
    lhs_parts = []
    rhs_parts = []
 
    lhs_match = re.search(r"lhs\((\[.*?\])\)", inner, re.DOTALL)
    rhs_match = re.search(r"rhs\((\[.*?\])\)", inner, re.DOTALL)
 
    if lhs_match:
        lhs_parts = _extract_string_values(lhs_match.group(1))
    if rhs_match:
        rhs_parts = _extract_string_values(rhs_match.group(1))
 
    lhs_text = " ".join(_process_inline_latex(p) for p in lhs_parts if p.strip())
    rhs_text = " ".join(_process_inline_latex(p) for p in rhs_parts if p.strip())
 
    if lhs_text and rhs_text:
        return f"{lhs_text} $=$ {rhs_text}"
    return f"{lhs_text}{rhs_text}"
 
 
def _parse_objective_answer_types(inner: str) -> str:
    """Convert MCQ options into a markdown list."""
    lines = ["**Choose the correct answer:**\n"]
    # Find string(...) values - they alternate label / description
    values = _extract_string_values(inner)
    i = 0
    while i < len(values):
        label = values[i].strip() if i < len(values) else ""
        desc = values[i + 1].strip() if i + 1 < len(values) else ""
        if label:
            desc_rendered = _process_inline_latex(desc)
            lines.append(f"- **({label})** {desc_rendered}")
        i += 2
    return "\n".join(lines)
 
 
def _extract_string_values(text: str) -> list:
    """Pull out the text inside all string(...) tokens in `text`."""
    values = []
    for _, val in _tokenize(text):
        if val.strip():
            # Strip any latex wrappers for plain text extraction
            clean = re.sub(r"latex\([^)]*\)", "", val).strip()
            if clean:
                values.append(val)  # keep original for latex processing
    return values
 
 
# ---------------------------------------------------------------------------
# 3.  RENDER HELPERS  (called from app.py)
# ---------------------------------------------------------------------------
 
def render_mentor_message(mentor_text: str) -> str:
    """
    Final pass on the mentor message:
    - Process any inline latex(...) wrappers
    - Clean escape sequences
    - Handle @conclude tag
    """
    text = mentor_text
    # Strip @conclude marker from display
    text = re.sub(r"@conclude\s*:?\s*<?>?", "", text).strip()
    text = _process_inline_latex(text)
    text = _clean_latex_escapes(text)
    return text
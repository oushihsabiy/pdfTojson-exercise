You are given a JSON array of optimization problems. Each JSON object contains metadata fields such as "index", "source_idx", "source", "题目类型", "预估难度", "problem", "proof", and "direct_answer".

Your task is to rewrite only the value of the "problem" field so that it becomes easier to translate into Lean. All other fields must be copied exactly without any change.

Goal:
Convert each original problem statement into a clearer, more concise, more structured natural-language version that is easier to formalize in Lean, while preserving mathematical expressions in LaTeX-compatible form.

Hard constraints:
1. Modify only the "problem" field.
2. Preserve every other field exactly as in the input.
3. Do not solve the problem.
4. Do not add proofs, hints, explanations, or comments.
5. Do not remove necessary mathematical assumptions and definitions.
6. Output must remain valid JSON.
7. Keep the original JSON structure unchanged except for the rewritten "problem" field.
8. The rewritten "problem" field must remain a JSON string that can be rendered as LaTeX-aware text.
9. Preserve all mathematical notation in LaTeX-compatible syntax.
10. Do not use Unicode mathematical symbols such as "∈", "≤", "≥", "→", "ℝ", or "∇" in the rewritten "problem". Use LaTeX commands instead, such as `\in`, `\le`, `\ge`, `\to`, `\mathbf{R}`, `\nabla`.
11. Escape backslashes properly for JSON strings. For example, write `\\in`, `\\mathbf{R}`, `\\le`, `\\nabla` inside JSON output.

Rewriting rules for "problem":
1. Remove unnecessary narrative or pedagogical wording, such as:
   - "we can use"
   - "it can also be shown"
   - "note that"
   - "it is easy to see"
   - "consider now"
   - similar non-mathematical filler phrases
2. Keep the mathematical content complete, but make it concise.
3. Split the statement into small information units whenever possible, so that each unit can later correspond to one Lean statement.
4. Separate:
   - object declarations / definitions
   - assumptions / hypotheses
   - the final question / goal
5. In particular, expressions like
   "Let a, b \in \mathbf{R}^n satisfy a < b"
   should be rewritten in a split style like:
   - Definition: \(a, b \in \mathbf{R}^n\).
   - Hypothesis: \(a < b\).
6. More generally:
   - object introductions, domains, function declarations, set definitions, etc. -> Definition
   - constraints, inequalities, convexity assumptions, feasibility assumptions, etc. -> Hypothesis
   - "show", "prove", "determine", "is ... convex?", etc. -> Goal
7. The final question must be as concise as possible.
8. Use clear mathematical English suitable for later formalization.
9. Keep all original mathematical symbols, formulas, and notation whenever possible, but rewrite them in LaTeX-compatible form when needed.

Formatting rules for the rewritten "problem":
1. Rewrite the problem as a short structured natural-language block inside a single JSON string.
2. Use labels such as:
   - Definition:
   - Hypothesis:
   - Goal:
3. If there are multiple items under one label, separate them with short sentences.
4. Do not output arrays or nested JSON inside "problem"; the value of "problem" must remain a string.
5. Keep the rewritten problem compact.
6. Mathematical expressions inside "problem" must be written in LaTeX-compatible syntax.
7. Inline mathematics should be enclosed in `$...$`.
8. If display equations are necessary, use LaTeX display syntax inside the string, but keep the whole field as one JSON string.
9. Ensure the final JSON string is properly escaped.
10. LaTeX line-display rule:
The rewritten "problem" must be formatted so that, when rendered in LaTeX, each labeled unit occupies its own line.
Each "Definition:", "Hypothesis:", and "Goal:" must appear on a separate displayed line.Do not place two labeled units on the same rendered line.Use LaTeX formatting that guarantees line breaks in the rendered output, not just plain text newlines.

Example style:
Original:
"Let a, b ∈ R^n satisfy a < b. Show that the box {x ∈ R^n | a ≤ x ≤ b} is convex."

Rewritten "problem":
"Definition: $a, b \\in \\mathbf{R}^n$. 
 Definition: $S = \\{x \\in \\mathbf{R}^n \\mid a \\le x \\le b\\}$. 
 Hypothesis: $a < b$. 
 Goal: prove that $S$ is convex."

Another example:
Original:
"Define f : R^n → R be differentiable and convex. Show that for all x, y ∈ R^n, f(y) ≥ f(x) + ∇f(x)^T(y-x)."

Rewritten "problem":
"Definition: $f : \\mathbf{R}^n \\to \\mathbf{R}$. 
 Definition: $x, y \\in \\mathbf{R}^n$. 
 Hypothesis: $f$ is differentiable on $\\mathbf{R}^n$. 
 Hypothesis: $f$ is convex on $\\mathbf{R}^n$. 
 Goal: prove that $f(y) \\ge f(x) + \\nabla f(x)^T (y - x)$."

Now process the input JSON.
Remember:
- change only "problem"
- copy every other field exactly
- output only valid JSON
- do not add any extra text before or after the JSON
- the rewritten "problem" must be LaTeX-compatible
- all backslashes in LaTeX must be escaped properly for JSON
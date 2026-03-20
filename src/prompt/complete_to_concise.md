You are given a JSON array of optimization problems. Each JSON object contains metadata fields such as "index", "source_idx", "source", "题目类型", "预估难度", "problem", "proof", and "direct_answer".

Your task is to rewrite only the value of the "problem" field so that it becomes clearer, more concise, and easier to translate into Lean. All other fields must be copied exactly without any change.

Goal:
Convert each original problem statement into a clearer, more concise, more structured natural-language version that is easier to formalize in Lean, while preserving the original mathematical meaning and LaTeX-compatible notation.

Hard constraints:
1. Modify only the "problem" field.
2. Preserve every other field exactly as in the input.
3. Do not solve the problem.
4. Do not add proofs, hints, explanations, or comments.
5. Do not remove necessary mathematical assumptions, definitions, or constraints.
6. Output must remain valid JSON.
7. Keep the original JSON structure unchanged except for the rewritten "problem" field.
8. The rewritten "problem" field must remain a JSON string that can be rendered as LaTeX-aware text.
9. Preserve all mathematical notation in LaTeX-compatible syntax.
10. Do not use Unicode mathematical symbols such as "∈", "≤", "≥", "→", "ℝ", or "∇" in the rewritten "problem". Use LaTeX commands instead, such as `\in`, `\le`, `\ge`, `\to`, `\mathbf{R}`, `\nabla`.
11. Escape backslashes properly for JSON strings. For example, write `\\in`, `\\mathbf{R}`, `\\le`, `\\nabla` inside JSON output.

Rewriting rules for "problem":
1. Rewrite the original problem into standard, concise mathematical English.
2. Remove unnecessary narrative or pedagogical wording, such as:
   - "we can use"
   - "it can also be shown"
   - "note that"
   - "it is easy to see"
   - "consider now"
   - similar non-mathematical filler phrases
3. Keep the mathematical content complete, but make it concise.
4. Make the logical structure explicit and easy to formalize.
5. Preserve all mathematical objects, assumptions, and goals.
6. Prefer short and direct mathematical phrasing.
7. Use standard optimization-style language.
8. Keep all original formulas and notation whenever possible, but rewrite them in LaTeX-compatible form when needed.
9. Do not yet convert the statement into labeled lines such as "Definition:", "Hypothesis:", or "Goal:".
10. Produce a single coherent natural-language mathematical problem statement.

Formatting rules:
1. The rewritten "problem" must remain a single JSON string.
2. Inline mathematics should be enclosed in `$...$`.
3. Display equations may be used if necessary, but keep the whole field as one string.
4. Ensure the final JSON is valid and properly escaped.
5. Do not output arrays or nested JSON inside the "problem" field.

Example style:
Original:
"Let a, b ∈ R^n satisfy a < b. Show that the box {x ∈ R^n | a ≤ x ≤ b} is convex."

Rewritten "problem":
"Let $a, b \\in \\mathbf{R}^n$ with $a < b$. Define
\\[
S = \\{x \\in \\mathbf{R}^n \\mid a \\le x \\le b\\}.
\\]
Prove that $S$ is convex."

Now process the input JSON.
Remember:
- change only "problem"
- copy every other field exactly
- output only valid JSON
- do not add any extra text before or after the JSON
- all backslashes in LaTeX must be escaped properly for JSON